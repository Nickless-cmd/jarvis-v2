"""Tests for provider_health_check.health_section.

2026-05-22 (Claude): added after dropping HH:MM:SS timestamp from the
section text. The timestamp was breaking DeepSeek's prompt cache
because the line landed in the awareness block at a position where
it became the first per-build-varying content.
"""
from __future__ import annotations
import re


class TestHealthSectionNoTimestamp:
    def test_section_omits_clock_pattern(self):
        from core.services.provider_health_check import health_section
        s = health_section()
        if s is None:
            return  # nothing to check
        assert not re.search(r"\d{1,2}:\d{2}:\d{2}", s)

    def test_section_still_reports_unreachable(self):
        """The information content (unreachable list) must still be there."""
        from unittest.mock import patch
        from core.services.provider_health_check import health_section
        with patch(
            "core.services.provider_health_check.latest_health_snapshot",
            return_value={"unreachable": ["mistral", "groq"]},
        ):
            s = health_section()
        assert s is not None
        assert "mistral" in s
        assert "groq" in s
        assert "2 unreachable" in s


# ── Jarvis-spec-udvidelse 2026-06-23: model-drift + cheap-dry + flag/auto-resolve ──

def test_model_drift_flags_disappeared_models(monkeypatch):
    import core.services.provider_health_check as ph
    # FØR: groq havde 5 modeller; NU: 0 (model udfaset) → drift
    store = {"provider_health:model_counts": {"groq": 5}}
    import core.services.shared_cache as sc
    monkeypatch.setattr(sc, "get", lambda k: store.get(k))
    monkeypatch.setattr(sc, "set", lambda k, v, **kw: store.__setitem__(k, v))
    monkeypatch.setattr(ph, "_PING_ENDPOINTS", {"groq": "x"})
    monkeypatch.setattr("core.services.cheap_provider_runtime.list_provider_models",
                        lambda **k: {"status": "ok", "models": []})
    drift = ph._model_drift()
    assert drift == [{"provider": "groq", "had": 5, "now": 0}]


def test_no_drift_when_models_present(monkeypatch):
    import core.services.provider_health_check as ph
    store = {"provider_health:model_counts": {"groq": 5}}
    import core.services.shared_cache as sc
    monkeypatch.setattr(sc, "get", lambda k: store.get(k))
    monkeypatch.setattr(sc, "set", lambda k, v, **kw: store.__setitem__(k, v))
    monkeypatch.setattr(ph, "_PING_ENDPOINTS", {"groq": "x"})
    monkeypatch.setattr("core.services.cheap_provider_runtime.list_provider_models",
                        lambda **k: {"status": "ok", "models": [{"id": "a"}, {"id": "b"}]})
    assert ph._model_drift() == []


def test_observe_and_flag_self_safe(monkeypatch):
    import core.services.provider_health_check as ph
    # alt nede → må ikke kaste; returnerer struktureret rapport
    monkeypatch.setattr(ph, "health_check_all_providers",
                        lambda: {"results": {"groq": {"reachable": False}}, "unreachable": ["groq"],
                                 "reachable_count": 0, "total_count": 1})
    monkeypatch.setattr(ph, "_model_drift", lambda: [])
    monkeypatch.setattr(ph, "_cheap_dry_providers", lambda: [])
    flagged = []
    monkeypatch.setattr("core.runtime.db_central_incidents.has_unresolved_message", lambda **k: False)
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: flagged.append(k))
    monkeypatch.setattr("core.runtime.db_central_incidents.resolve_central_incidents", lambda **k: 0)
    rep = ph.observe_and_flag()
    assert rep["status"] == "ok" and rep["unreachable"] == 1
    assert any(f.get("kind") == "provider_down" for f in flagged)


def test_catalog_has_provider_health():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert cc.nerve_cluster("provider_health") == "system"
