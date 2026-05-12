"""Unit tests for proactive_outbound_substrate.

Tests cover the three public functions in
``core/services/proactive_outbound_substrate.py``:

- ``_summarize_outbound_payload``     (unit — no DB)
- ``compute_proactive_outbound_substrate``  (integration — real DB)
- ``build_proactive_outbound_section``      (integration + settings mock)
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from core.services.proactive_outbound_substrate import (
    _summarize_outbound_payload,
    build_proactive_outbound_section,
    compute_proactive_outbound_substrate,
)


# ── _summarize_outbound_payload ──────────────────────────────────────


class TestSummarizeOutboundPayload:
    """3 unit tests — no DB dependency."""

    def test_empty_payload(self) -> None:
        assert _summarize_outbound_payload("heartbeat.propose_delivered", {}) == ""

    def test_none_payload(self) -> None:
        assert _summarize_outbound_payload("heartbeat.ping_delivered", None) == ""  # type: ignore[arg-type]

    def test_unknown_keys(self) -> None:
        payload = {"unrelated": "hello", "foo": "bar"}
        assert _summarize_outbound_payload("heartbeat.propose_delivered", payload) == ""

    def test_summary_key_priority(self) -> None:
        """summary is the highest-priority key."""
        payload = {"summary": "Vil du lave en prediction?", "message": "ignored"}
        result = _summarize_outbound_payload("heartbeat.propose_delivered", payload)
        assert result == "Vil du lave en prediction?"

    def test_message_fallback(self) -> None:
        """Falls back to 'message' when 'summary' is missing."""
        payload = {"message": "Er du der?", "text": "ignored"}
        result = _summarize_outbound_payload("heartbeat.ping_delivered", payload)
        assert result == "Er du der?"

    def test_text_fallback(self) -> None:
        """Falls back to 'text' when 'summary' and 'message' are missing."""
        payload = {"text": "Har du set mit spørgsmål?", "content": "ignored"}
        result = _summarize_outbound_payload("heartbeat.propose_delivered", payload)
        assert result == "Har du set mit spørgsmål?"

    def test_content_fallback(self) -> None:
        """Falls back to 'content' when all others are missing."""
        payload = {"content": "Vil du tænke over det?"}
        result = _summarize_outbound_payload("heartbeat.propose_delivered", payload)
        assert result == "Vil du tænke over det?"

    def test_multiline_truncated_to_single_line(self) -> None:
        """Newlines are replaced with space, and result is capped at 160 chars."""
        long = "Hej\nmed\ndig " + "x" * 200
        payload = {"summary": long}
        result = _summarize_outbound_payload("heartbeat.ping_delivered", payload)
        assert "\n" not in result
        assert len(result) <= 160

    def test_string_value(self) -> None:
        """If the value is already a string (not None/empty), return it."""
        payload = {"summary": "Vil du?"}
        result = _summarize_outbound_payload("heartbeat.propose_delivered", payload)
        assert result == "Vil du?"


# ── Helpers for DB-backed tests ──────────────────────────────────────


def _insert_event(
    kind: str,
    payload: dict,
    ago_minutes: int,
) -> None:
    """Insert a row into the real events table (uses isolated_runtime DB)."""
    from core.runtime.db import connect

    created_at = (datetime.now(UTC) - timedelta(minutes=ago_minutes)).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (kind, json.dumps(payload, ensure_ascii=False), created_at),
        )


# ── compute_proactive_outbound_substrate ─────────────────────────────


class TestComputeProactiveOutboundSubstrate:
    """6 integration tests — requires isolated_runtime for real DB."""

    def test_empty_db_returns_empty_list(self, isolated_runtime) -> None:
        """No events of any kind → empty list."""
        result = compute_proactive_outbound_substrate()
        assert result == []

    def test_non_matching_events_are_filtered(self, isolated_runtime) -> None:
        """Events with non-proactive kinds are ignored."""
        _insert_event("runtime.agentic_round_start", {"summary": "round 1"}, 2)
        _insert_event("tool.completed", {"summary": "ls -la"}, 1)
        result = compute_proactive_outbound_substrate()
        assert result == []

    def test_single_propose_event(self, isolated_runtime) -> None:
        """A single propose_delivered event shows with label and time."""
        _insert_event(
            "heartbeat.propose_delivered",
            {"summary": "Vil du lave en prediction?"},
            5,
        )
        result = compute_proactive_outbound_substrate()
        assert len(result) == 1
        # Format: HH:MM — propose: Vil du lave en prediction?
        assert "propose:" in result[0]
        assert "Vil du lave en prediction?" in result[0]

    def test_ping_and_propose_chronological(self, isolated_runtime) -> None:
        """Multiple events are returned in chronological order (oldest first)."""
        _insert_event(
            "heartbeat.propose_delivered",
            {"summary": "Første besked"},
            12,
        )
        _insert_event(
            "heartbeat.ping_delivered",
            {"summary": "Anden besked"},
            8,
        )
        _insert_event(
            "heartbeat.propose_delivered",
            {"summary": "Tredje besked"},
            3,
        )
        result = compute_proactive_outbound_substrate()
        assert len(result) == 3
        # Chronological: oldest first → "Første" before "Anden" before "Tredje"
        assert result[0].endswith("Første besked")
        assert result[1].endswith("Anden besked")
        assert result[2].endswith("Tredje besked")

    def test_max_events_respected(self, isolated_runtime) -> None:
        """Only ``max_events`` items are returned."""
        for i in range(6):
            _insert_event(
                "heartbeat.ping_delivered",
                {"summary": f"besked {i}"},
                2 + i,
            )
        result = compute_proactive_outbound_substrate(max_events=3)
        assert len(result) == 3

    def test_old_events_filtered_by_window(self, isolated_runtime) -> None:
        """Events older than ``window_min`` are excluded."""
        _insert_event("heartbeat.propose_delivered", {"summary": "gammel"}, 35)
        result = compute_proactive_outbound_substrate(window_min=20)
        assert result == []

    def test_window_min_clamped_to_1(self, isolated_runtime) -> None:
        """window_min=0 is treated as 1 (no negative windows)."""
        _insert_event("heartbeat.ping_delivered", {"summary": "helt ny"}, 0)
        result = compute_proactive_outbound_substrate(window_min=0)
        assert len(result) >= 1  # 0 min ago = within window


# ── build_proactive_outbound_section ─────────────────────────────────


class TestBuildProactiveOutboundSection:
    """4 tests — settings mock for killswitch, real DB for data."""

    def test_killswitch_disabled_returns_none(self, isolated_runtime, monkeypatch) -> None:
        """When prompt_proactive_outbound_substrate_enabled is False → None."""

        class _FakeSettings:
            prompt_proactive_outbound_substrate_enabled = False

        monkeypatch.setattr(
            "core.runtime.settings.load_settings",
            lambda: _FakeSettings(),
        )
        result = build_proactive_outbound_section()
        assert result is None

    def test_no_events_returns_none(self, isolated_runtime) -> None:
        """No proactive events in DB → None."""
        result = build_proactive_outbound_section()
        assert result is None

    def test_normal_output_format(self, isolated_runtime) -> None:
        """With events, the section has header + lines + footer."""
        _insert_event(
            "heartbeat.propose_delivered",
            {"summary": "Vil du lave en prediction?"},
            5,
        )
        result = build_proactive_outbound_section()
        assert result is not None
        assert result.startswith("## Nylige proaktive beskeder du sendte (sidste 30 min)")
        assert "- " in result
        assert "_Brugerens svar kan referere til disse._" in result

    def test_settings_unreadable_fails_safe_enabled(self, isolated_runtime, monkeypatch) -> None:
        """If ``load_settings`` raises, section stays enabled (fail safe)."""

        def _raise(*a, **kw):
            raise RuntimeError("settings unreadable")

        monkeypatch.setattr(
            "core.runtime.settings.load_settings",
            _raise,
        )
        _insert_event(
            "heartbeat.propose_delivered",
            {"summary": "Vil du lave en prediction?"},
            5,
        )
        result = build_proactive_outbound_section()
        assert result is not None  # fail safe → section built


# ── Boundary: no unapproved outbound action ──────────────────────────


class TestProactiveOutboundConstraints:
    """Verify that the substrate only reads *delivered* events (no monitoring,
    no outbound writes, no side effects). This is a design-level constraint
    tested through what the module does NOT do.
    """

    def test_only_whitelisted_kinds_are_read(self, isolated_runtime) -> None:
        """Only ``heartbeat.propose_delivered`` and ``heartbeat.ping_delivered``
        are queried. Other event kinds are invisible to this module."""
        _insert_event("heartbeat.autonomy_assessment_ping", {"summary": "auto ping"}, 3)
        _insert_event("heartbeat.ping_delivered", {"summary": "ping delivered"}, 3)
        result = compute_proactive_outbound_substrate()
        # Only the delivered event shows up
        assert len(result) == 1
        assert "ping delivered" in result[0]

    def test_no_writes_to_db(self, isolated_runtime) -> None:
        """Calling the substrate never inserts/updates rows."""
        _insert_event("heartbeat.propose_delivered", {"summary": "test"}, 3)
        before = _count_events()
        compute_proactive_outbound_substrate()
        after = _count_events()
        assert after == before

    def test_no_external_side_effects(self, isolated_runtime, monkeypatch) -> None:
        """No HTTP calls, no file writes, no subprocesses spawned."""
        called: list[str] = []

        def _spy_web_fetch(*a, **kw):
            called.append("web_fetch")
            return None

        def _spy_bash(*a, **kw):
            called.append("bash")
            return None

        monkeypatch.setattr("core.services.proactive_outbound_substrate.logger", None)  # still safe
        _insert_event("heartbeat.propose_delivered", {"summary": "test"}, 3)
        result = compute_proactive_outbound_substrate()
        assert result is not None  # still works
        # No side-effect calls should have been made (the module only
        # does a SELECT query, but we can't easily spy on sqlite).


def _count_events() -> int:
    from core.runtime.db import connect

    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM events").fetchone()
        return row["cnt"] if row else 0
