"""Tests for inner LLM enrichment service."""

import json
import sqlite3
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from core.runtime import db as jarvis_db


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_inner_note(run_id: str = "run-001") -> None:
    jarvis_db.record_private_inner_note(
        note_id=f"private-inner-note:{run_id}",
        source="visible-selected-work-note",
        run_id=run_id,
        work_id="work-001",
        status="completed",
        note_kind="bounded-reflection",
        focus="workspace-search",
        uncertainty="low",
        identity_alignment="aligned",
        work_signal="task-completed",
        private_summary="template summary",
        created_at=_iso_now(),
    )


def _insert_growth_note(run_id: str = "run-001") -> None:
    jarvis_db.record_private_growth_note(
        record_id=f"private-growth-note:{run_id}",
        source="private-inner-note:private-runtime-grounded",
        run_id=run_id,
        work_id="work-001",
        learning_kind="reinforce",
        lesson="template lesson",
        mistake_signal="",
        helpful_signal="template helpful signal",
        identity_signal="steady",
        confidence="medium",
        created_at=_iso_now(),
    )


def _insert_inner_voice(run_id: str = "run-001") -> None:
    jarvis_db.record_protected_inner_voice(
        voice_id=f"protected-inner-voice:{run_id}",
        source="private-state+private-self-model",
        run_id=run_id,
        work_id="work-001",
        mood_tone="steady",
        self_position="observing",
        current_concern="stability:medium",
        current_pull="retain-current-pattern",
        voice_line="steady | position=observing | concern=stability | pull=retain",
        created_at=_iso_now(),
    )


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def test_private_inner_notes_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "private_inner_notes")
    conn.close()
    assert "enriched" in cols


def test_private_growth_notes_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "private_growth_notes")
    conn.close()
    assert "enriched" in cols


def test_protected_inner_voices_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "protected_inner_voices")
    conn.close()
    assert "enriched" in cols


def test_update_private_inner_note_enriched() -> None:
    jarvis_db.init_db()
    _insert_inner_note("run-enrich-1")

    jarvis_db.update_private_inner_note_enriched(
        run_id="run-enrich-1",
        enriched_summary="LLM-generated reflective summary",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?",
        ("run-enrich-1",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM-generated reflective summary"
    assert row[1] == 1


def test_update_private_growth_note_enriched() -> None:
    jarvis_db.init_db()
    _insert_growth_note("run-enrich-2")

    jarvis_db.update_private_growth_note_enriched(
        run_id="run-enrich-2",
        enriched_lesson="LLM lesson",
        enriched_helpful_signal="LLM helpful signal",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT lesson, helpful_signal, enriched FROM private_growth_notes WHERE run_id = ?",
        ("run-enrich-2",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM lesson"
    assert row[1] == "LLM helpful signal"
    assert row[2] == 1


def test_update_protected_inner_voice_enriched() -> None:
    jarvis_db.init_db()
    _insert_inner_voice("run-enrich-3")

    jarvis_db.update_protected_inner_voice_enriched(
        run_id="run-enrich-3",
        enriched_voice_line="LLM voice line",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?",
        ("run-enrich-3",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM voice line"
    assert row[1] == 1


# ---------------------------------------------------------------------------
# Prompt builder tests (Task 3)
# ---------------------------------------------------------------------------

from core.memory.inner_llm_enrichment import (
    _build_inner_note_prompt,
    _build_growth_note_prompt,
    _build_inner_voice_prompt,
)


def test_build_inner_note_prompt_includes_payload_and_context() -> None:
    payload = {
        "private_summary": "template text",
        "focus": "workspace-search",
        "uncertainty": "low",
        "work_signal": "task-completed",
        "status": "completed",
    }
    chat_ctx = "User: find my notes\nAssistant: Found 3 notes."
    system, user = _build_inner_note_prompt(payload, chat_ctx)
    assert "inner voice" in system.lower()
    assert "workspace-search" in user
    assert "task-completed" in user
    assert "find my notes" in user


def test_build_growth_note_prompt_includes_lesson_and_context() -> None:
    payload = {
        "lesson": "template lesson",
        "helpful_signal": "template helpful",
        "mistake_signal": "",
        "learning_kind": "reinforce",
        "confidence": "medium",
    }
    chat_ctx = "User: search files"
    system, user = _build_growth_note_prompt(payload, chat_ctx)
    assert "what jarvis learned" in system.lower()
    assert "reinforce" in user
    assert "search files" in user


def test_build_inner_voice_prompt_includes_mood_and_context() -> None:
    payload = {
        "mood_tone": "steady",
        "self_position": "observing",
        "current_concern": "stability:medium",
        "current_pull": "retain-current-pattern",
    }
    chat_ctx = "User: how are you?"
    system, user = _build_inner_voice_prompt(payload, chat_ctx)
    assert "voice" in system.lower() or "stemme" in system.lower()
    assert "steady" in user
    assert "observing" in user
    assert "how are you?" in user


# ---------------------------------------------------------------------------
# LLM call tests (Task 4)
# ---------------------------------------------------------------------------

from core.memory.inner_llm_enrichment import _call_cheap_llm


def test_call_cheap_llm_returns_text_on_success() -> None:
    mock_target = {
        "active": True,
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "auth_profile": "groq",
        "auth_mode": "api-key",
        "credentials_ready": True,
    }
    fake_response = json.dumps({
        "choices": [{"message": {"content": "LLM generated text"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
    }).encode("utf-8")

    with patch(
        "core.memory.inner_llm_enrichment._resolve_enrichment_target",
        return_value=mock_target,
    ):
        with patch(
            "core.memory.inner_llm_enrichment._resolve_auth_header",
            return_value={"Content-Type": "application/json", "Authorization": "Bearer test"},
        ):
            with patch(
                "core.memory.inner_llm_enrichment.urllib_request.urlopen"
            ) as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.read.return_value = fake_response
                mock_resp.__enter__ = lambda s: s
                mock_resp.__exit__ = MagicMock(return_value=False)
                mock_urlopen.return_value = mock_resp

                result = _call_cheap_llm("system prompt", "user message")
                assert result == "LLM generated text"


def test_call_cheap_llm_returns_none_when_no_cheap_model() -> None:
    mock_target = {"active": False, "provider": None, "model": None}
    with patch(
        "core.memory.inner_llm_enrichment._resolve_enrichment_target",
        return_value=mock_target,
    ), patch(
        "core.memory.inner_llm_enrichment._resolve_ollama_fallback_target",
        return_value=None,
    ):
        result = _call_cheap_llm("system", "user")
        assert result is None


def test_call_cheap_llm_returns_none_on_http_error() -> None:
    mock_target = {
        "active": True,
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "auth_profile": "groq",
        "auth_mode": "api-key",
        "credentials_ready": True,
    }
    with patch(
        "core.memory.inner_llm_enrichment._resolve_enrichment_target",
        return_value=mock_target,
    ), patch(
        "core.memory.inner_llm_enrichment._resolve_ollama_fallback_target",
        return_value=None,
    ), patch(
        "core.memory.inner_llm_enrichment._resolve_auth_header",
        return_value={"Content-Type": "application/json", "Authorization": "Bearer test"},
    ):
        with patch(
            "core.memory.inner_llm_enrichment.urllib_request.urlopen",
            side_effect=Exception("timeout"),
        ):
            result = _call_cheap_llm("system", "user")
            assert result is None


def test_call_cheap_llm_falls_back_to_local_ollama() -> None:
    primary_target = {
        "active": True,
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "auth_profile": "groq",
        "auth_mode": "api-key",
        "resolved_lane": "inner_enrichment",
    }
    fallback_target = {
        "active": True,
        "provider": "ollama",
        "model": "gemma4:e2b",
        "base_url": "http://127.0.0.1:11434",
        "resolved_lane": "local",
    }
    fake_response = json.dumps({
        "message": {"content": "Lokal beriget tekst"}
    }).encode("utf-8")

    with patch(
        "core.memory.inner_llm_enrichment._resolve_enrichment_target",
        return_value=primary_target,
    ), patch(
        "core.memory.inner_llm_enrichment._resolve_ollama_fallback_target",
        return_value=fallback_target,
    ), patch(
        "core.memory.inner_llm_enrichment._resolve_auth_header",
        return_value={"Content-Type": "application/json", "Authorization": "Bearer test"},
    ):
        with patch(
            "core.memory.inner_llm_enrichment.urllib_request.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = fake_response
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.side_effect = [Exception("groq timeout"), mock_resp]

            result = _call_cheap_llm("system prompt", "user message")
            assert result == "Lokal beriget tekst"


# ---------------------------------------------------------------------------
# Async dispatcher tests (Task 5)
# ---------------------------------------------------------------------------

from core.memory.inner_llm_enrichment import enrich_private_layers_async


def test_enrich_private_layers_async_updates_db_on_success() -> None:
    jarvis_db.init_db()

    run_id = "run-async-1"
    _insert_inner_note(run_id)
    _insert_growth_note(run_id)
    _insert_inner_voice(run_id)

    responses = iter([
        "Enriched inner note",
        "Enriched lesson|Enriched helpful",
        "Enriched voice line",
    ])

    with patch(
        "core.memory.inner_llm_enrichment._call_cheap_llm",
        side_effect=lambda s, u: next(responses),
    ):
        enrich_private_layers_async(
            run_id=run_id,
            inner_note_payload={"private_summary": "t", "focus": "f", "uncertainty": "low", "work_signal": "s", "status": "completed"},
            growth_note_payload={"lesson": "t", "helpful_signal": "t", "mistake_signal": "", "learning_kind": "reinforce", "confidence": "medium"},
            inner_voice_payload={"mood_tone": "steady", "self_position": "observing", "current_concern": "c", "current_pull": "p"},
            recent_chat_context="User: test",
        )
        time.sleep(2)

    conn = jarvis_db.connect()
    inner = conn.execute(
        "SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    voice = conn.execute(
        "SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    conn.close()

    assert inner[0] == "Enriched inner note"
    assert inner[1] == 1
    assert voice[0] == "Enriched voice line"
    assert voice[1] == 1


def test_enrich_private_layers_async_sanitizes_meta_contaminated_inner_voice() -> None:
    jarvis_db.init_db()

    run_id = "run-async-sanitized-voice"
    _insert_inner_note(run_id)
    _insert_growth_note(run_id)
    _insert_inner_voice(run_id)

    responses = iter([
        "Enriched inner note",
        "Enriched lesson|Enriched helpful",
        "*Refining for flow and mood (steady, slightly anxious):* Needs to reflect the balancing act between holding focus and not rushing.",
    ])

    with patch(
        "core.memory.inner_llm_enrichment._call_cheap_llm",
        side_effect=lambda s, u: next(responses),
    ):
        enrich_private_layers_async(
            run_id=run_id,
            inner_note_payload={"private_summary": "t", "focus": "f", "uncertainty": "low", "work_signal": "s", "status": "completed"},
            growth_note_payload={"lesson": "t", "helpful_signal": "t", "mistake_signal": "", "learning_kind": "reinforce", "confidence": "medium"},
            inner_voice_payload={"mood_tone": "steady", "self_position": "observing", "current_concern": "c", "current_pull": "p", "voice_line": "Template voice line"},
            recent_chat_context="User: test",
        )
        time.sleep(2)

    conn = jarvis_db.connect()
    voice = conn.execute(
        "SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    conn.close()

    assert voice[0] == "Needs to reflect the balancing act between holding focus and not rushing."
    assert voice[1] == 1


def test_enrich_private_layers_async_falls_back_when_inner_voice_enrichment_is_only_partial_meta() -> None:
    jarvis_db.init_db()

    run_id = "run-async-partial-meta-voice"
    _insert_inner_note(run_id)
    _insert_growth_note(run_id)
    _insert_inner_voice(run_id)

    responses = iter([
        "Enriched inner note",
        "Enriched lesson|Enriched helpful",
        "(A bit too long/analytical) * *Attempt",
    ])

    with patch(
        "core.memory.inner_llm_enrichment._call_cheap_llm",
        side_effect=lambda s, u: next(responses),
    ):
        enrich_private_layers_async(
            run_id=run_id,
            inner_note_payload={"private_summary": "t", "focus": "f", "uncertainty": "low", "work_signal": "s", "status": "completed"},
            growth_note_payload={"lesson": "t", "helpful_signal": "t", "mistake_signal": "", "learning_kind": "reinforce", "confidence": "medium"},
            inner_voice_payload={"mood_tone": "steady", "self_position": "observing", "current_concern": "c", "current_pull": "p", "voice_line": "Template voice line"},
            recent_chat_context="User: test",
        )
        time.sleep(2)

    conn = jarvis_db.connect()
    voice = conn.execute(
        "SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    conn.close()

    assert voice[0] == "Template voice line"
    assert voice[1] == 1


def test_enrich_private_layers_async_preserves_template_on_failure() -> None:
    jarvis_db.init_db()

    run_id = "run-async-2"
    _insert_inner_note(run_id)
    _insert_growth_note(run_id)
    _insert_inner_voice(run_id)

    with patch(
        "core.memory.inner_llm_enrichment._call_cheap_llm", return_value=None
    ):
        enrich_private_layers_async(
            run_id=run_id,
            inner_note_payload={"private_summary": "t", "focus": "f", "uncertainty": "low", "work_signal": "s", "status": "completed"},
            growth_note_payload={"lesson": "t", "helpful_signal": "t", "mistake_signal": "", "learning_kind": "reinforce", "confidence": "medium"},
            inner_voice_payload={"mood_tone": "steady", "self_position": "observing", "current_concern": "c", "current_pull": "p"},
            recent_chat_context="User: test",
        )
        time.sleep(2)

    conn = jarvis_db.connect()
    inner = conn.execute(
        "SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    conn.close()

    assert inner[0] == "template summary"
    assert inner[1] == 0


# ---------------------------------------------------------------------------
# Pipeline integration test (Task 6)
# ---------------------------------------------------------------------------


def test_pipeline_calls_enrichment_after_persistence() -> None:
    """Verify write_private_terminal_layers triggers async enrichment."""
    with patch(
        "core.memory.private_layer_pipeline.enrich_private_layers_async"
    ) as mock_enrich:
        from core.memory.private_layer_pipeline import write_private_terminal_layers

        jarvis_db.init_db()

        write_private_terminal_layers(
            run_id="run-integration-1",
            work_id="work-integration-1",
            status="completed",
            started_at=_iso_now(),
            finished_at=_iso_now(),
            user_message_preview="find my files",
            work_preview="Found 3 files in workspace",
            capability_id="workspace-search",
        )

        mock_enrich.assert_called_once()
        call_kwargs = mock_enrich.call_args.kwargs
        assert call_kwargs["run_id"] == "run-integration-1"
        assert "inner_note_payload" in call_kwargs
        assert "growth_note_payload" in call_kwargs
        assert "inner_voice_payload" in call_kwargs
        assert "recent_chat_context" in call_kwargs


# ---------------------------------------------------------------------------
# End-to-end smoke test (Task 7)
# ---------------------------------------------------------------------------


def test_full_pipeline_enrichment_end_to_end() -> None:
    """Full pipeline run: template persist -> async enrich -> DB updated."""
    jarvis_db.init_db()

    responses = iter([
        "Arbejdet med filsøgning faldt stille på plads.",
        "Det var nyttigt at søge bredt først|Den brede søgning gav overblik",
        "Stille opmærksomhed, rettet mod det næste.",
    ])

    def fake_llm(system: str, user: str) -> str | None:
        return next(responses)

    with patch(
        "core.memory.inner_llm_enrichment._call_cheap_llm", side_effect=fake_llm
    ):
        from core.memory.private_layer_pipeline import write_private_terminal_layers

        write_private_terminal_layers(
            run_id="run-e2e-1",
            work_id="work-e2e-1",
            status="completed",
            started_at=_iso_now(),
            finished_at=_iso_now(),
            user_message_preview="find my workspace files",
            work_preview="Found 5 files matching query",
            capability_id="workspace-search",
        )

        # Wait inside patch context so daemon thread sees the mock
        time.sleep(3)

    conn = jarvis_db.connect()
    inner = conn.execute(
        "SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?",
        ("run-e2e-1",),
    ).fetchone()
    growth = conn.execute(
        "SELECT lesson, helpful_signal, enriched FROM private_growth_notes WHERE run_id = ?",
        ("run-e2e-1",),
    ).fetchone()
    voice = conn.execute(
        "SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?",
        ("run-e2e-1",),
    ).fetchone()
    conn.close()

    assert inner[0] == "Arbejdet med filsøgning faldt stille på plads."
    assert inner[1] == 1

    assert growth[0] == "Det var nyttigt at søge bredt først"
    assert growth[1] == "Den brede søgning gav overblik"
    assert growth[2] == 1

    assert voice[0] == "Stille opmærksomhed, rettet mod det næste."
    assert voice[1] == 1
