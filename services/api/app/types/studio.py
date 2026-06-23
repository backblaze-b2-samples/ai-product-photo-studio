"""Pydantic models for the studio (product-photo generation) surface."""

from datetime import datetime

from pydantic import BaseModel, Field

# gpt-image-1 enums (validated against the installed genblaze-openai wheel).
QUALITY_VALUES = frozenset({"low", "medium", "high", "auto"})
SIZE_VALUES = frozenset({"1024x1024", "1536x1024", "1024x1536", "auto"})


class GenerationRequest(BaseModel):
    """A request to generate one or more product shots from a reference photo."""

    scene_prompt: str = Field(..., min_length=1, max_length=2000)
    reference_key: str = Field(..., min_length=1)
    # Optional preset modifiers fanned out into per-variant prompts.
    angle_presets: list[str] = Field(default_factory=list)
    season_presets: list[str] = Field(default_factory=list)
    variants: int | None = None
    size: str | None = None
    quality: str | None = None


class GeneratedShot(BaseModel):
    """A single generated image plus its B2 location and provenance."""

    key: str | None = None
    url: str | None = None
    sha256: str | None = None
    prompt: str
    size: str
    quality: str
    cost_usd: float | None = None
    width: int | None = None
    height: int | None = None


class GenerationResult(BaseModel):
    """The outcome of one generate run: run id, manifest, and the shots."""

    sku: str
    run_id: str
    manifest_uri: str | None = None
    canonical_hash: str | None = None
    shots: list[GeneratedShot]
    failed: int = 0


class SkuSummary(BaseModel):
    """A SKU listed on the dashboard / library index."""

    sku: str
    reference_count: int
    shot_count: int
    total_size_bytes: int
    total_size_human: str
    latest_at: datetime | None = None


class SkuDetail(BaseModel):
    """Full per-SKU view: reference photos + every generated shot."""

    sku: str
    references: list["SkuAsset"]
    shots: list["SkuAsset"]


class SkuAsset(BaseModel):
    """An asset scoped to a SKU prefix, with provenance where known."""

    key: str
    filename: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None
    run_id: str | None = None
    is_manifest: bool = False


SkuDetail.model_rebuild()
