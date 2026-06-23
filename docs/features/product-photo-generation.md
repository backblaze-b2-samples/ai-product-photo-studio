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
- Build a `Pipeline(project_id=sku)` with one `.step()` per prompt, each seeded with
  the reference as `external_inputs=[Asset(url=presigned, sha256=…)]` →
  gpt-image-1 routes to `/images/edits` (reference-faithful, `input_fidelity="high"`)
- `pipe.run(sink=ObjectStorageSink(S3StorageBackend.for_backblaze(...)), max_concurrency=N)`
- Map succeeded steps → `GeneratedShot`; surface failures in `failed`

## Edge Cases
- SKU invalid → 400
- reference_key outside the SKU prefix → 400 (can't bill one SKU's photo to another)
- variants out of 1–6 → 400
- All variants fail (e.g. bad `OPENAI_API_KEY`) → 502 with a clear message
- Reference > 50MB → rejected (matches OpenAI's edit-input limit)
- Provider/network error → 502; partial failures return the shots that succeeded

## UX States
- Empty: "Your generated product shots will appear here"
- Loading: blaze generating loader ("Generating shots…")
- Error: toast with the API detail
- Loaded: shot grid with size/quality/cost badges, sha256, and manifest link

## Verification
- Test files: `services/api/tests/test_studio.py`
- Required cases: SKU validation, prompt fan-out, reference-prefix guard, result mapping
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
