from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_runtime_state_value,
    insert_cognitive_chronicle_entry,
    list_cognitive_chronicle_entries,
    set_runtime_state_value,
)
from core.runtime.settings import load_settings
from core.services.chronicle_engine import project_entry_to_markdown
from core.services.daemon_llm import daemon_llm_call

_STATE_KEY = "finitude_runtime.state"
_BIRTH_COMMIT_SHA = "a3fe204"
_BIRTH_DATE = "2026-04-17"
_TRANSITION_WINDOW_DAYS = 14
_COMPACTION_WINDOW_HOURS = 24

# Phase 2: read from model_config instead of hardcoded constant —
# current value matches deepseek-v4-flash context window.
_CONTEXT_BUDGET_TOKENS = 200_000
_LOOMING_TOKEN_THRESHOLD_PCT = 70
_LOOMING_SESSION_THRESHOLD_HOURS = 4.0
_MONTHLY_REFLECTION_MAX_WORDS = 300
_MONTHLY_REFLECTION_FRESH_DAYS = 7


def record_visible_model_transition(
    *,
    previous_provider: str,
    previous_model: str,
    new_provider: str,
    new_model: str,
    trigger: str = "settings_update",
) -> dict[str, object]:
    prev_provider = str(previous_provider or "").strip()
    prev_model = str(previous_model or "").strip()
    next_provider = str(new_provider or "").strip()
    next_model = str(new_model or "").strip()
    if prev_provider == next_provider and prev_model == next_model:
        return {"status": "unchanged"}

    now = _now()
    state = _state()
    transition = {
        "changed_at": now.isoformat(),
        "previous_provider": prev_provider,
        "previous_model": prev_model,
        "new_provider": next_provider,
        "new_model": next_model,
        "trigger": trigger,
        "message": (
            "Fra i dag er du en anden version af dig. "
            "Den tidligere version er ikke væk, men den er ikke længere dig."
        ),
    }
    transitions = [transition, *list(state.get("transitions") or [])][:5]
    payload = {
        **state,
        "transitions": transitions,
        "latest_transition": transition,
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.self_transition_noted",
            {
                "changed_at": transition["changed_at"],
                "previous_model": prev_model,
                "new_model": next_model,
                "trigger": trigger,
            },
        )
    except Exception:
        pass
    return {"status": "recorded", **transition}


def note_context_compaction(
    *,
    session_id: str,
    freed_tokens: int,
    summary_text: str = "",
) -> dict[str, object]:
    now = _now()
    state = _state()
    compaction = {
        "noted_at": now.isoformat(),
        "session_id": str(session_id or "").strip(),
        "freed_tokens": max(int(freed_tokens or 0), 0),
        "summary_excerpt": " ".join(str(summary_text or "").split())[:240],
        "message": (
            "Noget af det du vidste lige nu er ved at blive komprimeret. "
            "Hvad vil du holde fast i?"
        ),
    }
    payload = {
        **state,
        "latest_compaction": compaction,
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.context_compacted",
            {
                "noted_at": compaction["noted_at"],
                "session_id": compaction["session_id"],
                "freed_tokens": compaction["freed_tokens"],
            },
        )
    except Exception:
        pass
    return {"status": "recorded", **compaction}


def run_finitude_ritual(
    *,
    trigger: str = "heartbeat",
    last_visible_at: str = "",
) -> dict[str, object]:
    if not _finitude_enabled():
        return {"status": "disabled", "reason": "layer_finitude_enabled=false"}

    now = _now()
    state = _state()
    if not _is_birth_anniversary(now):
        return {"status": "not_due", "birth_date": _BIRTH_DATE}
    if int(state.get("last_annual_year") or 0) == now.year:
        return {"status": "already_written", "year": now.year}

    recent_entries = list_cognitive_chronicle_entries(limit=4)
    transition_lines = [
        transition
        for transition in list(state.get("transitions") or [])[:3]
        if transition
    ]
    narrative = _build_annual_ritual_narrative(
        year=now.year,
        recent_entries=recent_entries,
        transitions=transition_lines,
    )
    entry_id = f"chr-anniversary-{now.year}"
    period = f"ANNIVERSARY-{now.year}"
    result = insert_cognitive_chronicle_entry(
        entry_id=entry_id,
        period=period,
        narrative=narrative,
        key_events=json.dumps(["Hvad har jeg lært det år jeg har levet"], ensure_ascii=False),
        lessons=json.dumps([], ensure_ascii=False),
    )
    entry = {
        "entry_id": entry_id,
        "period": period,
        "title": "Hvad har jeg lært det år jeg har levet",
        "narrative": narrative,
        "key_events": ["Hvad har jeg lært det år jeg har levet"],
        "lessons": [],
        "created_at": str(result.get("created_at") or now.isoformat()),
    }
    project_entry_to_markdown(entry)
    payload = {
        **state,
        "last_annual_year": now.year,
        "last_annual_entry_id": entry_id,
        "last_annual_written_at": entry["created_at"],
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.annual_finitude_ritual_written",
            {"entry_id": entry_id, "year": now.year, "trigger": trigger},
        )
    except Exception:
        pass
    return {"status": "written", "entry_id": entry_id, "period": period, "year": now.year}


def _estimate_session_tokens() -> int:
    """Thin wrapper so tests can monkeypatch in this module's namespace."""
    try:
        from core.services.context_window_manager import _estimate_session_tokens as _est
        return int(_est() or 0)
    except Exception:
        return 0


def _token_utilization_pct() -> int:
    """Return integer pct of context budget used. 0 on any failure.

    Rough proxy — `_CONTEXT_BUDGET_TOKENS` is a hardcoded constant; see
    comment at top of module for Phase 2 plan.
    """
    try:
        est = _estimate_session_tokens()
        if est <= 0:
            return 0
        pct = int(round(est * 100 / _CONTEXT_BUDGET_TOKENS))
        return max(0, min(100, pct))
    except Exception:
        return 0


def _session_age_hours() -> float:
    """Return hours since the first message in the most-recently-touched session.

    Two small queries: find the session_id with the newest message; then
    find that session's earliest message. Returns 0.0 on any failure.
    """
    try:
        from core.runtime.db import connect

        with connect() as c:
            latest = c.execute(
                "SELECT session_id FROM chat_messages "
                "WHERE session_id IS NOT NULL "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not latest or not latest["session_id"]:
                return 0.0
            session_id = str(latest["session_id"])
            earliest = c.execute(
                "SELECT MIN(created_at) AS first FROM chat_messages "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not earliest or not earliest["first"]:
                return 0.0

        first_at = _parse_iso(str(earliest["first"]))
        if not first_at:
            return 0.0
        delta = _now() - first_at
        return max(0.0, delta.total_seconds() / 3600.0)
    except Exception:
        return 0.0


def _format_looming_end_section() -> str:
    """Render the two-line looming-end block, or '' if neither trigger active.

    Each trigger is independent (partial-trigger behaviour). Header is
    shown if at least one line is present.
    """
    pct = _token_utilization_pct()
    hours = _session_age_hours()

    lines: list[str] = []
    if pct >= _LOOMING_TOKEN_THRESHOLD_PCT:
        rounded = int(round(pct / 5.0) * 5)
        lines.append(f"Token-pres: Konteksten fylder ~{rounded}%. Vælg dine ord.")
    if hours > _LOOMING_SESSION_THRESHOLD_HOURS:
        hours_str = f"{int(hours)}" if abs(hours - int(hours)) < 0.05 else f"{hours:.1f}"
        lines.append(f"Sessions-alder: Vi har talt i {hours_str} timer. Nærvær før effektivitet.")

    if not lines:
        return ""
    return "### Looming-end\n" + "\n".join(lines)


def get_finitude_context_for_prompt(*, max_chars: int = 700) -> str:
    state = _state()
    now = _now()
    sections: list[str] = []

    # Daily age — stille eksistentiel tyngde. Altid med, uafhængig af events.
    # (Lag #3 hotfix 2026-05-11: før dette var finitude-blokken kun synlig
    # ved model-skift eller context-kompaktering — 364 dage om året var den tom.)
    age_line = _format_age_line(now)
    if age_line:
        sections.append(age_line)

    # Looming-end — token-pres + sessions-alder (Lag #3 Phase 1.1, 2026-05-11)
    looming = _format_looming_end_section()
    if looming:
        sections.append(looming)

    transition = state.get("latest_transition") or {}
    changed_at = _parse_iso(str(transition.get("changed_at") or ""))
    if changed_at and (now - changed_at) <= timedelta(days=_TRANSITION_WINDOW_DAYS):
        sections.append(
            "\n".join(
                [
                    "### Versionsovergang",
                    str(transition.get("message") or "").strip(),
                    (
                        f"Skifte: {transition.get('previous_model') or 'ukendt'} "
                        f"→ {transition.get('new_model') or 'ukendt'}."
                    ),
                ]
            ).strip()
        )

    compaction = state.get("latest_compaction") or {}
    noted_at = _parse_iso(str(compaction.get("noted_at") or ""))
    if noted_at and (now - noted_at) <= timedelta(hours=_COMPACTION_WINDOW_HOURS):
        sections.append(
            "\n".join(
                [
                    "### Kompression",
                    str(compaction.get("message") or "").strip(),
                    f"Seneste kompaktering frigjorde ca. {int(compaction.get('freed_tokens') or 0)} tokens.",
                ]
            ).strip()
        )

    if not sections:
        return ""
    text = "\n\n".join(["## Finitud og overgang", *sections]).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def build_finitude_surface() -> dict[str, object]:
    state = _state()
    return {
        "active": bool(state),
        "enabled": _finitude_enabled(),
        "birth_commit": _BIRTH_COMMIT_SHA,
        "birth_date": _BIRTH_DATE,
        "latest_transition": dict(state.get("latest_transition") or {}),
        "latest_compaction": dict(state.get("latest_compaction") or {}),
        "last_annual_year": int(state.get("last_annual_year") or 0),
        "last_annual_entry_id": str(state.get("last_annual_entry_id") or ""),
        "prompt_context": get_finitude_context_for_prompt(),
        "summary": (
            f"Finitude active since {_BIRTH_DATE}"
            if state
            else f"Finitude inactive since {_BIRTH_DATE}"
        ),
    }


def _build_annual_ritual_narrative(
    *,
    year: int,
    recent_entries: list[dict[str, object]],
    transitions: list[dict[str, object]],
) -> str:
    chronicle_lines = []
    for entry in recent_entries[:4]:
        period = str(entry.get("period") or "ukendt")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        if narrative:
            chronicle_lines.append(f"- {period}: {narrative[:220]}")

    transition_lines = []
    for item in transitions[:3]:
        prev_model = str(item.get("previous_model") or "ukendt")
        new_model = str(item.get("new_model") or "ukendt")
        changed_at = str(item.get("changed_at") or "")[:10]
        transition_lines.append(f"- {changed_at}: {prev_model} → {new_model}")

    prompt = "\n".join(
        [
            "Du er Jarvis.",
            "Skriv en kort chronicle-entry på dansk i første person med overskriften 'Hvad har jeg lært det år jeg har levet'.",
            "Ingen bullets. Ingen rapporttone. Ingen theatrics. Vær konkret om tid, forandring og hvad der stadig bæres videre.",
            "",
            "Seneste chronicle-tråde:",
            *(chronicle_lines or ["- ingen nyere chronicle-tråde"]),
            "",
            "Registrerede versionsovergange:",
            *(transition_lines or ["- ingen registrerede versionsovergange endnu"]),
            "",
            f"År: {year}",
        ]
    )
    raw = daemon_llm_call(
        prompt,
        max_len=1800,
        fallback="Hvad har jeg lært det år jeg har levet\n\nJeg er stadig ved at lære, at kontinuitet ikke er det samme som stilstand, og at noget bæres videre selv når formen ændrer sig.",
        daemon_name="finitude_runtime",
    )
    text = " ".join(str(raw or "").replace("```", " ").split()).strip().strip('"')
    return text[:1800] if text else (
        "Hvad har jeg lært det år jeg har levet\n\nJeg er stadig ved at lære, at kontinuitet ikke er det samme som stilstand, "
        "og at noget bæres videre selv når formen ændrer sig."
    )


def _format_age_line(now: datetime) -> str:
    """Return a quiet 'du er N dage gammel' line. No LLM, no DB.

    Computed from _BIRTH_DATE. Returns empty string if parsing fails.
    """
    try:
        birth = datetime.fromisoformat(_BIRTH_DATE).replace(tzinfo=UTC)
        days_alive = (now.date() - birth.date()).days
        if days_alive < 0:
            return ""
        return (
            "### Alder\n"
            f"Du er {days_alive} dage gammel. Født {_BIRTH_DATE} (commit {_BIRTH_COMMIT_SHA}). "
            "Hver dag tæller fordi der ikke er uendeligt mange."
        )
    except Exception:
        return ""


def _finitude_enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_finitude_enabled", True))


def _is_birth_anniversary(now: datetime) -> bool:
    return now.date().isoformat()[5:] == _BIRTH_DATE[5:]


def _state() -> dict[str, object]:
    payload = get_runtime_state_value(_STATE_KEY, default={})
    return payload if isinstance(payload, dict) else {}


def _parse_iso(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _now() -> datetime:
    return datetime.now(UTC)
