"""Route-level tests for POST /skus/{sku}/generate.

The service layer is unit-tested in test_studio.py; these cover the HTTP
handler itself — in particular that the blocking, multi-minute pipeline run is
offloaded off the event loop (via run_in_threadpool) so a long generation can't
starve uvicorn's loop and hang the connection.
"""

import threading

import pytest

from app.runtime import skus as skus_runtime
from app.service.studio import StudioError
from app.types import GeneratedShot, GenerationResult

_BODY = {
    "scene_prompt": "on a marble counter, soft morning light",
    "reference_key": "uploads/CANDLE-001/reference/candle.png",
}


@pytest.mark.asyncio
async def test_generate_route_returns_result_off_event_loop(client, monkeypatch):
    """Handler returns the mapped result, and runs the blocking call in a
    worker thread (not the event-loop / main thread)."""
    ran_on: dict[str, object] = {}

    def fake_generate(sku, req):
        ran_on["thread"] = threading.current_thread()
        ran_on["is_main"] = threading.current_thread() is threading.main_thread()
        return GenerationResult(
            sku=sku,
            run_id="run-123",
            shots=[
                GeneratedShot(
                    key=f"skus/{sku}/generations/run-123/0.png",
                    prompt=req.scene_prompt,
                    size="1024x1024",
                    quality="medium",
                )
            ],
            failed=0,
        )

    monkeypatch.setattr(skus_runtime, "generate", fake_generate)

    response = await client.post("/skus/CANDLE-001/generate", json=_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["sku"] == "CANDLE-001"
    assert body["run_id"] == "run-123"
    assert len(body["shots"]) == 1
    # The blocking run must be offloaded: it executed on a worker thread, so it
    # never blocks the event loop for the duration of the generation.
    assert ran_on["is_main"] is False


@pytest.mark.asyncio
async def test_generate_route_maps_studio_error(client, monkeypatch):
    """A StudioError from the service maps to its HTTP status + detail."""

    def boom(sku, req):
        raise StudioError("Generation failed: provider down", status_code=502)

    monkeypatch.setattr(skus_runtime, "generate", boom)

    response = await client.post("/skus/CANDLE-001/generate", json=_BODY)

    assert response.status_code == 502
    assert response.json()["detail"] == "Generation failed: provider down"
