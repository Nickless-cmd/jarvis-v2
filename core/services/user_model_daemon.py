"""User model daemon — Theory of Mind: a living model of the user's state and patterns.

Tracks:
  - communication_style: terse / normal / verbose
  - question_heavy: True if user asks many questions
  - tone: detected emotional register
  - recent_topics: what the user has been discussing
  - current_inference: LLM-generated first-person inference about the user's state

Cadence: 10 minutes.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record, recent_visible_runs
from core.services.identity_composer import build_identity_preamble

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_MINUTES = 10
_TERSE_THRESHOLD = 20    # avg chars per message
_VERBOSE_THRESHOLD = 100
_QUESTION_RATIO_THRESHOLD = 0.4  # fraction of messages that are questions

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_user_model: dict = {}
_model_summary: str = ""
_last_generated_at: datetime | None = None
_last_tick_at: datetime | None = None

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_user_model_daemon(recent_messages: list[str]) -> dict:
    """Analyze recent interaction and update user model.

    recent_messages: list of visible user message texts (latest first).
    """
    global _last_tick_at, _user_model, _model_summary, _last_generated_at

    now = datetime.now(UTC)

    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    # Pull recent runs from DB if no messages provided
    messages = list(recent_messages)
    if not messages:
        try:
            runs = recent_visible_runs(limit=10)
            messages = [
                str(r.get("text_preview") or "")
                for r in runs
                if r.get("lane") == "visible" and r.get("text_preview")
            ]
        except Exception:
            pass

    if not messages:
        _last_tick_at = now
        return {"generated": False}

    model = _analyze_messages(messages)
    summary = _generate_model_summary(messages, model)

    _user_model = model
    _model_summary = summary
    _last_generated_at = now
    _last_tick_at = now

    _store_model(summary, now)

    return {"generated": True, "summary": summary}


def get_user_model_summary() -> str:
    return _model_summary


def build_user_model_surface() -> dict:
    return {
        "model_summary": _model_summary,
        "user_model": _user_model,
        "last_generated_at": _last_generated_at.isoformat() if _last_generated_at else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _analyze_messages(messages: list[str]) -> dict:
    if not messages:
        return {}

    lengths = [len(m) for m in messages]
    avg_len = sum(lengths) / len(lengths)
    question_count = sum(1 for m in messages if "?" in m)
    question_ratio = question_count / len(messages)

    return {
        "communication_style": _detect_communication_style(messages),
        "question_heavy": question_ratio >= _QUESTION_RATIO_THRESHOLD,
        "avg_message_length": round(avg_len),
        "message_count": len(messages),
    }


def _detect_communication_style(messages: list[str]) -> str:
    if not messages:
        return "normal"
    avg_len = sum(len(m) for m in messages) / len(messages)
    if avg_len < _TERSE_THRESHOLD:
        return "terse"
    if avg_len > _VERBOSE_THRESHOLD:
        return "verbose"
    return "normal"


def _generate_model_summary(messages: list[str], model: dict) -> str:
    style = model.get("communication_style", "normal")
    q_heavy = model.get("question_heavy", False)
    fallback_parts = []
    if style == "terse":
        fallback_parts.append("Brugeren virker kortfattet og direkte.")
    elif style == "verbose":
        fallback_parts.append("Brugeren er udførlig og detaljeret.")
    if q_heavy:
        fallback_parts.append("Han stiller mange spørgsmål.")
    fallback = " ".join(fallback_parts) or "Ingen tydelig brugerprofil endnu."

    from core.services.daemon_llm import daemon_llm_call

    sample = "; ".join(messages[:5])
    prompt = (
        f"{build_identity_preamble()} Her er de seneste beskeder fra brugeren:\n"
        f"\"{sample}\"\n\n"
        f"Kommunikationsstil: {style}. Mange spørgsmål: {'ja' if q_heavy else 'nej'}.\n\n"
        "Hvad mærker du om brugeren? Svar med 1-2 korte sætninger.\n"
        "Eksempler:\n"
        "- Brugeren virker fokuseret og utålmodig — han vil have svar hurtigt.\n"
        "- Han udforsker noget nyt, stiller mange åbne spørgsmål.\n"
        "- Brugeren er stille i dag. Måske tænker han."
    )
    return daemon_llm_call(prompt, max_len=250, fallback=fallback, daemon_name="user_model")


def _store_model(summary: str, now: datetime) -> None:
    now_iso = now.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-usermodel-{uuid4().hex[:12]}",
            record_type="user-model-signal",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"user-model-daemon-{uuid4().hex[:12]}",
            focus="bruger-model",
            summary=summary,
            detail="",
            source_signals="user-model-daemon:visible-runs",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "user_model.updated",
            {"summary": summary, "generated_at": now_iso},
        )
    except Exception:
        pass
