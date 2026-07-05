"""dead_skills + null visible-bridge skal ikke længere bygges på visible-lanen."""
from __future__ import annotations
import inspect
import core.services.prompt_contract as pc


def test_dead_skills_not_called_in_assembly():
    src = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    assert "dead_skills_section(" not in src


def test_null_bridge_future_not_submitted():
    src = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    assert "_build_inner_visible_prompt_bridge_decision" not in src
