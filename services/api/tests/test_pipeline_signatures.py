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

from genblaze_core import Asset, Modality, Pipeline
from genblaze_openai import DalleProvider


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
