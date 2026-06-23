<!-- last_verified: 2026-06-23 -->
# App Workflows

The seller's journey through AI Product Photo Studio.

## Generate product photos for a SKU (core flow)

- User navigates to `/studio`
- Enters a **SKU** (the product identifier and namespace for all its assets)
- Uploads a **reference photo** (PNG / JPEG / WebP) — stored at
  `uploads/<sku>/reference/<filename>` on B2
- Writes a **scene prompt** (e.g. "on a marble kitchen counter, soft morning light")
- Picks **angle presets** and/or **seasonal presets**, a **variant count**
  (1–6), **quality** (low/medium/high), and **size**
- Clicks **Generate shots** — the blaze loader runs while the pipeline executes
- The app fans the prompt out into N gpt-image-1 *edit* steps (each seeded with
  the reference photo), runs them concurrently via the Genblaze pipeline, and
  writes each result + a SHA-256 manifest to `skus/<sku>/generations/<run_id>/`
- Results appear in a grid with size/quality/cost badges and a sha256 fingerprint;
  a link to the provenance manifest is shown
- See: [Product Photo Generation](features/product-photo-generation.md)

## Browse a SKU's library

- User navigates to `/library` (or clicks "View in library" after a generation)
- Without a `?sku=` param: a grid of SKU cards (reference + shot counts, storage)
- With a SKU selected: two sections — **Reference photos** and **Generated shots**,
  scoped to that SKU's `skus/<sku>/` prefix, each card showing the run id and
  provenance timestamp
- See: [Per-SKU Library](features/per-sku-library.md)

## Browse the whole bucket

- User navigates to `/files`
- Tree view of every object in the bucket (references and generations alike)
- Hover a row for preview / download / delete; delete is prefix-scoped
- See: [File Browser](features/file-browser.md)

## Upload a reference photo directly

- User navigates to `/upload`
- Drops or selects an image (PNG / JPEG / WebP; pdf/csv/zip/audio/video are rejected)
- Progress bar per file; toast on success/failure
- See: [File Upload](features/file-upload.md)

## View the dashboard

- User navigates to `/` (home)
- Stat cards: **SKUs**, **generated shots**, **storage used**, **generations today**
- **Storage Growth** chart — cumulative asset count over the last 14 days (the
  B2 storage-curve story: references + many generations per SKU accumulate)
- **Recent Generations** table — most recently active SKUs, linking to their library
- See: [Dashboard](features/dashboard.md)
