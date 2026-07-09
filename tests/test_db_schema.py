import sqlite3
from core.runtime.db_schema import _ensure_chat_messages_content_json_column


def test_adds_content_json_column_idempotently():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, message_id TEXT, "
        "session_id TEXT, role TEXT, content TEXT)"
    )
    _ensure_chat_messages_content_json_column(conn)
    _ensure_chat_messages_content_json_column(conn)  # idempotent — must not raise
    cols = [r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()]
    assert "content_json" in cols
