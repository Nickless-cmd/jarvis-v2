from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.services.tool_result_store import (
    build_tool_result_reference,
    parse_tool_result_reference,
    save_tool_result,
)
from core.runtime.db import connect


def create_chat_session(*, title: str = "New chat") -> dict[str, object]:
    session_id = f"chat-{uuid4().hex}"
    created_at = datetime.now(UTC).isoformat()
    normalized_title = _normalize_title(title) or "New chat"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions (session_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, normalized_title, created_at, created_at),
        )
    return get_chat_session(session_id) or {
        "session_id": session_id,
        "title": normalized_title,
        "created_at": created_at,
        "updated_at": created_at,
        "last_message": "",
        "message_count": 0,
        "messages": [],
    }


def list_chat_sessions() -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                s.session_id,
                s.title,
                s.created_at,
                s.updated_at,
                COALESCE((
                    SELECT content
                    FROM chat_messages m
                    WHERE m.session_id = s.session_id
                    ORDER BY m.id DESC
                    LIMIT 1
                ), '') AS last_message,
                COALESCE((
                    SELECT COUNT(*)
                    FROM chat_messages m2
                    WHERE m2.session_id = s.session_id
                ), 0) AS message_count
            FROM chat_sessions s
            ORDER BY s.updated_at DESC, s.id DESC
            """
        ).fetchall()
    return [_session_summary(dict(row)) for row in rows]


def get_chat_session(session_id: str) -> dict[str, object] | None:
    normalized = (session_id or "").strip()
    if not normalized:
        return None
    with connect() as conn:
        session = conn.execute(
            """
            SELECT session_id, title, created_at, updated_at
            FROM chat_sessions
            WHERE session_id = ?
            """,
            (normalized,),
        ).fetchone()
        if session is None:
            return None
        messages = conn.execute(
            """
            SELECT message_id, role, content, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (normalized,),
        ).fetchall()
    message_items = [
        {
            "id": str(row["message_id"]),
            "role": str(row["role"]),
            "content": str(row["content"]),
            "ts": _time_label(str(row["created_at"])),
            "created_at": str(row["created_at"]),
        }
        for row in messages
    ]
    summary = _session_summary(
        {
            **dict(session),
            "last_message": message_items[-1]["content"] if message_items else "",
            "message_count": len(message_items),
        }
    )
    return {
        **summary,
        "messages": message_items,
    }


def append_chat_message(
    *,
    session_id: str,
    role: str,
    content: str,
    created_at: str | None = None,
    tool_name: str | None = None,
    tool_arguments: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized_session = (session_id or "").strip()
    if not normalized_session:
        raise ValueError("session_id must not be empty")
    normalized_role = (role or "").strip()
    if normalized_role not in {"user", "assistant", "tool", "compact_marker"}:
        raise ValueError("role must be user, assistant, tool, or compact_marker")
    normalized_content = str(content or "").strip()
    if not normalized_content:
        raise ValueError("content must not be empty")

    timestamp = created_at or datetime.now(UTC).isoformat()

    # Feel-layer: let incoming user text produce a micro-resonance signal
    # BEFORE meaning-making. Fire-and-forget — never break chat persistence.
    if normalized_role == "user":
        try:
            from core.services.text_resonance import resonate
            resonate(normalized_content, source=f"chat:{normalized_session}")
        except Exception:
            pass

    if normalized_role == "tool" and not parse_tool_result_reference(normalized_content):
        normalized_tool_name = (tool_name or _infer_tool_name_from_content(normalized_content) or "tool").strip()
        result_id = save_tool_result(
            normalized_tool_name,
            tool_arguments or {},
            normalized_content,
            created_at=timestamp,
        )
        normalized_content = build_tool_result_reference(
            result_id,
            tool_name=normalized_tool_name,
            summary=normalized_content,
        )
    message_id = f"message-{uuid4().hex}"
    with connect() as conn:
        exists = conn.execute(
            "SELECT session_id, title FROM chat_sessions WHERE session_id = ?",
            (normalized_session,),
        ).fetchone()
        if exists is None:
            raise ValueError("chat session not found")

        conn.execute(
            """
            INSERT INTO chat_messages (message_id, session_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, normalized_session, normalized_role, normalized_content, timestamp),
        )

        next_title = str(exists["title"])
        if normalized_role == "user" and next_title == "New chat":
            next_title = _normalize_title(normalized_content) or next_title

        conn.execute(
            """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (next_title, timestamp, normalized_session),
        )

    return {
        "id": message_id,
        "role": normalized_role,
        "content": normalized_content,
        "ts": _time_label(timestamp),
        "created_at": timestamp,
    }


def _infer_tool_name_from_content(content: str) -> str:
    normalized = str(content or "").strip()
    if normalized.startswith("[") and "]:" in normalized:
        return normalized[1:].split("]:", 1)[0].strip()
    return ""


def recent_chat_session_messages(session_id: str, *, limit: int = 12) -> list[dict[str, str]]:
    normalized = (session_id or "").strip()
    if not normalized:
        return []
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = ? AND role != 'compact_marker'
            ORDER BY id DESC
            LIMIT ?
            """,
            (normalized, max(limit, 1)),
        ).fetchall()
    return [
        {
            "role": str(row["role"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
        }
        for row in reversed(rows)
    ]


def store_compact_marker(session_id: str, summary_text: str) -> str:
    """Store a compact marker for the session. Returns the marker message_id."""
    normalized_session = (session_id or "").strip()
    if not normalized_session:
        raise ValueError("session_id must not be empty")
    normalized_content = str(summary_text or "").strip()
    if not normalized_content:
        raise ValueError("summary_text must not be empty")
    timestamp = datetime.now(UTC).isoformat()
    marker_id = f"compact-{uuid4().hex}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (message_id, session_id, role, content, created_at)
            VALUES (?, ?, 'compact_marker', ?, ?)
            """,
            (marker_id, normalized_session, normalized_content, timestamp),
        )
    return marker_id


def get_compact_marker(session_id: str) -> str | None:
    """Return the most recent compact marker summary for the session, or None."""
    normalized = (session_id or "").strip()
    if not normalized:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT content FROM chat_messages
            WHERE session_id = ? AND role = 'compact_marker'
            ORDER BY id DESC
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
    return str(row["content"]) if row else None


def recent_chat_tool_messages(session_id: str, *, limit: int = 6) -> list[dict[str, str]]:
    normalized = (session_id or "").strip()
    if not normalized:
        return []
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = ? AND role = 'tool'
            ORDER BY id DESC
            LIMIT ?
            """,
            (normalized, max(limit, 1)),
        ).fetchall()
    return [
        {
            "role": str(row["role"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
        }
        for row in reversed(rows)
    ]


def rename_chat_session(session_id: str, *, title: str) -> dict[str, object] | None:
    normalized = (session_id or "").strip()
    new_title = _normalize_title(title) or "New chat"
    if not normalized:
        return None
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE session_id = ?",
            (new_title, now, normalized),
        )
    return get_chat_session(normalized)


def delete_chat_session(session_id: str) -> bool:
    normalized = (session_id or "").strip()
    if not normalized:
        return False
    with connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (normalized,))
        conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (normalized,))
    return True


def _session_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(row.get("session_id") or ""),
        "title": str(row.get("title") or "New chat"),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "last_message": _preview_text(str(row.get("last_message") or "")) or "Ready",
        "message_count": int(row.get("message_count") or 0),
    }


def _normalize_title(value: str) -> str:
    text = " ".join((value or "").split()).strip()
    if not text:
        return ""
    return text[:48] + ("…" if len(text) > 48 else "")


def _preview_text(value: str) -> str:
    text = " ".join((value or "").split()).strip()
    if not text:
        return ""
    return text[:64] + ("…" if len(text) > 64 else "")


def _time_label(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    return dt.astimezone().strftime("%I:%M %p")


def parse_channel_from_session_title(title: str | None) -> tuple[str, str | None]:
    """Parse channel type and detail from a session title.

    Returns (channel_type, channel_detail) where channel_type is one of:
    'discord', 'telegram', 'webchat', 'unknown'.

    Examples:
        "Discord DM"         -> ("discord", "DM")
        "Discord #123456789" -> ("discord", "#123456789")
        "Telegram DM"        -> ("telegram", "DM")
        "New chat"           -> ("webchat", None)
        None                 -> ("webchat", None)
        "Something weird"    -> ("unknown", None)
    """
    if not title or title.strip() in ("New chat", ""):
        return ("webchat", None)
    t = title.strip()
    if t == "Discord DM":
        return ("discord", "DM")
    if t.startswith("Discord #"):
        return ("discord", t[len("Discord "):])
    if t.startswith("Discord"):
        return ("discord", None)
    if t == "Telegram DM":
        return ("telegram", "DM")
    if t.startswith("Telegram"):
        return ("telegram", None)
    return ("unknown", None)

