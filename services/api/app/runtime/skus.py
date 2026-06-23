"""Studio routes: per-SKU generation + per-SKU asset listing.

Handlers import only from ``app.service`` / ``app.types`` — never from
``genblaze_*`` or ``boto3`` directly (enforced by tests/test_structure.py).
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.service.studio import (
    StudioError,
    generate,
    get_sku,
    get_sku_shots,
    list_skus,
)
from app.types import (
    GenerationRequest,
    GenerationResult,
    SkuAsset,
    SkuDetail,
    SkuSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/skus", response_model=list[SkuSummary])
async def list_skus_endpoint():
    return list_skus()


@router.get("/skus/{sku}", response_model=SkuDetail)
async def get_sku_endpoint(sku: str):
    try:
        return get_sku(sku)
    except StudioError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/skus/{sku}/shots", response_model=list[SkuAsset])
async def get_sku_shots_endpoint(sku: str):
    try:
        return get_sku_shots(sku)
    except StudioError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post("/skus/{sku}/generate", response_model=GenerationResult)
async def generate_endpoint(sku: str, req: GenerationRequest):
    # ``generate`` is a blocking, multi-minute call (gpt-image-1 edits + B2
    # writes). Running it directly on the event loop would starve the loop for
    # the whole run, so uvicorn could not service this connection's keep-alive
    # and an intermediary (edge/proxy) may drop the now-idle-looking connection
    # before the response is sent — the work completes but the client hangs.
    # Offload to a threadpool so the loop stays responsive and the response is
    # delivered when the run finishes.
    try:
        result = await run_in_threadpool(generate, sku, req)
    except StudioError as e:
        logger.warning("generate rejected for sku=%s: %s", sku, e.detail)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    logger.info(
        "generate ok: sku=%s run=%s shots=%d failed=%d",
        sku,
        result.run_id,
        len(result.shots),
        result.failed,
    )
    return result
