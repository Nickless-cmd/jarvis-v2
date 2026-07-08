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
    # 2026-06-23 (Bjørn): sænket 200k→130k. På glm-5.2 (200k vindue) lod 200k en session
    # sidde på ~173k (87% af vinduet) uden at compacte → loop/cut-off. 130k giver headroom.
    assert s.context_compact_threshold_tokens == 130_000


def test_settings_run_compact_threshold_default():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.context_run_compact_threshold_tokens == 240_000


def test_settings_keep_recent_defaults():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.context_keep_recent == 20
    assert s.context_keep_recent_pairs == 4


def test_settings_serialise_round_trip():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    d = s.to_dict()
    assert d["context_compact_threshold_tokens"] == 130_000
    assert d["context_run_compact_threshold_tokens"] == 240_000
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

    # Production schema includes user_id + reasoning_content fields
    # (added 2026-04-x for user-attribution + reasoning content support);
    # fixture rows must mirror the schema so the production code's
    # row["user_id"] lookup doesn't KeyError.
    all_rows = [
        {"role": "user", "content": "hello", "created_at": "2026-01-01",
         "user_id": "u1", "reasoning_content": ""},
        {"role": "compact_marker", "content": "old summary", "created_at": "2026-01-01",
         "user_id": "u1", "reasoning_content": ""},
        {"role": "assistant", "content": "hi", "created_at": "2026-01-01",
         "user_id": "u1", "reasoning_content": ""},
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
    # call_compact_llm now tries _call_cheap_no_groq FIRST and only falls
    # through to _call_heartbeat_llm_simple if cheap returns empty.
    # Patch both so the test is deterministic regardless of provider state.
    monkeypatch.setattr(compact_llm, "_call_cheap_no_groq", lambda prompt: "")
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

    monkeypatch.setattr(compact_llm, "_call_cheap_no_groq", lambda prompt: "")
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
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text, git_sha="": "marker-1")

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
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text, git_sha="": "marker-1")

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
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text, git_sha="": "m")

    session_compact.compact_session_history(
        "session-x", keep_recent=20, summarise_fn=_capture_summarise
    )
    # Only the oldest 5 messages (25-20) should be passed to summarise_fn
    assert len(captured_input["msgs"]) == 5


# ── Task 7: session compact wiring ────────────────────────────────────────

def test_build_transcript_prepends_compact_marker_when_present(monkeypatch):
    from core.services import prompt_contract

    monkeypatch.setattr(
        prompt_contract,
        "recent_chat_session_messages_by_user_turns",
        lambda sid, *, user_turns, max_total: [
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
        "recent_chat_session_messages_by_user_turns",
        lambda sid, *, user_turns, max_total: [
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


# ── Task 10: Lag C — Post-compact validation ──────────────────────────────

def test_parse_compact_claims_empty_text():
    from core.context.compact_ground_truth import _parse_compact_claims
    assert _parse_compact_claims("") == []
    assert _parse_compact_claims("Nothing suspicious here") == []


def test_parse_compact_claims_detects_missing_pattern():
    from core.context.compact_ground_truth import _parse_compact_claims

    text = "The credit assignment module is **not implemented** yet."
    claims = _parse_compact_claims(text)
    assert len(claims) == 1
    assert "not implemented" in claims[0]["context"].lower()
    assert claims[0]["claim_type"] in ("missing_file", "missing_feature", "unimplemented")


def test_parse_compact_claims_danish_patterns():
    from core.context.compact_ground_truth import _parse_compact_claims

    text = "Lag 1 credit assignment mangler stadig. Workspace-loader er ikke påbegyndt."
    claims = _parse_compact_claims(text)
    assert len(claims) >= 2  # 'mangler' + 'ikke påbegyndt'
    patterns = [c["pattern"] for c in claims]
    assert "mangler" in patterns
    assert "ikke påbegyndt" in patterns


def test_parse_compact_claims_deduplicates_by_context():
    from core.context.compact_ground_truth import _parse_compact_claims

    text = "X mangler. X mangler stadig. X mangler helt."
    claims = _parse_compact_claims(text)
    assert len(claims) == 1  # all three are the same "X mangler" context


def test_check_claim_detects_file_exists(monkeypatch):
    from core.context.compact_ground_truth import _check_claim_against_ground_truth

    ground_truth = {
        "current_git_sha": "abc1234",
        "key_files": {
            "core/runtime/db_credit_assignment.py": "exists",
            "core/services/chat_sessions.py": "exists",
        },
        "cognitive_decisions_count": 47,
    }

    # Claim about a file that DOES exist
    claim = {
        "pattern": "not implemented",
        "context": "The db_credit_assignment module is not implemented yet",
        "claim_type": "missing_file",
    }
    result = _check_claim_against_ground_truth(claim, ground_truth)
    assert result["verified_false"] is True
    assert result["confidence"] == "high"


def test_check_claim_accepts_file_really_missing(monkeypatch):
    from core.context.compact_ground_truth import _check_claim_against_ground_truth

    ground_truth = {
        "current_git_sha": "abc1234",
        "key_files": {
            "core/runtime/db_credit_assignment.py": "missing",
        },
        "cognitive_decisions_count": 0,
    }

    claim = {
        "pattern": "missing",
        "context": "The db_credit_assignment file is missing",
        "claim_type": "missing_file",
    }
    result = _check_claim_against_ground_truth(claim, ground_truth)
    assert result["verified_false"] is False  # file IS missing, claim is honest
    assert result["confidence"] == "high"


def test_check_claim_cognitive_decisions_exists():
    from core.context.compact_ground_truth import _check_claim_against_ground_truth

    ground_truth = {
        "current_git_sha": "abc1234",
        "key_files": {},
        "cognitive_decisions_count": 47,
    }

    claim = {
        "pattern": "missing",
        "context": "cognitive decisions tracking is still missing",
        "claim_type": "missing_feature",
    }
    result = _check_claim_against_ground_truth(claim, ground_truth)
    assert result["verified_false"] is True
    assert "47" in result["evidence"]


def test_check_claim_inconclusive_if_no_match():
    from core.context.compact_ground_truth import _check_claim_against_ground_truth

    ground_truth = {
        "current_git_sha": "abc1234",
        "key_files": {"some/file.py": "exists"},
        "cognitive_decisions_count": None,
    }

    claim = {
        "pattern": "missing",
        "context": "Something completely unrelated is missing",
        "claim_type": "unimplemented",
    }
    result = _check_claim_against_ground_truth(claim, ground_truth)
    assert result["verified_false"] is False
    assert result["confidence"] == "low"


def test_validate_compact_marker_passed_with_no_claims():
    from core.context.compact_ground_truth import validate_compact_marker

    report = validate_compact_marker("session-x", "Everything was built and working fine.")
    assert report["passed"] is True
    assert report["total_suspicious_claims"] == 0
    assert report["verified_false"] == 0


def test_validate_compact_marker_never_logs_on_pass():
    from core.context.compact_ground_truth import validate_compact_marker

    report = validate_compact_marker("session-x", "Normal conversation about testing.")
    assert report["logged"] is False


def test_auto_regenerate_noop_when_passed(monkeypatch):
    """auto_regenerate should return None when marker has no false claims."""
    from core.context.compact_ground_truth import auto_regenerate_compact_marker

    monkeypatch.setattr(
        "core.services.chat_sessions.get_compact_marker_with_sha",
        lambda sid: ("Clean marker with no issues", "abc1234"),
    )
    result = auto_regenerate_compact_marker("session-x")
    assert result is None  # no regeneration needed


def test_compact_result_validation_default():
    """CompactResult should still work without validation field (backward compat)."""
    from core.context.session_compact import CompactResult
    r = CompactResult(freed_tokens=100, summary_text="test", marker_id="m-1")
    assert r.validation is None
    assert r.freed_tokens == 100


def test_compact_result_validation_provided():
    """CompactResult accepts validation field."""
    from core.context.session_compact import CompactResult
    r = CompactResult(
        freed_tokens=100,
        summary_text="test",
        marker_id="m-1",
        validation={"passed": True, "verified_false": 0},
    )
    assert r.validation["passed"] is True


# ── Task 11: Lag D — Self-healing compaction loop ─────────────────────────

def test_extract_topic_words_removes_noise():
    from core.context.compact_ground_truth import _extract_topic_words
    words = _extract_topic_words("det er bare en test af credit assignment")
    assert "test" in words
    assert "credit" in words
    assert "assignment" in words
    assert "det" not in words
    assert "er" not in words
    assert "bare" not in words


def test_extract_topic_words_returns_set():
    from core.context.compact_ground_truth import _extract_topic_words
    result = _extract_topic_words("Lag 1 credit assignment mangler stadig")
    assert isinstance(result, set)
    assert len(result) >= 1


def test_check_user_message_against_marker_no_signal():
    """A normal user message without correction signal should return None."""
    from core.context.compact_ground_truth import _check_user_message_against_marker
    result = _check_user_message_against_marker(
        "Kan du bygge credit assignment modulet?",
        "Lag 1 credit assignment mangler og er åbent",
    )
    assert result is None  # no correction signal phrase


def test_check_user_message_against_marker_detects_correction():
    """A user message with correction signal + topic overlap should match."""
    from core.context.compact_ground_truth import _check_user_message_against_marker
    result = _check_user_message_against_marker(
        "Det er da implementeret, credit assignment kører fint",
        "Lag 1 credit assignment mangler og er åbent",
    )
    assert result is not None
    assert result["matched"] is True
    # "credit" and "assignment" should overlap
    assert "credit" in result["marker_topic_overlap"] or "assignment" in result["marker_topic_overlap"]


def test_check_user_message_against_marker_high_confidence_with_failure():
    """If a known failure context matches, confidence should be 'high'."""
    from core.context.compact_ground_truth import _check_user_message_against_marker
    failures = [
        {
            "pattern": "mangler",
            "context": "credit assignment modulet mangler og er ikke implementeret",
            "verified_false": True,
            "confidence": "high",
        }
    ]
    result = _check_user_message_against_marker(
        "Det virker fint, credit assignment er på plads",
        "Lag 1 credit assignment mangler",
        marker_failures=failures,
    )
    assert result is not None
    assert result["matched"] is True
    assert result["confidence"] == "high"


def test_check_user_message_against_marker_medium_confidence_no_failure():
    """Without known failures, topic overlap alone gives medium confidence."""
    from core.context.compact_ground_truth import _check_user_message_against_marker
    result = _check_user_message_against_marker(
        "Det er bygget, workspace loader kører allerede",
        "Workspace loader mangler og er ikke påbegyndt",
    )
    assert result is not None
    assert result["matched"] is True
    assert result["confidence"] == "medium"
    assert "workspace" in result["marker_topic_overlap"] or "loader" in result["marker_topic_overlap"]


def test_detect_compact_mismatch_in_chat_no_marker(monkeypatch):
    """If no compact marker exists, should return empty list."""
    from core.context.compact_ground_truth import detect_compact_mismatch_in_chat
    monkeypatch.setattr(
        "core.services.chat_sessions.get_compact_marker_with_sha",
        lambda sid: (None, None),
    )
    result = detect_compact_mismatch_in_chat("session-x")
    assert result == []


def test_detect_compact_mismatch_in_chat_no_mismatch(monkeypatch):
    """If user messages don't contradict the marker, return empty list."""
    from core.context.compact_ground_truth import detect_compact_mismatch_in_chat
    monkeypatch.setattr(
        "core.services.chat_sessions.get_compact_marker_with_sha",
        lambda sid: ("All features are implemented and working", "abc1234"),
    )
    monkeypatch.setattr(
        "core.services.chat_sessions.recent_chat_session_messages",
        lambda sid, limit: [
            {"role": "user", "content": "Hvad med at bygge noget nyt?"},
            {"role": "assistant", "content": "Sure"},
        ],
    )
    monkeypatch.setattr(
        "core.context.compact_ground_truth.get_validation_failures",
        lambda sid, limit: [],
    )
    result = detect_compact_mismatch_in_chat("session-x")
    assert result == []


def test_resolve_stale_markers_on_load_no_failures(monkeypatch):
    """If no unresolved failures, should return None."""
    from core.context.compact_ground_truth import resolve_stale_markers_on_load
    monkeypatch.setattr(
        "core.context.compact_ground_truth.get_validation_failures",
        lambda sid, limit: [],
    )
    result = resolve_stale_markers_on_load("session-x")
    assert result is None


def test_resolve_stale_markers_on_load_skips_fresh_marker(monkeypatch):
    """If marker is fresh (SHA matches), skip even if old failures exist."""
    from core.context.compact_ground_truth import resolve_stale_markers_on_load
    monkeypatch.setattr(
        "core.context.compact_ground_truth.get_validation_failures",
        lambda sid, limit: [
            {"resolved_at": None, "marker_id": "old-marker", "session_id": "session-x"},
        ],
    )
    monkeypatch.setattr(
        "core.services.chat_sessions.get_compact_marker_with_sha",
        lambda sid: ("stale text", "abc1234"),
    )
    monkeypatch.setattr(
        "core.context.compact_ground_truth.get_compact_marker_freshness",
        lambda sha: {"fresh": True, "status": "fresh"},
    )
    result = resolve_stale_markers_on_load("session-x")
    assert result is None


def test_compact_healthcheck_daemon_tick_no_failures(monkeypatch):
    """If no sessions have unresolved failures, return empty list."""
    from core.context.compact_ground_truth import compact_healthcheck_daemon_tick

    class _FakeEmptyCursor:
        def fetchall(self): return []
        def execute(self, *a, **kw): return self

    class _FakeConn:
        def execute(self, *a, **kw): return _FakeEmptyCursor()
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr(
        "core.context.compact_ground_truth._ensure_compaction_validation_table",
        lambda: None,
    )
    monkeypatch.setattr("core.runtime.db.connect", lambda: _FakeConn())

    result = compact_healthcheck_daemon_tick()
    assert result == []


def test_compact_healthcheck_daemon_tick_with_unresolved(monkeypatch):
    """If sessions have unresolved failures, attempt healing."""
    from core.context.compact_ground_truth import compact_healthcheck_daemon_tick

    class _FakeCursor:
        def __init__(self, rows):
            self._rows = rows
            self._idx = 0
        def fetchall(self): return self._rows
        def execute(self, *a, **kw): return self

    class _FakeConn:
        def execute(self, *a, **kw):
            return _FakeCursor([{"session_id": "session-x"}])
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr(
        "core.context.compact_ground_truth._ensure_compaction_validation_table",
        lambda: None,
    )
    monkeypatch.setattr("core.runtime.db.connect", lambda: _FakeConn())
    monkeypatch.setattr(
        "core.context.compact_ground_truth.resolve_stale_markers_on_load",
        lambda sid: "new-marker-42",
    )

    result = compact_healthcheck_daemon_tick()
    assert len(result) == 1
    assert result[0]["session_id"] == "session-x"
    assert result[0]["regenerated"] is True
    assert result[0]["new_marker_id"] == "new-marker-42"


def test_auto_compact_is_async_and_deduped(monkeypatch):
    """Bjørn 2026-06-23: compaction må IKKE blokere prompt-assembly. _maybe_auto_compact_session
    skal returnere straks (spawn baggrundstråd) og dedup'e pr. session."""
    import core.services.prompt_contract as pc

    class _S:
        context_compact_threshold_tokens = 100
        context_keep_recent = 20

    started = []
    monkeypatch.setattr(pc, "_run_session_compaction",
                        lambda sid, kr: started.append(sid))
    # Stor besked → over tærskel (100 tokens)
    msgs = [{"role": "user", "content": "x" * 5000}]
    pc._compact_inflight.discard("s1")
    pc._maybe_auto_compact_session("s1", msgs, _S())
    # tråden spawnes; vent kort på den
    import time
    for _ in range(50):
        if started:
            break
        time.sleep(0.01)
    assert started == ["s1"]


def test_auto_compact_skips_below_threshold(monkeypatch):
    import core.services.prompt_contract as pc

    class _S:
        context_compact_threshold_tokens = 1_000_000
        context_keep_recent = 20

    called = []
    monkeypatch.setattr(pc, "_run_session_compaction", lambda sid, kr: called.append(sid))
    pc._maybe_auto_compact_session("s2", [{"role": "user", "content": "kort"}], _S())
    import time; time.sleep(0.05)
    assert called == []  # under tærskel → ingen compaction
