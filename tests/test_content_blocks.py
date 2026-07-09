"""Tests for pure content-block helpers: text projection + serve-on-read reconstruction."""
from core.services.content_blocks import (
    content_blocks_to_text,
    reconstruct_blocks_from_legacy,
)


def test_text_only_projection_is_plain_text():
    blocks = [{"type": "text", "text": "hej med dig"}]
    assert content_blocks_to_text(blocks) == "hej med dig"


def test_multiple_text_blocks_joined_with_blank_line():
    blocks = [{"type": "text", "text": "linje et"}, {"type": "text", "text": "linje to"}]
    assert content_blocks_to_text(blocks) == "linje et\n\nlinje to"


def test_tool_use_and_result_omitted_from_text_projection():
    blocks = [
        {"type": "text", "text": "svar"},
        {"type": "tool_use", "id": "toolu_1", "name": "bash", "input": {}},
        {"type": "tool_result", "tool_use_id": "toolu_1", "status": "done", "content": "x", "is_error": False},
    ]
    assert content_blocks_to_text(blocks) == "svar"


def test_empty_blocks_gives_empty_string():
    assert content_blocks_to_text([]) == ""


def test_progress_block_omitted_from_text_projection():
    """progress-blokke er ikke prosa → udelades af tekst-projektionen (som tool_use/tool_result)."""
    blocks = [
        {"type": "text", "text": "svar"},
        {"type": "progress", "tool_use_id": "toolu_1", "parent_tool_use_id": None,
         "message": "Analyserede billede: foto.png", "status": "done"},
    ]
    assert content_blocks_to_text(blocks) == "svar"


def test_reconstruct_plain_text_message_is_single_text_block():
    blocks = reconstruct_blocks_from_legacy("assistant", "bare tekst", load_result=lambda ref: None)
    assert blocks == [{"type": "text", "text": "bare tekst"}]


def test_reconstruct_tool_message_with_reference_becomes_tool_result_block():
    """Tool messages with [tool_result:...] format get reconstructed as tool_result blocks."""
    tool_result_data = {"tool_name": "bash", "content": "file1\nfile2"}

    def _load(result_id):
        if result_id == "tool-result-abc123":
            return tool_result_data
        return None

    # Format produced by build_tool_result_reference in tool_result_store.py
    content = "[tool_result:tool-result-abc123]\n[bash]: file1 file2\nUse read_tool_result with result_id=\"tool-result-abc123\" to inspect the full output."
    blocks = reconstruct_blocks_from_legacy("tool", content, load_result=_load)

    assert len(blocks) == 1
    assert blocks[0]["type"] == "tool_result"
    assert blocks[0]["tool_use_id"] == ""
    assert blocks[0]["status"] == "done"
    assert blocks[0]["content"] == "file1\nfile2"
    assert blocks[0]["is_error"] is False
    assert blocks[0]["name"] == "bash"


def test_reconstruct_tool_message_unresolvable_ref_degrades_to_text():
    """Tool messages with unresolvable refs degrade to text blocks."""
    content = "[tool_result:missing-id]\n[bash]: some content"
    blocks = reconstruct_blocks_from_legacy("tool", content, load_result=lambda ref: None)
    assert blocks == [{"type": "text", "text": content}]


def test_reconstruct_assistant_message_stays_text():
    """Assistant messages always become text blocks."""
    blocks = reconstruct_blocks_from_legacy("assistant", "I ran bash", load_result=lambda ref: None)
    assert blocks == [{"type": "text", "text": "I ran bash"}]
