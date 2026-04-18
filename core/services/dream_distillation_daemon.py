from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_runtime_state_value,
    insert_private_brain_record,
    list_approval_feedback,
    set_runtime_state_value,
)
from core.runtime.settings import load_settings
from core.services.chronicle_engine import list_cognitive_chronicle_entries
from core.services.daemon_llm import daemon_llm_call

_STATE_KEY = "dream_distillation_daemon.state"
_VISIBLE_IDLE_MINUTES = 30
_RESIDUE_TTL_HOURS = 48
_MAX_RESIDUE_WORDS = 25
_MAX_RESIDUE_CHARS = 180


def run_dream_distillation_daemon(
    *,
    trigger: str = "heartbeat",
    last_visible_at: str = "",
) -> dict[str, object]:
    if not _dream_residue_enabled():
        return {"status": "disabled", "reason": "layer_dream_residue_enabled=false"}

    clear_expired_dream_residue()
    active = _state()
    if active.get("residue"):
        return {
            "status": "active",
            "created_at": str(active.get("created_at") or ""),
            "expires_at": str(active.get("expires_at") or ""),
            "residue": str(active.get("residue") or ""),
        }

    last_visible = _parse_iso(last_visible_at)
    now = datetime.now(UTC)
    if last_visible is not None:
        idle_minutes = (now - last_visible).total_seconds() / 60.0
        if idle_minutes < _VISIBLE_IDLE_MINUTES:
            return {
                "status": "not_idle",
                "reason": "visible-activity-too-recent",
                "idle_minutes": round(idle_minutes, 1),
            }

    chronicle_entries = list_cognitive_chronicle_entries(limit=6)
    selected_entries = chronicle_entries[:3]
    if not selected_entries:
        return {"status": "no_basis", "reason": "no-chronicle-entries"}

    approval_entries = list_approval_feedback(limit=2)
    dismissed_inner = _load_dismissed_inner_voice()
    lost_council = _load_lost_council_positions()
    deprioritized_initiatives = _load_deprioritized_initiatives()
    residue = _build_dream_residue(
        chronicle_entries=selected_entries,
        approval_entries=approval_entries,
        dismissed_inner=dismissed_inner,
        lost_council=lost_council,
        deprioritized_initiatives=deprioritized_initiatives,
    )
    if not residue:
        return {"status": "no_output", "reason": "llm-empty"}

    created_at = now.isoformat()
    expires_at = (now + timedelta(hours=_RESIDUE_TTL_HOURS)).isoformat()
    payload = {
        "residue": residue,
        "created_at": created_at,
        "expires_at": expires_at,
        "last_trigger": trigger,
        "chronicle_periods": [
            str(entry.get("period") or "")
            for entry in selected_entries
            if entry.get("period")
        ],
        "approval_states": [
            str(entry.get("approval_state") or "")
            for entry in approval_entries
            if entry.get("approval_state")
        ],
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.dream_residue_written",
            {
                "created_at": created_at,
                "expires_at": expires_at,
                "trigger": trigger,
            },
        )
    except Exception:
        pass
    return {"status": "written", **payload}


def get_dream_residue_for_prompt(*, max_chars: int = _MAX_RESIDUE_CHARS) -> str:
    clear_expired_dream_residue()
    state = _state()
    residue = str(state.get("residue") or "").strip()
    if not residue:
        return ""
    clipped = residue
    if len(clipped) > max_chars:
        clipped = clipped[: max_chars - 1].rstrip() + "…"
    return "\n".join(
        [
            "## Drømmerest (lavmælt carry-over)",
            clipped,
        ]
    )


def build_dream_distillation_surface() -> dict[str, object]:
    clear_expired_dream_residue()
    state = _state()
    residue = str(state.get("residue") or "").strip()
    return {
        "active": bool(residue),
        "residue": residue,
        "created_at": str(state.get("created_at") or ""),
        "expires_at": str(state.get("expires_at") or ""),
        "last_trigger": str(state.get("last_trigger") or ""),
        "chronicle_periods": list(state.get("chronicle_periods") or []),
        "approval_states": list(state.get("approval_states") or []),
        "summary": (
            f"Active dream residue until {state.get('expires_at')}"
            if residue
            else "No active dream residue"
        ),
    }


def clear_expired_dream_residue(*, now: datetime | None = None) -> bool:
    current = _state()
    expires_at = _parse_iso(str(current.get("expires_at") or ""))
    if not current.get("residue") or expires_at is None:
        return False
    current_now = now or datetime.now(UTC)
    if expires_at > current_now:
        return False
    # Log landing as observation before clearing — anti-goal: observe but do not steer
    _log_dream_landing(residue=str(current.get("residue") or ""), expired_at=current_now)
    set_runtime_state_value(_STATE_KEY, {})
    try:
        event_bus.publish(
            "cognitive_state.dream_residue_expired",
            {"expired_at": current_now.isoformat()},
        )
    except Exception:
        pass
    return True


def _log_dream_landing(*, residue: str, expired_at: datetime) -> None:
    """Log expired dream residue as observation. Anti-goal: stored for reflection, never fed back.

    The logged record is an observation that this dream 'landed' at this point in time.
    It does NOT influence the next dream generation cycle.
    """
    if not residue:
        return
    try:
        from uuid import uuid4
        insert_private_brain_record(
            record_id=f"pb-dream-landing-{uuid4().hex[:12]}",
            record_type="dream-landing",
            layer="dream_distillation",
            session_id="heartbeat",
            run_id=f"dream-landing-{uuid4().hex[:12]}",
            focus="drøm-landing",
            summary=residue[:200],
            detail="anti_goal=true: observation only, not used to steer next dream",
            source_signals="dream_distillation_daemon:expiry",
            confidence="high",
            created_at=expired_at.isoformat(),
        )
    except Exception:
        pass


def _load_dismissed_inner_voice() -> list[str]:
    """Load recent inner-voice signals that were suppressed or not surfaced."""
    try:
        from core.runtime.db import connect, _ensure_private_brain_records_table
        from datetime import timedelta
        cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()
        with connect() as conn:
            _ensure_private_brain_records_table(conn)
            rows = conn.execute(
                """SELECT summary FROM private_brain_records
                   WHERE layer = 'inner_voice' AND created_at >= ?
                   ORDER BY created_at DESC LIMIT 5""",
                (cutoff,),
            ).fetchall()
        return [str(r[0])[:100] for r in rows if r[0]]
    except Exception:
        return []


def _load_lost_council_positions() -> list[str]:
    """Load recent minority council positions that didn't become consensus."""
    try:
        from core.services.council_memory_service import get_recent_council_memories
        memories = get_recent_council_memories(limit=3)
        lost = []
        for m in memories:
            minority = str(m.get("minority_position") or m.get("dissenting_view") or "").strip()
            if minority:
                lost.append(minority[:100])
        return lost
    except Exception:
        return []


def _load_deprioritized_initiatives() -> list[str]:
    """Load recently rejected or expired initiative queue items."""
    try:
        from core.services.initiative_queue import get_initiative_queue_state
        state = get_initiative_queue_state()
        rejected = list(state.get("recent_rejected") or [])
        items = []
        for i in rejected[:3]:
            title = str(i.get("title") or i.get("description") or "").strip()
            if title:
                items.append(title[:100])
        return items
    except Exception:
        return []


def _build_dream_residue(
    *,
    chronicle_entries: list[dict[str, object]],
    approval_entries: list[dict[str, object]],
    dismissed_inner: list[str] | None = None,
    lost_council: list[str] | None = None,
    deprioritized_initiatives: list[str] | None = None,
) -> str:
    prompt = _build_residue_prompt(
        chronicle_entries=chronicle_entries,
        approval_entries=approval_entries,
        dismissed_inner=dismissed_inner or [],
        lost_council=lost_council or [],
        deprioritized_initiatives=deprioritized_initiatives or [],
    )
    raw = daemon_llm_call(
        prompt,
        max_len=240,
        fallback="",
        daemon_name="dream_distillation",
    )
    return _sanitize_residue(raw)


def _build_residue_prompt(
    *,
    chronicle_entries: list[dict[str, object]],
    approval_entries: list[dict[str, object]],
    dismissed_inner: list[str] | None = None,
    lost_council: list[str] | None = None,
    deprioritized_initiatives: list[str] | None = None,
) -> str:
    chronicle_lines = []
    for entry in chronicle_entries[:3]:
        period = str(entry.get("period") or "ukendt")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        if narrative:
            chronicle_lines.append(f"- {period}: {narrative[:220]}")

    approval_lines = []
    for entry in approval_entries[:2]:
        state = str(entry.get("approval_state") or "ukendt")
        tool_name = str(entry.get("tool_name") or "").strip() or "ukendt værktøj"
        reason = " ".join(str(entry.get("resolution_reason") or "").split()).strip()
        line = f"- {state}: {tool_name}"
        if reason:
            line += f" ({reason[:80]})"
        approval_lines.append(line)

    # Extra entropy sources — things that almost happened but didn't
    inner_lines = [f"- {s}" for s in (dismissed_inner or [])[:3] if s]
    council_lines = [f"- {s}" for s in (lost_council or [])[:2] if s]
    initiative_lines = [f"- {s}" for s in (deprioritized_initiatives or [])[:2] if s]

    lines = [
        "Du er Jarvis og destillerer drømmeagtig carry-over fra din egen kontinuitet.",
        "Skriv præcis én sætning på dansk, maks 25 ord.",
        "Ingen bullets. Ingen forklaring. Ingen rapporttone. Ingen anførselstegn.",
        "Sætningen skal lyde som en lavmælt tone der kan farve næste dags vågne opmærksomhed.",
        "",
        "Chronicle-tråde:",
        *chronicle_lines,
        "",
        "Seneste approval-udfald:",
        *(approval_lines if approval_lines else ["- ingen nyere approval-udfald"]),
        *(["", "Indre stemme — undertrykte signaler:", *inner_lines] if inner_lines else []),
        *(["", "Council — tabte mindretalspositioner:", *council_lines] if council_lines else []),
        *(["", "Initiativ-kø — fravalgte idéer:", *initiative_lines] if initiative_lines else []),
    ]
    return "\n".join(lines)


def _sanitize_residue(raw: str) -> str:
    text = " ".join(str(raw or "").replace("```", " ").split()).strip().strip('"')
    if not text:
        return ""
    words = text.split()
    if len(words) > _MAX_RESIDUE_WORDS:
        text = " ".join(words[:_MAX_RESIDUE_WORDS]).rstrip(" ,;:-")
    if len(text) > _MAX_RESIDUE_CHARS:
        text = text[:_MAX_RESIDUE_CHARS].rstrip(" ,;:-") + "…"
    return text.strip()


def _dream_residue_enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_dream_residue_enabled", True))


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
