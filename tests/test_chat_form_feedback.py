"""Formmålingen af forrige svar: dannes korrekt, når halen, rører ikke prefixet."""
from __future__ import annotations

from core.services import chat_form_feedback as cff
from core.services.visible_chat_pragmatics import build_chat_mode_dynamic_tail
from core.tools.tool_scoping import tool_scope

WALL = "\n\n".join(f"Afsnit nummer {i} med nogle ord i." for i in range(6))
MIXED = (
    "Intro der siger pointen.\n\n"
    "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\n"
    "- et\n- to\n- tre\n\n"
    "```py\nprint(1)\n\nprint(2)\n```\n\n"
    '```jarvis-ui\n{"type":"callout","body":"x"}\n```\n\n'
    "Slut."
)


def test_wall_of_prose_counts_paragraphs_and_no_surface():
    m = cff.measure_answer_form(WALL)
    assert m["paragraphs"] == 6 and m["surfaces"] == 0 and m["words"] == 6 * 7
    assert cff.form_line(m) == "Sidste svar: 6 afsnit uden flade, 0 flader, 42 ord"


def test_surfaces_counted_once_each():
    m = cff.measure_answer_form(MIXED)
    assert (m["tables"], m["lists"], m["code"], m["ui"]) == (1, 1, 1, 1)
    assert m["paragraphs"] == 2  # intro + slut; blank line inside fence ignored
    assert cff.form_line(m).startswith("Sidste svar: 2 afsnit, 4 flader")


def test_empty_text():
    assert cff.measure_answer_form("")["words"] == 0


def _rows(*pairs):
    return lambda sid, limit=6: [{"role": r, "content": c} for r, c in pairs]


def test_previous_assistant_answer_is_measured(monkeypatch):
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages", _rows(
        ("assistant", "gammelt svar"), ("user", "hej"), ("assistant", WALL), ("user", "nu"),
    ))
    assert cff.previous_answer_form_line("s1") == "Sidste svar: 6 afsnit uden flade, 0 flader, 42 ord"


def test_no_previous_answer_gives_none(monkeypatch):
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages", _rows(("user", "hej")))
    assert cff.previous_answer_form_line("s1") is None
    assert cff.previous_answer_form_line("") is None


def test_line_reaches_chat_tail_only_and_is_deterministic(monkeypatch):
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages", _rows(("assistant", WALL), ("user", "x")))
    with tool_scope("chat"):
        a = build_chat_mode_dynamic_tail("TAIL", message="hej", session_id="s1")
        b = build_chat_mode_dynamic_tail("TAIL", message="hej", session_id="s1")
    assert a == b  # byte-identisk inden for turen (runder i samme tur)
    assert a.count("Sidste svar:") == 1
    assert "6 afsnit uden flade" in a
    with tool_scope("code"):
        code = build_chat_mode_dynamic_tail("TAIL", message="hej", session_id="s1")
    assert "Sidste svar:" not in code


def test_line_is_not_in_stable_prefix():
    from core.services.prompt_sections.chat_mode import _visible_mode_orientation_instruction
    with tool_scope("chat"):
        prefix = _visible_mode_orientation_instruction(compact=False) or ""
    assert "Sidste svar:" not in prefix
