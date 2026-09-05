"""Kun Bjørns egne ture må koste penge (2026-09-05).

Reglen stod i settings.py fra 16. juli, men lane-opslaget sker i
provider_router.json — og dér pegede `inner_enrichment` på api.deepseek.com i
omkring syv uger uden at nogen opdagede det. Vagten spørger det sted der
faktisk bestemmer.
"""
from __future__ import annotations

import pytest

from core.services import paid_lane_guard as PLG

_PAID = "https://api.deepseek.com/v1"
_FREE = "http://127.0.0.1:11434"


def _targets(mapping, monkeypatch):
    def _resolve(*, lane):
        if lane not in mapping:
            raise RuntimeError("ukendt lane")
        provider, model, url = mapping[lane]
        return {"provider": provider, "model": model, "base_url": url}
    monkeypatch.setattr(
        "core.runtime.provider_router.resolve_provider_router_target", _resolve)


def test_a_clean_setup_reports_nothing(monkeypatch):
    _targets({
        "visible": ("deepseek", "deepseek-v4-flash", _PAID),
        "inner_enrichment": ("ollama", "deepseek-v4-flash:cloud", _FREE),
        "local": ("ollama", "glm-5.2:cloud", _FREE),
        "cheap": ("aihubmix", "gpt-5.5-free", "https://aihubmix.com/v1"),
    }, monkeypatch)
    assert PLG.audit_paid_lanes() == []
    assert PLG.build_paid_lane_guard_surface()["ok"] is True


def test_the_actual_leak_is_caught(monkeypatch):
    """Praecis den tilstand der stod i syv uger."""
    _targets({
        "visible": ("deepseek", "deepseek-v4-flash", _PAID),
        "inner_enrichment": ("deepseek", "deepseek-v4-flash", _PAID),
    }, monkeypatch)
    leaks = PLG.audit_paid_lanes()
    assert len(leaks) == 1
    assert leaks[0]["lane"] == "inner_enrichment"
    assert leaks[0]["host"] == "api.deepseek.com"
    surface = PLG.build_paid_lane_guard_surface()
    assert surface["ok"] is False and "inner_enrichment" in surface["summary"]


def test_his_own_lanes_are_allowed_to_cost_money(monkeypatch):
    _targets({"visible": ("deepseek", "deepseek-v4-flash", _PAID)}, monkeypatch)
    assert PLG.audit_paid_lanes() == []
    assert "primary" in PLG._ALLOWED_PAID_LANES


@pytest.mark.parametrize("url,paid", [
    ("https://api.deepseek.com/v1", True),
    ("https://API.DeepSeek.com/v1/chat", True),
    ("http://127.0.0.1:11434", False),
    ("https://api.groq.com/openai/v1", False),
    ("", False),
    ("ikke en url", False),
])
def test_only_the_paid_host_counts(url, paid):
    assert PLG.is_paid(url) is paid


def test_an_unresolvable_lane_is_skipped_not_reported(monkeypatch):
    _targets({"visible": ("deepseek", "x", _PAID)}, monkeypatch)  # resten kaster
    assert PLG.audit_paid_lanes() == []


def test_the_guard_never_fixes_anything_itself(monkeypatch):
    """Et lane-valg er en driftsbeslutning. Vagten maa goere det synligt,
    ikke lave det om bag ryggen paa Bjoern."""
    import inspect
    src = inspect.getsource(PLG)
    for forbidden in ("configure_provider_router_entry", "write_text", "set_runtime_state_value"):
        assert forbidden not in src


def test_a_broken_resolver_never_raises(monkeypatch):
    def _boom(**_kw):
        raise RuntimeError("registret er vaek")
    monkeypatch.setattr(
        "core.runtime.provider_router.resolve_provider_router_target", _boom)
    assert PLG.audit_paid_lanes() == []
    assert PLG.check_paid_lanes()["leaks"] == []
