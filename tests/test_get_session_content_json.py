"""GET-session serialisering returnerer content_json (parset eller rekonstrueret)."""
import json

from core.services.chat_sessions import (
    append_chat_message,
    create_chat_session,
    get_chat_session,
)
from core.services.tool_result_store import save_tool_result, build_tool_result_reference


def _sid():
    return create_chat_session(title="t")["id"]


def test_stored_content_json_is_parsed_to_array():
    sid = _sid()
    blocks = [{"type": "text", "text": "svar"}]
    append_chat_message(session_id=sid, role="assistant", content="svar",
                        content_json=json.dumps(blocks))
    out = get_chat_session(sid)
    msg = [m for m in out["messages"] if m["role"] == "assistant"][-1]
    assert msg["content_json"] == blocks   # parset til array, ikke streng


def test_legacy_text_message_reconstructs_to_text_block():
    sid = _sid()
    append_chat_message(session_id=sid, role="assistant", content="gammel prosa")
    out = get_chat_session(sid)
    msg = [m for m in out["messages"] if m["role"] == "assistant"][-1]
    assert msg["content_json"] == [{"type": "text", "text": "gammel prosa"}]


def test_legacy_tool_message_reconstructs_to_tool_result_block():
    sid = _sid()
    # Gem et ægte tool-resultat og persistér en role="tool" besked der refererer det.
    result_id = save_tool_result("bash", {"cmd": "ls"}, "file1\nfile2")
    ref = build_tool_result_reference(result_id, tool_name="bash", summary="file1\nfile2")
    append_chat_message(session_id=sid, role="tool", content=ref)
    out = get_chat_session(sid)
    tool_msg = [m for m in out["messages"] if m["role"] == "tool"][-1]
    blocks = tool_msg["content_json"]
    assert len(blocks) == 1
    assert blocks[0]["type"] == "tool_result"
    assert blocks[0]["content"] == "file1\nfile2"
    assert blocks[0]["name"] == "bash"
