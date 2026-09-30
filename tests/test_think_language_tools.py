"""Værktøjet `think_language` — killswitch-kommandoen (30/9-2026).

Værktøjet er den kanal Bjørn skriver igennem. Testene fastholder at det
bekræfter sig selv ved at læse flaget tilbage (et «ok» er først sandt når den
læste værdi er den ønskede), og at en søgt handling ikke sætter noget.
"""
from __future__ import annotations

import core.services.think_language as tl
from core.tools.think_language_tools import (
    THINK_LANGUAGE_TOOL_DEFINITIONS,
    THINK_LANGUAGE_TOOL_HANDLERS,
    _exec_think_language,
)


def fake_kv(monkeypatch, start: dict | None = None) -> dict:
    """Erstat runtime-state med et in-memory-dict (ingen DB i testen)."""
    store: dict = dict(start or {})

    def _get(key, default=None):
        return store.get(key, default)

    def _set(key, value, **_kw):
        store[key] = value

    monkeypatch.setattr(tl, "get_runtime_state_value", _get)
    monkeypatch.setattr(tl, "set_runtime_state_value", _set)
    return store


def test_rundtur_og_readback(monkeypatch):
    store = fake_kv(monkeypatch)

    res = _exec_think_language({"action": "en"})
    assert res["status"] == "ok" and res["confirmed"] is True
    assert res["before"] == "da" and res["language"] == "en"
    assert store["think_language"] == "en", "flaget skal staa i butikken, ikke kun i svaret"

    res = _exec_think_language({"action": "da"})
    assert res["status"] == "ok" and res["language"] == "da"
    assert tl.directive() == "", "slukket igen → prompten er uaendret"


def test_status_uden_argumenter_laeser_aktivt_sprog(monkeypatch):
    fake_kv(monkeypatch, {"think_language": "en"})
    res = _exec_think_language({})
    assert res["status"] == "ok"
    assert res["language"] == "en"


def test_soegt_action_afvises_og_aendrer_intet(monkeypatch):
    fake_kv(monkeypatch)
    res = _exec_think_language({"action": "fr"})
    assert res["status"] == "error"
    assert tl.current() == "da", "en afvist handling maa ikke aendre flaget"


def test_definition_og_handler_er_parret():
    """Vagten i tests/test_tool_definition_v2.py fanger ellers et annonceret
    vaerktoej uden executor — her holdes parringen lokalt, saa fejlen ses her."""
    navne_def = {d["function"]["name"] for d in THINK_LANGUAGE_TOOL_DEFINITIONS}
    assert navne_def == set(THINK_LANGUAGE_TOOL_HANDLERS)
    assert navne_def == {"think_language"}
