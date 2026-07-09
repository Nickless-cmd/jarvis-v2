"""_build_turn_blocks: byg kanonisk content-blok-array for en assistant-tur."""
from core.services.content_blocks import content_blocks_to_text
from core.services.visible_runs import _build_turn_blocks


def test_build_blocks_orders_text_and_tools():
    blocks = _build_turn_blocks(
        text="Der er to filer.",
        tool_calls=[{"id": "toolu_1", "name": "bash", "input": {"cmd": "ls"}}],
        tool_results=[{"tool_use_id": "toolu_1", "status": "done", "content": "a\nb", "is_error": False}],
    )
    types = [b["type"] for b in blocks]
    assert "tool_use" in types and "tool_result" in types and "text" in types
    # Tekst-projektionen forbliver ren prosa.
    assert content_blocks_to_text(blocks) == "Der er to filer."
    # tool_result følger sin tool_use og bærer indhold + status.
    tr = [b for b in blocks if b["type"] == "tool_result"][0]
    assert tr["tool_use_id"] == "toolu_1"
    assert tr["content"] == "a\nb"
    assert tr["status"] == "done"


def test_build_blocks_text_only_no_tools():
    blocks = _build_turn_blocks(text="bare svar", tool_calls=[], tool_results=[])
    assert blocks == [{"type": "text", "text": "bare svar"}]


def test_build_blocks_tool_without_result_still_emits_tool_use():
    blocks = _build_turn_blocks(
        text="", tool_calls=[{"id": "toolu_9", "name": "read", "input": {}}], tool_results=[])
    # tool_use emittes selv uden result; progress-sporet (spec 2026-07-09 §5)
    # tilføjer ét settlet element pr. tool-kald bagefter.
    assert [b["type"] for b in blocks] == ["tool_use", "progress"]


def test_build_blocks_error_result_maps_status():
    blocks = _build_turn_blocks(
        text="x",
        tool_calls=[{"id": "t1", "name": "bash", "input": {}}],
        tool_results=[{"tool_use_id": "t1", "status": "error", "content": "boom", "is_error": True}],
    )
    tr = [b for b in blocks if b["type"] == "tool_result"][0]
    assert tr["status"] == "error"
    assert tr["is_error"] is True
