<!-- last_verified: 2026-04-22 -->
# Security

Security principles and implementation for the ai-product-photo-studio.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4 (endpoint derived from `B2_REGION`)
- **API -> OpenAI**: `OPENAI_API_KEY`, kept separate from B2 credentials
- **Client -> B2**: Presigned URLs for download/preview (short expiry, `Content-Disposition: attachment`)

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against allowlist
- Chunked streaming with size enforcement (100MB default)
- Content-type allowlist: `image/jpeg`, `image/png`, `image/webp` only
- Optional `sku` validated (1–64 chars `[A-Za-z0-9._-]`) before it becomes a key prefix
- Empty file rejection

## Generation Safety

- `reference_key` must be under the requested SKU's `uploads/<sku>/reference/` prefix —
  prevents using one SKU's photo to bill generations against another
- Per-SKU deletes are scoped to `skus/` / `uploads/` prefixes (never wipe shared data)

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The bucket is the only access boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
