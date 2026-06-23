"""Studio service: orchestrate product-photo generation per SKU.

Sits between the HTTP router (``runtime/skus.py``) and the repo layer. It
validates input, resolves the reference photo's B2 URL, fans the scene prompt
out into per-variant prompts, invokes the Genblaze pipeline in ``repo/``, and
maps the plain dict result onto typed ``GeneratedShot`` / ``SkuDetail`` models.
This layer imports NO provider/storage SDK directly.
"""

import logging
import re

from app.config import settings
from app.repo import (
    generate_shots as repo_generate_shots,
)
from app.repo import (
    get_presigned_url,
    list_files,
)
from app.types import (
    GeneratedShot,
    GenerationRequest,
    GenerationResult,
    SkuAsset,
    SkuDetail,
    SkuSummary,
)

logger = logging.getLogger(__name__)

# A SKU is the only namespace in v1 — keep it filesystem/key-safe.
_SKU_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_REFERENCE_PREFIX = "uploads/{sku}/reference/"
_GENERATIONS_PREFIX = "skus/{sku}/generations/"
_RUN_ID_RE = re.compile(r"/generations/(?:[^/]+/)*([0-9a-f-]{8,})/")


class StudioError(Exception):
    """Raised when a generate request is invalid."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def validate_sku(sku: str) -> None:
    if not _SKU_RE.match(sku):
        raise StudioError(
            "Invalid SKU. Use 1-64 chars: letters, digits, '.', '_', '-'."
        )


def _variant_prompts(req: GenerationRequest, count: int) -> list[str]:
    """Fan a single scene prompt out into ``count`` per-variant prompts.

    Angle and seasonal presets are appended as scene modifiers, cycling so a
    single request can produce a spread of distinct, reference-faithful shots.
    """
    modifiers: list[str] = []
    for angle in req.angle_presets:
        modifiers.append(f"{req.scene_prompt}, {angle} angle")
    for season in req.season_presets:
        modifiers.append(f"{req.scene_prompt}, {season} seasonal styling")
    if not modifiers:
        modifiers = [req.scene_prompt]

    prompts: list[str] = []
    for i in range(count):
        prompts.append(modifiers[i % len(modifiers)])
    return prompts


def generate(sku: str, req: GenerationRequest) -> GenerationResult:
    """Validate, resolve the reference URL, and run the generation pipeline."""
    validate_sku(sku)

    quality = req.quality or settings.studio_default_quality
    size = req.size or settings.studio_default_size
    if quality not in {"low", "medium", "high", "auto"}:
        raise StudioError(f"Invalid quality '{quality}'")
    if size not in {"1024x1024", "1536x1024", "1024x1536", "auto"}:
        raise StudioError(f"Invalid size '{size}'")

    count = req.variants or settings.studio_default_variants
    if count < 1 or count > settings.studio_max_variants:
        raise StudioError(
            f"variants must be between 1 and {settings.studio_max_variants}"
        )

    # The reference must live under this SKU's upload prefix — prevents using
    # one SKU's reference to bill generations against another.
    expected_prefix = _REFERENCE_PREFIX.format(sku=sku)
    if not req.reference_key.startswith(expected_prefix):
        raise StudioError(
            f"reference_key must be under '{expected_prefix}'", status_code=400
        )

    # Short-lived presigned GET so the provider can fetch the reference.
    reference_url = get_presigned_url(req.reference_key, expires_in=900)

    prompts = _variant_prompts(req, count)
    try:
        raw = repo_generate_shots(
            sku,
            reference_url,
            prompts,
            size=size,
            quality=quality,
        )
    except ValueError as e:
        raise StudioError(str(e)) from None
    except Exception as e:  # provider / network failure
        logger.exception("studio generate failed for sku=%s", sku)
        raise StudioError(f"Generation failed: {e}", status_code=502) from None

    shots = [GeneratedShot(**s) for s in raw["shots"]]
    if not shots:
        raise StudioError(
            "All variants failed to generate. Check OPENAI_API_KEY and try again.",
            status_code=502,
        )

    return GenerationResult(
        sku=sku,
        run_id=raw["run_id"],
        manifest_uri=raw.get("manifest_uri"),
        canonical_hash=raw.get("canonical_hash"),
        shots=shots,
        failed=raw.get("failed", 0),
    )


def _run_id_from_key(key: str) -> str | None:
    m = _RUN_ID_RE.search("/" + key)
    return m.group(1) if m else None


def _to_sku_asset(meta, *, run_id: str | None = None) -> SkuAsset:
    return SkuAsset(
        key=meta.key,
        filename=meta.filename,
        size_bytes=meta.size_bytes,
        size_human=meta.size_human,
        content_type=meta.content_type,
        uploaded_at=meta.uploaded_at,
        url=meta.url,
        run_id=run_id or _run_id_from_key(meta.key),
        is_manifest=meta.filename == "manifest.json",
    )


def list_skus() -> list[SkuSummary]:
    """Aggregate per-SKU counts from the uploads/ and skus/ prefixes."""
    from app.types.formatting import humanize_bytes

    refs = list_files(prefix="uploads/", max_keys=1000)
    gens = list_files(prefix="skus/", max_keys=1000)

    summaries: dict[str, dict] = {}

    def _bucket(sku: str) -> dict:
        return summaries.setdefault(
            sku,
            {"reference_count": 0, "shot_count": 0, "total_size_bytes": 0, "latest_at": None},
        )

    for f in refs:
        parts = f.key.split("/")
        if len(parts) >= 3 and parts[0] == "uploads" and parts[2] == "reference":
            b = _bucket(parts[1])
            b["reference_count"] += 1
            b["total_size_bytes"] += f.size_bytes
            if b["latest_at"] is None or f.uploaded_at > b["latest_at"]:
                b["latest_at"] = f.uploaded_at

    for f in gens:
        parts = f.key.split("/")
        if len(parts) >= 2 and parts[0] == "skus":
            b = _bucket(parts[1])
            if f.filename != "manifest.json":
                b["shot_count"] += 1
            b["total_size_bytes"] += f.size_bytes
            if b["latest_at"] is None or f.uploaded_at > b["latest_at"]:
                b["latest_at"] = f.uploaded_at

    return [
        SkuSummary(
            sku=sku,
            reference_count=b["reference_count"],
            shot_count=b["shot_count"],
            total_size_bytes=b["total_size_bytes"],
            total_size_human=humanize_bytes(b["total_size_bytes"]),
            latest_at=b["latest_at"],
        )
        for sku, b in sorted(summaries.items())
    ]


def get_sku(sku: str) -> SkuDetail:
    """Return a SKU's reference photos and every generated shot."""
    validate_sku(sku)
    refs = list_files(prefix=_REFERENCE_PREFIX.format(sku=sku), max_keys=1000)
    gens = list_files(prefix=_GENERATIONS_PREFIX.format(sku=sku), max_keys=1000)
    return SkuDetail(
        sku=sku,
        references=[_to_sku_asset(f) for f in refs],
        shots=[_to_sku_asset(f) for f in gens],
    )


def get_sku_shots(sku: str) -> list[SkuAsset]:
    """Return only the generated shots (no references) for a SKU."""
    validate_sku(sku)
    gens = list_files(prefix=_GENERATIONS_PREFIX.format(sku=sku), max_keys=1000)
    return [_to_sku_asset(f) for f in gens if f.filename != "manifest.json"]
