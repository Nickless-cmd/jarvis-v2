from __future__ import annotations

import importlib


def test_working_conclusion_prompt_surfaces_next_step(isolated_runtime) -> None:
    conclusions = importlib.import_module("core.services.agentic_working_conclusions")
    conclusions = importlib.reload(conclusions)

    conclusions.update_working_conclusion(
        run_id="run-working",
        session_id="session-working",
        user_message="fix loop",
        round_index=3,
        observation="pytest failed because provider timeout is marked completed",
        next_step="change autonomous completion event to interrupted",
    )

    section = conclusions.working_conclusion_prompt_section("session-working")

    assert section is not None
    assert "round: 3" in section
    assert "provider timeout" in section
    assert "change autonomous completion" in section


def test_build_round_observation_falls_back_to_tool_results(isolated_runtime) -> None:
    conclusions = importlib.import_module("core.services.agentic_working_conclusions")
    conclusions = importlib.reload(conclusions)

    observation = conclusions.build_round_observation(
        text="",
        tool_names=["read_file"],
        result_texts=["important result"],
    )

    assert observation == "important result"
