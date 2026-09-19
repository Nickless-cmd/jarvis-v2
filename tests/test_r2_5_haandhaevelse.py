"""R2.5-håndhævelsen: en åben blok afviser næste mutation, indtil et kig tilbage.

Adfærden testes mod en falsk eventbus — samme kilde (``tool.completed``) som
verification_gate tæller fra, så testene måler den rigtige søm.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import r2_5_haandhaevelse as h

T0 = datetime(2026, 9, 19, 16, 0, tzinfo=UTC)


class _Bus:
    def __init__(self):
        self.events: list[dict] = []
        self.publiceret: list[tuple[str, dict]] = []

    def tool(self, vaerktoej, *, status="ok", efter_s=1, result=None):
        p = {"tool": vaerktoej, "status": status}
        if result is not None:
            p["result"] = result
        self.events.append({"kind": "tool.completed", "payload": p,
                            "created_at": (T0 + timedelta(seconds=efter_s)).isoformat()})

    def recent_by_family(self, family, *, limit=50):
        assert family == "tool"
        return list(reversed(self.events))[:limit]

    def publish(self, kind, data):
        self.publiceret.append((kind, data))


@pytest.fixture
def bus(monkeypatch):
    b = _Bus()
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "recent_by_family", b.recent_by_family)
    monkeypatch.setattr(bus_mod.event_bus, "publish", b.publish)
    monkeypatch.setattr("core.services.gate_enforcement.is_enforced", lambda *a, **k: True)
    h.nulstil()
    yield b
    h.nulstil()


def _aaben():
    h.aktiver({"action_line": "Næste move: read_file den fil du senest skrev til.",
               "tier": "fast", "threshold": 5, "unverified_effective": 6}, nu=T0)


NU = T0 + timedelta(seconds=30)


def test_uden_blok_koerer_alt(bus):
    assert h.afvis_mutation("edit_file", {"path": "x"}, nu=NU) is None


def test_aaben_blok_afviser_mutation_med_naeste_move(bus):
    _aaben()
    tekst = h.afvis_mutation("edit_file", {"path": "x"}, nu=NU)
    assert tekst and "R2.5" in tekst and "edit_file" in tekst
    assert "read_file den fil du senest skrev til" in tekst
    assert ("r2_5_gate.mutation_refused", {"tool": "edit_file", "refused": 1,
                                           "run_id": "", "tier": "fast"}) in bus.publiceret


def test_laesning_slipper_altid_igennem(bus):
    _aaben()
    for navn in ("read_file", "db_query", "verify_file_contains", "git_log"):
        assert h.afvis_mutation(navn, {}, nu=NU) is None


def test_shell_kun_afvist_naar_kommandoen_aendrer_noget(bus):
    _aaben()
    assert h.afvis_mutation("bash", {"command": "git status"}, nu=NU) is None
    assert h.afvis_mutation("bash", {"command": "rm -rf build"}, nu=NU)


@pytest.mark.parametrize("navn", ["bash_session_run", "operator_bash_session_run",
                                  "bash_session_open", "operator_bash_session_open"])
def test_bjoerns_bagdoer_gates_aldrig(bus, navn):
    """bash_session* og operator_bash_session* er Bjørns vej udenom — uanset hvad."""
    _aaben()
    assert h.afvis_mutation(navn, {"command": "rm -rf build"}, nu=NU) is None


def test_et_kig_tilbage_efter_blokken_loefter_den(bus):
    _aaben()
    bus.tool("read_file", efter_s=10)
    assert h.afvis_mutation("edit_file", {}, nu=NU) is None
    assert any(k == "r2_5_gate.released" and d["reason"] == "kig_tilbage"
               for k, d in bus.publiceret)
    # Og den er lukket — ikke bare sprunget over én gang.
    bus.events.clear()
    assert h.afvis_mutation("edit_file", {}, nu=NU) is None


def test_et_kig_FOER_blokken_loefter_den_ikke(bus):
    _aaben()
    bus.tool("read_file", efter_s=-5)
    assert h.afvis_mutation("edit_file", {}, nu=NU)


def test_et_fejlet_verify_er_ogsaa_et_kig_tilbage(bus):
    _aaben()
    bus.tool("verify_file_contains", status="failed")
    assert h.afvis_mutation("edit_file", {}, nu=NU) is None


def test_et_fejlet_readback_vaerktoej_loefter_ikke(bus):
    _aaben()
    bus.tool("read_file", status="error")
    assert h.afvis_mutation("edit_file", {}, nu=NU)


def test_et_read_only_shell_kald_er_et_kig_tilbage(bus):
    """R2.5's eget råd efter en bash er «kør en bash der inspicerer udfaldet»."""
    _aaben()
    bus.events.append({"kind": "tool.completed",
                       "payload": {"tool": "bash", "status": "ok", "mutating": False},
                       "created_at": (T0 + timedelta(seconds=3)).isoformat()})
    assert h.afvis_mutation("edit_file", {}, nu=NU) is None


def test_et_muterende_shell_kald_loefter_ikke(bus):
    _aaben()
    bus.events.append({"kind": "tool.completed",
                       "payload": {"tool": "bash", "status": "ok", "mutating": True},
                       "created_at": (T0 + timedelta(seconds=3)).isoformat()})
    assert h.afvis_mutation("edit_file", {}, nu=NU)


def test_en_skrivning_der_baerer_sit_readback_loefter_blokken(bus):
    _aaben()
    bus.tool("edit_file", result={"readback": True})
    assert h.afvis_mutation("write_file", {}, nu=NU) is None


def test_blokken_udloeber_med_gatens_vindue(bus):
    _aaben()
    assert h.afvis_mutation("edit_file", {}, nu=T0 + timedelta(minutes=9))
    assert h.afvis_mutation("edit_file", {}, nu=T0 + timedelta(minutes=11)) is None


def test_kill_switch_slukker_haandhaevelsen(bus, monkeypatch):
    noteret = []
    monkeypatch.setattr("core.services.gate_enforcement.is_enforced", lambda *a, **k: False)
    monkeypatch.setattr("core.services.gate_enforcement.note_suppressed_block",
                        lambda *a, **k: noteret.append(a))
    _aaben()
    assert h.afvis_mutation("edit_file", {}, nu=NU) is None
    assert noteret and noteret[0][0] == "r2_5_gate"


def test_gentagelse_bliver_en_synlig_incident(bus, monkeypatch):
    incidents = []
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: incidents.append(k))
    _aaben()
    h.afvis_mutation("edit_file", {}, run_id="r1", nu=NU)
    assert incidents == []
    h.afvis_mutation("edit_file", {}, run_id="r1", nu=NU)
    assert len(incidents) == 1
    assert incidents[0]["nerve"] == "r2_5_gate" and incidents[0]["dedup"] is True
    assert incidents[0]["run_id"] == "r1"


def test_kan_bussen_ikke_laeses_holdes_han_ikke_fast(bus, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("db væk")
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "recent_by_family", _boom)
    _aaben()
    assert h.afvis_mutation("edit_file", {}, nu=NU) is None


def test_r2_5_blokken_aabner_haandhaevelsen(bus, monkeypatch):
    """Sømmen: når R2.5 beslutter at blokere, er håndhævelsen åben bagefter."""
    from core.services import r2_5_blocking_gate as gate
    gate._last_block_at = None
    monkeypatch.setattr("core.services.verification_gate.evaluate_verification_gate",
                        lambda **k: {"failed_verify_count": 0, "unverified_effective": 9,
                                     "by_tool": {"edit_file": 9}, "suggestions": []})
    monkeypatch.setattr(gate, "_heed_rate_24h", lambda: 0.1)
    assert gate.should_block_for_verification(reasoning_tier="fast")
    assert h.afvis_mutation("edit_file", {})
    gate._last_block_at = None


def test_vaerktoejsloekken_afviser_og_koerer_ikke(bus, monkeypatch):
    """I executoren: en afvist mutation bliver et gate_blocked-svar, ikke et kald."""
    from core.services import simple_tool_executor as ex
    from core.services.commit_gate_arbiter import CommitGateOutcome
    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates",
                        lambda **k: CommitGateOutcome())
    monkeypatch.setattr("core.services.agentic_tool_cache.get_cached_result", lambda *a: None)
    h.aktiver({"action_line": "Næste move: kig.", "threshold": 5,
               "unverified_effective": 6})
    tc = {"id": "c1", "function": {"name": "edit_file", "arguments": {"path": "a.py"}}}
    kind, res = ex._prepare_call(tc, force=False, run_id="r1", session_id="s1",
                                 user_message="", controller=None, round_seen=set())
    assert kind == "result"
    assert res["status"] == "gate_blocked"
    assert res["result"]["gate_type"] == "r2_5_gate"
    assert res["result_text"].startswith("[r2_5_gate] R2.5:")
    # Læsning går stadig igennem til eksekvering.
    tc2 = {"id": "c2", "function": {"name": "read_file", "arguments": {"path": "a.py"}}}
    kind2, _ = ex._prepare_call(tc2, force=False, run_id="r1", session_id="s1",
                                user_message="", controller=None, round_seen=set())
    assert kind2 == "run"
