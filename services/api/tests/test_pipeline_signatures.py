"""No-network guard against Genblaze SDK signature drift.

The studio's headline call site (`repo/studio_pipeline.py::generate_shots`)
builds a real `genblaze_core.Pipeline` + `genblaze_openai.DalleProvider` chain
and calls `pipe.run(...)`. The other studio tests monkeypatch the repo, so they
never exercise the real SDK and can't catch a signature mismatch (e.g. passing
`max_concurrency=` to `run()` when it's a constructor-only kwarg).

These tests construct the REAL pipeline with the exact kwargs the studio uses
and bind them against the installed SDK signatures — without any OpenAI/B2
network call — so SDK upgrades that change the API fail loudly in CI.
"""

import inspect
import mimetypes
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

from genblaze_core import Asset, Modality, Pipeline
from genblaze_openai import DalleProvider
from genblaze_openai.dalle import _resolve_local_file

from app.repo import studio_pipeline


def _build_real_pipeline(n_variants: int) -> Pipeline:
    """Mirror exactly what generate_shots() builds (no network)."""
    reference = Asset(
        url="https://example.com/ref.png",
        media_type="image/png",
        sha256="a" * 64,
        size_bytes=123,
    )
    pipe = Pipeline(
        "ai-product-photo-studio",
        project_id="SKU-001",
        max_concurrency=n_variants or 1,
    )
    for prompt in [f"scene {i}" for i in range(n_variants)]:
        pipe = pipe.step(
            DalleProvider(api_key="sk-test-not-used"),
            model="gpt-image-1",
            modality=Modality.IMAGE,
            prompt=prompt,
            external_inputs=[reference],
            size="1024x1024",
            quality="medium",
            input_fidelity="high",
        )
    return pipe


def test_pipeline_constructor_accepts_studio_kwargs():
    """Pipeline(...) must accept project_id + max_concurrency (constructor-only)."""
    sig = inspect.signature(Pipeline.__init__)
    assert "max_concurrency" in sig.parameters, (
        "max_concurrency moved off the Pipeline constructor — update "
        "repo/studio_pipeline.py"
    )
    # Real construct + step chain validates capabilities/modality (no network).
    pipe = _build_real_pipeline(3)
    pipe._validate_steps()
    assert len(pipe._steps) == 3


def test_run_signature_binds_studio_kwargs_and_rejects_max_concurrency():
    """The exact run() kwargs the studio passes must bind; max_concurrency must NOT.

    This is the regression guard for the round-2 fix: max_concurrency belongs on
    the constructor, not run().
    """
    run_sig = inspect.signature(Pipeline.run)

    # The studio's actual run() call: sink + timeout + raise_on_failure.
    # bind_partial against the unbound signature (self omitted) must succeed.
    bound = run_sig.bind_partial(
        sink=object(), timeout=300, raise_on_failure=False
    )
    assert "max_concurrency" not in bound.arguments

    # And run() must reject max_concurrency (it has no **kwargs).
    assert "max_concurrency" not in run_sig.parameters
    has_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in run_sig.parameters.values()
    )
    assert not has_var_kw, "run() grew **kwargs — re-check the studio call site"


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff\xe0"
_WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP"


def _fake_download(payload: bytes):
    """Patch the urlopen the pipeline uses, returning a context manager."""
    resp = mock.MagicMock()
    resp.read.return_value = payload
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return mock.patch.object(
        studio_pipeline.urllib.request, "urlopen", return_value=resp
    )


def test_reference_asset_is_a_typed_local_file_not_dotimg():
    """Regression: the reference reaches OpenAI as a correctly-typed image.

    The pinned SDK hands ``client.images.edit`` an OPEN FILE HANDLE and the
    OpenAI client infers the multipart mimetype from that handle's filename.
    If the SDK fetches the presigned URL itself it writes a ``.img`` temp file →
    ``application/octet-stream`` → OpenAI 400. The app must instead pass a
    ``file://`` URL to a temp file whose extension names a real image type, and
    that path must resolve through the SDK's local-file branch.
    """
    cases = (
        (_PNG_MAGIC + b"rest", ".png", "image/png"),
        (_JPEG_MAGIC + b"rest", ".jpg", "image/jpeg"),
        (_WEBP_BYTES + b"rest", ".webp", "image/webp"),
    )
    for payload, want_suffix, want_media in cases:
        with _fake_download(payload):
            asset, tmp = studio_pipeline._reference_asset("https://b2.example/ref?sig=x")
        try:
            # Asset carries a file:// URL (NOT the presigned https URL), so the
            # SDK skips its broken .img download path.
            assert urlparse(asset.url).scheme == "file"
            assert asset.url.endswith(want_suffix)
            assert asset.media_type == want_media
            # The SDK would open this exact path; its name must yield a real
            # image mimetype, never octet-stream.
            resolved = _resolve_local_file(asset.url, None)
            assert resolved == tmp.resolve()
            assert mimetypes.guess_type(resolved.name)[0] == want_media
        finally:
            tmp.unlink(missing_ok=True)
        assert not tmp.exists()


def test_unknown_reference_bytes_still_named_as_an_image():
    """Unrecognized bytes must still get an image extension, never .img/octet."""
    with _fake_download(b"not-an-image-header"):
        asset, tmp = studio_pipeline._reference_asset("https://b2.example/ref")
    try:
        suffix = Path(urlparse(asset.url).path).suffix
        assert suffix in {".png", ".jpg", ".jpeg", ".webp"}
        assert mimetypes.guess_type("x" + suffix)[0] in {
            "image/png",
            "image/jpeg",
            "image/webp",
        }
    finally:
        tmp.unlink(missing_ok=True)


def test_dalle_step_kwargs_are_accepted():
    """DalleProvider step kwargs (input_fidelity, size, quality) flow as params."""
    pipe = _build_real_pipeline(1)
    step = pipe._steps[0]
    assert step.model == "gpt-image-1"
    assert step.modality == Modality.IMAGE
    # external_inputs seeds Step.inputs at runtime → routes to /images/edits.
    assert step.external_inputs and step.external_inputs[0].sha256 == "a" * 64
    # Advisory + shape params land in step.params.
    assert step.params.get("input_fidelity") == "high"
    assert step.params.get("size") == "1024x1024"
    assert step.params.get("quality") == "medium"
