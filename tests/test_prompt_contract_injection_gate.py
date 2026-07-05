"""rule_conclusions læser injektion når live, ellers direkte build (rollback-gatet)."""
from __future__ import annotations
import inspect
import core.services.prompt_contract as pc


def test_rule_conclusions_reads_injection_when_live():
    src = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    assert 'injection_live("rule_conclusions")' in src
    assert 'read_injection("rule_conclusions")' in src


def test_cognitive_state_reads_injection_when_live():
    src = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    assert 'injection_live("cognitive_state")' in src
    assert 'read_injection("cognitive_state")' in src
