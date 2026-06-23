<!-- last_verified: 2026-06-23 -->
# Feature: Per-SKU Library

## Purpose
Give the seller a scoped view of a single SKU — its reference photo(s) and every
generated shot — distinct from the full-bucket file explorer.

## Used By
- UI: `/library` page (`components/library/sku-library.tsx`)
- API: `GET /skus`, `GET /skus/{sku}`, `GET /skus/{sku}/shots`

## Core Functions
- `services/api/app/service/studio.py` — `list_skus()`, `get_sku()`, `get_sku_shots()`
- `services/api/app/runtime/skus.py` — the three GET handlers
- `apps/web/src/lib/queries.ts` — `useSkus()`, `useSku()`, `useSkuShots()`

## Canonical Files
- SKU aggregation: `services/api/app/service/studio.py`
- Library UI: `apps/web/src/components/library/sku-library.tsx`

## Inputs
- sku: string (path, for the detail/shots endpoints)

## Outputs
- `GET /skus` → `SkuSummary[]` (sku, reference_count, shot_count, total_size, latest_at)
- `GET /skus/{sku}` → `SkuDetail` (references[], shots[])
- `GET /skus/{sku}/shots` → `SkuAsset[]` (generations only, manifests excluded)

## Flow
- `/library` with no `?sku=` lists SKU cards aggregated from the `uploads/` and `skus/` prefixes
- Selecting a SKU lists its reference photos (`uploads/<sku>/reference/`) and its
  generated shots (`skus/<sku>/generations/`), each with run id + provenance timestamp
- The run id is parsed from the object key so shots from the same generation group visually
- Each asset thumbnail renders through the shared `PresignedImage` component
  (`apps/web/src/components/presigned-image.tsx`), which fetches an inline presigned
  URL from `GET /files/{key}/preview` via the `usePreviewUrl` hook. The bucket is
  private, so embedding the static public URL would 401 in the browser; the inline
  presigned URL renders regardless of bucket ACL.

## Edge Cases
- Unknown SKU → empty reference/shot sections (not an error)
- Invalid SKU string → 400
- `manifest.json` objects are filtered out of the shot grid (they're provenance, not images)

## UX States
- Empty: "No SKUs yet" / "No generations yet" / "No reference photos"
- Loading: skeletons
- Error: inline `ErrorState` with retry
- Loaded: SKU cards or the two-section detail grid

## Verification
- Test files: covered indirectly via `services/api/tests/test_studio.py` (SKU validation);
  inline-preview disposition (the path that renders thumbnails) in
  `services/api/tests/test_download_stats.py::test_preview_requests_inline_disposition`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: pytest green; `/library` renders SKU cards and per-SKU assets

## Related Docs
- [Product Photo Generation](product-photo-generation.md)
- [File Browser](file-browser.md)
- [App Workflows](../app-workflows.md)
