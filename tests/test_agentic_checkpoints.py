from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass
class Result:
    tool_call_id: str
    tool_name: str
    content: str


@dataclass
class Exchange:
    text: str
    tool_calls: list[dict]
    results: list[Result]


def test_agentic_checkpoint_prompt_surfaces_last_round_state(isolated_runtime) -> None:
    checkpoints = importlib.import_module("core.services.agentic_checkpoints")
    checkpoints = importlib.reload(checkpoints)

    checkpoints.save_checkpoint(
        run_id="run-checkpoint",
        session_id="session-checkpoint",
        user_message="fix interrupted loop",
        provider="github-copilot",
        model="gpt-4o-mini",
        round_index=2,
        phase="round-complete",
        exchanges=[
            Exchange(
                text="read the files",
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": {"path": "README.md"}},
                    }
                ],
                results=[Result("call-1", "read_file", "README content")],
            )
        ],
        partial_text="I found the likely cause.",
    )

    section = checkpoints.checkpoint_prompt_section("session-checkpoint")

    assert section is not None
    assert "run-checkpoint" in section
    assert "round: 2" in section
    assert "read_file" in section
    assert "README content" in section
    assert "I found the likely cause" in section
