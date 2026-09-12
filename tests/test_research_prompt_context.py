import asyncio

from core.services.research_contract import ResearchPolicy
from core.services.research_prompt_context import research_context, research_prompt_section


def test_context_is_scoped_and_resets():
    with research_context(ResearchPolicy(source_target=7), skill_instructions="Use primary sources"):
        section = research_prompt_section()
        assert "RESEARCH CONTRACT" in section
        assert "Use primary sources" in section
        assert "7" in section
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
