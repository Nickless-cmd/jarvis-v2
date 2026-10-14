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
