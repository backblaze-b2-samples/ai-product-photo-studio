<!-- last_verified: 2026-06-23 -->
# Feature: Provenance Manifest

## Purpose
Every generation run writes a SHA-256 provenance manifest to B2 so each generated
asset can be traced back to the exact run, model, and parameters that produced it —
generative-media provenance, durable in object storage.

## Used By
- API: written automatically during `POST /skus/{sku}/generate`
- UI: manifest URI + per-shot sha256 shown in `/studio` results and `/library`

## Core Functions
- `services/api/app/repo/studio_pipeline.py` — the `ObjectStorageSink` writes the
  manifest; `generate_shots()` returns `manifest_uri` and `canonical_hash`
- Genblaze `Manifest` (in `genblaze_core`) — schema, canonical hash, `verify()`

## Canonical Files
- Sink + manifest plumbing: `services/api/app/repo/studio_pipeline.py`

## Inputs
- The completed Genblaze `Run` (steps, models, params, asset hashes)

## Outputs
- `skus/<sku>/generations/<run_id>/manifest.json` on B2 — a canonical-JSON manifest
  with `schema_version`, the `Run`, `canonical_hash`, and `manifest_uri`
- `GenerationResult.manifest_uri` (durable, credential-free URL) and `canonical_hash`
- Each `GeneratedShot.sha256` — the content hash of the generated image

## Flow
- The sink uploads each generated asset, recomputes the manifest's canonical hash
  after asset transfer (URLs/hashes settle), then writes `manifest.json`
- `manifest_uri` is set to the backend's durable URL (no SigV4 signature / expiry)
- The manifest is treated as immutable per run; B2 versioning + the sink's existence
  check avoid churn on retries

## Edge Cases
- Partial asset-transfer failure → recorded on the manifest's non-hashed
  `transfer_failures` field; `verify()` still succeeds
- Reference URL rotation (presigned) → mitigated by computing the reference's sha256
  up front so the canonical hash stays stable across reruns

## UX States
- Not applicable (provenance is surfaced as a manifest link + sha256 badges)

## Verification
- Quick verify command: `pnpm test:api`
- Live check: after a real generation, `manifest_uri` resolves on B2 and the stored
  manifest verifies (`Manifest.verify()` / sink `read_manifest`)
- Pass criteria: every shot carries a sha256; the run's manifest exists in B2

## Related Docs
- [Product Photo Generation](product-photo-generation.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
