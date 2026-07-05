from __future__ import annotations
import core.services.central_governance as gov


def _store(monkeypatch):
    store = {}
    monkeypatch.setattr(gov, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(gov, "_kv_set", lambda k, v: store.update({k: v}))
    return store


def test_list_flags_returns_all_with_values_and_danger(monkeypatch):
    _store(monkeypatch)
    flags = gov.list_flags()
    keys = {f["key"] for f in flags}
    assert {"lag4_live", "gut_consumer_mode", "generative_autonomy", "self_prompt",
            "healer_enabled", "injection:cognitive_state"} <= keys
    lag4 = next(f for f in flags if f["key"] == "lag4_live")
    assert lag4["dangerous"] is True
    assert "value" in lag4
    sp = next(f for f in flags if f["key"] == "self_prompt")
    assert sp["dangerous"] is False


def test_set_nondangerous_flag_writes(monkeypatch):
    store = _store(monkeypatch)
    res = gov.set_flag("self_prompt", True, confirm=False)
    assert res["ok"] is True
    assert store.get("central_self_prompt_enabled") is True


def test_set_dangerous_flag_requires_confirm(monkeypatch):
    store = _store(monkeypatch)
    res = gov.set_flag("generative_autonomy", False, confirm=False)
    assert res["ok"] is False and res.get("needs_confirm") is True
    assert "generative_autonomy_enabled" not in store   # ikke skrevet
    res2 = gov.set_flag("generative_autonomy", False, confirm=True)
    assert res2["ok"] is True
    assert store.get("generative_autonomy_enabled") is False


def test_set_unknown_flag_errors(monkeypatch):
    _store(monkeypatch)
    res = gov.set_flag("nope", True, confirm=True)
    assert res["ok"] is False and "ukendt" in res.get("error", "").lower()


def test_enum_flag_validates_value(monkeypatch):
    _store(monkeypatch)
    ok = gov.set_flag("gut_consumer_mode", "shadow", confirm=True)
    assert ok["ok"] is True
    bad = gov.set_flag("gut_consumer_mode", "banana", confirm=True)
    assert bad["ok"] is False
