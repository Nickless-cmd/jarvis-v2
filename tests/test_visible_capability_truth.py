from __future__ import annotations

from unittest.mock import patch

from core.services.prompt_sections.visible_capability_truth import (
    _visible_capability_id_summary,
    _visible_capability_truth_instruction,
)


def test_capability_truth_is_scoped_to_chat_or_code(monkeypatch):
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
