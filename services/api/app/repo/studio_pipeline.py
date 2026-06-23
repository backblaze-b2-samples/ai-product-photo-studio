"""Genblaze image-generation pipeline — the ONLY home for ``genblaze_*`` imports.

This mirrors the starter's "boto3 only in repo/" structural rule: every
provider-orchestration import (``genblaze_core`` / ``genblaze_openai`` /
``genblaze_s3``) is confined here. Service and runtime layers depend on the
plain dicts this module returns, never on Genblaze types.

Routing fact (gpt-image-1, from ``genblaze_openai/dalle.py``): a step with
inputs present routes to ``/images/edits`` (reference-faithful); a step with
no inputs routes to ``/images/generations``. We attach the user-uploaded
reference photo as ``external_inputs=[Asset(...)]`` on every edit step — the
published 0.3.x API for "seed Step.inputs from a caller-held Asset" — which
triggers the edit route per variant. (``external_inputs`` and ``input_from``
are mutually exclusive; ``input_from`` references a *prior step's* output,
which we don't have for a first-time user upload.)
"""

import hashlib
import logging
import os
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import quote

from genblaze_core import (
    Asset,
    KeyStrategy,
    Manifest,
    Modality,
    ObjectStorageSink,
    Pipeline,
    Run,
)
from genblaze_openai import DalleProvider
from genblaze_s3 import S3StorageBackend

from app.config import settings

logger = logging.getLogger(__name__)

PIPELINE_NAME = "ai-product-photo-studio"
_MAX_REFERENCE_BYTES = 50 * 1024 * 1024  # matches OpenAI's edit-input limit

# Magic-byte sniff → (file extension, MIME type). gpt-image-1's /images/edits
# only accepts image/png|jpeg|webp, so we restrict the reference to those three.
# The extension matters: the pinned Genblaze SDK hands OpenAI an OPEN FILE
# HANDLE for the edit input, and the OpenAI client infers the multipart upload
# mimetype from that handle's *filename*. If the SDK downloads the reference
# itself it writes a ``.img`` temp file (genblaze_openai/dalle.py
# ``_download_https_to_temp``) → ``mimetypes.guess_type('*.img')`` is ``None`` →
# ``application/octet-stream`` → OpenAI 400 ``unsupported_mimetype``. We sidestep
# that by downloading the reference ourselves to a temp file with a correct
# image extension and passing a ``file://`` URL: the SDK's ``_resolve_local_file``
# branch opens our well-named file as-is, so OpenAI infers a valid image type.
_MAGIC_TO_FORMAT: tuple[tuple[bytes, str, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
)


def _sniff_image_format(data: bytes) -> tuple[str, str]:
    """Return (suffix, media_type) from magic bytes; webp needs a windowed check.

    Defaults to PNG for unrecognized bytes — OpenAI is the final authority on
    whether the upload is a usable image, but the extension must still name a
    type its edit route accepts (png/jpeg/webp), never octet-stream.
    """
    for magic, suffix, media_type in _MAGIC_TO_FORMAT:
        if data.startswith(magic):
            return suffix, media_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return ".png", "image/png"


def _backend() -> S3StorageBackend:
    """Build the genblaze-s3 backend with explicit B2 credentials.

    All B2_* values are passed explicitly — we never rely on Genblaze's
    ``B2_APP_KEY`` env fallback. The library owns the boto3 client it builds
    here and stamps its own identifying user agent on it (the documented
    Genblaze UA-delegation exception); the app's per-app identity is carried
    in ``Pipeline(name=...)`` and written into every B2 manifest.
    """
    return S3StorageBackend.for_backblaze(
        settings.b2_bucket_name,
        region=settings.b2_region,
        key_id=settings.b2_application_key_id,
        app_key=settings.b2_application_key,
        public_url_base=settings.b2_public_url_base,
    )


def _sink(sku: str) -> ObjectStorageSink:
    """Per-SKU hierarchical sink: assets land under ``skus/<sku>/generations/``.

    HIERARCHICAL groups every asset + manifest of a run together under the
    prefix, so a SKU's generations stay scoped to its own namespace and never
    collide with another SKU or the full-bucket ``uploads/`` tree.
    """
    return ObjectStorageSink(
        _backend(),
        prefix=f"skus/{sku}/generations",
        key_strategy=KeyStrategy.HIERARCHICAL,
    )


def _reference_asset(reference_url: str) -> tuple[Asset, Path]:
    """Download the reference photo to a correctly-typed local temp file.

    Returns the Asset (whose ``url`` is a ``file://`` URL to the temp file) and
    the temp Path so the caller can clean it up after the run. We download here
    rather than letting the SDK fetch the presigned ``reference_url`` because the
    SDK's own fetch writes a ``.img`` temp file that OpenAI's edit route rejects
    as ``application/octet-stream`` (see module docstring + ``_MAGIC_TO_FORMAT``).
    The temp file lands under the system temp dir, which the SDK's
    ``_resolve_local_file`` allowlists, so the ``file://`` URL resolves cleanly.

    Computing sha256 up front keeps the step cache key and the manifest's
    canonical hash stable across reruns even when ``reference_url`` is a
    rotating presigned URL.
    """
    req = urllib.request.Request(reference_url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read(_MAX_REFERENCE_BYTES + 1)
    if len(data) > _MAX_REFERENCE_BYTES:
        raise ValueError("Reference photo exceeds 50MB edit-input limit")

    suffix, media_type = _sniff_image_format(data)
    fd, tmp = tempfile.mkstemp(prefix="studio-ref-", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
    tmp_path = Path(tmp)

    asset = Asset(
        url=f"file://{quote(str(tmp_path.resolve()))}",
        media_type=media_type,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
    )
    return asset, tmp_path


def _key_from_url(url: str | None) -> str | None:
    """Derive the B2 object key from a durable public URL.

    After transfer, ``asset.url`` is ``{B2_PUBLIC_URL_BASE}/{key}``; strip the
    base so the app can address the object via its own boto3 client (preview,
    delete, per-SKU listing) without importing genblaze types downstream.
    """
    if not url:
        return None
    base = settings.b2_public_url_base.rstrip("/")
    if base and url.startswith(base + "/"):
        return url[len(base) + 1 :]
    return None


def _shot_from_step(step) -> dict | None:
    """Map a succeeded Genblaze Step to a plain shot dict (no SDK types leak)."""
    asset = step.assets[0] if step.assets else None
    if asset is None:
        return None
    params = step.params or {}
    return {
        "key": _key_from_url(asset.url),
        "url": asset.url,
        "sha256": asset.sha256,
        "prompt": step.prompt or "",
        "size": params.get("size", settings.studio_default_size),
        "quality": params.get("quality", settings.studio_default_quality),
        "cost_usd": float(step.cost_usd) if step.cost_usd is not None else None,
        "width": asset.width,
        "height": asset.height,
    }


def generate_shots(
    sku: str,
    reference_url: str,
    variant_prompts: list[str],
    *,
    size: str,
    quality: str,
    input_fidelity: str = "high",
) -> dict:
    """Generate N reference-faithful product shots and persist them to B2.

    Returns a plain dict (run_id, manifest_uri, canonical_hash, shots, failed)
    so the service/runtime layers never import Genblaze types.
    """
    if not variant_prompts:
        raise ValueError("At least one variant prompt is required")

    reference, reference_tmp = _reference_asset(reference_url)

    try:
        # max_concurrency is a Pipeline(...) constructor kwarg in genblaze-core
        # 0.3.2 — NOT a run() kwarg (run() takes no **kwargs). Setting it here
        # caps how many edit steps run in parallel.
        pipe = Pipeline(
            PIPELINE_NAME,
            project_id=sku,
            max_concurrency=len(variant_prompts) or 1,
        )
        for prompt in variant_prompts:
            # Reference attached as external_inputs => step.inputs is non-empty
            # => DalleProvider routes to /images/edits (reference-faithful).
            pipe = pipe.step(
                DalleProvider(api_key=settings.openai_api_key),
                model="gpt-image-1",
                modality=Modality.IMAGE,
                prompt=prompt,
                external_inputs=[reference],
                size=size,
                quality=quality,
                input_fidelity=input_fidelity,
            )

        result = pipe.run(
            sink=_sink(sku),
            timeout=settings.studio_run_timeout,
            raise_on_failure=False,
        )
    finally:
        # The SDK opens the temp file during the run (it does not delete it,
        # since for file:// inputs it treats the path as caller-owned). Remove
        # it once every variant has been issued.
        reference_tmp.unlink(missing_ok=True)

    run: Run = result.run
    manifest: Manifest = result.manifest

    shots: list[dict] = []
    for step in result.succeeded_steps():
        mapped = _shot_from_step(step)
        if mapped is not None:
            shots.append(mapped)

    failed = len(result.failed_steps())
    if failed:
        logger.warning(
            "studio generate: %d/%d variants failed for sku=%s: %s",
            failed,
            len(variant_prompts),
            sku,
            result.error_summary(),
        )

    return {
        "run_id": run.run_id,
        "manifest_uri": manifest.manifest_uri,
        "canonical_hash": manifest.canonical_hash,
        "shots": shots,
        "failed": failed,
    }
