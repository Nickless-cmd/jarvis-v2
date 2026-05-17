"""Meta-reflection daemon — cross-signal pattern insight every 30 minutes.

Also checks for unreviewed prompt-variant decisions (Lag 1 credit assignment)
on each tick — see _check_credit().
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.runtime.db_credit_assignment import (
    list_unreviewed_decisions,
    link_outcome_to_decision,
)
from core.services.daemon_llm import daemon_llm_call
from core.services.identity_composer import build_identity_preamble

_CADENCE_MINUTES = 30
_BUFFER_MAX = 5

_last_meta_at: datetime | None = None
_cached_meta_insight: str = ""
_meta_buffer: list[str] = []


def tick_meta_reflection_daemon(cross_snapshot: dict) -> dict[str, object]:
    """Generate cross-signal meta-insight if cadence allows. Also checks for
    unreviewed prompt-variant decisions (Lag 1 credit assignment) every tick.
    cross_snapshot keys (all optional): energy_level, inner_voice_mode, latest_fragment,
    last_surprise, last_conflict, last_irony, last_taste, curiosity_signal."""
    # ── Always: check for unreviewed decisions ──────────────────────────
    credit_result = _check_credit(cross_snapshot)

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

    insight = _generate_meta_insight(cross_snapshot)
    if not insight:
        return {"generated": False, "credit": credit_result}

    _store_meta_insight(insight)
    _last_meta_at = datetime.now(UTC)
    return {"generated": True, "insight": insight, "credit": credit_result}


def _check_credit(cross_snapshot: dict) -> dict[str, object]:
    """Check for unreviewed prompt_variant decisions and score them.

    Runs every tick — cheap query for unreviewed decisions, then uses
    available signals to generate a credit_score and link it.
    """
    try:
        unreviewed = list_unreviewed_decisions(kind="prompt_variant", limit=3)
    except Exception:
        return {"checked": False, "error": "list_unreviewed failed (schema may not exist yet)"}

    if not unreviewed:
        return {"checked": True, "scored": 0}

    scored = 0
    for dec in unreviewed:
        decision_id = dec["decision_id"]
        try:
            # Build credit_score from available signals
            score = _estimate_credit_score(dec, cross_snapshot)
            evidence = _build_evidence_summary(dec, cross_snapshot)

            link_outcome_to_decision(
                decision_id=decision_id,
                credit_score=score,
                rationale=f"Automated Lag 1 outcome for {dec.get('title', decision_id)}",
                evidence_summary=evidence,
                run_id=f"credit-check-{uuid4().hex[:12]}",
            )
            scored += 1
        except Exception:
            continue

    return {"checked": True, "scored": scored}


def _estimate_credit_score(decision: dict, cross_snapshot: dict) -> float:
    """Heuristic credit score 0-100 based on available signals.

    Starts at neutral 65, adjusts:
    - +5 if energy_level is moderate (not low, not frantic)
    - -10 if there's a recent conflict signal
    - +10 if curiosity_signal is present (exploration is good)
    - +/- from Lag 2 drift trend if available
    """
    score = 65.0

    energy = str(cross_snapshot.get("energy_level", "")).lower()
    if "moderate" in energy or energy in ("0.5", "0.4", "0.6"):
        score += 5.0
    elif "low" in energy:
        score -= 5.0

    if cross_snapshot.get("last_conflict"):
        score -= 10.0

    if cross_snapshot.get("curiosity_signal"):
        score += 10.0

    return max(0.0, min(100.0, score))


def _build_evidence_summary(decision: dict, cross_snapshot: dict) -> str:
    """Build a short evidence string explaining the credit score."""
    parts = []
    if decision.get("options") and decision.get("options") != "[]":
        parts.append(f"options: {decision['options']}")
    if decision.get("decision"):
        parts.append(f"chose: {decision['decision'][:60]}")
    if cross_snapshot.get("energy_level"):
        parts.append(f"energy={cross_snapshot['energy_level']}")
    if cross_snapshot.get("last_conflict"):
        parts.append("conflict_detected")
    if cross_snapshot.get("curiosity_signal"):
        parts.append("curiosity_active")
    return "; ".join(parts) if parts else "auto-scored"


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
    from core.services.daemon_llm import daemon_llm_call

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
