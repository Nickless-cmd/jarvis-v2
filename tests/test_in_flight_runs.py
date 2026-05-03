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

    section = runs.interruption_prompt_section("session-resume")

    assert section is not None
    assert "ret tests og commit" in section
    assert "sidste tool var read_file" in section
    assert "provider-timeout" in section
    assert "fortsæt fra denne tilstand" in section
