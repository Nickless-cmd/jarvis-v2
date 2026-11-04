from __future__ import annotations

from unittest.mock import patch

from core.services.prompt_mode_layout import (
    filter_visible_rules,
    mode_layout_v2_enabled,
    scope_stable_blocks_v3_enabled,
)
from core.services.prompt_sections.chat_mode import (
    _visible_chat_tone_instruction,
    _visible_mode_orientation_instruction,
)
from core.services.prompt_sections.visible_capability_truth import (
    _visible_capability_id_summary,
    _visible_capability_truth_instruction,
)
from core.services.visible_chat_pragmatics import (
    CHAT_MODE_HOW_I_TALK,
    build_chat_mode_dynamic_tail,
)


def test_kill_switch_env_overrides_config(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "0")
    assert mode_layout_v2_enabled() is False
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "yes")
    assert mode_layout_v2_enabled() is True


def test_kill_switch_restores_legacy_attention_envelope(monkeypatch):
    from core.services.attention_budget import get_attention_budget

    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "0")
    assert get_attention_budget("visible_full").total_char_target == 5000
    assert get_attention_budget("visible_full").mode_orientation.max_chars == 900
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    assert get_attention_budget("visible_full").total_char_target == 22000
    assert get_attention_budget("visible_full").mode_orientation.max_chars == 19000


def test_v3_has_an_independent_kill_switch_and_requires_v2(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    monkeypatch.setenv("JARVIS_PROMPT_SCOPE_STABLE_BLOCKS_V3", "1")
    assert scope_stable_blocks_v3_enabled(scope="chat") is True
    assert scope_stable_blocks_v3_enabled(scope="code") is True
    assert scope_stable_blocks_v3_enabled(scope="cowork") is False
    monkeypatch.setenv("JARVIS_PROMPT_SCOPE_STABLE_BLOCKS_V3", "0")
    assert scope_stable_blocks_v3_enabled(scope="code") is False
    monkeypatch.setenv("JARVIS_PROMPT_SCOPE_STABLE_BLOCKS_V3", "1")
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "0")
    assert scope_stable_blocks_v3_enabled(scope="code") is False


def test_v3_moves_catalog_and_code_orchestrator_without_duplicates(monkeypatch):
    from core.services.prompt_sections.agent_orchestration import _TEXT

    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    monkeypatch.setenv("JARVIS_PROMPT_SCOPE_STABLE_BLOCKS_V3", "1")
    monkeypatch.setattr(
        "core.services.agent_contract_service.capability_enabled", lambda: True,
    )
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="chat"):
        chat = _visible_mode_orientation_instruction(compact=False) or ""
        from core.services.tool_catalog import build_catalog_text
        assert "KERNE-VÆRKTØJER" in chat
        assert build_catalog_text() == ""
        assert "Agenter (orchestrator-v2)" not in chat
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="code"):
        code = _visible_mode_orientation_instruction(compact=False) or ""
        from core.services.prompt_sections.agent_orchestration import orchestrator_section
        assert "KERNE-VÆRKTØJER" in code
        assert _TEXT.format(version="orchestrator-v2") in code
        assert orchestrator_section() == ""


def test_v3_off_keeps_catalog_and_orchestrator_cache_late(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    monkeypatch.setenv("JARVIS_PROMPT_SCOPE_STABLE_BLOCKS_V3", "0")
    monkeypatch.setattr(
        "core.services.agent_contract_service.capability_enabled", lambda: True,
    )
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="code"):
        orientation = _visible_mode_orientation_instruction(compact=False) or ""
        from core.services.prompt_sections.agent_orchestration import orchestrator_section
        from core.services.tool_catalog import build_catalog_text
        assert "KERNE-VÆRKTØJER" not in orientation
        assert "KERNE-VÆRKTØJER" in build_catalog_text()
        assert "Agenter (orchestrator-v2)" in orchestrator_section()


def test_v2_chat_contract_is_cache_first_not_duplicated_in_tail(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="chat"):
        orientation = _visible_mode_orientation_instruction(compact=False) or ""
        tone = _visible_chat_tone_instruction(compact=False)
        tail = build_chat_mode_dynamic_tail(
            "existing", message="hej", session_id="layout-v2-chat",
        )
    assert CHAT_MODE_HOW_I_TALK in orientation
    assert "## Tone (chat)" in orientation
    assert tone is None
    assert CHAT_MODE_HOW_I_TALK not in tail
    assert "denne brugers samtalestil" in tail
    assert "current turn" in tail


def test_chat_orientation_keeps_read_only_investigation_in_chat(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="chat"):
        full = _visible_mode_orientation_instruction(compact=False) or ""
        compact = _visible_mode_orientation_instruction(compact=True) or ""

    for orientation in (full, compact):
        assert "Peg kun på code mode" in orientation
        assert "En read-only undersøgelse hører stadig til her" in orientation
        assert "brug dem fuldt ud" in orientation


def test_v2_code_contract_is_cache_first_plan_stays_dynamic(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="code"):
        orientation = _visible_mode_orientation_instruction(compact=False) or ""
        tail = build_chat_mode_dynamic_tail(
            "existing", message="ret den", session_id="layout-v2-code",
        )
    assert "Code mode: arbejdsadfærd" in orientation
    assert "Code mode: arbejdsadfærd" not in tail
    assert "cache-first code contract remains in force" in tail


def test_v2_code_keeps_exact_base_and_active_plan(monkeypatch):
    from core.services.prompt_sections.code_mode import base_section

    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="code"), \
         patch("core.services.plan_mode.prompt_section", return_value="ACTIVE PLAN STATE"):
        base = base_section(compact=False) or ""
        orientation = _visible_mode_orientation_instruction(compact=False) or ""
        tail = build_chat_mode_dynamic_tail(
            "", message="fortsæt", session_id="layout-v2-plan",
        )
    assert base in orientation
    assert "ACTIVE PLAN STATE" not in orientation
    assert "ACTIVE PLAN STATE" in tail


def test_kill_switch_restores_legacy_dynamic_placement(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "0")
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="chat"):
        orientation = _visible_mode_orientation_instruction(compact=False) or ""
        tone = _visible_chat_tone_instruction(compact=False)
        tail = build_chat_mode_dynamic_tail(
            "existing", message="hej", session_id="layout-legacy-chat",
        )
    assert CHAT_MODE_HOW_I_TALK not in orientation
    assert tone and "## Tone (chat)" in tone
    assert CHAT_MODE_HOW_I_TALK in tail


def test_capability_truth_matches_scope(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="chat"):
        chat = _visible_capability_truth_instruction(compact=False) or ""
        chat_ids = _visible_capability_id_summary() or ""
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="code"):
        code = _visible_capability_truth_instruction(compact=False) or ""
        code_ids = _visible_capability_id_summary() or ""
    assert "no shell, file-write, edit" in chat
    assert "no shell or file mutation" in chat_ids
    assert "inspect and mutate" in code
    assert "file, search, shell" in code_ids


def test_code_filters_only_conversational_visible_rules(monkeypatch):
    text = "\n".join([
        "Visible chat guidance rules:",
        "**Honesty:** keep",
        "- **I don't end the conversation:** chat only",
        "- **Format:** chat only",
        "- **Silence and authenticity:** chat only",
    ])
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "1")
    filtered = filter_visible_rules(text, scope="code") or ""
    assert "**Honesty:** keep" in filtered
    assert "I don't end" not in filtered
    assert "**Format:**" not in filtered
    assert filter_visible_rules(text, scope="chat") == text
    monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", "0")
    assert filter_visible_rules(text, scope="code") == text
