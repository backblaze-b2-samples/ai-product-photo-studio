"""Tests for the studio (product-photo generation) service.

These exercise validation, the prompt fan-out, and the orchestration mapping
without calling OpenAI — the repo pipeline is monkeypatched. Real provider
wiring is covered end-to-end by a live demo run, not in unit tests.
"""

import pytest

from app.service import studio as studio_service
from app.service.studio import StudioError
from app.types import GenerationRequest


def test_validate_sku_accepts_and_rejects():
    studio_service.validate_sku("SKU-123_v2.1")
    for bad in ["", "../etc", "has space", "x" * 65, "/leading"]:
        with pytest.raises(StudioError):
            studio_service.validate_sku(bad)


def test_variant_prompts_fan_out():
    req = GenerationRequest(
        scene_prompt="on a marble countertop",
        reference_key="uploads/sku1/reference/p.png",
        angle_presets=["front", "three-quarter"],
        season_presets=["holiday"],
    )
    prompts = studio_service._variant_prompts(req, 3)
    assert len(prompts) == 3
    assert all("on a marble countertop" in p for p in prompts)
    assert any("front angle" in p for p in prompts)


def test_variant_prompts_default_when_no_presets():
    req = GenerationRequest(
        scene_prompt="studio lighting",
        reference_key="uploads/sku1/reference/p.png",
    )
    assert studio_service._variant_prompts(req, 2) == ["studio lighting", "studio lighting"]


def test_generate_rejects_reference_outside_sku_prefix(monkeypatch):
    monkeypatch.setattr(studio_service, "get_presigned_url", lambda *a, **k: "https://x/y")
    req = GenerationRequest(
        scene_prompt="x",
        reference_key="uploads/other-sku/reference/p.png",
    )
    with pytest.raises(StudioError):
        studio_service.generate("sku1", req)


def test_generate_maps_repo_result(monkeypatch):
    monkeypatch.setattr(
        studio_service, "get_presigned_url", lambda *a, **k: "https://b2/presigned"
    )

    def fake_repo(sku, url, prompts, *, size, quality):
        return {
            "run_id": "run-abc",
            "manifest_uri": "https://b2/skus/sku1/generations/run-abc/manifest.json",
            "canonical_hash": "deadbeef",
            "shots": [
                {
                    "key": "skus/sku1/generations/2026-06-23/run-abc/0.png",
                    "url": "https://b2/skus/sku1/generations/2026-06-23/run-abc/0.png",
                    "sha256": "abc123",
                    "prompt": prompts[0],
                    "size": size,
                    "quality": quality,
                    "cost_usd": 0.07,
                    "width": 1024,
                    "height": 1024,
                }
            ],
            "failed": 0,
        }

    monkeypatch.setattr(studio_service, "repo_generate_shots", fake_repo)

    req = GenerationRequest(
        scene_prompt="on a beach at sunset",
        reference_key="uploads/sku1/reference/p.png",
        variants=1,
    )
    result = studio_service.generate("sku1", req)
    assert result.run_id == "run-abc"
    assert result.canonical_hash == "deadbeef"
    assert len(result.shots) == 1
    assert result.shots[0].sha256 == "abc123"
    assert result.shots[0].cost_usd == 0.07
