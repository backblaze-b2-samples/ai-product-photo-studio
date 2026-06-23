<!-- last_verified: 2026-06-23 -->
# Feature: Dashboard

## Purpose
Tell the SKU / storage-curve story at a glance: how many SKUs and generated shots
exist, how much B2 storage they occupy, and how that storage accumulates over time.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /skus`, `GET /files/stats`, `GET /files/stats/activity`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — SKUs, generated shots, storage used, generations today
- `apps/web/src/components/dashboard/upload-chart.tsx` — cumulative storage-growth area chart
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — recently active SKUs ("Recent Generations")
- `apps/web/src/lib/queries.ts` — `useSkus()`, `useFileStats()`, `useUploadActivity()`

## Canonical Files
- Stat cards: `apps/web/src/components/dashboard/stats-cards.tsx`
- Storage curve: `apps/web/src/components/dashboard/upload-chart.tsx`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /skus` → `SkuSummary[]` (drives SKU count, total shots, recent-generations table)
- `GET /files/stats` → `UploadStats` (total storage, generations/uploads today)
- `GET /files/stats/activity?days=14` → `DailyUploadCount[]` (accumulated into the storage curve)

## Flow
- Page loads → parallel queries for SKUs, stats, and 14-day activity
- Stat cards: SKU count, total generated shots (summed across SKUs), storage used, generations today
- Storage Growth chart: cumulative object count over the last 14 days (the B2 storage curve)
- Recent Generations table: most recently active SKUs, each linking to its library

## Edge Cases
- API unavailable → stat cards show an inline error with retry (no fake zeros)
- No SKUs / no activity → empty states in the table and chart
- Large object count → stats endpoint paginates with `ContinuationToken`

## UX States
- Loading: skeleton placeholders
- Empty: "No SKUs yet" / "No generations yet" / "No assets yet"
- Loaded: populated cards, storage curve, recent-generations table

## Verification
- Test files: `services/api/tests/test_upload_activity.py`, `services/api/tests/test_recent_files.py`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: pytest green, no ruff/eslint violations, dashboard renders SKU stats

## Related Docs
- [Per-SKU Library](per-sku-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
