from __future__ import annotations

from unittest.mock import patch

from core.services.prompt_mode_layout import (
    filter_visible_rules,
    mode_layout_v2_enabled,
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
