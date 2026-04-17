"""Tests for context compact system."""
from __future__ import annotations

from unittest.mock import Mock


# ── Task 1: token_estimate ─────────────────────────────────────────────────

def test_estimate_tokens_empty():
    from core.context.token_estimate import estimate_tokens
    assert estimate_tokens("") == 0


def test_estimate_tokens_basic():
    from core.context.token_estimate import estimate_tokens
    # 35 chars / 3.5 = 10
    assert estimate_tokens("a" * 35) == 10


def test_estimate_messages_tokens_sums_content():
    from core.context.token_estimate import estimate_messages_tokens
    messages = [
        {"role": "user", "content": "a" * 35},       # 10 tokens
        {"role": "assistant", "content": "b" * 35},   # 10 tokens
    ]
    assert estimate_messages_tokens(messages) == 20


def test_estimate_messages_tokens_missing_content():
    from core.context.token_estimate import estimate_messages_tokens
    messages = [{"role": "user"}, {"role": "assistant", "content": None}]
    assert estimate_messages_tokens(messages) == 0


def test_estimate_messages_tokens_list_content():
    from core.context.token_estimate import estimate_messages_tokens
    # Some providers use list content
    messages = [{"role": "user", "content": ["hello", "world"]}]
    result = estimate_messages_tokens(messages)
    assert result >= 1  # Just check it doesn't crash


# ── Task 2: settings ──────────────────────────────────────────────────────

def test_settings_compact_threshold_default():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.context_compact_threshold_tokens == 40_000


def test_settings_run_compact_threshold_default():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.context_run_compact_threshold_tokens == 60_000


def test_settings_keep_recent_defaults():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.context_keep_recent == 20
    assert s.context_keep_recent_pairs == 4


def test_settings_serialise_round_trip():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    d = s.to_dict()
    assert d["context_compact_threshold_tokens"] == 40_000
    assert d["context_run_compact_threshold_tokens"] == 60_000
    assert d["context_keep_recent"] == 20
    assert d["context_keep_recent_pairs"] == 4


# ── Task 3: DB compact marker ─────────────────────────────────────────────

def test_get_compact_marker_returns_none_when_absent(monkeypatch):
    from core.services import chat_sessions

    class _FakeCursor:
        def fetchone(self): return None
        def execute(self, *a, **kw): return self

    class _FakeConn:
        def execute(self, *a, **kw): return _FakeCursor()
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr(chat_sessions, "connect", lambda: _FakeConn())
    result = chat_sessions.get_compact_marker("session-abc")
    assert result is None


def test_recent_session_messages_excludes_compact_markers(monkeypatch):
    from core.services import chat_sessions

    all_rows = [
        {"role": "user", "content": "hello", "created_at": "2026-01-01"},
        {"role": "compact_marker", "content": "old summary", "created_at": "2026-01-01"},
        {"role": "assistant", "content": "hi", "created_at": "2026-01-01"},
    ]

    class _FakeCursor:
        def fetchall(self):
            return [r for r in all_rows if r.get("role") != "compact_marker"]
        def execute(self, *a, **kw): return self

    class _FakeConn:
        def execute(self, *a, **kw): return _FakeCursor()
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr(chat_sessions, "connect", lambda: _FakeConn())
    messages = chat_sessions.recent_chat_session_messages("session-abc", limit=10)
    roles = [m["role"] for m in messages]
    assert "compact_marker" not in roles


# ── Task 4: compact_llm ───────────────────────────────────────────────────

def test_call_compact_llm_returns_string(monkeypatch):
    from core.context import compact_llm
    monkeypatch.setattr(
        compact_llm,
        "_call_heartbeat_llm_simple",
        lambda prompt, max_tokens: "Summary result",
    )
    result = compact_llm.call_compact_llm("Summarise this", max_tokens=200)
    assert result == "Summary result"


def test_call_compact_llm_fallback_on_error(monkeypatch):
    from core.context import compact_llm

    def _fail(prompt, max_tokens):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(compact_llm, "_call_heartbeat_llm_simple", _fail)
    result = compact_llm.call_compact_llm("Summarise this", max_tokens=200)
    assert isinstance(result, str)
    assert len(result) > 0


# ── Task 5: session_compact ───────────────────────────────────────────────

def test_compact_session_history_skips_if_too_few_messages(monkeypatch):
    from core.context import session_compact
    summarise_fn = Mock(return_value="Summary")

    monkeypatch.setattr(
        session_compact,
        "_get_all_session_messages",
        lambda session_id: [{"role": "user", "content": "hi"} for _ in range(5)],
    )
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text: "marker-1")

    result = session_compact.compact_session_history(
        "session-x", keep_recent=20, summarise_fn=summarise_fn
    )
    assert result is None
    assert not summarise_fn.called


def test_compact_session_history_calls_summarise_on_enough_messages(monkeypatch):
    from core.context import session_compact
    summarise_fn = Mock(return_value="Compressed history")

    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(30)
    ]
    monkeypatch.setattr(session_compact, "_get_all_session_messages", lambda sid: messages)
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text: "marker-1")

    result = session_compact.compact_session_history(
        "session-x", keep_recent=20, summarise_fn=summarise_fn
    )
    assert result is not None
    assert result.summary_text == "Compressed history"
    assert result.freed_tokens > 0
    assert result.marker_id == "marker-1"
    assert summarise_fn.called


def test_compact_session_history_compresses_only_old_messages(monkeypatch):
    from core.context import session_compact
    captured_input = {}

    def _capture_summarise(msgs):
        captured_input["msgs"] = msgs
        return "Summary"

    messages = [{"role": "user", "content": f"msg {i}"} for i in range(25)]
    monkeypatch.setattr(session_compact, "_get_all_session_messages", lambda sid: messages)
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text: "m")

    session_compact.compact_session_history(
        "session-x", keep_recent=20, summarise_fn=_capture_summarise
    )
    # Only the oldest 5 messages (25-20) should be passed to summarise_fn
    assert len(captured_input["msgs"]) == 5


# ── Task 6: run_compact ───────────────────────────────────────────────────

def test_run_compact_returns_same_if_too_few_pairs():
    from core.context.run_compact import compact_run_messages
    summarise_fn = Mock(return_value="Compressed")
    messages = [
        {"role": "user", "content": "do stuff"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "Tool results: done"},
    ]
    result = compact_run_messages(
        messages, keep_base=1, keep_recent_pairs=4, summarise_fn=summarise_fn
    )
    assert result == messages
    assert not summarise_fn.called


def test_run_compact_compresses_middle_messages():
    from core.context.run_compact import compact_run_messages
    summarise_fn = Mock(return_value="Ran 3 tools: read, write, bash")

    base = [{"role": "user", "content": "start task"}]
    pairs = []
    for i in range(6):
        pairs.append({"role": "assistant", "content": f"Calling tool {i}"})
        pairs.append({"role": "user", "content": f"Tool results: result {i}"})
    messages = base + pairs  # 13 messages total

    result = compact_run_messages(
        messages, keep_base=1, keep_recent_pairs=2, summarise_fn=summarise_fn
    )
    assert len(result) < len(messages)
    assert any("[KOMPRIMERET KONTEKST:" in m.get("content", "") for m in result)
    assert summarise_fn.called


def test_run_compact_always_keeps_base_messages():
    from core.context.run_compact import compact_run_messages
    summarise_fn = Mock(return_value="Summary")

    base = [
        {"role": "system", "content": "You are Jarvis"},
        {"role": "user", "content": "Do the task"},
    ]
    pairs = []
    for i in range(6):
        pairs.append({"role": "assistant", "content": f"Calling tool {i}"})
        pairs.append({"role": "user", "content": f"Tool results: result {i}"})
    messages = base + pairs

    result = compact_run_messages(
        messages, keep_base=2, keep_recent_pairs=2, summarise_fn=summarise_fn
    )
    assert result[0] == base[0]
    assert result[1] == base[1]


# ── Task 7: session compact wiring ────────────────────────────────────────

def test_build_transcript_prepends_compact_marker_when_present(monkeypatch):
    from core.services import prompt_contract

    monkeypatch.setattr(
        prompt_contract,
        "recent_chat_session_messages",
        lambda sid, limit: [
            {"role": "user", "content": "hello", "created_at": "2026-01-01"},
            {"role": "assistant", "content": "hi", "created_at": "2026-01-01"},
        ],
    )
    monkeypatch.setattr(
        prompt_contract,
        "_get_compact_marker_for_transcript",
        lambda sid: "Old summarised history here",
    )
    monkeypatch.setattr(
        prompt_contract,
        "_maybe_auto_compact_session",
        lambda sid, messages, settings: None,
    )

    result = prompt_contract._build_structured_transcript_messages(
        "session-x", limit=60, include=True
    )
    assert result[0]["role"] == "user"
    assert "Old summarised history here" in result[0]["content"]
    assert result[1]["role"] == "assistant"
    assert result[1]["content"] == "Forstået."


def test_build_transcript_no_marker_no_prepend(monkeypatch):
    from core.services import prompt_contract

    monkeypatch.setattr(
        prompt_contract,
        "recent_chat_session_messages",
        lambda sid, limit: [
            {"role": "user", "content": "hello", "created_at": "2026-01-01"},
            {"role": "assistant", "content": "hi", "created_at": "2026-01-01"},
        ],
    )
    monkeypatch.setattr(
        prompt_contract,
        "_get_compact_marker_for_transcript",
        lambda sid: None,
    )
    monkeypatch.setattr(
        prompt_contract,
        "_maybe_auto_compact_session",
        lambda sid, messages, settings: None,
    )

    result = prompt_contract._build_structured_transcript_messages(
        "session-x", limit=60, include=True
    )
    assert result[0]["content"] == "hello"


# ── Task 8: run compact wiring ────────────────────────────────────────────

def test_maybe_compact_agentic_messages_no_compact_below_threshold():
    from core.services import visible_runs
    from core.runtime.settings import RuntimeSettings

    settings = RuntimeSettings()
    settings.context_run_compact_threshold_tokens = 60_000

    messages = [{"role": "user", "content": "short"}]
    result = visible_runs._maybe_compact_agentic_messages(
        messages, base_count=1, settings=settings
    )
    assert result is messages


def test_maybe_compact_agentic_messages_compacts_above_threshold(monkeypatch):
    from core.services import visible_runs
    from core.runtime.settings import RuntimeSettings

    settings = RuntimeSettings()
    settings.context_run_compact_threshold_tokens = 10  # very low

    monkeypatch.setattr(
        visible_runs,
        "_compact_llm_for_run",
        lambda prompt: "Compressed tool history",
    )

    base = [{"role": "user", "content": "start"}]
    pairs = []
    for i in range(8):
        pairs.append({"role": "assistant", "content": f"calling tool {i}" * 20})
        pairs.append({"role": "user", "content": f"tool result {i}" * 20})
    messages = base + pairs

    result = visible_runs._maybe_compact_agentic_messages(
        messages, base_count=1, settings=settings
    )
    assert len(result) < len(messages)
    assert any("[KOMPRIMERET KONTEKST:" in m.get("content", "") for m in result)


# ── Task 9: compact_context tool ──────────────────────────────────────────

def test_compact_context_tool_is_registered():
    from core.tools.simple_tools import get_tool_definitions
    tool_names = [t["function"]["name"] for t in get_tool_definitions() if "function" in t]
    assert "compact_context" in tool_names


def test_compact_context_tool_no_compact_when_short(monkeypatch):
    from core.tools import simple_tools
    monkeypatch.setattr(
        simple_tools,
        "_exec_compact_context_session",
        lambda session_id: None,
    )
    result = simple_tools._exec_compact_context({})
    assert result["status"] == "ok"
    assert result["freed_tokens"] == 0


def test_compact_context_tool_returns_freed_tokens(monkeypatch):
    from core.tools import simple_tools
    from core.context.session_compact import CompactResult

    compact_result = CompactResult(
        freed_tokens=5000,
        summary_text="Old history summary",
        marker_id="marker-1",
    )
    monkeypatch.setattr(
        simple_tools,
        "_exec_compact_context_session",
        lambda session_id: compact_result,
    )
    result = simple_tools._exec_compact_context({})
    assert result["status"] == "ok"
    assert result["freed_tokens"] == 5000
