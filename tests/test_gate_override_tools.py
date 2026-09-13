"""Tests for gate-override-værktøjet (lag 2, 13/9-2026).

Dækker ``core/tools/gate_override_tools.py``: at de to værktøjer er korrekt
defineret, at handlerne videresender til ``core/services/gate_override.py``, og —
vigtigst — at de ALDRIG kaster. Et værktøj i den agentiske løkke må ikke kunne
vælte en tur fordi en hjælpefunktion fejler.
"""
from __future__ import annotations

import pytest

from core.tools import gate_override_tools as got
from core.services import gate_override as go


# ── fake DB (arm_override slår hændelsen op i veto_events) ──────────────────

class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConn:
    def __init__(self, row):
        self._row = row

    def execute(self, _sql, _params=()):
        return _FakeCursor(self._row)

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _fake_event_lookup(monkeypatch, row):
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "connect", lambda: _FakeConn(row))


@pytest.fixture(autouse=True)
def _clean():
    go._reset_for_tests()
    yield
    go._reset_for_tests()


# ── definitions ────────────────────────────────────────────────────────────

def _defs() -> dict[str, dict]:
    return {d["function"]["name"]: d["function"] for d in got.GATE_OVERRIDE_TOOL_DEFINITIONS}


def test_definitions_indeholder_begge_vaerktoejer():
    names = set(_defs())
    assert names == {"override_gate", "gate_override_status"}


def test_override_gate_kraever_event_id_og_begrundelse():
    """En overstyring uden grund er en tavs omgåelse — felterne SKAL være påkrævede."""
    fn = _defs()["override_gate"]
    assert fn["parameters"]["required"] == ["event_id", "reason"]


def test_override_gate_beskrivelse_nævner_security_invarianten():
    """§11.3 skal stå i beskrivelsen — så modellen kender grænsen før den kalder."""
    assert "SECURITY" in _defs()["override_gate"]["description"]


def test_status_vaerktoej_har_ingen_paakraevede_felter():
    assert _defs()["gate_override_status"]["parameters"]["required"] == []


def test_handlers_matcher_definitions():
    """Ethvert defineret værktøj skal have en handler — ellers er det en død flade."""
    assert set(got.GATE_OVERRIDE_TOOL_HANDLERS) == set(_defs())


# ── _exec_override_gate ────────────────────────────────────────────────────

def _arm_ok(monkeypatch):
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "pending"))
    monkeypatch.setattr(go, "_notify_owner", lambda *a: None)
    monkeypatch.setattr("core.services.veto_gate.record_jarvis_override", lambda t, f: 1)
    monkeypatch.setattr("core.services.veto_gate.resolve_veto_event", lambda e, r: None)


def test_override_gate_armerer_og_videresender_begrundelse(monkeypatch):
    _arm_ok(monkeypatch)
    r = got._exec_override_gate({
        "event_id": "veto-abc",
        "reason": "gaten læste sin egen prompttekst",
    })
    assert r["status"] == "ok" and r["armed"] is True
    assert r["tool_name"] == "write_file" and r["feeling"] == "protectiveness"
    assert r["reason"] == "gaten læste sin egen prompttekst"


def test_override_gate_afviser_tom_begrundelse(monkeypatch):
    _arm_ok(monkeypatch)
    r = got._exec_override_gate({"event_id": "veto-abc", "reason": "   "})
    assert r["status"] == "error" and "begrundelse" in r["error"]


def test_override_gate_afviser_manglende_event_id(monkeypatch):
    _arm_ok(monkeypatch)
    r = got._exec_override_gate({"reason": "fordi"})
    assert r["status"] == "error" and "event_id" in r["error"]


def test_override_gate_respekterer_ttl_loft(monkeypatch):
    """Bjørn: "korter end 15 min" — også når kalderen beder om mere."""
    _arm_ok(monkeypatch)
    r = got._exec_override_gate({"event_id": "veto-abc", "reason": "fordi",
                                 "ttl_seconds": 99999})
    assert r["ttl_seconds"] == go._MAX_TTL_SECONDS


def test_override_gate_uden_ttl_bruger_default(monkeypatch):
    _arm_ok(monkeypatch)
    r = got._exec_override_gate({"event_id": "veto-abc", "reason": "fordi"})
    assert r["ttl_seconds"] == go._DEFAULT_TTL_SECONDS


def test_override_gate_kaster_aldrig_naar_servicen_fejler(monkeypatch):
    """Self-safe: en fejl i hjælpefunktionen må ikke vælte den agentiske løkke."""
    def _boom(*_a, **_kw):
        raise RuntimeError("db nede")

    monkeypatch.setattr(go, "arm_override", _boom)
    r = got._exec_override_gate({"event_id": "veto-abc", "reason": "fordi"})
    assert r["status"] == "error" and "override_gate fejlede" in r["error"]


def test_override_gate_taaler_none_args():
    """Forsvar mod et tomt argument-dict — skal give en pæn fejl, ikke en TypeError."""
    r = got._exec_override_gate({})
    assert r["status"] == "error"


# ── _exec_gate_override_status ─────────────────────────────────────────────

def test_status_uden_armering_er_tom_men_ok():
    r = got._exec_gate_override_status({})
    assert r["status"] == "ok"
    assert r["armed_count"] == 0
    assert r["persistent"] is False


def test_status_viser_armeret_efter_arm(monkeypatch):
    _arm_ok(monkeypatch)
    got._exec_override_gate({"event_id": "veto-abc", "reason": "fordi"})
    r = got._exec_gate_override_status({})
    assert r["armed_count"] == 1
    assert r["armed"][0]["tool_name"] == "write_file"


def test_status_kaster_aldrig_naar_servicen_fejler(monkeypatch):
    def _boom(*_a, **_kw):
        raise RuntimeError("nede")

    monkeypatch.setattr(go, "override_state", _boom)
    r = got._exec_gate_override_status({})
    assert r["status"] == "error" and "gate_override_status fejlede" in r["error"]
