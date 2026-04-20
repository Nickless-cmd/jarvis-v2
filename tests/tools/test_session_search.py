"""Tests for session_search tool."""
from unittest.mock import MagicMock, patch


def _make_row(role, content, created_at, session_id, title, message_id="m1"):
    row = MagicMock()
    row.__getitem__ = lambda self, k: {
        "role": role,
        "content": content,
        "created_at": created_at,
        "session_id": session_id,
        "session_title": title,
        "message_id": message_id,
    }[k]
    return row


def _mock_connect(rows):
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchall.return_value = rows
    return mock_conn


def test_keyword_search_returns_results():
    from core.tools.session_search import exec_search_sessions

    fake_rows = [
        _make_row("user", "hej discord", "2026-04-19T10:00:00", "s1", "Discord DM", "m1"),
        _make_row("assistant", "hej tilbage", "2026-04-19T10:01:00", "s1", "Discord DM", "m2"),
    ]

    with patch("core.tools.session_search.connect", return_value=_mock_connect(fake_rows)):
        result = exec_search_sessions({"query": "hej", "mode": "keyword"})

    assert result["status"] == "ok"
    assert result["count"] == 2
    assert result["results"][0]["channel"] == "discord"
    assert result["results"][0]["session_title"] == "Discord DM"


def test_channel_filter_discord_only():
    from core.tools.session_search import exec_search_sessions

    mock_conn = _mock_connect([])

    with patch("core.tools.session_search.connect", return_value=mock_conn):
        result = exec_search_sessions({"query": "test", "mode": "keyword", "channel": "discord"})

    call_args = mock_conn.execute.call_args
    # Channel filter is passed as a SQL parameter, not embedded in the query string
    params = call_args[0][1]
    assert any("Discord" in str(p) for p in params)
    assert result["count"] == 0


def test_empty_query_returns_error():
    from core.tools.session_search import exec_search_sessions
    result = exec_search_sessions({"query": ""})
    assert result["status"] == "error"
    assert "query" in result["error"]


def test_no_results_returns_ok():
    from core.tools.session_search import exec_search_sessions

    with patch("core.tools.session_search.connect", return_value=_mock_connect([])):
        result = exec_search_sessions({"query": "xyzzy", "mode": "keyword"})

    assert result["status"] == "ok"
    assert result["count"] == 0


def test_result_includes_channel_field():
    from core.tools.session_search import exec_search_sessions

    fake_rows = [
        _make_row("user", "test telegram", "2026-04-19T10:00:00", "s2", "Telegram DM", "m3"),
    ]

    with patch("core.tools.session_search.connect", return_value=_mock_connect(fake_rows)):
        result = exec_search_sessions({"query": "telegram", "mode": "keyword"})

    assert result["results"][0]["channel"] == "telegram"
    assert result["results"][0]["channel_detail"] == "DM"
