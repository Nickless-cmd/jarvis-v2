"""Unit-test for single-flight-guarden i detached-stien (rod-årsag-fix 2026-06-19).

To samtidige runs i samme session klobbede hinanden via active-run-singletonen.
Guarden bruger run_event_log (synkron create) som single-flight-autoritet.
"""
import core.services.run_event_log as rel
import core.services.visible_runs_sections.detached_run as dr


def _reset():
    rel._RUNS.clear()


def test_attaches_when_session_has_live_run(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr(dr, "start_user_run_detached",
                        lambda **kw: calls.append(kw) or "should-not-be-called")
    # En eksisterende, LIVE kørsel i sessionen (create = synkron, frisk = live)
    rel.create("visible-existing", "sess-1")
    rid, attached = dr.start_or_attach_user_run(
        message="anden besked", session_id="sess-1", nudge_enabled=False)
    assert attached is True
    assert rid == "visible-existing"
    assert calls == []  # spawnede IKKE et samtidigt run


def test_starts_fresh_when_no_live_run(monkeypatch):
    _reset()
    monkeypatch.setattr(dr, "start_user_run_detached",
                        lambda **kw: "visible-fresh")
    rid, attached = dr.start_or_attach_user_run(
        message="foerste", session_id="sess-2", nudge_enabled=False)
    assert attached is False
    assert rid == "visible-fresh"


def test_starts_fresh_when_existing_run_done(monkeypatch):
    _reset()
    monkeypatch.setattr(dr, "start_user_run_detached",
                        lambda **kw: "visible-fresh2")
    rel.create("visible-old", "sess-3")
    rel.mark_done("visible-old")  # afsluttet → ikke live → må starte frisk
    rid, attached = dr.start_or_attach_user_run(
        message="ny tur", session_id="sess-3", nudge_enabled=False)
    assert attached is False
    assert rid == "visible-fresh2"


def test_different_session_starts_fresh(monkeypatch):
    _reset()
    monkeypatch.setattr(dr, "start_user_run_detached",
                        lambda **kw: "visible-other")
    rel.create("visible-sessA", "sess-A")  # live run i ANDEN session
    rid, attached = dr.start_or_attach_user_run(
        message="i session B", session_id="sess-B", nudge_enabled=False)
    assert attached is False
    assert rid == "visible-other"
