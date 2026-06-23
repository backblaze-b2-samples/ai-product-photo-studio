<!-- last_verified: 2026-06-23 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Long-Running Generation

- `POST /skus/{sku}/generate` is a multi-minute call. The handler offloads the
  blocking pipeline run to a threadpool (`run_in_threadpool`) so uvicorn's event
  loop is never starved — the connection's keep-alive and `/health` stay
  responsive for the whole run, so intermediaries don't drop the connection
  before the response is sent.
- Server run cap: `studio_run_timeout` (default 300s). Client backstop:
  `generateShots()` aborts after ~360s and surfaces a 408, so the UI can never
  spin forever on a stalled connection.
- The frontend invalidates queries `onSettled`, so shots that completed and
  landed in B2 surface in the Library/dashboard even if the original response
  was lost.

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
