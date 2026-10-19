from __future__ import annotations


def _modules():
    from core.services import in_flight_runs as ifr
    from core.services import run_event_log as rel
    from core.services import run_stream_locator as locator

    rel._RUNS.clear()
    rel._ALIASER.clear()
    rel._ALIASER_OMVENDT.clear()
    return ifr, rel, locator


def test_mark_started_records_current_process_role(isolated_runtime, monkeypatch):
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "runtime")
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")

    assert ifr.get_record("r1")["producer_process"] == "runtime"


def test_locator_distinguishes_remote_running_from_unknown(
    isolated_runtime, monkeypatch
):
    ifr, _rel, locator = _modules()
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "runtime")
    ifr.mark_started(run_id="remote", session_id="s-remote", user_message="x")
    monkeypatch.setattr(ifr, "owner_still_alive", lambda _owner: True)

    found = locator.locate_run("remote")

    assert found.lifecycle == "running"
    assert found.producer_process == "runtime"
    assert found.local_available is False
    assert found.session_id == "s-remote"
    assert locator.locate_run("missing").lifecycle == "unknown"


def test_locator_reports_terminal_pruned_stream(isolated_runtime, monkeypatch):
    ifr, _rel, locator = _modules()
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "runtime")
    ifr.mark_started(run_id="done", session_id="s-done", user_message="x")
    ifr.settle_terminal("done", status="completed", reason="completed")

    found = locator.locate_run("done")

    assert found.lifecycle == "terminal"
    assert found.journal_status == "completed"
    assert found.local_available is False


def test_locator_reports_dead_owner_as_stale(isolated_runtime, monkeypatch):
    ifr, _rel, locator = _modules()
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "runtime")
    ifr.mark_started(run_id="dead", session_id="s-dead", user_message="x")
    monkeypatch.setattr(ifr, "owner_still_alive", lambda _owner: False)

    assert locator.locate_run("dead").lifecycle == "stale_owner"


def test_legacy_record_never_guesses_current_process(isolated_runtime, monkeypatch):
    ifr, _rel, locator = _modules()
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "api")
    ifr.mark_started(run_id="legacy", session_id="s-legacy", user_message="x")

    def remove_role(records):
        records["legacy"].pop("producer_process", None)

    ifr._mutate(remove_role)
    monkeypatch.setattr(ifr, "owner_still_alive", lambda _owner: True)

    found = locator.locate_run("legacy")

    assert found.lifecycle == "running"
    assert found.producer_process == "unknown"


def test_local_log_is_available_even_without_journal(isolated_runtime):
    _ifr, rel, locator = _modules()
    rel.create("local", "s-local")

    found = locator.locate_run("local")

    assert found.lifecycle == "running"
    assert found.local_available is True
    assert found.session_id == "s-local"


# ── active_locations: den funktion /chat/active-runs FAKTISK bruger ──────────
#
# Målt 19/10-2026: `locate_run` var testet for død ejer, men `active_locations`
# — den eneste vej ruten bruger — var ikke. Forskellen er ikke kosmetisk: den
# første svarer på «hvad ER dette run», den anden på «hvad skal desk'en vise
# som arbejdende». En post der aldrig blev afmeldt må ikke blive hængende som
# en spinner, og et run der arbejder må ikke forsvinde midt i et værktøjskald.


def _tom_journal(ifr) -> None:
    """Journalen er delt mellem tests i samme proces — ryd den, ellers måler
    hver test også de foregående tests' runs."""
    ifr._mutate(lambda r: (r.clear(), 0)[1])


def _alder(rec: dict, minutter: float) -> None:
    from datetime import UTC, datetime, timedelta

    t = (datetime.now(UTC) - timedelta(minutes=minutter)).isoformat()
    rec["started_at"] = t
    rec["last_progress_at"] = t


def test_active_locations_skjuler_run_hvis_ejerproces_er_doed(
    isolated_runtime, monkeypatch
):
    """En post hvis ejer er væk er en zombie — uanset hvor frisk den ser ud."""
    ifr, _rel, locator = _modules()
    _tom_journal(ifr)
    ifr.mark_started(run_id="zombie", session_id="s-z", user_message="x")
    monkeypatch.setattr(ifr, "owner_still_alive", lambda _owner: False)

    assert [l.run_id for l in locator.active_locations()] == []


def test_active_locations_skjuler_run_der_har_staaet_stille_over_loftet(
    isolated_runtime, monkeypatch
):
    """31 min uden et værktøjskald = dødt nok. Uden loftet ville posten
    blokere hvert efterfølgende wakeup for evigt."""
    ifr, _rel, locator = _modules()
    _tom_journal(ifr)
    ifr.mark_started(run_id="stille", session_id="s-s", user_message="x")
    monkeypatch.setattr(ifr, "owner_still_alive", lambda _owner: True)
    ifr._mutate(lambda r: (_alder(r["stille"], 31), 0)[1])

    assert [l.run_id for l in locator.active_locations()] == []


def test_active_locations_viser_run_der_lige_har_roert_sig(
    isolated_runtime, monkeypatch
):
    """29 min stille er stadig levende — loftet måler STILSTAND, ikke levetid.
    Et langt run der rørte sig for to minutter siden skal blive synligt."""
    ifr, _rel, locator = _modules()
    _tom_journal(ifr)
    ifr.mark_started(run_id="lang", session_id="s-l", user_message="x")
    monkeypatch.setattr(ifr, "owner_still_alive", lambda _owner: True)
    ifr._mutate(lambda r: (_alder(r["lang"], 29), 0)[1])

    assert [l.run_id for l in locator.active_locations()] == ["lang"]


def test_active_locations_maal_er_stilstand_ikke_samlet_levetid(
    isolated_runtime, monkeypatch
):
    """Et run startet for en time siden, men som rørte sig for et minut
    siden, ER levende. Det er hele grunden til at `last_progress_at` findes."""
    from datetime import UTC, datetime, timedelta

    ifr, _rel, locator = _modules()
    _tom_journal(ifr)
    ifr.mark_started(run_id="gammelt-men-levende", session_id="s-g", user_message="x")
    monkeypatch.setattr(ifr, "owner_still_alive", lambda _owner: True)

    def skru(records):
        rec = records["gammelt-men-levende"]
        rec["started_at"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        rec["last_progress_at"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()

    ifr._mutate(lambda r: (skru(r), 0)[1])

    assert [l.run_id for l in locator.active_locations()] == ["gammelt-men-levende"]
