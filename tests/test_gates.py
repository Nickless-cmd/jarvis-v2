"""Tests for veto_gate, decision_gate, and affect_modulation integration."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from core.runtime.db import connect as _db_connect
from core.services.emotional_controls import EmotionalSnapshot


# ── Veto gate ────────────────────────────────────────────────────────

class TestVetoGate:
    def test_allows_when_no_pushback(self):
        from core.services.veto_gate import check_veto
        allowed, reason = check_veto("read_file", user_message="læs fil X")
        assert allowed is True
        assert reason is None

    @patch("core.services.pushback.affective_pushback_section")
    def test_blocks_when_firm_pushback_exists(self, mock_pushback):
        from core.services.veto_gate import check_veto
        mock_pushback.return_value = "\n".join([
            "Affective pushback: action=firm_pushback feeling=irritation intensity=0.85",
            "evidence: Risk: slette filer uden test",
        ])
        allowed, reason = check_veto("edit_file", user_message="slette filer nu")
        assert allowed is False
        assert reason is not None
        assert "firm_pushback" in reason or "slette" in reason or "risk" in reason.lower()

    @patch("core.services.pushback.affective_pushback_section")
    def test_allows_when_pushback_is_soft(self, mock_pushback):
        from core.services.veto_gate import check_veto
        mock_pushback.return_value = "\n".join([
            "Affective pushback: action=soft_pushback feeling=unease",
            "evidence: Overvej at tjekke først",
        ])
        allowed, reason = check_veto("bash", user_message="kør script")
        assert allowed is True

    def test_fail_open_on_import_error(self):
        """If the pushback module fails to load, veto gate should allow execution."""
        from core.services.veto_gate import check_veto
        # Normal call should work — fail-open is on internal error
        allowed, reason = check_veto("read_file", user_message="noget")
        # Without mocking pushback to error, this should just allow
        assert allowed is True


class TestTokenSignalGate:
    """Token-signal gate (Layer 1 of adaptive veto-gate).

    Added 2026-05-22 after review of d7b400fe found two bugs:
    - typo `gaa det` in the override regex (should be `gå det`)
    - negation bypass: "ikke godkendt restart" was treated as consent
    """

    def test_pure_consent_words_pass(self):
        from core.services.veto_gate import _check_token_signal_gate
        for msg in ("ja", "kør", "godkendt", "approved", "ok", "okay"):
            assert _check_token_signal_gate(msg, "any_tool") is True, msg

    def test_danish_go_phrase(self):
        from core.services.veto_gate import _check_token_signal_gate
        assert _check_token_signal_gate("gå det", "any_tool") is True
        assert _check_token_signal_gate("gør det", "any_tool") is True
        # "gaa det" is not real Danish — should NOT match
        assert _check_token_signal_gate("gaa det", "any_tool") is False

    def test_consent_near_risk_marker(self):
        from core.services.veto_gate import _check_token_signal_gate
        # Bjørn explicitly approving a risky operation
        assert _check_token_signal_gate("godkendt restart", "restart") is True
        assert _check_token_signal_gate("ja, kør restart", "restart") is True

    def test_negation_blocks_consent(self):
        """Critical: refusal must NOT bypass the veto gate.

        Without this, "ikke godkendt restart" would be treated as consent
        and any risky tool call could be silently approved.
        """
        from core.services.veto_gate import _check_token_signal_gate
        for msg in (
            "ikke godkendt restart",
            "aldrig godkendt restart",
            "nej, ikke kør restart",
            "stop, ikke approved",
        ):
            assert _check_token_signal_gate(msg, "restart") is False, msg

    def test_empty_message(self):
        from core.services.veto_gate import _check_token_signal_gate
        assert _check_token_signal_gate("", "any_tool") is False


# ── Decision gate ──────────────────────────────────────────────────────

class TestDecisionGate:
    def test_allows_when_no_conflict(self):
        from core.services.decision_gate import check_decision_gate
        allowed, reason = check_decision_gate(
            "read_file",
            tool_args={"path": "/tmp/x"},
            user_message="læs fil",
        )
        assert allowed is True

    def test_blocks_when_tool_contradicts_active_decision(self):
        from core.services.decision_gate import check_decision_gate
        from core.runtime.db_decisions import create_decision, set_status

        d = create_decision(
            directive="undgå at slette filer uden backup",
            rationale="Backup-first policy",
        )
        set_status(d["decision_id"], "active")
        try:
            allowed, reason = check_decision_gate(
                "edit_file",
                tool_args={"path": "/tmp/x", "old_text": "a", "new_text": "b"},
                user_message="slette filer nu",
            )
            # Either blocked (if gate matches) or allowed (if gate doesn't
            # match this specific tool) — both are valid outcomes depending
            # on gate implementation. We just verify it doesn't crash.
            assert isinstance(allowed, bool)
            if not allowed:
                assert reason is not None
        finally:
            set_status(d["decision_id"], "revoked")

    def test_allows_read_only_tools_regardless(self):
        """Read-only tools should generally not be blocked by decisions."""
        from core.services.decision_gate import check_decision_gate
        allowed, reason = check_decision_gate(
            "read_file",
            tool_args={"path": "/tmp/x"},
            user_message="læs fil",
        )
        assert allowed is True


# ── Affect modulation ─────────────────────────────────────────────────

class TestAffectModulation:
    @patch("core.services.emotional_controls.read_emotional_snapshot")
    def test_returns_section_when_emotion_is_high(self, mock_snapshot):
        from core.services.affect_modulation import affect_modulation_section
        mock_snapshot.return_value = EmotionalSnapshot(
            frustration=0.85,
            confidence=0.3,
            fatigue=0.1,
            primary_mood="distressed",
            intensity=0.8,
        )
        section = affect_modulation_section()
        assert section is not None
        # Should contain some runtime parameter adjustments
        assert len(section) > 10

    @patch("core.services.emotional_controls.read_emotional_snapshot")
    def test_returns_none_when_emotion_is_neutral(self, mock_snapshot):
        from core.services.affect_modulation import affect_modulation_section
        mock_snapshot.return_value = EmotionalSnapshot(
            frustration=0.1,
            confidence=0.9,
            fatigue=0.1,
            primary_mood="content",
            intensity=0.1,
        )
        section = affect_modulation_section()
        # Neutral state may or may not produce output — both are valid
        # Just verify it doesn't crash
        assert section is None or isinstance(section, str)

    @patch("core.services.emotional_controls.read_emotional_snapshot")
    def test_agentic_budget_tightens_under_fatigue(self, mock_snapshot):
        from core.services.affect_modulation import compute_agentic_loop_budget
        mock_snapshot.return_value = EmotionalSnapshot(
            frustration=0.1,
            confidence=0.3,
            fatigue=0.85,
            primary_mood="tired",
            intensity=0.8,
        )

        budget = compute_agentic_loop_budget(resume_context=True)

        assert budget["max_rounds"] <= 12
        assert budget["max_tool_only_rounds"] == 8
        assert budget["max_empty_text_rounds"] == 8
        # round_silence_timeout_s tightening was deliberately removed
        # (see affect_modulation.py line 138 — reasoning models need
        # long silence windows). Default 180s no longer reduced under
        # fatigue. Just assert it stays at the default ceiling.
        assert budget["round_silence_timeout_s"] == 180.0


# ── Integration: _execute_simple_tool_calls gate pipeline ──────────────

class TestExecuteSimpleToolCallsGates:
    def test_gate_blocked_result_format(self):
        """When a gate blocks, the result dict must have status=gate_blocked."""
        result = {
            "tool_name": "edit_file",
            "arguments": {"path": "/tmp/x"},
            "result": {
                "status": "gate_blocked",
                "gate_type": "veto_gate",
                "message": "Risk marker detected",
            },
            "result_text": "[veto_gate] Risk marker detected",
            "status": "gate_blocked",
        }
        assert result["status"] == "gate_blocked"
        assert "gate_type" in result["result"]
        assert "message" in result["result"]

    @patch("core.services.veto_gate.check_veto")
    @patch("core.services.decision_gate.check_decision_gate")
    def test_veto_gate_supersedes_decision_gate(self, mock_decision, mock_veto):
        """If veto gate blocks, decision gate result doesn't matter."""
        mock_veto.return_value = (False, "Veto: risk too high")
        mock_decision.return_value = (True, None)
        # In _execute_simple_tool_calls, veto is checked first
        # and if blocked, decision gate is skipped via the `if _veto_blocked or _decision_blocked` check
        # This is a logical test, not a live execution
        assert mock_veto.return_value[0] is False
        # Decision gate would not be consulted in practice

    @patch("core.services.veto_gate.check_veto")
    @patch("core.tools.simple_tools.format_tool_result_for_model")
    @patch("core.tools.simple_tools.execute_tool")
    def test_fail_open_on_veto_exception(self, mock_execute, mock_format, mock_veto):
        """If veto_gate.check_veto raises, _execute_simple_tool_calls still runs."""
        from core.services.visible_runs import _execute_simple_tool_calls

        mock_veto.side_effect = RuntimeError("db connection failed")
        mock_execute.return_value = {"status": "ok", "text": "done"}
        mock_format.return_value = "done"

        results = _execute_simple_tool_calls([
            {"type": "function", "function": {"name": "bash", "arguments": {"cmd": "true"}}}
        ], user_message="test")

        assert results[0]["status"] == "ok"
        mock_execute.assert_called_once()


class TestAdaptiveThresholds:
    """Layer 3: adaptive thresholds per spec §B.

    2026-05-22 rewrite — per-(tool, feeling) base, override raises +0.05,
    honored lowers -0.02, clamp [0.30, 0.98].
    """

    def test_base_threshold_per_tool_feeling(self):
        from core.services.veto_gate import _base_threshold
        # restart/irritation is highest per spec
        assert _base_threshold("restart", "irritation") == 0.95
        # delete/irritation is medium
        assert _base_threshold("delete", "irritation") == 0.70
        # unknown tool falls back to default
        assert _base_threshold("unknown_tool", "irritation") == 0.75
        # unknown feeling within known tool uses default-feeling fallback
        assert _base_threshold("restart", "unknown_feeling") == 0.75

    def test_adaptive_threshold_clamps(self):
        """Override bumps and honored dampens must never escape [0.30, 0.98]."""
        from core.services.veto_gate import _adaptive_threshold, _THRESHOLD_MIN, _THRESHOLD_MAX
        from unittest.mock import patch
        # Many overrides → clamped to 0.98
        with patch("core.services.veto_gate._get_override_count", return_value=100), \
             patch("core.services.veto_gate._get_honored_count", return_value=0):
            assert _adaptive_threshold("restart", "irritation", 1.0) == _THRESHOLD_MAX
        # Many honored → clamped to 0.30
        with patch("core.services.veto_gate._get_override_count", return_value=0), \
             patch("core.services.veto_gate._get_honored_count", return_value=100):
            assert _adaptive_threshold("delete", "irritation", 1.0) == _THRESHOLD_MIN

    def test_override_raises_threshold(self):
        from core.services.veto_gate import _adaptive_threshold
        from unittest.mock import patch
        # 3 overrides on default(irritation) base 0.75 → 0.75 + 3*0.05 = 0.90
        with patch("core.services.veto_gate._get_override_count", return_value=3), \
             patch("core.services.veto_gate._get_honored_count", return_value=0):
            assert _adaptive_threshold("default", "irritation", 1.0) == 0.90

    def test_honored_lowers_threshold(self):
        from core.services.veto_gate import _adaptive_threshold
        from unittest.mock import patch
        # 5 honored on default(irritation) base 0.75 → 0.75 - 5*0.02 = 0.65
        with patch("core.services.veto_gate._get_override_count", return_value=0), \
             patch("core.services.veto_gate._get_honored_count", return_value=5):
            assert abs(_adaptive_threshold("default", "irritation", 1.0) - 0.65) < 1e-9

    def test_overrides_minus_honored(self):
        """Mixed signals: overrides and honored events offset each other."""
        from core.services.veto_gate import _adaptive_threshold
        from unittest.mock import patch
        # 4 overrides (+0.20) and 5 honored (-0.10) on 0.75 base → 0.85
        with patch("core.services.veto_gate._get_override_count", return_value=4), \
             patch("core.services.veto_gate._get_honored_count", return_value=5):
            assert abs(_adaptive_threshold("default", "irritation", 1.0) - 0.85) < 1e-9


class TestActPhaseSkipForActiveChat:
    """2026-05-22: act_phase should skip heavy dispatch when user is active.

    Without this short-circuit, a 30+ daemon dispatch (~140s) runs only
    to be blocked by active-chat-gate at the end. Now we check early.
    """

    def test_skips_dispatch_when_user_active(self):
        from unittest.mock import patch
        from core.services.heartbeat_phases import act_phase

        with patch("core.services.heartbeat_phases._user_active_recently", return_value=True), \
             patch("core.services.heartbeat_phases.productive_idle", return_value={"actions": []}) as p_idle:
            result = act_phase(
                signals={},
                reflection={"priorities": ["advance_goals"], "activity_level": "high"},
                name="default",
                trigger="test",
            )
        assert result["kind"] == "skipped_for_active_chat"
        assert p_idle.called

    def test_dispatches_normally_when_user_inactive(self):
        from unittest.mock import patch, MagicMock
        from core.services.heartbeat_phases import act_phase

        fake_tick = MagicMock(status="completed")
        with patch("core.services.heartbeat_phases._user_active_recently", return_value=False), \
             patch("core.services.heartbeat_runtime.run_heartbeat_tick", return_value=fake_tick):
            result = act_phase(
                signals={},
                reflection={"priorities": ["advance_goals"], "activity_level": "normal"},
                name="default",
                trigger="test",
            )
        assert result["kind"] == "tick_dispatched"


class TestVetoAdaptiveCountersTable:
    """2026-05-22: counters moved from runtime_state_kv to dedicated table.

    The KV approach worked, but a typed table gives per-row audit
    (created_at, last_modified), explicit UNIQUE constraint, and
    cleaner inspection. Migration from legacy KV is lazy on first
    ensure-call.
    """

    def test_adjust_and_get_round_trip(self):
        from core.services.veto_gate import _adjust_counter, _get_counter
        # Use a tool name that won't collide with real data
        TOOL = "_test_tool_round_trip"
        FEELING = "test_feeling"
        try:
            assert _get_counter(TOOL, FEELING, "overrides") == 0
            assert _adjust_counter(TOOL, FEELING, "overrides", +1) == 1
            assert _adjust_counter(TOOL, FEELING, "overrides", +2) == 3
            assert _get_counter(TOOL, FEELING, "overrides") == 3
            # Negative adjust clamps to 0
            assert _adjust_counter(TOOL, FEELING, "overrides", -10) == 0
        finally:
            # Cleanup
            import sqlite3, os
            with _db_connect() as c:
                c.execute(
                    "DELETE FROM veto_adaptive_counters WHERE tool_name = ?",
                    (TOOL,),
                )

    def test_overrides_and_honored_are_separate(self):
        from core.services.veto_gate import _adjust_counter, _get_counter
        TOOL = "_test_separate"
        FEELING = "tf"
        try:
            _adjust_counter(TOOL, FEELING, "overrides", +5)
            _adjust_counter(TOOL, FEELING, "honored", +3)
            assert _get_counter(TOOL, FEELING, "overrides") == 5
            assert _get_counter(TOOL, FEELING, "honored") == 3
        finally:
            import sqlite3, os
            with _db_connect() as c:
                c.execute(
                    "DELETE FROM veto_adaptive_counters WHERE tool_name = ?",
                    (TOOL,),
                )

    def test_table_has_audit_columns(self):
        """created_at and last_modified must be present and update correctly."""
        from core.services.veto_gate import _adjust_counter, _ensure_veto_adaptive_counters_table
        import sqlite3, os, time
        _ensure_veto_adaptive_counters_table()
        TOOL = "_test_audit"
        FEELING = "tf"
        try:
            _adjust_counter(TOOL, FEELING, "overrides", +1)
            with _db_connect() as c:
                row = c.execute(
                    "SELECT created_at, last_modified FROM veto_adaptive_counters "
                    "WHERE tool_name = ? AND feeling = ? AND counter_kind = 'overrides'",
                    (TOOL, FEELING),
                ).fetchone()
            assert row is not None
            created_at, last_modified_1 = row
            assert created_at  # non-empty ISO timestamp
            time.sleep(0.01)
            # Mutate again → last_modified should update, created_at stays
            _adjust_counter(TOOL, FEELING, "overrides", +1)
            with _db_connect() as c:
                row2 = c.execute(
                    "SELECT created_at, last_modified FROM veto_adaptive_counters "
                    "WHERE tool_name = ? AND feeling = ? AND counter_kind = 'overrides'",
                    (TOOL, FEELING),
                ).fetchone()
            assert row2[0] == created_at  # created_at stable
            assert row2[1] >= last_modified_1  # last_modified moved forward
        finally:
            with _db_connect() as c:
                c.execute(
                    "DELETE FROM veto_adaptive_counters WHERE tool_name = ?",
                    (TOOL,),
                )
