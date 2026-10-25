"""Direct guards for the extracted, cache-stable chat-mode sections."""
from __future__ import annotations

from unittest.mock import patch

from core.services.prompt_sections.chat_mode import (
    _visible_chat_tone_instruction,
    _visible_mode_orientation_instruction,
)


def test_chat_tone_is_flexible_and_not_a_mechanical_hook():
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="chat"):
        text = _visible_chat_tone_instruction(compact=False) or ""

    assert "Reager først" in text
    assert "Formen er en del af nærværet" in text
    assert "overskrifter, fremhævelse eller lister" in text
    assert "Slut med en krog" not in text
    assert "Højst tre linjer" not in text
    assert "Bjørns nuværende besked" in text


def test_code_mode_keeps_chat_tone_out_but_retains_orientation():
    with patch("core.tools.tool_scoping.current_tool_scope", return_value="code"):
        assert _visible_chat_tone_instruction(compact=False) is None
        orientation = _visible_mode_orientation_instruction(compact=False) or ""

    assert "CODE MODE" in orientation
    assert "CHAT MODE" not in orientation
