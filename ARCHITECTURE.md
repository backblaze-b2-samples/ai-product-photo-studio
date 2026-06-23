<!-- last_verified: 2026-06-23 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Studio (`/studio`) — reference upload, scene prompt, presets, generation
  - Per-SKU Library (`/library`) — scoped explorer for one SKU's assets
  - File browser (`/files`) — full-bucket browse/preview/download/delete
  - Upload (`/upload`) — drag-and-drop reference-photo upload
  - Dashboard (`/`) — SKU/shot stats and the storage-growth curve
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for generation, per-SKU listing, upload, file management
  - **Genblaze image pipeline** (`repo/studio_pipeline.py`) — gpt-image-1 edits → B2
  - B2 S3 integration via boto3 (`repo/b2_client.py`)
  - Image metadata extraction (dimensions, EXIF, checksums)
  - Health, metrics, structured JSON logging with request tracing
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Backend Layering

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access — boto3 B2 client AND the Genblaze pipeline
  |
service/   Business logic — calls repo, returns typed models / plain dicts
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types -> config -> repo -> service -> runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. **`genblaze_*` only allowed in `repo/` layer** (specifically `repo/studio_pipeline.py`)
5. All boundary data uses Pydantic models / plain dicts (no SDK types across layers)
6. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (studio.py, files.py, stats.py, upload.py)
    config/                Settings loaded from environment (B2_* + OPENAI_API_KEY)
    repo/                  b2_client.py (boto3) + studio_pipeline.py (Genblaze)
    service/               Business logic (studio, upload, files, metadata)
    runtime/               FastAPI route handlers (skus, upload, files, health, metrics)
  tests/                   pytest tests (structural + integration)
```

## The Genblaze pipeline layer

`repo/studio_pipeline.py` is the only module that imports `genblaze_core`,
`genblaze_openai`, or `genblaze_s3`. It builds and runs the image pipeline:

```
Pipeline("ai-product-photo-studio", project_id=<sku>)
  .step(DalleProvider(api_key=OPENAI_API_KEY),
        model="gpt-image-1", modality=IMAGE,
        prompt=<variant prompt>,
        external_inputs=[Asset(url=<presigned reference>, sha256=…)],  # → /images/edits
        size=…, quality=…, input_fidelity="high")   # repeated per variant
  .run(sink=ObjectStorageSink(
          S3StorageBackend.for_backblaze(bucket, region=…, key_id=…,
                                         app_key=…, public_url_base=…),
          prefix="skus/<sku>/generations",
          key_strategy=HIERARCHICAL),
       max_concurrency=N, raise_on_failure=False)
```

- **Routing**: `external_inputs` makes `Step.inputs` non-empty, which routes
  gpt-image-1 to `/images/edits` (reference-faithful editing) rather than
  `/images/generations`. The reference's sha256 is computed up front so the
  step cache key and the manifest's canonical hash stay stable across reruns.
- **Output mapping**: after `run()`, `result.run.steps` carry the durable B2
  asset URLs and `result.manifest` carries the SHA-256 manifest URI + canonical
  hash. The repo maps these into plain dicts; the service builds typed
  `GeneratedShot` / `GenerationResult` models. No Genblaze type escapes `repo/`.

## B2 surface (all via the S3-compatible API)

- `PutObject` — reference photos (upload path); Genblaze sink writes shots + manifests
- `GetObject` / presigned GET — preview/download; presigned reference URL fed to the provider
- `ListObjectsV2` — full-bucket explorer, per-SKU prefix listing, dashboard stats
- `HeadObject` — metadata; `HeadBucket` — `/health`
- `DeleteObject` — delete files / SKU assets, scoped to `skus/` / `uploads/` prefixes

Two S3 clients exist: the app's boto3 client in `repo/b2_client.py` (custom
`user_agent_extra="b2ai-product-photo-studio"`), and the boto3 client owned
internally by `genblaze-s3`'s `S3StorageBackend` — the latter stamps its own
identifying user agent, which is the documented Genblaze UA-delegation pattern.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently` (web :3000, API :8000)
- **Railway** — two services from the same repo; see `infra/railway/README.md`

## Data Stores

- **Backblaze B2** — object storage (S3-compatible). No application database;
  SKU state is derived by listing the `uploads/` and `skus/` prefixes.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md).

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4 (endpoint derived from `B2_REGION`)
- **API -> OpenAI** — `OPENAI_API_KEY`, separate from B2 credentials
- **Client -> B2** — presigned URLs for download/preview (short expiry, forced attachment)

## Data Flows

- **Generate**: Browser -> `POST /skus/{sku}/generate` -> service validates SKU/prompt,
  presigns the reference -> repo runs the Genblaze pipeline (gpt-image-1 edits) ->
  sink writes shots + manifest to B2 -> typed result returned
- **Library**: Browser -> `GET /skus` / `GET /skus/{sku}` -> service lists the SKU prefixes
- **Upload**: Browser -> `POST /upload` (multipart, optional `sku`) -> validate -> repo writes to B2
- **List/Download/Delete**: full-bucket explorer over `GET /files…`, presigned download, prefix-scoped delete

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware; `/metrics` (Prometheus); `/health` (B2 connectivity)

## Canonical Files

- Genblaze pipeline (repo layer): `services/api/app/repo/studio_pipeline.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Studio orchestration: `services/api/app/service/studio.py`
- Studio routes: `services/api/app/runtime/skus.py`
- Pydantic models: `services/api/app/types/` (`studio.py`, `files.py`, `stats.py`, `upload.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Product Photo Generation](docs/features/product-photo-generation.md)
- [Per-SKU Library](docs/features/per-sku-library.md)
- [Provenance Manifest](docs/features/provenance-manifest.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
