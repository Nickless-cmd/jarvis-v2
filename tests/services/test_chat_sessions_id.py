from core.services.chat_sessions import (
    create_chat_session, append_chat_message,
    chat_session_messages_since_last_compact,
)


def test_messages_include_integer_id():
    # create_chat_session mints its own uuid session_id (no session_id kwarg);
    # capture it so the test stays deterministic (no randomness on our side).
    sess = create_chat_session(title="t")
    sid = str(sess["id"])
    append_chat_message(session_id=sid, role="user", content="hej")
    append_chat_message(session_id=sid, role="assistant", content="svar")
    msgs = chat_session_messages_since_last_compact(sid)
    assert len(msgs) == 2
    assert all("id" in m for m in msgs)
    assert msgs[0]["id"] < msgs[1]["id"]
    assert isinstance(msgs[0]["id"], int)
