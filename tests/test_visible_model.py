"""Tests for visible_model module.

Cache-token plumbing assertions live in test_visible_runs.py since
they verify the full pipeline. This file exists to satisfy the
test-coverage hook for direct visible_model.py changes.
"""
from __future__ import annotations


class TestVisibleModelResultSurface:
    def test_visible_model_result_imports(self):
        from core.services.visible_model import VisibleModelResult
        assert VisibleModelResult is not None

    def test_visible_model_result_has_cache_fields(self):
        """Added 2026-05-22 (Claude) — cache_hit/miss fields surface
        DeepSeek prompt-cache utilisation upstream."""
        from core.services.visible_model import VisibleModelResult
        r = VisibleModelResult(
            text="x", input_tokens=10, output_tokens=2, cost_usd=0.0,
        )
        # Both fields must exist with sensible defaults
        assert hasattr(r, "cache_hit_tokens")
        assert hasattr(r, "cache_miss_tokens")
        assert r.cache_hit_tokens == 0
        assert r.cache_miss_tokens == 0

    def test_reasoning_content_default(self):
        """Pre-existing reasoning_content field must still exist."""
        from core.services.visible_model import VisibleModelResult
        r = VisibleModelResult(
            text="x", input_tokens=10, output_tokens=2, cost_usd=0.0,
        )
        assert r.reasoning_content == ""
