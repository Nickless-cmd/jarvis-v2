"""Live killswitch for samtale-reglerne — den skal virke UDEN genstart."""
from __future__ import annotations

from unittest.mock import patch

from core.services import chat_conversation_rules as ccr


def _scope(scope: str):
    return patch(
        "core.tools.tool_scoping.current_tool_scope", return_value=scope
    )


def test_standard_er_til_naar_filen_mangler(monkeypatch):
    monkeypatch.setattr(ccr, "load_json", lambda *a, **k: {})
    assert ccr.enabled() is True


def test_kill_slaar_fra_og_revive_slaar_til(monkeypatch):
    state = {"enabled": True}

    def _load(key, default):
        return dict(state)

    def _save(key, data):
        state.clear()
        state.update(data)

    monkeypatch.setattr(ccr, "load_json", _load)
    monkeypatch.setattr("core.runtime.state_store.save_json", _save)
    assert ccr.section(compact=False) is not None

    ccr.kill("test")
    assert ccr.enabled() is False
    assert ccr.section(compact=False) is None, "killswitchen skal virke fra næste build"

    ccr.revive()
    assert ccr.enabled() is True
    assert ccr.section(compact=False) is not None


def test_gælder_kun_chat_scope(monkeypatch):
    monkeypatch.setattr(ccr, "load_json", lambda *a, **k: {})
    with _scope("code"):
        assert ccr.section(compact=False) is None
    with _scope("chat"):
        assert ccr.section(compact=False) is not None


def test_reglerne_naevner_forbud_og_substans(monkeypatch):
    monkeypatch.setattr(ccr, "load_json", lambda *a, **k: {})
    with _scope("chat"):
        tekst = ccr.section(compact=False) or ""
    assert "jeg husker" in tekst.lower()
    assert "substans-testen" in tekst.lower()
    assert "selvnedgørelse" in tekst.lower()
