<!-- last_verified: 2026-06-23 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| `humanizeBytes` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| `formatDate` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| genblaze-openai 0.3.0 downloads edit-input refs to a `*.img` temp file → OpenAI `/images/edits` rejects the `application/octet-stream` upload (`dalle.py::_download_https_to_temp`) | App must self-download the reference to a correctly-typed temp file and pass a `file://` Asset (`repo/studio_pipeline.py::_reference_asset`) instead of the presigned https URL | Drop the workaround once an SDK release names the temp file by content type (or accepts an explicit mimetype) | Medium | Workaround in place |
