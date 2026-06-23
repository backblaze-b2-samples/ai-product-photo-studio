"""Studio routes: per-SKU generation + per-SKU asset listing.

Handlers import only from ``app.service`` / ``app.types`` — never from
``genblaze_*`` or ``boto3`` directly (enforced by tests/test_structure.py).
"""

import logging

from fastapi import APIRouter, HTTPException

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
    try:
        result = generate(sku, req)
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
