"""Tests for the workspace-led inner voice daemon.

Verifies:
- Workspace prompt asset is loaded and used
- Grounding bundle flows correctly into render path
- LLM-rendered vs fallback is observable
- Invalid/empty output is handled bounded
- Cadence gates are respected
- Policy disabled/missing stops the daemon
- Persistence works
- Composition is not hardcoded in Python
"""
from __future__ import annotations

import json
from unittest.mock import patch


# ---------------------------------------------------------------------------
# 1. Policy loading from workspace asset
# ---------------------------------------------------------------------------

def test_inner_voice_policy_loads_from_workspace(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    policy = daemon.load_inner_voice_policy()
    assert policy["loaded"] is True
    assert policy["status"] == "enabled"
    assert policy["authority"] == "non-authoritative"
    assert policy["max_length"] == 160
    assert "INNER_VOICE.md" in policy["path"]


def test_inner_voice_policy_disabled_skips(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    workspace = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    iv_path = workspace / "INNER_VOICE.md"
    iv_path.write_text("# INNER VOICE\n\nStatus: disabled\n", encoding="utf-8")

    result = daemon.run_inner_voice_daemon(trigger="test")
    assert result["action"] == "skipped"
    assert "disabled" in result["reason"]


def test_inner_voice_policy_empty_skips(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    workspace = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    iv_path = workspace / "INNER_VOICE.md"
    iv_path.write_text("", encoding="utf-8")

    policy = daemon.load_inner_voice_policy()
    assert policy["loaded"] is False
    assert policy["status"] == "empty"


# ---------------------------------------------------------------------------
# 2. Grounding bundle
# ---------------------------------------------------------------------------

def test_grounding_bundle_returns_defaults_without_prior_voice(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    grounding = daemon._build_grounding_bundle()
    assert grounding["mood_tone"] == "quiet"
    assert grounding["source"] == "default-no-prior-voice"


def test_grounding_bundle_reads_from_protected_inner_voice(isolated_runtime) -> None:
    db = isolated_runtime.db
    daemon = isolated_runtime.inner_voice_daemon
    db.record_protected_inner_voice(
        voice_id="test-voice-1",
        source="test",
        run_id="test-run-1",
        work_id="test-work-1",
        mood_tone="attentive",
        self_position="exploring",
        current_concern="stability:watch",
        current_pull="observe-current-pattern",
        voice_line="test voice line",
        created_at="2026-01-01T00:00:00Z",
    )
    grounding = daemon._build_grounding_bundle()
    assert grounding["mood_tone"] == "attentive"
    assert grounding["self_position"] == "exploring"
    assert grounding["source"] == "protected-inner-voice-record"


# ---------------------------------------------------------------------------
# 3. LLM render path (mocked)
# ---------------------------------------------------------------------------

def test_llm_render_produces_bounded_note(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    # Reset cadence
    daemon._last_render_at = ""

    llm_response = json.dumps({
        "note": "I notice a quiet settling around the current work.",
        "grounded_in": "mood_tone",
    })

    with patch.object(daemon, "_call_llm", return_value={
        "text": llm_response,
        "provider": "ollama",
        "model": "test",
        "status": "success",
    }):
        result = daemon.run_inner_voice_daemon(trigger="test")

    assert result["action"] == "rendered"
    assert result["render_source"] == "llm"
    assert result["llm_status"] == "success"
    assert result["validation_outcome"] == "valid"
    assert result["grounded_in"] == "mood_tone"


def test_llm_failure_falls_back_to_python(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    daemon._last_render_at = ""

    with patch.object(daemon, "_call_llm", side_effect=RuntimeError("connection refused")):
        result = daemon.run_inner_voice_daemon(trigger="test")

    assert result["action"] == "rendered"
    assert result["render_source"] == "fallback"
    assert "error" in result["llm_status"]


def test_llm_empty_response_falls_back(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    daemon._last_render_at = ""

    with patch.object(daemon, "_call_llm", return_value={
        "text": "",
        "provider": "ollama",
        "model": "test",
        "status": "no-llm",
    }):
        result = daemon.run_inner_voice_daemon(trigger="test")

    assert result["action"] == "rendered"
    assert result["render_source"] == "fallback"


# ---------------------------------------------------------------------------
# 4. Validation
# ---------------------------------------------------------------------------

def test_validation_rejects_user_facing_language(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    daemon._last_render_at = ""

    llm_response = json.dumps({
        "note": "Sure, I will help you with that task right away!",
        "grounded_in": "mood_tone",
    })

    with patch.object(daemon, "_call_llm", return_value={
        "text": llm_response,
        "provider": "ollama",
        "model": "test",
        "status": "success",
    }):
        result = daemon.run_inner_voice_daemon(trigger="test")

    # Should fall back because "sure," is forbidden
    assert result["render_source"] == "fallback"


def test_validation_rejects_empty_note(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    valid, reason = daemon._validate_note("")
    assert valid is False
    assert reason == "empty-note"


def test_validation_rejects_too_long_note(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    valid, reason = daemon._validate_note("x" * 201)
    assert valid is False
    assert reason == "too-long"


def test_validation_accepts_bounded_reflective_note(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    valid, reason = daemon._validate_note(
        "I notice a quiet settling. The concern around stability feels less pressing now."
    )
    assert valid is True
    assert reason == "valid"


# ---------------------------------------------------------------------------
# 5. Cadence gate
# ---------------------------------------------------------------------------

def test_cadence_gate_blocks_rapid_reruns(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    daemon._last_render_at = ""

    llm_response = json.dumps({
        "note": "I hold this quietly.",
        "grounded_in": "mood_tone",
    })

    with patch.object(daemon, "_call_llm", return_value={
        "text": llm_response,
        "provider": "ollama",
        "model": "test",
        "status": "success",
    }):
        result1 = daemon.run_inner_voice_daemon(trigger="test")
        result2 = daemon.run_inner_voice_daemon(trigger="test")

    assert result1["action"] == "rendered"
    assert result2["action"] == "skipped"
    assert "cadence" in result2["reason"]


# ---------------------------------------------------------------------------
# 6. Persistence
# ---------------------------------------------------------------------------

def test_rendered_note_is_persisted(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    db = isolated_runtime.db
    daemon._last_render_at = ""

    llm_response = json.dumps({
        "note": "I notice the work has settled into a steady rhythm.",
        "grounded_in": "current_pull",
    })

    with patch.object(daemon, "_call_llm", return_value={
        "text": llm_response,
        "provider": "ollama",
        "model": "test",
        "status": "success",
    }):
        daemon.run_inner_voice_daemon(trigger="test")

    voice = db.get_protected_inner_voice()
    assert voice is not None
    assert "workspace-led:llm" in voice["source"]
    assert "settled into a steady rhythm" in voice["voice_line"]


# ---------------------------------------------------------------------------
# 7. Workspace prompt asset is actually used (not hardcoded)
# ---------------------------------------------------------------------------

def test_workspace_asset_text_appears_in_llm_prompt(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    daemon._last_render_at = ""

    captured_prompts = []

    def mock_call_llm(*, prompt):
        captured_prompts.append(prompt)
        return {"text": "", "provider": "phase1-runtime", "model": "test", "status": "no-llm"}

    with patch.object(daemon, "_call_llm", side_effect=mock_call_llm):
        daemon.run_inner_voice_daemon(trigger="test")

    assert len(captured_prompts) == 1
    prompt_text = captured_prompts[0]
    # The workspace INNER_VOICE.md content should be in the prompt
    assert "Inner voice is Jarvis" in prompt_text
    assert "Runtime Grounding Bundle" in prompt_text
    assert "mood_tone" in prompt_text


# ---------------------------------------------------------------------------
# 8. Observability: render source visible in result
# ---------------------------------------------------------------------------

def test_observability_distinguishes_llm_vs_fallback(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    daemon._last_render_at = ""

    # Fallback path
    with patch.object(daemon, "_call_llm", return_value={
        "text": "",
        "provider": "phase1-runtime",
        "model": "test",
        "status": "no-llm",
    }):
        fallback_result = daemon.run_inner_voice_daemon(trigger="test")

    assert fallback_result["render_source"] == "fallback"
    assert fallback_result["workspace_asset"] != ""

    # LLM path (reset cadence)
    daemon._last_render_at = ""
    llm_response = json.dumps({
        "note": "I hold this quietly.",
        "grounded_in": "mood_tone",
    })
    with patch.object(daemon, "_call_llm", return_value={
        "text": llm_response,
        "provider": "ollama",
        "model": "test",
        "status": "success",
    }):
        llm_result = daemon.run_inner_voice_daemon(trigger="test")

    assert llm_result["render_source"] == "llm"
    assert llm_result["workspace_asset"] != ""


# ---------------------------------------------------------------------------
# 9. Parse LLM response edge cases
# ---------------------------------------------------------------------------

def test_parse_llm_response_with_extra_text(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    raw = 'Here is the JSON:\n{"note": "I notice quiet.", "grounded_in": "mood_tone"}\nDone.'
    parsed = daemon._parse_llm_response(raw)
    assert parsed is not None
    assert parsed["note"] == "I notice quiet."


def test_parse_llm_response_invalid_json(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    parsed = daemon._parse_llm_response("this is not json at all")
    assert parsed is None


def test_parse_llm_response_missing_note_field(isolated_runtime) -> None:
    daemon = isolated_runtime.inner_voice_daemon
    parsed = daemon._parse_llm_response('{"grounded_in": "mood_tone"}')
    assert parsed is None
