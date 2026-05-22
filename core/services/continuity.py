"""Continuity Kernel — state capsule + live update + graded wake-up.

Carries Jarvis' felt state (mood, attention, relation, somatic, goals)
across sessions via a JSON state capsule on disk, updated after every
visible turn. At session start, a graded wake-up block is injected into
the prompt assembly instead of a cold reset.

Spec: docs/superpowers/specs/2026-05-11-continuity-design.md
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────

CAPSULE_DIR = Path.home() / ".jarvis-v2" / "state"
CAPSULE_CURRENT = CAPSULE_DIR / "session_capsule.json"
CAPSULE_PREV = CAPSULE_DIR / "session_capsule.prev.json"
CAPSULE_OLDER = CAPSULE_DIR / "session_capsule.older.json"

_MAX_CAPSULE_SIZE_BYTES = 4096  # hard limit; truncate if exceeded

# ── Schema ────────────────────────────────────────────────────────────

_EMPTY_CAPSULE: dict[str, Any] = {
    "schema_version": 1,
    "captured_at": "",
    "workspace_id": "default",
    "mood": {
        "valence": 0.5,
        "arousal": 0.5,
        "dominance": 0.5,
        "curiosity": 0.5,
        "fatigue": 0.0,
        "frustration": 0.0,
        "confidence": 0.5,
        "bearing": "neutral",
    },
    "attention": {
        "active_goal_id": None,
        "active_goal_title": None,
        "open_thread": None,
        "current_focus": None,
        "interrupted_task": None,
    },
    "relation": {
        "last_user_mood": "neutral",
        "last_user_arousal": 0.5,
        "last_interaction_type": "chat",
        "session_count_today": 1,
        "total_sessions_with_user": 0,
        "relationship_phase": "co-development",
    },
    "somatic": {
        "last_visual": None,
        "last_audio": None,
        "atmosphere": None,
        "visual_updated_at": None,
    },
    "goals": {
        "active_goals": [],
        "recent_completions": [],
    },
    "recent_activity": {
        "last_5_messages": [],
        "last_3_actions": [],
        "tools_used_recently": [],
        "last_tool_result_summary": None,
    },
    "wake_provenance": {
        "previous_session_id": None,
        "previous_session_ended_at": None,
        "hours_since_last_session": 0.0,
    },
}


# ── Helpers ───────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_dir() -> None:
    CAPSULE_DIR.mkdir(parents=True, exist_ok=True)


def _truncate_capsule(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure capsule stays under _MAX_CAPSULE_SIZE_BYTES.

    Truncates recent_activity and somatic sections first.
    """
    serialized = json.dumps(data, ensure_ascii=False, default=str)
    if len(serialized.encode("utf-8")) <= _MAX_CAPSULE_SIZE_BYTES:
        return data

    # Truncate recent_activity messages
    ra = data.get("recent_activity", {})
    msgs = ra.get("last_5_messages", [])
    while msgs and len(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")) > _MAX_CAPSULE_SIZE_BYTES * 0.9:
        msgs.pop(0)  # remove oldest
    ra["last_5_messages"] = msgs
    actions = ra.get("last_3_actions", [])
    ra["last_3_actions"] = actions[-2:] if len(actions) > 2 else actions
    data["recent_activity"] = ra

    # If still too big, truncate somatic
    if len(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")) > _MAX_CAPSULE_SIZE_BYTES:
        data["somatic"] = {
            "last_visual": None,
            "last_audio": None,
            "atmosphere": None,
            "visual_updated_at": None,
        }

    return data


# ── Public API ────────────────────────────────────────────────────────


def capture_state(
    *,
    mood: dict[str, Any] | None = None,
    attention: dict[str, Any] | None = None,
    relation: dict[str, Any] | None = None,
    somatic: dict[str, Any] | None = None,
    goals: dict[str, Any] | None = None,
    recent_activity: dict[str, Any] | None = None,
    workspace_id: str = "default",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Build a complete state capsule dict from partial inputs.

    Missing fields fall back to current capsule values or defaults.
    """
    current = read_capsule() or dict(_EMPTY_CAPSULE)

    capsule = dict(_EMPTY_CAPSULE)
    capsule["schema_version"] = 1
    capsule["captured_at"] = _now_iso()
    capsule["workspace_id"] = workspace_id

    # Mood: merge provided over current over defaults
    merged_mood = dict(current.get("mood", {}))
    merged_mood.update(mood or {})
    capsule["mood"] = merged_mood

    # Attention
    merged_attention = dict(current.get("attention", {}))
    merged_attention.update(attention or {})
    capsule["attention"] = merged_attention

    # Relation
    merged_relation = dict(current.get("relation", {}))
    merged_relation.update(relation or {})
    # Increment session count if fresh session
    if session_id and session_id != current.get("wake_provenance", {}).get("previous_session_id"):
        merged_relation["session_count_today"] = merged_relation.get("session_count_today", 0) + 1
    capsule["relation"] = merged_relation

    # Somatic
    merged_somatic = dict(current.get("somatic", {}))
    merged_somatic.update(somatic or {})
    capsule["somatic"] = merged_somatic

    # Goals
    merged_goals = dict(current.get("goals", {}))
    merged_goals.update(goals or {})
    capsule["goals"] = merged_goals

    # Recent activity
    merged_ra = dict(current.get("recent_activity", {}))
    if recent_activity:
        # Merge messages (keep newest)
        new_msgs = recent_activity.get("last_5_messages", [])
        existing_msgs = merged_ra.get("last_5_messages", [])
        merged_ra["last_5_messages"] = (existing_msgs + new_msgs)[-5:]
        # Actions
        if recent_activity.get("last_3_actions"):
            merged_ra["last_3_actions"] = recent_activity["last_3_actions"][-3:]
        # Tools
        if recent_activity.get("tools_used_recently"):
            merged_tools = set(merged_ra.get("tools_used_recently", []))
            merged_tools.update(recent_activity["tools_used_recently"])
            merged_ra["tools_used_recently"] = sorted(merged_tools)[-15:]
        # Summary
        if recent_activity.get("last_tool_result_summary"):
            merged_ra["last_tool_result_summary"] = recent_activity["last_tool_result_summary"]
    capsule["recent_activity"] = merged_ra

    # Wake provenance
    prev_prov = current.get("wake_provenance", {})
    capsule["wake_provenance"] = {
        "previous_session_id": session_id or prev_prov.get("previous_session_id"),
        "previous_session_ended_at": _now_iso(),
        "hours_since_last_session": prev_prov.get("hours_since_last_session", 0.0),
    }

    return _truncate_capsule(capsule)


def write_capsule(capsule: dict[str, Any]) -> None:
    """Write capsule to disk with rotation.

    current → prev → older → discarded.
    """
    _ensure_dir()

    # Rotate
    if CAPSULE_CURRENT.exists():
        CAPSULE_CURRENT.rename(CAPSULE_PREV)
    if CAPSULE_PREV.exists():
        CAPSULE_PREV.rename(CAPSULE_OLDER)

    # Write new current
    serialized = json.dumps(capsule, ensure_ascii=False, default=str, indent=2)
    CAPSULE_CURRENT.write_text(serialized, encoding="utf-8")


def read_capsule() -> dict[str, Any] | None:
    """Read the latest capsule from disk.

    Returns None if no capsule exists (fresh start).
    """
    path = CAPSULE_CURRENT
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.debug("Failed to read state capsule: %s", exc)
        return None


def get_wake_tier(hours_since_last: float) -> str:
    """Determine wake tier based on time since last session.

    Returns: "quick_return" | "normal" | "deep_sleep"
    """
    if hours_since_last < 0.5:
        return "quick_return"
    if hours_since_last < 4:
        return "normal"
    return "deep_sleep"


def build_conversation_continuity(*, limit: int = 3) -> str | None:
    """Build a 'hvad talte vi om' block from recent session data.

    Combines session titles, LLM-generated summaries, and recent messages
    into a narrative thread so Jarvis wakes up knowing what was discussed.

    Returns a markdown-formatted string or None if no data.
    """
    import logging as _log
    _log.debug("build_conversation_continuity")

    lines: list[str] = []
    seen_topics: set[str] = set()

    # 1. Recent session titles from chat_sessions
    try:
        from core.services.chat_sessions import list_chat_sessions as _lcs
        sessions = _lcs(limit=limit)
        if sessions:
            for s in sessions:
                sid = str(s.get("id") or s.get("session_id") or "")
                title = str(s.get("title") or "").strip()
                if sid and title and title.lower() != "new chat" and title not in seen_topics:
                    seen_topics.add(title)
                    created = str(s.get("created_at") or "")[:10] if s.get("created_at") else ""
                    date_str = f" ({created})" if created else ""
                    lines.append(f"- **{title}**{date_str}")
    except Exception:
        pass

    # 2. LLM-generated session summaries.
    # 2026-05-22 (Claude): filter out fresh summaries (<5 min old) and
    # round timestamps to HOUR (was minute). Live cache diff found this
    # list rotated every chat turn — each new turn generates a fresh
    # session summary that pushed the top entry down, breaking the
    # prompt cache. 5-min cooling window means recent activity is
    # invisible (the user is still seeing it in the active chat anyway);
    # only stable cross-session summaries appear here.
    try:
        from core.runtime.db import session_summary_recent as _ssr
        from datetime import datetime as _dt, timedelta as _td, UTC as _UTC
        # Over-fetch so the cooling filter doesn't yield empty.
        summaries = _ssr(limit=limit * 3)
        cutoff = _dt.now(_UTC) - _td(minutes=5)
        accepted = 0
        if summaries:
            for s in summaries:
                created_raw = str(s.get("created_at") or "")
                try:
                    created_dt = _dt.fromisoformat(created_raw.replace("Z", "+00:00"))
                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=_UTC)
                    if created_dt > cutoff:
                        continue  # too fresh; would rotate cache every turn
                except (ValueError, AttributeError):
                    pass
                # Round to hour (was minute) for extra cache stability
                created_label = created_raw[:13]  # YYYY-MM-DDTHH
                text = str(s.get("summary") or "").strip()
                if text:
                    lines.append(f"  - [{created_label}] {text[:200]}")
                    accepted += 1
                    if accepted >= limit:
                        break
    except Exception:
        pass

    # 3. Latest user message from most recent session (pick up open thread)
    try:
        from core.services.chat_sessions import recent_chat_session_messages as _rcsm
        if sessions:
            latest_sid = str(sessions[0].get("id") or sessions[0].get("session_id") or "")
            if latest_sid:
                msgs = _rcsm(latest_sid, limit=3)
                if msgs:
                    latest_user = None
                    for m in reversed(msgs):
                        if m.get("role") == "user":
                            latest_user = str(m.get("content") or "")[:120]
                            break
                    if latest_user:
                    # Don't add as separate line — it's already visible in context.
                    # Just use it to check if the thread is clearly still open.
                        pass
    except Exception:
        pass

    if not lines:
        return None

    header = "## Tidligere samtaler (seneste først)" if len(lines) > 1 else "## Seneste samtale"
    return f"{header}\n" + "\n".join(lines)


def build_wake_up_block(capsule: dict[str, Any] | None = None) -> str | None:
    """Build the wake-up block for prompt injection.

    Returns a formatted text block, or None if no prior state exists.
    """
    if capsule is None:
        capsule = read_capsule()
    if capsule is None:
        return None

    provenance = capsule.get("wake_provenance", {})
    hours_since = provenance.get("hours_since_last_session", 0.0)
    tier = get_wake_tier(hours_since)

    # Format duration
    if hours_since < 1:
        gap_str = f"{int(hours_since * 60)} min"
    elif hours_since < 24:
        gap_str = f"{int(hours_since)} timer"
    else:
        days = int(hours_since / 24)
        gap_str = f"{days} dag{'e' if days > 1 else ''}"

    mood = capsule.get("mood", {})
    attention = capsule.get("attention", {})
    relation = capsule.get("relation", {})
    somatic = capsule.get("somatic", {})
    goals_data = capsule.get("goals", {})
    recent = capsule.get("recent_activity", {})

    lines: list[str] = []

    # Header with tier indicator
    tier_label = {
        "quick_return": "Quick return",
        "normal": "Wake-up",
        "deep_sleep": "Deep sleep",
    }.get(tier, "Wake-up")
    lines.append(f"▲ CONTINUITY — {tier_label} ({gap_str} since last session)")

    # Warm tier: mood + focus (always included)
    # 2026-05-22 (Claude): bucket mood values to 0.1 increments. Live cache
    # investigation found CONTINUITY mood at byte 78,924 was the prime
    # cache-killer — curiosity=0.50 vs 0.49 between consecutive calls broke
    # the prompt-cache prefix every time. 0.1 buckets give 10 levels per
    # dimension (plenty of gradation for awareness) and survive small drift.
    mood_parts = []
    for k in ("curiosity", "fatigue", "frustration", "confidence"):
        v = mood.get(k)
        if v is not None:
            try:
                bucketed = round(float(v) * 10) / 10
                mood_parts.append(f"{k}={bucketed:.1f}")
            except (TypeError, ValueError):
                mood_parts.append(f"{k}={v}")
    bearing = mood.get("bearing", "")
    if mood_parts:
        lines.append(f"  Mood: {', '.join(mood_parts)}")
    if bearing:
        lines.append(f"  Bearing: {bearing}")

    focus = attention.get("current_focus") or attention.get("active_goal_title")
    if focus:
        lines.append(f"  Focus: {focus}")
    open_thread = attention.get("open_thread")
    if open_thread:
        lines.append(f"  Open thread: {open_thread}")

    # Relationship
    rel_phase = relation.get("relationship_phase", "")
    last_type = relation.get("last_interaction_type", "")
    if rel_phase or last_type:
        rel_str = f"  Relationship: {rel_phase}"
        if last_type:
            rel_str += f" — last interaction was {last_type}"
        lines.append(rel_str)

    # Somatic (compact)
    visual = somatic.get("last_visual")
    audio = somatic.get("last_audio")
    atmosphere = somatic.get("atmosphere")
    env_parts = []
    if visual:
        env_parts.append(visual[:60])
    if audio:
        env_parts.append(audio[:40])
    if atmosphere:
        env_parts.append(atmosphere)
    if env_parts:
        lines.append(f"  Environment: {', '.join(env_parts)}")

    # Cold tier: reference links (always included)
    active_goals = goals_data.get("active_goals", [])
    if active_goals:
        goal_refs = [f"\"{g.get('title', '')[:60]}\"" for g in active_goals[:3] if g.get('title')]
        if goal_refs:
            lines.append(f"  Active goals: {', '.join(goal_refs)}")
    completions = goals_data.get("recent_completions", [])
    if completions:
        lines.append(f"  Recent completions: {', '.join(completions[:3])}")

    # 2026-05-22 (Claude): "Last activity" and "Last exchange" removed from
    # continuity head. They duplicate content already present in the chat
    # transcript (the actual user/assistant messages following the system
    # prompt) and were the next cache-breaker after the mood fix —
    # changing every turn at byte ~79,288. The model still sees the same
    # information via the transcript; continuity stays focused on stable
    # session-context (bearing, focus, relationship, environment).

    lines.append(
        f"  Gap: {gap_str} since previous capsule. "
        "Continuity is reconstructed from stored capsule data."
    )

    return "\n".join(lines)


def live_update_after_turn(
    *,
    mood: dict[str, Any] | None = None,
    attention: dict[str, Any] | None = None,
    relation: dict[str, Any] | None = None,
    somatic: dict[str, Any] | None = None,
    goals: dict[str, Any] | None = None,
    recent_activity: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> None:
    """Call this after every visible turn to persist the state capsule.

    Wrapped: failures here must never break the visible chat.
    """
    try:
        capsule = capture_state(
            mood=mood,
            attention=attention,
            relation=relation,
            somatic=somatic,
            goals=goals,
            recent_activity=recent_activity,
            session_id=session_id,
        )
        write_capsule(capsule)
    except Exception as exc:
        logger.warning("continuity live_update failed: %s", exc)
