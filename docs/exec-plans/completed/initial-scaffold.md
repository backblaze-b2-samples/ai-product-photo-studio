# Scaffold plan — `ai-product-photo-studio`

Source of truth for the delta: a freshly-cloned `vibe-coding-starter-kit`.
Parent standards: the program-root `CLAUDE.md` (S3-only default, custom UA,
standardized `B2_*` names). This plan was the contract for the initial scaffold
and is retained here as the completed exec-plan of record.

## Headless defaults (open questions resolved)
- **Single-seller v1** — no multi-tenant auth/tenancy. SKUs are the only namespace.
- **No background-removal sidecar** — out of scope for v1. (Genblaze ships a
  `ModerationHook` seam we note but do not wire.)

---

## 1. Purpose
`ai-product-photo-studio` is a B2-backed sample for e-commerce sellers (Shopify/Etsy):
upload one product photo, describe a scene, and generate studio-quality **lifestyle
shots, multiple angles, and seasonal variants** — with a per-SKU history that
accumulates. It demonstrates the storage curve B2 is priced for (a reference library
+ many generations per SKU pile up fast) and shows generative-media provenance
(every generated asset carries a SHA-256 manifest). Image generation is routed through
the **Genblaze SDK** (`Pipeline -> DalleProvider (gpt-image-1 edits) -> ObjectStorageSink`),
so a full demo exercises both the published Genblaze wheels and B2 as the durable store.

This is the **core capability** of the app (per `api-provider-selection.md` Step 1):
the image provider MUST be really wired — real calls, real artifacts to B2 — not simulated.

---

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling. Keep its reusable B2 surface + scaffolding; strip
what a product-photo app doesn't need; add the studio/generation surface.

### KEEP (as-is)
- **UI kit** — `apps/web/src/components/ui/**`, design tokens in `globals.css`, the
  `/design` page + `components/design/**`.
- **Layered FastAPI backend skeleton** — `app/types`, `app/config`, `app/repo/b2_client.py`
  (boto3, S3-compatible, **custom UA kept**), `app/service`, `app/runtime`; structural
  tests; JSON logging; `/health`; `/metrics`; request-id timing middleware.
- **Bucket explorer (NON-NEGOTIABLE KEEP)** — `/files` page + `components/files/**`
  (`file-browser`, `file-preview`, `file-metadata-panel`): full-bucket browse, preview,
  download, delete.
- **Upload flow** — `/upload` + `components/upload/**` (dropzone, progress). Reused as
  the **reference-photo upload** path.
- **Data layer** — TanStack Query (`lib/queries.ts`, `query-client.tsx`, `api-client.ts`),
  `refresh-context`, `health-banner`, `command-palette`, `theme-provider`, sidebar/header.
- **Tooling** — `scripts/doctor.mjs` preflight, `scripts/dev.sh`, `pick-port.mjs`,
  pnpm-workspace monorepo, settings page + danger-zone (delete scoped to a prefix),
  metadata-extraction service (image dims/EXIF — useful for reference photos).

### TRIM (remove/narrow from starter)
- **Upload allow-list** — narrow `ALLOWED_TYPES`/`MIME_EXTENSION_MAP` in
  `app/service/upload.py` to image inputs (`image/jpeg`, `image/png`, `image/webp`).
  Drop pdf/csv/json/zip/mp4/audio/gif/svg. Update any affected upload test fixtures.
- **PDF/audio metadata branches** — trim `service/metadata.py` + `types/files.py` fields
  that only serve PDF/audio (keep image dims/EXIF, md5/sha256). Drop `PyPDF2` from
  requirements if nothing else needs it.
- **Starter marketing/README copy** — "Use this template", "vibe coders", template
  reinit instructions: rewrite for the product (see section 5).
- **Starter exec-plans** — delete `docs/exec-plans/completed/2026-02-*.md`; keep
  `tech-debt-tracker.md` as an empty-ish stub. This plan lands in `completed/` at finalize.
- **Default public SVGs** — `vercel.svg`, `next.svg` (cosmetic).

### ADD (new for ai-product-photo-studio)
Backend (layered, Genblaze imports confined to `repo/`):
- `app/repo/studio_pipeline.py` — the Genblaze pipeline (see section 4 snippet). Confines
  `genblaze_*` imports to `repo/`, mirroring the boto3 rule.
- `app/service/studio.py` — orchestrates a generate request: validates SKU + prompt,
  resolves the reference photo's B2 URL, calls the repo pipeline, maps results.
- `app/types/studio.py` — `Sku`, `GenerationRequest` (scene prompt, variants, angle/season
  presets, size, quality), `GeneratedShot` (key, url, sha256, manifest_uri, params),
  `SkuProject` (reference + shots).
- `app/runtime/studio.py` (built as `runtime/skus.py`) — router: `POST /skus/{sku}/generate`,
  `GET /skus`, `GET /skus/{sku}` (per-SKU reference + generations), `GET /skus/{sku}/shots`.
- Structural test addition: assert `genblaze_*` (and `boto3`) imported only under `app/repo/`.

Frontend:
- `/studio` (or `/generate`) page — pick/upload a product photo, write a scene prompt,
  choose variant presets (angles, seasonal) + count + quality, run generation, watch
  progress (reuse the `generating-loader`), see results.
- **Sample-specific asset explorer (NON-NEGOTIABLE ADD)** — `/library` (per-SKU):
  scoped to the `skus/<sku>/` prefix, shows the reference photo + every generated shot
  & variant for that SKU with provenance (sha256 / manifest). Distinct from the
  full-bucket `/files` explorer, which stays.
- **Re-themed Dashboard (`/`)** — stat cards = # SKUs, # generated shots, total storage,
  generations today; "recent generations" table; a storage-growth chart that tells the
  B2 storage-curve story (replaces the generic upload-activity framing).
- Sidebar nav: add **Studio** and **Library**; keep **Files** (bucket explorer),
  **Upload**, **Settings**, **Design System**.

---

## 3. B2 surface (S3 operations)
All via the **S3-compatible API** (parent standard #1) — no b2-native calls.
- `PutObject` — reference photos (existing upload path); Genblaze sink writes generated
  images + provenance manifests.
- `GetObject` / presigned GET — preview/download references & generated shots.
- `ListObjectsV2` — full-bucket explorer, per-SKU prefix listing, dashboard stats pagination.
- `HeadObject` — metadata; `HeadBucket` — `/health`.
- `DeleteObject` — delete files / SKU assets (settings danger-zone + per-SKU delete),
  **scoped to the app's `skus/`/`uploads/` prefixes** (never wipe shared bucket data).

**Object layout**
```
uploads/<sku>/reference/<filename>               # user-uploaded product photo
skus/<sku>/generations/<run_id>/<variant>.png    # generated shots (Genblaze sink, HIERARCHICAL)
skus/<sku>/generations/<run_id>/manifest.json    # SHA-256 provenance manifest
```

**Justified deviation (parent standard #2 — custom UA on every S3 client):**
the boto3 client in `repo/b2_client.py` keeps `user_agent_extra` (custom UA). The
**Genblaze `genblaze-s3` backend** manages its own S3 client and the UA is delegated to
the library — this is the documented Genblaze UA-delegation exception already encoded in
the `/b2-doctor` skill (check #2). No b2-native usage anywhere.

---

## 4. Key features + provider/orchestration

Feature bullets (seed README + `docs/features/*` stubs):
1. **Reference-driven product photo generation** — upload a product photo + scene prompt
   -> studio lifestyle shot (gpt-image-1 edit, reference-faithful).
2. **Multiple angles & seasonal variants** — one request fans out to N variants in parallel.
3. **Per-SKU library** — reference + all generations for a SKU, scoped explorer.
4. **Provenance on every shot** — SHA-256 manifest per generated asset (Genblaze).
5. **Full-bucket explorer + dashboard** — browse the whole bucket; storage-curve metrics.

### External API provider (per `api-provider-selection.md`)
- **Classification:** CORE (the app exists to generate photos) -> must be really wired.
- **Provider/model:** OpenAI **`gpt-image-1`** via **`genblaze-openai` `DalleProvider`**.
  Chosen because reference-image *editing* is the whole point and gpt-image-1 is the most
  reliable reference-faithful path; `genblaze-openai` exposes it with `+ edits` and
  `supports_input_fidelity=True`. (Priority order in the doc: free-tier -> Anthropic
  (no image gen) -> **OpenAI** -> Replicate.)
- **Deployment:** remote.
- **Env var:** `OPENAI_API_KEY` (provider default; placeholder in `.env.example`).
- **Cost (flagged for transparency — core API):** OpenAI has no free tier. At the app
  defaults (`quality="medium"`, `size="1024x1024"`, 3 variants/request) a generate is
  ~3 x $0.07 ~= **$0.21**; a full 3-SKU walkthrough ~= **$0.85** — **under $1**. Raising
  quality to `high` (~$0.19/img) or generating more variants pushes a full run **over $1**;
  surfaced here per the doc's core-API cost rule. Defaults are NOT a downgrade-to-fit —
  gpt-image-1 stays the model; only the quality/variant knobs default conservatively.

### Provider orchestration via Genblaze (REQUIRED — stack names Genblaze)
Route ALL provider calls through the Genblaze SDK; keep `genblaze_*` imports inside
`services/api/app/repo/`. Packages: add `genblaze-core`, `genblaze-openai`, `genblaze-s3`
to `requirements.txt`/`pyproject.toml`.

`gpt-image-1` routing fact (from `genblaze_openai/dalle.py`): **step inputs present ->
`/images/edits`; no inputs -> `/images/generations`.** So the user's reference photo is
fed as a step **input** to trigger reference-faithful editing.

> **API-shape confirmation (resolved during build against installed wheels):** the
> published `genblaze-core 0.3.2` has **no** `Pipeline.ingest_step(...)` instance method —
> the correct mechanism to attach a caller-held reference asset to an edit step is
> `external_inputs=[Asset(...)]` on `.step()` (mutually exclusive with `input_from`).
> `input_fidelity` is a valid advisory kwarg for `gpt-image-1`; `quality ∈ {low,medium,high}`;
> `size ∈ {1024x1024,1536x1024,1024x1536,auto}`. **`max_concurrency` is a `Pipeline(...)`
> constructor kwarg, NOT a `run()` kwarg** (a `run(..., max_concurrency=...)` call raises
> `TypeError` on 0.3.2 — fixed in round 2; guarded by `tests/test_pipeline_signatures.py`,
> a no-network signature regression test). Smoke-test of the three imports passed; resolved
> versions: genblaze-core 0.3.2, genblaze-openai 0.3.0, genblaze-s3 0.3.2.

Handlers import only from `app.repo`/`app.service` — never `genblaze_*` directly.
Map Genblaze `Run`/`Asset`/manifest fields into `types/studio.py`.

---

## 5. Doc transforms
- **Rewrite:** `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `docs/app-workflows.md`,
  `docs/features/{dashboard,file-upload,metadata-extraction}.md`.
- **Delete:** `docs/exec-plans/completed/2026-02-*.md` (starter history).
- **Stub new:** `docs/features/{product-photo-generation,per-sku-library,provenance-manifest}.md`.

---

## 6. Rename table
| Identifier (starter) | -> ai-product-photo-studio |
|---|---|
| kebab `vibe-coding-starter-kit` | `ai-product-photo-studio` |
| snake `vibe_coding_starter_kit` | `ai_product_photo_studio` |
| display "Vibe Coding Starter Kit" / "OSS Starter Kit" | "AI Product Photo Studio" |
| npm scope `@vibe-coding-starter-kit/web` | `@ai-product-photo-studio/web` |
| FastAPI `title` / `APP_NAME` | "AI Product Photo Studio" |
| Genblaze `Pipeline(name=...)` slug | `ai-product-photo-studio` (provenance) |
| boto3 `user_agent_extra` / UTM `utm_content` | `b2ai-product-photo-studio` |

**Env-var standardization (parent standard #3):** rename the starter's
`B2_KEY_ID`/`B2_ENDPOINT`/`b2_public_url` to the standard set everywhere:
`B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`,
`B2_PUBLIC_URL_BASE`; derive the S3 endpoint from region
(`https://s3.{B2_REGION}.backblazeb2.com`); feed these explicitly into BOTH the boto3
client and `S3StorageBackend.for_backblaze(...)`. `OPENAI_API_KEY` is separate.

---

## Outcome (as built + reviewed)
- Build committed from the freshly-cloned starter; Genblaze wheels smoke-tested.
- Round-1 review found one `❌` (`max_concurrency` passed to `run()` — rejected by 0.3.2)
  + one `⚠️` (undocumented `NEXT_PUBLIC_API_URL`).
- Round-2 fix: moved `max_concurrency` to the `Pipeline()` constructor, corrected the
  feature doc, added `tests/test_pipeline_signatures.py` (no-network signature guard),
  documented `NEXT_PUBLIC_API_URL`.
- Round-2 review: **CLEAN** — both `❌` and the `⚠️` resolved, no regressions; 31 backend
  tests pass, ruff clean, structural tests (layering / boto3-in-repo / genblaze-in-repo /
  file-size) pass.
