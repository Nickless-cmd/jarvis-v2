import asyncio

from core.services.research_contract import ResearchPolicy
from core.services.research_prompt_context import research_context, research_prompt_section
from unittest.mock import patch


def test_context_is_scoped_and_resets():
    with research_context(ResearchPolicy(source_target=7), skill_instructions="Use primary sources"):
        section = research_prompt_section()
        assert "RESEARCH CONTRACT" in section
        assert "Use primary sources" in section
        assert "7" in section
        assert "immediately after the sentence or paragraph" in section
        assert "current, explicitly dated source" in section
        assert "navigation materially helps" in section
        assert "Never invent citations" in section
    assert research_prompt_section() == ""


def test_concurrent_contexts_are_isolated():
    async def read(target):
        with research_context(ResearchPolicy(source_target=target)):
            await asyncio.sleep(0)
            return research_prompt_section()

    async def run_both():
        return await asyncio.gather(read(2), read(9))

    one, two = asyncio.run(run_both())
    assert "source target: 2" in one.lower()
    assert "source target: 9" in two.lower()


def test_research_hierarchy_follows_mode_without_leaking_chat_into_code():
    with research_context(ResearchPolicy()):
        with patch("core.tools.tool_scoping.current_tool_scope", return_value="chat"):
            chat = research_prompt_section()
        with patch("core.tools.tool_scoping.current_tool_scope", return_value="code"):
            code = research_prompt_section()

    assert "inside CHAT MODE" in chat
    assert "subordinate to the active CODE MODE contract" in code
    assert "inside CHAT MODE" not in code


def test_preflight_requires_one_question_before_research():
    with research_context(ResearchPolicy(), clarification="Hvad skal undersøges?"):
        section = research_prompt_section()
    assert "material ambiguity" in section
    assert "Ask exactly one" in section
    assert "Hvad skal undersøges?" in section
