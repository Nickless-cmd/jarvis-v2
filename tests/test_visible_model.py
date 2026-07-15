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


# ── Stream-cluster: VISIBLE-lane provider-fejl synlige (2026-06-23) ──────────
def test_rate_limited_exception_observes(monkeypatch):
    """VisibleModelRateLimited.__init__ observerer HVER rate-limit (også first-pass)."""
    import core.services.visible_model as vm
    seen = {}
    class _C:
        def observe(self, ev): seen.update(ev)
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: _C())
    exc = vm.VisibleModelRateLimited("GitHub Copilot visible lane is rate-limited",
                                     provider="github-copilot", model="gpt-5.4")
    assert isinstance(exc, RuntimeError)
    assert seen["nerve"] == "provider_rate_limited" and seen["lane"] == "visible"
    assert seen["provider"] == "github-copilot"


def test_rate_limited_self_safe(monkeypatch):
    import core.services.visible_model as vm
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    # må ikke kaste fra __init__ (observabilitet må aldrig forstyrre fejl-stien)
    vm.VisibleModelRateLimited("boom")


def test_apply_visible_ollama_options_caps_num_ctx_to_model_window():
    """Bjørn 2026-06-23: num_ctx må ALDRIG overstige modellens reelle vindue.
    glm (200k) cappes selv om settings siger 512k; deepseek-flash (1M) urøres."""
    import core.services.visible_model as vm
    pg = {"model": "glm-5.2:cloud"}
    vm._apply_visible_ollama_options(pg)
    assert pg["options"]["num_ctx"] <= 200_000  # cappet til glm-vinduet

    pf = {"model": "deepseek-v4-flash:cloud"}
    vm._apply_visible_ollama_options(pf)
    # flash er 1M → num_ctx-settingen (≤512k) består uændret
    assert pf["options"]["num_ctx"] >= 200_000


class TestWS5V4ProGate:
    """WS5 (spec 2026-07-13): deepseek-v4-pro må KUN bruges owner + visible-lane
    + kill-switch tændt. Fail-safe: enhver usikkerhed → nedgradér til v4-flash,
    så den ~3× dyrere pro-model aldrig kan lække kost."""

    def _patch(self, monkeypatch, *, flag_on: bool, owner: bool):
        import core.services.visible_model as vm
        import core.runtime.db_core as db_core
        monkeypatch.setattr(
            db_core, "get_runtime_state_bool",
            lambda key, default=False: flag_on, raising=True,
        )
        monkeypatch.setattr(vm, "_turn_is_owner_scoped", lambda: owner)

    def test_owner_and_flag_on_allows_v4pro(self, monkeypatch):
        import core.services.visible_model as vm
        self._patch(monkeypatch, flag_on=True, owner=True)
        assert vm.gate_visible_model_tier("deepseek", "deepseek-v4-pro") == "deepseek-v4-pro"

    def test_non_owner_downgrades_v4pro_to_flash(self, monkeypatch):
        import core.services.visible_model as vm
        self._patch(monkeypatch, flag_on=True, owner=False)
        assert vm.gate_visible_model_tier("deepseek", "deepseek-v4-pro") == "deepseek-v4-flash"

    def test_flag_off_downgrades_v4pro_to_flash(self, monkeypatch):
        import core.services.visible_model as vm
        self._patch(monkeypatch, flag_on=False, owner=True)
        assert vm.gate_visible_model_tier("deepseek", "deepseek-v4-pro") == "deepseek-v4-flash"

    def test_default_fail_safe_no_cost_leak(self, monkeypatch):
        """Uden nogen flag/owner (rå default) → pro nedgraderes til flash."""
        import core.services.visible_model as vm
        self._patch(monkeypatch, flag_on=False, owner=False)
        assert vm.gate_visible_model_tier("deepseek", "deepseek-v4-pro") == "deepseek-v4-flash"

    def test_runtime_state_read_error_is_fail_safe(self, monkeypatch):
        import core.services.visible_model as vm
        import core.runtime.db_core as db_core

        def boom(*a, **k):
            raise RuntimeError("db nede")

        monkeypatch.setattr(db_core, "get_runtime_state_bool", boom)
        monkeypatch.setattr(vm, "_turn_is_owner_scoped", lambda: True)
        assert vm.gate_visible_model_tier("deepseek", "deepseek-v4-pro") == "deepseek-v4-flash"

    def test_flash_passes_through_unchanged(self, monkeypatch):
        import core.services.visible_model as vm
        self._patch(monkeypatch, flag_on=False, owner=False)
        assert vm.gate_visible_model_tier("deepseek", "deepseek-v4-flash") == "deepseek-v4-flash"

    def test_reasoner_alias_is_not_pro_tier(self, monkeypatch):
        """deepseek-reasoner er en flash-thinking-alias (WS4), IKKE pro-tier —
        den må ikke rammes/nedgraderes af pro-gaten."""
        import core.services.visible_model as vm
        self._patch(monkeypatch, flag_on=False, owner=False)
        assert vm.gate_visible_model_tier("deepseek", "deepseek-reasoner") == "deepseek-reasoner"

    def test_non_deepseek_provider_untouched(self, monkeypatch):
        import core.services.visible_model as vm
        self._patch(monkeypatch, flag_on=False, owner=False)
        # selv et 'pro'-navn hos anden provider er ikke DeepSeek-pro → urørt
        assert vm.gate_visible_model_tier("ollama", "some-pro-model") == "some-pro-model"

    def test_explicit_is_owner_override(self, monkeypatch):
        import core.services.visible_model as vm
        import core.runtime.db_core as db_core
        monkeypatch.setattr(db_core, "get_runtime_state_bool", lambda key, default=False: True)
        # is_owner=False eksplicit → nedgradér, uanset context-var
        assert vm.gate_visible_model_tier(
            "deepseek", "deepseek-v4-pro", is_owner=False
        ) == "deepseek-v4-flash"
        assert vm.gate_visible_model_tier(
            "deepseek", "deepseek-v4-pro", is_owner=True
        ) == "deepseek-v4-pro"
