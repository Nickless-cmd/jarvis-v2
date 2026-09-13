"""Tests for per-kald gate-override (lag 2, 13/9-2026).

Kontrakten (Bjørn: "B med C som forudsætning"):
- Gaten fyrer og logger FØRST. Overstyringen er et SVAR på signalet, ikke en vej udenom.
- Én one-shot, forbrugt ved brug. Næste kald skal overstyres igen.
- Udløber ubrugt. In-memory — genstart giver håndhævelsen tilbage.
- SECURITY kan aldrig (§11.3).
- Begrundelse er påkrævet: en overstyring uden grund er en tavs omgåelse.
"""
from __future__ import annotations

import time

import pytest

from core.services import gate_override as go

_FIRM_SECTION = (
    "PUSHBACK\n"
    "- feeling=protectiveness intensity=0.81 action=firm_pushback\n"
    "- evidence: risk marker: 'push'\n"
)


# ── fake DB (arm_override slår hændelsen op i veto_events) ──────────────────

class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row

    def fetchall(self):
        return [self._row] if self._row else []


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
    """row = (tool_name, feeling, veto_result, resolution) eller None."""
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "connect", lambda: _FakeConn(row))


@pytest.fixture(autouse=True)
def _clean():
    go._reset_for_tests()
    yield
    go._reset_for_tests()


# ── arm_override: afvisninger ──────────────────────────────────────────────

def test_arm_afviser_tom_begrundelse():
    r = go.arm_override("veto-abc", "   ")
    assert r["status"] == "error" and "begrundelse" in r["error"]


def test_arm_afviser_tomt_event_id():
    r = go.arm_override("", "fordi")
    assert r["status"] == "error" and "event_id" in r["error"]


def test_arm_afviser_security_nerve():
    """§11.3 — samme invariant som gate_enforcement, ét sted mere."""
    r = go.arm_override("veto-abc", "fordi", nerve="exec_workspace_trust")
    assert r["status"] == "error" and "SECURITY" in r["error"]


def test_arm_afviser_ukendt_event(monkeypatch):
    _fake_event_lookup(monkeypatch, None)
    r = go.arm_override("veto-findes-ikke", "fordi")
    assert r["status"] == "error" and "ukendt" in r["error"]


def test_arm_afviser_ikke_blokeret_haendelse(monkeypatch):
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "allowed", "pending"))
    r = go.arm_override("veto-abc", "fordi")
    assert r["status"] == "error" and "intet at overstyre" in r["error"]


def test_arm_afviser_allerede_afsluttet(monkeypatch):
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "honored"))
    r = go.arm_override("veto-abc", "fordi")
    assert r["status"] == "error" and "afsluttet" in r["error"]


def test_arm_afviser_reasoning_raekke_uden_vaerktoej(monkeypatch):
    """Rækker med tomt tool_name kom fra reasoning-vejen (lukket 00080eb5)."""
    _fake_event_lookup(monkeypatch, ("", "protectiveness", "blocked", "pending"))
    r = go.arm_override("veto-abc", "fordi")
    assert r["status"] == "error" and "intet værktøj" in r["error"]


# ── arm → consume ──────────────────────────────────────────────────────────

def test_arm_og_consume_returnerer_begrundelse(monkeypatch):
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "pending"))
    monkeypatch.setattr(go, "_notify_owner", lambda *a: None)
    monkeypatch.setattr("core.services.veto_gate.record_jarvis_override", lambda t, f: 1)
    monkeypatch.setattr("core.services.veto_gate.resolve_veto_event", lambda e, r: None)

    r = go.arm_override("veto-abc", "gaten læste sin egen prompttekst")
    assert r["status"] == "ok" and r["armed"] is True
    assert r["tool_name"] == "write_file" and r["feeling"] == "protectiveness"

    assert go.consume_override("write_file", "protectiveness") == "gaten læste sin egen prompttekst"


def test_one_shot_forbruges_kun_en_gang(monkeypatch):
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "pending"))
    monkeypatch.setattr(go, "_notify_owner", lambda *a: None)
    monkeypatch.setattr("core.services.veto_gate.record_jarvis_override", lambda t, f: 1)
    monkeypatch.setattr("core.services.veto_gate.resolve_veto_event", lambda e, r: None)

    go.arm_override("veto-abc", "fordi")
    assert go.consume_override("write_file", "protectiveness") is not None
    # Forbrugt = væk. Næste kald skal overstyres igen — så det skal menes hver gang.
    assert go.consume_override("write_file", "protectiveness") is None


def test_consume_uden_armering_er_none():
    assert go.consume_override("write_file", "protectiveness") is None


def test_consume_paa_forkert_vaerktoej_er_none(monkeypatch):
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "pending"))
    go.arm_override("veto-abc", "fordi")
    assert go.consume_override("db_query", "protectiveness") is None
    # ... og armeringen ligger stadig urørt.
    assert go.override_state()["armed_count"] == 1


def test_udloebet_ubrugt_armering_rammer_ikke(monkeypatch):
    """En armeret overstyring der aldrig bruges er bare en glemt knap — den udløber."""
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "pending"))
    go.arm_override("veto-abc", "fordi", ttl_seconds=1)
    # Simulér at TTL'en er passeret.
    with go._LOCK:
        for a in go._ARMED.values():
            a.expires_at = time.monotonic() - 1.0
    assert go.consume_override("write_file", "protectiveness") is None
    assert go.override_state()["armed_count"] == 0


def test_ttl_har_et_haardt_loft(monkeypatch):
    """Bjørn: "korter end 15 min" — loftet er 14 min, ikke 15."""
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "pending"))
    r = go.arm_override("veto-abc", "fordi", ttl_seconds=99999)
    assert r["ttl_seconds"] == go._MAX_TTL_SECONDS
    assert go._MAX_TTL_SECONDS < 900.0


def test_ingen_persistens_reset_toemmer(monkeypatch):
    """In-memory: genstart giver håndhævelsen tilbage. Reset = genstart-semantik."""
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "pending"))
    go.arm_override("veto-abc", "fordi")
    assert go.override_state()["armed_count"] == 1
    go._reset_for_tests()
    assert go.override_state()["armed_count"] == 0
    assert go.override_state()["persistent"] is False


def test_state_rapporterer_armeret(monkeypatch):
    _fake_event_lookup(monkeypatch, ("write_file", "protectiveness", "blocked", "pending"))
    go.arm_override("veto-abc", "fordi")
    st = go.override_state()
    assert st["armed_count"] == 1
    assert st["armed"][0]["tool_name"] == "write_file"
    assert st["armed"][0]["seconds_left"] > 0


# ── integration med check_veto ─────────────────────────────────────────────

def _isolate_veto(monkeypatch, written: list[dict]):
    from core.services import veto_gate as vg
    monkeypatch.setattr(vg, "_check_token_signal_gate", lambda msg, tool: False)
    monkeypatch.setattr(vg, "_adaptive_threshold", lambda tool, feeling, intensity: 0.5)
    monkeypatch.setattr(vg, "log_veto_event", lambda **kw: (written.append(kw) or "veto-test"))
    monkeypatch.setattr("core.services.pushback.affective_pushback_section",
                        lambda msg: _FIRM_SECTION)
    return vg


def test_check_veto_forbruger_armeret_override(monkeypatch):
    """Armeret one-shot → gaten fyrer, men Jarvis' svar lukker den igennem."""
    from core.services import gate_override as go2
    written: list[dict] = []
    vg = _isolate_veto(monkeypatch, written)
    learned: list[tuple[str, str]] = []
    monkeypatch.setattr(vg, "record_jarvis_override", lambda t, f: (learned.append((t, f)) or 1))
    monkeypatch.setattr(vg, "resolve_veto_event", lambda e, r: None)
    monkeypatch.setattr(go2, "_notify_owner", lambda *a: None)

    go2._ARMED[("write_file", "protectiveness")] = go2._Armed(
        tool_name="write_file", feeling="protectiveness", event_id="veto-x",
        reason="gaten tog fejl", expires_at=time.monotonic() + 60)

    allowed, reason = vg.check_veto("write_file", "jeg pusher nu")
    assert allowed is True and reason is None
    # Sporet skal vise at gaten fyrede OG at Jarvis svarede — ikke en tavs omgåelse.
    assert written[0]["veto_result"] == "overridden"
    assert written[0]["resolution"] == "overridden_by_jarvis"
    # Læringen: tærsklen skal stige for netop denne kombination.
    assert learned == [("write_file", "protectiveness")]


def test_check_veto_uden_armering_blokerer_som_foer(monkeypatch):
    """Regression: uden en armering er gaten uændret."""
    written: list[dict] = []
    vg = _isolate_veto(monkeypatch, written)
    allowed, reason = vg.check_veto("write_file", "jeg pusher nu")
    assert allowed is False and "VETO" in reason
    assert written[0]["veto_result"] == "blocked"


def test_override_er_one_shot_ogsaa_gennem_check_veto(monkeypatch):
    from core.services import gate_override as go2
    written: list[dict] = []
    vg = _isolate_veto(monkeypatch, written)
    monkeypatch.setattr(vg, "record_jarvis_override", lambda t, f: 1)
    monkeypatch.setattr(vg, "resolve_veto_event", lambda e, r: None)
    monkeypatch.setattr(go2, "_notify_owner", lambda *a: None)

    go2._ARMED[("write_file", "protectiveness")] = go2._Armed(
        tool_name="write_file", feeling="protectiveness", event_id="veto-x",
        reason="fordi", expires_at=time.monotonic() + 60)

    assert vg.check_veto("write_file", "jeg pusher nu")[0] is True
    # Andet kald: armeringen er væk → gaten blokerer igen.
    assert vg.check_veto("write_file", "jeg pusher nu")[0] is False


def test_record_event_false_forbruger_ikke_en_armering(monkeypatch):
    """En genanvendelse af gaten (reasoning-vejen) må ikke brænde en armering af."""
    from core.services import gate_override as go2
    written: list[dict] = []
    vg = _isolate_veto(monkeypatch, written)
    go2._ARMED[("write_file", "protectiveness")] = go2._Armed(
        tool_name="write_file", feeling="protectiveness", event_id="veto-x",
        reason="fordi", expires_at=time.monotonic() + 60)

    allowed, _ = vg.check_veto("write_file", "jeg pusher nu", record_event=False)
    assert allowed is False           # dømmekraften kører uændret
    assert written == []              # ... men skriver intet
    assert go2.override_state()["armed_count"] == 1  # armeringen er urørt
