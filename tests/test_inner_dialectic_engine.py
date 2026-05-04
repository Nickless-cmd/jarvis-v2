from __future__ import annotations


def test_inner_dialectic_balances_agi_research_frame(isolated_runtime) -> None:
    from core.services.inner_dialectic_engine import (
        build_inner_dialectic_prompt_section,
        run_inner_dialectic,
    )

    result = run_inner_dialectic(focus="AGI research and living Jarvis")
    assert "overclaiming" in result["critic"]["claim"]
    assert "Research" in result["ally"]["claim"]
    assert result["synthesis"]["next_move"]

    section = build_inner_dialectic_prompt_section()
    assert section is not None
    assert "Inner dialectic" in section
