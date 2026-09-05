"""Tests for Followup-cluster (followup_observer) — agentisk loop synlig i Centralen."""
from __future__ import annotations

import pytest

from core.services import followup_observer as fo


@pytest.fixture
def captured(monkeypatch):
    events = []
    monkeypatch.setattr(fo, "_observe",
                        lambda nerve, run_id, **d: events.append({"nerve": nerve, "run_id": run_id, **d}))
    return events


def test_note_round(captured):
    fo.note_round("r1", 2, "deepseek", "deepseek-v4-flash:cloud", exchanges=3)
    e = captured[0]
    assert e["nerve"] == "followup_round" and e["round_num"] == 2
    assert e["provider"] == "deepseek" and e["exchanges"] == 3


def test_note_round_failed_truncates_error(captured):
    fo.note_round_failed("r1", 1, "github-copilot", "x" * 400)
    e = captured[0]
    assert e["nerve"] == "followup_failed" and e["provider"] == "github-copilot"
    assert len(e["error"]) <= 200


def test_note_loop_complete(captured):
    fo.note_loop_complete("r1", rounds=4, exit_reason="completed", provider="p", model="m")
    e = captured[0]
    assert e["nerve"] == "followup_loop_complete" and e["rounds"] == 4
    assert e["exit_reason"] == "completed"


def test_note_truncation(captured):
    """Afkortet svar (finish_reason=length) skal være synligt i Centralen med
    længde + runde — aldrig tavs (2026-08-19: 'runnet stod som completed')."""
    fo.note_truncation("r1", provider="deepseek", model="deepseek-v4-flash",
                       text_len=12703, round_num=3)
    e = captured[0]
    assert e["nerve"] == "provider_length_truncation"
    assert e["text_len"] == 12703 and e["round_num"] == 3
    assert e["provider"] == "deepseek" and e["model"] == "deepseek-v4-flash"


def test_self_safe_on_central_failure(monkeypatch):
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    fo.note_round("r", 1)            # må ikke kaste
    fo.note_round_failed("r", 1)
    fo.note_loop_complete("r", rounds=1)
    fo.note_truncation("r", text_len=100, round_num=1)


def test_followup_summary_aggregates_avg(monkeypatch):
    class _Rec:
        def __init__(self, nerve, payload=None):
            self.cluster = "loop"; self.nerve = nerve; self.payload = payload or {}

    class _Sink:
        def recent(self, limit=500):
            return [_Rec("followup_round"), _Rec("followup_round"), _Rec("followup_failed"),
                    _Rec("followup_loop_complete", {"rounds": 4}),
                    _Rec("followup_loop_complete", {"rounds": 2}),
                    _Rec("tool_budget")]  # andet loop-nerve ignoreres i tællingen

    import core.services.central_trace as ct
    monkeypatch.setattr(ct, "sink", lambda: _Sink())
    s = fo.followup_summary()
    assert s["followup_rounds"] == 2 and s["followup_failures"] == 1
    assert s["followup_loops"] == 2 and s["avg_rounds_per_loop"] == 3.0


def test_followup_nerves_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("loop")]
    assert "followup_round" in names and "followup_failed" in names
    assert "followup_loop_complete" in names


# ── Tomme løfter når Centralen, 05-09-2026 ──────────────────────────────────
# Signalet landede KUN i trace-sinken (per-proces ring-buffer, tabt ved genstart).
# Centralen tæller `central_incidents`, så den kunne ikke se Jarvis' hyppigste
# fejl: den dag stod der ÉN `empty_completion` mod 31 faktiske tomme løfter.

@pytest.fixture
def incidents(monkeypatch):
    """Opsnapper incident-laget uden at røre databasen."""
    skrevet: list[dict] = []
    import core.runtime.db_central_incidents as dbi
    monkeypatch.setattr(dbi, "has_open_incident", lambda **k: False)
    monkeypatch.setattr(dbi, "bump_open_incident",
                        lambda **k: skrevet.append({"op": "bump", **k}))
    monkeypatch.setattr(dbi, "record_central_incident",
                        lambda **k: skrevet.append({"op": "record", **k}))
    return skrevet


def test_uindloest_loefte_bliver_en_error_incident(captured, incidents):
    fo.note_hollow_promise("r9", provider="deepseek", model="m", resolved=False)
    assert len(incidents) == 1
    i = incidents[0]
    assert i["nerve"] == "hollow_promise" and i["kind"] == "promise_broken"
    assert i["severity"] == "error"


def test_indloest_loefte_er_info_ikke_error(captured, incidents):
    """Et nudge der VIRKEDE må ikke larme som en fejl — ellers drukner de gange
    det ikke virkede, og det er dem der skal handles på."""
    fo.note_hollow_promise("r9", provider="deepseek", model="m", resolved=True)
    assert incidents[0]["severity"] == "info"
    assert incidents[0]["kind"] == "promise_kept"


def test_gentagelse_bumper_i_stedet_for_at_dedup_e_vaek(captured, monkeypatch):
    """Bjørn 29. jun: «centralen fanger det ikke» — tavs dedup skjulte frekvensen."""
    skrevet: list[dict] = []
    import core.runtime.db_central_incidents as dbi
    monkeypatch.setattr(dbi, "has_open_incident", lambda **k: True)
    monkeypatch.setattr(dbi, "bump_open_incident",
                        lambda **k: skrevet.append({"op": "bump", **k}))
    monkeypatch.setattr(dbi, "record_central_incident",
                        lambda **k: skrevet.append({"op": "record", **k}))
    fo.note_hollow_promise("r9", provider="deepseek", model="m", resolved=False)
    assert skrevet[0]["op"] == "bump"


def test_trace_signalet_bevares(captured, incidents):
    """Incidenten er TILFØJET — den gamle observe() må ikke være forsvundet."""
    fo.note_hollow_promise("r9", provider="deepseek", model="m", resolved=False)
    assert captured[0]["nerve"] == "hollow_promise"
    assert captured[0]["path"] == "still_hollow"


def test_incident_fejl_vaelter_aldrig_loopet(captured, monkeypatch):
    import core.runtime.db_central_incidents as dbi
    monkeypatch.setattr(dbi, "has_open_incident",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("db nede")))
    fo.note_hollow_promise("r9", provider="deepseek", model="m", resolved=False)
    assert captured[0]["nerve"] == "hollow_promise"
