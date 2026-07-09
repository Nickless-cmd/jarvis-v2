from __future__ import annotations

import importlib


def test_interrupted_record_survives_next_started_run_for_resume(isolated_runtime, monkeypatch):
    runs = importlib.import_module("core.services.in_flight_runs")
    runs = importlib.reload(runs)

    monkeypatch.setattr(runs, "_MIN_AGE_TO_SURFACE_SECONDS", 0)

    runs.mark_started(
        run_id="run-interrupted",
        session_id="session-resume",
        user_message="ret tests og commit",
    )
    runs.mark_tool("run-interrupted", "read_file")
    runs.mark_interrupted(
        "run-interrupted",
        reason="provider-timeout",
        summary="followup-round-2-timeout",
    )

    runs.mark_started(
        run_id="run-retry",
        session_id="session-resume",
        user_message="prøv igen",
    )

    section = runs.interruption_prompt_section("session-resume", user_message="prøv igen")

    assert section is not None
    assert "ret tests og commit" in section
    assert "sidste tool var read_file" in section
    assert "provider-timeout" in section
    assert "AUTO-RESUME" in section


def test_resume_intent_policy_distinguishes_restart_and_unclear(isolated_runtime) -> None:
    runs = importlib.import_module("core.services.in_flight_runs")
    runs = importlib.reload(runs)

    assert runs.classify_resume_intent("prøv igen") == "resume"
    assert runs.classify_resume_intent("fortsæt lige") == "resume"
    assert runs.classify_resume_intent("start forfra med noget andet") == "restart"
    assert runs.classify_resume_intent("hvad tænker du?") == "unclear"


def test_mark_started_persists_kind_provider_model(isolated_runtime) -> None:
    runs = importlib.import_module("core.services.in_flight_runs")
    runs = importlib.reload(runs)

    runs.mark_started(
        run_id="run-meta",
        session_id="s1",
        user_message="gør noget",
        kind="autonomous",
        provider="deepseek",
        model="deepseek-chat",
    )
    rec = runs._load()["run-meta"]
    assert rec["kind"] == "autonomous"
    assert rec["provider"] == "deepseek"
    assert rec["model"] == "deepseek-chat"


def test_mark_started_defaults_kind_visible(isolated_runtime) -> None:
    runs = importlib.import_module("core.services.in_flight_runs")
    runs = importlib.reload(runs)

    runs.mark_started(run_id="run-default", session_id="s1", user_message="hej")
    rec = runs._load()["run-default"]
    assert rec["kind"] == "visible"
    assert rec["provider"] == ""
    assert rec["model"] == ""


def test_list_running_orphans_returns_only_stale_running(isolated_runtime, monkeypatch) -> None:
    import importlib as _il
    from datetime import UTC, datetime, timedelta

    runs = _il.import_module("core.services.in_flight_runs")
    runs = _il.reload(runs)

    now = datetime.now(UTC)
    records = {
        # stale running -> orphan
        "run-stale": {
            "run_id": "run-stale", "session_id": "s1", "status": "running",
            "excerpt": "gammelt", "started_at": (now - timedelta(seconds=1000)).isoformat(),
            "last_tool": "",
        },
        # fresh running -> NOT orphan
        "run-fresh": {
            "run_id": "run-fresh", "session_id": "s2", "status": "running",
            "excerpt": "friskt", "started_at": (now - timedelta(seconds=5)).isoformat(),
            "last_tool": "",
        },
        # stale but already interrupted -> NOT orphan
        "run-interrupted": {
            "run_id": "run-interrupted", "session_id": "s3", "status": "interrupted",
            "excerpt": "afbrudt", "started_at": (now - timedelta(seconds=1000)).isoformat(),
            "last_tool": "",
        },
    }
    runs._save(records)

    orphans = runs.list_running_orphans(600)
    ids = {o["run_id"] for o in orphans}
    assert ids == {"run-stale"}


def test_list_running_orphans_handles_bad_started_at(isolated_runtime) -> None:
    import importlib as _il

    runs = _il.import_module("core.services.in_flight_runs")
    runs = _il.reload(runs)

    runs._save({
        "run-bad": {
            "run_id": "run-bad", "session_id": "s1", "status": "running",
            "excerpt": "x", "started_at": "not-a-date", "last_tool": "",
        },
    })
    # Must not raise; unparseable started_at is not counted as a confirmed orphan.
    assert runs.list_running_orphans(600) == []
