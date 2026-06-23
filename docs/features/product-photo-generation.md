<!-- last_verified: 2026-06-23 -->
# Feature: Product Photo Generation

## Purpose
Turn one uploaded product photo plus a scene prompt into N reference-faithful
studio shots (angles / seasonal variants) using OpenAI gpt-image-1, orchestrated
through the Genblaze SDK and written to Backblaze B2 — this is the app's core capability.

## Used By
- UI: `/studio` page (`components/studio/studio-form.tsx`, `shot-grid.tsx`)
- API: `POST /skus/{sku}/generate`

## Core Functions
- `services/api/app/repo/studio_pipeline.py` — `generate_shots()` builds and runs the Genblaze pipeline (the ONLY home for `genblaze_*` imports)
- `services/api/app/service/studio.py` — `generate()` validates, presigns the reference, fans out variant prompts, maps results
- `services/api/app/runtime/skus.py` — `POST /skus/{sku}/generate` handler
- `apps/web/src/lib/queries.ts` — `useGenerateShots()`

## Canonical Files
- Pipeline: `services/api/app/repo/studio_pipeline.py`
- Orchestration: `services/api/app/service/studio.py`

## Inputs
- sku: string (path) — product identifier, 1–64 chars `[A-Za-z0-9._-]`
- scene_prompt: string (body)
- reference_key: string (body) — must be under `uploads/<sku>/reference/`
- angle_presets / season_presets: string[] (body) — fanned into per-variant prompts
- variants: int (body, default 3, max 6)
- size: `1024x1024 | 1536x1024 | 1024x1536 | auto` (default `1024x1024`)
- quality: `low | medium | high | auto` (default `medium`)

## Outputs
- `GenerationResult`: sku, run_id, manifest_uri, canonical_hash, shots[], failed
- Each `GeneratedShot`: key, url, sha256, prompt, size, quality, cost_usd, width, height
- Side effects: per-variant PNGs + a SHA-256 `manifest.json` written to B2 under
  `skus/<sku>/generations/<run_id>/`

## Flow
- Validate SKU, prompt, quality/size enums, and variant count
- Confirm `reference_key` is under this SKU's `uploads/<sku>/reference/` prefix
- Presign a short-lived (15 min) GET URL for the reference photo
- Fan the scene prompt out into `variants` prompts (cycling angle/season presets)
- In `repo/studio_pipeline.py`, fetch the presigned reference once and write it
  to a local temp file with an image extension matched to the bytes' magic
  number (`.png`/`.jpg`/`.webp`), then seed each step with a `file://` Asset to
  that temp file. This is deliberate, not an artifact: the pinned genblaze-openai
  0.3.0 hands `client.images.edit` an open file handle and the OpenAI client
  infers the multipart mimetype from that handle's filename. If the SDK fetches
  the presigned URL itself it writes a `*.img` temp file → `guess_type` returns
  `None` → `application/octet-stream` → OpenAI 400 `unsupported_mimetype`. Passing
  a `file://` URL routes the SDK through `_resolve_local_file`, which opens our
  correctly-named file so OpenAI infers a valid `image/*` type. The temp file is
  removed in a `finally` after the run.
- Build a `Pipeline(project_id=sku, max_concurrency=N)` (the concurrency cap is a
  constructor kwarg in genblaze-core 0.3.2, not a `run()` kwarg) with one `.step()`
  per prompt, each seeded with the reference as
  `external_inputs=[Asset(url="file://…", sha256=…)]` → gpt-image-1 routes to
  `/images/edits` (reference-faithful, `input_fidelity="high"`)
- `pipe.run(sink=ObjectStorageSink(S3StorageBackend.for_backblaze(...)), timeout=…, raise_on_failure=False)`
- Map succeeded steps → `GeneratedShot`; surface failures in `failed`
- The Studio result grid and the reference-photo thumbnail render each image
  through the shared `PresignedImage` component
  (`apps/web/src/components/presigned-image.tsx`), which fetches an inline
  presigned URL from `GET /files/{key}/preview` via `usePreviewUrl`. The bucket
  is private, so embedding the static public B2 URL in `<img src>` would 401;
  the inline presigned URL renders regardless of bucket ACL.

## Edge Cases
- SKU invalid → 400
- reference_key outside the SKU prefix → 400 (can't bill one SKU's photo to another)
- variants out of 1–6 → 400
- All variants fail (e.g. bad `OPENAI_API_KEY`) → 502 with a clear message
- Reference > 50MB → rejected (matches OpenAI's edit-input limit)
- Provider/network error → 502; partial failures return the shots that succeeded
- Long run / stalled connection: a generation can take minutes. The route
  offloads the blocking pipeline run to a threadpool (`run_in_threadpool`) so
  uvicorn's event loop keeps the connection alive (and `/health` responsive)
  for the whole run — without this the loop is starved and an edge/proxy can
  drop the idle-looking connection, completing the work but hanging the client.
  As a client-side backstop, `generateShots()` aborts after ~360s (just above
  the 300s server `studio_run_timeout`) and surfaces a 408; `useGenerateShots`
  invalidates queries `onSettled` (not just `onSuccess`), so shots that did land
  in B2 still surface in the Library/dashboard even when the response was lost.

## UX States
- Empty: "Your generated product shots will appear here"
- Loading: blaze generating loader ("Generating shots…")
- Error: toast with the API detail. On a client-side timeout (408) the toast
  instead points the user to the Library for that SKU, where any completed
  shots appear — the loader always clears (never spins forever).
- Loaded: shot grid with size/quality/cost badges, sha256, and manifest link;
  each shot image loads via the inline presigned-preview path (private-bucket safe)

## Verification
- Test files: `services/api/tests/test_studio.py`,
  `services/api/tests/test_pipeline_signatures.py`
- Required cases: SKU validation, prompt fan-out, reference-prefix guard, result
  mapping; reference asset is a `file://` URL to a temp file with a real image
  extension (never `.img`/octet-stream), incl. unrecognized bytes
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Live check: with real `B2_*` + `OPENAI_API_KEY`, `POST /skus/<sku>/generate` returns
  shots whose URLs resolve on B2 and whose manifest verifies
- Pass criteria: pytest green; structural tests confirm `genblaze_*` only in `repo/`

## Related Docs
- [Per-SKU Library](per-sku-library.md)
- [Provenance Manifest](provenance-manifest.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
