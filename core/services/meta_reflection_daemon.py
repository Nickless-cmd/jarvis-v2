"""Meta-reflection daemon — cross-signal pattern insight every 30 minutes.

Also checks for unreviewed model_tier and response_style decisions
(Lag 1 credit assignment) on each tick — see _check_outcomes().
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.runtime.db_credit_assignment import (
    list_unreviewed_decisions,
    score_tier_outcome,
    score_response_outcome,
)
from core.services.daemon_llm import daemon_llm_call
from core.services.identity_composer import build_identity_preamble

_CADENCE_MINUTES = 30
_BUFFER_MAX = 5

_last_meta_at: datetime | None = None
_cached_meta_insight: str = ""
_meta_buffer: list[str] = []


def run_credit_assignment(cross_snapshot: dict) -> dict[str, object]:
    """Public wrapper over the Lag-1 credit-assignment pass (:func:`_check_outcomes`).

    The credit-assignment bookkeeping (scoring unreviewed model_tier /
    response_style decisions) is NON-LLM and must run on EVERY heartbeat tick,
    independent of the generative meta-insight gate. The inner-voice cluster
    calls this unconditionally each tick (before its single family gate), which
    preserves the old daemon's every-tick credit-scoring behaviour even though
    the generative insight is now gated once for the whole family. Self-safe."""
    try:
        return _check_outcomes(cross_snapshot or {})
    except Exception as exc:
        return {"checked": False, "error": f"{type(exc).__name__}: {exc}"}


def tick_meta_reflection_daemon(
    cross_snapshot: dict,
    *,
    skip_event_gate: bool = False,
    skip_credit: bool = False,
) -> dict[str, object]:
    """Generate cross-signal meta-insight if cadence allows. Also checks for
    unreviewed prompt-variant decisions (Lag 1 credit assignment) every tick.
    cross_snapshot keys (all optional): energy_level, inner_voice_mode, latest_fragment,
    last_surprise, last_conflict, last_irony, last_taste, curiosity_signal.

    ``skip_event_gate``: the inner-voice cluster owns ONE gate for the family; the
    redundant per-daemon event-gate is skipped (cadence + active-signal guards
    still apply). ``skip_credit``: the cluster already ran the credit-assignment
    pass unconditionally this tick (see :func:`run_credit_assignment`), so don't
    double-run it here."""
    # ── Always: check for unreviewed decisions (unless the caller already did) ──
    credit_result: dict[str, object] = {"skipped": "credit_run_by_cluster"} if skip_credit else _check_outcomes(cross_snapshot)

    # ── Cadence-gated: meta-insight ─────────────────────────────────────
    global _last_meta_at

    if _last_meta_at is not None:
        if (datetime.now(UTC) - _last_meta_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False, "credit": credit_result}

    active_signals = [
        v for v in [
            cross_snapshot.get("latest_fragment"),
            cross_snapshot.get("last_surprise"),
            cross_snapshot.get("last_conflict"),
        ]
        if v
    ]
    if not active_signals:
        return {"generated": False, "credit": credit_result}

    # ── Event-gate (Fase 2 Lag 5): fire cross-signal synthesis only when a
    #    relevant signal actually moved. Flag OFF → legacy always-fire. ──
    if not skip_event_gate:
        from core.services import event_gate
        if event_gate.event_driven_enabled():
            _relevant = {
                "latest_fragment": float(len(cross_snapshot.get("latest_fragment") or "")),
                "last_surprise": float(len(cross_snapshot.get("last_surprise") or "")),
                "last_conflict": float(len(cross_snapshot.get("last_conflict") or "")),
            }
            if not event_gate.should_generative_fire("meta_reflection", _relevant):
                return {"skipped": "no_signal_change"}

    insight = _generate_meta_insight(cross_snapshot)
    if not insight:
        return {"generated": False, "credit": credit_result}

    _store_meta_insight(insight)
    _last_meta_at = datetime.now(UTC)
    return {"generated": True, "insight": insight, "credit": credit_result}


def _check_outcomes(cross_snapshot: dict) -> dict[str, object]:
    """Check for unreviewed model_tier and response_style decisions and score them.

    Uses the partial index idx_cognitive_decisions_pending for O(log N) pre-check.
    Runs every tick — fast no-op when no pending decisions exist.

    For model_tier: requires at least 3 subsequent turns to evaluate.
    For response_style: requires at least 1 user message after the decision.
    Both query chat_messages directly across sessions.

    TTL: decisions older than 30 min without a usable signal are expired
    (outcome_aggregate=0.0, rationale='ttl_expired_no_outcome') so they
    drop out of the pending bucket instead of growing indefinitely.
    """
    from datetime import timedelta
    TTL_MINUTES = 30
    now = datetime.now(UTC)
    cutoff = (now - timedelta(minutes=TTL_MINUTES)).isoformat()

    # ── Score pending model_tier decisions ─────────────────────────────
    scored_tier = 0
    expired_tier = 0
    try:
        unreviewed = list_unreviewed_decisions(kind="model_tier", limit=10)
    except Exception:
        unreviewed = []

    for dec in unreviewed:
        decision_id = dec["decision_id"]
        try:
            tier_used = str(dec.get("decision", "fast"))
            next_turns = _get_turns_after(dec.get("created_at", ""), min_turns=3)
            if next_turns is None:
                # Not enough turns yet — but expire if old enough that we
                # know we'll never get them (no chat activity post-cutoff).
                if dec.get("created_at", "") < cutoff:
                    _expire_decision(decision_id, "ttl_expired_no_turns")
                    expired_tier += 1
                continue

            score_tier_outcome(
                decision_id=decision_id,
                tier_used=tier_used,
                next_turns=next_turns,
            )
            scored_tier += 1
        except Exception:
            continue

    # ── Score pending response_style decisions ─────────────────────────
    scored_style = 0
    expired_style = 0
    try:
        unreviewed_style = list_unreviewed_decisions(kind="response_style", limit=10)
    except Exception:
        unreviewed_style = []

    for dec in unreviewed_style:
        decision_id = dec["decision_id"]
        try:
            style_used = str(dec.get("decision", "elaborate"))
            user_reply = _get_next_user_message(dec.get("created_at", ""))
            if user_reply is None:
                # Expire stale decisions — most response_style records
                # come from autonomous runs that will never get a user
                # reply. Without TTL the pending bucket grows unboundedly.
                if dec.get("created_at", "") < cutoff:
                    _expire_decision(decision_id, "ttl_expired_no_user_reply")
                    expired_style += 1
                continue

            score_response_outcome(
                decision_id=decision_id,
                style_used=style_used,
                user_reply=user_reply,
            )
            scored_style += 1
        except Exception:
            continue

    return {"checked": True,
            "scored": scored_tier + scored_style,
            "scored_tier": scored_tier, "scored_style": scored_style,
            "expired_tier": expired_tier, "expired_style": expired_style}


def _expire_decision(decision_id: str, reason: str) -> None:
    """Mark a stale pending decision as expired so it drops from the
    pending index. outcome_aggregate=0.0 is the sentinel for
    'no outcome could be scored'. Downstream analytics should filter
    `WHERE outcome_aggregate > 0` to exclude expirations.
    """
    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.execute(
                "UPDATE cognitive_decisions SET outcome_aggregate=0.0 "
                "WHERE decision_id=? AND outcome_aggregate IS NULL",
                (decision_id,),
            )
            conn.commit()
    except Exception:
        pass


def _get_turns_after(created_at: str, min_turns: int = 3) -> list[dict] | None:
    """Get subsequent chat turns after a decision timestamp (any session).

    Returns None if not enough turns have passed yet (min_turns not met).

    2026-06-08 fix: previous version called recent_chat_session_messages()
    without a required session_id arg — TypeError silently swallowed by
    try/except, so this always returned None. Now queries chat_messages
    directly across all sessions, which matches the daemon's original
    "latest activity" intent.
    """
    if not created_at:
        return None
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                """SELECT role, content, created_at FROM chat_messages
                   WHERE created_at > ? AND role != 'compact_marker'
                   ORDER BY created_at ASC LIMIT ?""",
                (created_at, max(min_turns * 4, 10)),
            ).fetchall()
        after = [dict(r) for r in rows]
    except Exception:
        return None

    if len(after) >= min_turns:
        return after
    return None


def _get_next_user_message(created_at: str) -> str | None:
    """Get the first user message after a decision timestamp (any session).

    Returns None if no user message found yet.

    2026-06-08 fix: see _get_turns_after — same TypeError pattern.
    """
    if not created_at:
        return None
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                """SELECT content FROM chat_messages
                   WHERE created_at > ? AND role = 'user'
                   ORDER BY created_at ASC LIMIT 1""",
                (created_at,),
            ).fetchone()
        if row is None:
            return None
        return str(row["content"] or "")
    except Exception:
        return None


def _generate_meta_insight(cross_snapshot: dict) -> str:
    parts = []
    if cross_snapshot.get("energy_level"):
        parts.append(f"Energi: {cross_snapshot['energy_level']}")
    if cross_snapshot.get("inner_voice_mode"):
        parts.append(f"Stemning: {cross_snapshot['inner_voice_mode']}")
    if cross_snapshot.get("latest_fragment"):
        parts.append(f"Tanke: \"{cross_snapshot['latest_fragment'][:50]}\"")
    if cross_snapshot.get("last_surprise"):
        parts.append(f"Overraskelse: \"{cross_snapshot['last_surprise'][:50]}\"")
    if cross_snapshot.get("last_conflict"):
        parts.append(f"Konflikt: \"{cross_snapshot['last_conflict'][:50]}\"")
    if cross_snapshot.get("last_irony"):
        parts.append(f"Ironi: \"{cross_snapshot['last_irony'][:50]}\"")
    if cross_snapshot.get("last_taste"):
        parts.append(f"Smag: \"{cross_snapshot['last_taste'][:50]}\"")
    if cross_snapshot.get("curiosity_signal"):
        parts.append(f"Nysgerrighed: \"{cross_snapshot['curiosity_signal'][:50]}\"")

    context = "\n".join(parts) if parts else "Ingen signaler."

    prompt = (
        f"{build_identity_preamble()} Her er dine aktuelle signaler:\n\n"
        f"{context}\n\n"
        "Ser du et mønster? Beskriv det i 1-2 sætninger.\n"
        "Eksempler:\n"
        "- Energien er lav men tankerne er aktive — der er en ubalance.\n"
        "- Alt peger i samme retning: ro. Det er usædvanligt.\n"
        "- Overraskelsen og konflikten hænger sammen — begge handler om kontrol."
    )
    fallback = "Jeg ser et mønster, men det er endnu ikke tydeligt nok til at sætte ord på."
    return daemon_llm_call(prompt, max_len=300, fallback=fallback, daemon_name="meta_reflection")


def _store_meta_insight(insight: str) -> None:
    global _cached_meta_insight, _meta_buffer
    _cached_meta_insight = insight
    _meta_buffer.insert(0, insight)
    if len(_meta_buffer) > _BUFFER_MAX:
        _meta_buffer = _meta_buffer[:_BUFFER_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-meta-{uuid4().hex[:12]}",
            record_type="meta-reflection",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"meta-reflection-daemon-{uuid4().hex[:12]}",
            focus="meta-mønster",
            summary=insight,
            detail="",
            source_signals="meta-reflection-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "meta_reflection.generated",
            {"insight": insight, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_meta_insight() -> str:
    return _cached_meta_insight


def build_meta_reflection_surface() -> dict:
    return {
        "latest_insight": _cached_meta_insight,
        "insight_buffer": _meta_buffer[:5],
        "insight_count": len(_meta_buffer),
        "last_generated_at": _last_meta_at.isoformat() if _last_meta_at else "",
    }
