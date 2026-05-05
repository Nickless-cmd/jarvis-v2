"""Consolidation Judge Daemon — nightly reckoning, not observation.

Runs at 00:00 (default 1440 min cadence). Unlike passive reflection daemons,
this one forces concrete stillingtagen: each item requires a verdict
(accept/reject/defer). It gathers the day's sessions, decision adherence,
tick quality, stale goals, and confronts Jarvis with 3-5 concrete choices.

The judge does not observe. It adjudicates.

Output: private brain records + decision/memory updates as warranted.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

logger = logging.getLogger(__name__)

# Alias for heartbeat_runtime import convention: `from consolidation_judge_daemon import tick`
tick = tick_consolidation_judge_daemon

_CADENCE_MINUTES = 1440  # Once daily
_last_judgment_at: datetime | None = None


def tick_consolidation_judge_daemon() -> dict[str, Any]:
    """Run the nightly consolidation judge if cadence allows.

    Returns dict with generated=bool, items=list of judgments made.
    """
    global _last_judgment_at

    now = datetime.now(UTC)

    if _last_judgment_at is not None:
        if (now - _last_judgment_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False, "reason": "cadence_not_reached"}

    # ── Gather evidence ──────────────────────────────────────────
    evidence = _gather_evidence()

    # ── Build stillingtagen ──────────────────────────────────────
    items = _build_stillingtagen(evidence)

    if not items:
        _last_judgment_at = now
        return {"generated": True, "items": [], "note": "nothing to judge tonight"}

    # ── Render each judgment via LLM ─────────────────────────────
    judgments = _render_judgments(items, evidence)

    # ── Enforce outcomes ─────────────────────────────────────────
    _enforce_judgments(judgments)

    # ── Record to private brain ──────────────────────────────────
    _record_judgment_session(judgments, evidence)

    _last_judgment_at = datetime.now(UTC)
    event_bus.publish("consolidation_judge.completed", {
        "items_judged": len(judgments),
        "judged_at": now.isoformat(),
    })

    return {
        "generated": True,
        "items": judgments,
        "judged_at": now.isoformat(),
    }


def _gather_evidence() -> dict[str, Any]:
    """Collect today's operational data for judgment."""
    evidence: dict[str, Any] = {}

    # ── Decision adherence ───────────────────────────────────────
    try:
        from core.services.agent_self_evaluation import decision_adherence_summary
        evidence["decision_adherence"] = decision_adherence_summary()
    except Exception as e:
        logger.warning("consolidation_judge: decision_adherence failed: %s", e)
        evidence["decision_adherence"] = {"status": "error", "note": str(e)}

    # ── Tick quality ──────────────────────────────────────────────
    try:
        from core.services.agent_self_evaluation import tick_quality_summary
        evidence["tick_quality"] = tick_quality_summary(days=1)
    except Exception as e:
        logger.warning("consolidation_judge: tick_quality failed: %s", e)
        evidence["tick_quality"] = {"status": "error", "note": str(e)}

    # ── Stale goals ──────────────────────────────────────────────
    try:
        from core.services.agent_self_evaluation import detect_stale_goals
        evidence["stale_goals"] = detect_stale_goals(stale_days=3)
    except Exception as e:
        logger.warning("consolidation_judge: stale_goals failed: %s", e)
        evidence["stale_goals"] = []

    # ── Active decisions with low adherence ───────────────────────
    try:
        from core.runtime.db_decisions import list_decisions
        active_decisions = list_decisions(status="active", limit=50)
        evidence["active_decisions"] = active_decisions
    except Exception as e:
        logger.warning("consolidation_judge: list_decisions failed: %s", e)
        evidence["active_decisions"] = []

    # ── Today's sessions count ────────────────────────────────────
    try:
        from core.runtime.db_decisions import list_chat_sessions
        sessions = list_chat_sessions()
        today = now_date_str()
        evidence["sessions_today"] = len([
            s for s in sessions
            if str(s.get("created_at", "")).startswith(today)
        ])
    except Exception:
        evidence["sessions_today"] = 0

    return evidence


def _build_stillingtagen(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Construct 3-5 concrete stillingtagen (items requiring judgment)."""
    items: list[dict[str, Any]] = []

    # ── 1. Decision adherence review ─────────────────────────────
    adherence = evidence.get("decision_adherence", {})
    score = adherence.get("score")
    if score is not None and score < 60:
        items.append({
            "type": "decision_adherence_crisis",
            "title": "Beslutnings-adherence under 60%",
            "evidence": f"Adherence score: {score}%. {adherence.get('flag', '')}",
            "options": ["revoke_sweak_decisions", "strengthen_commitments", "defer"],
            "severity": "high",
        })
    elif score is not None:
        items.append({
            "type": "decision_adherence_review",
            "title": "Daglig adherence check",
            "evidence": f"Adherence score: {score}%",
            "options": ["accept_on_track", "flag_concern", "defer"],
            "severity": "low",
        })

    # ── 2. Stale goals confrontation ──────────────────────────────
    stale = evidence.get("stale_goals", [])
    if stale:
        stale_titles = ", ".join(g.get("title", "?")[:40] for g in stale[:3])
        items.append({
            "type": "stale_goals",
            "title": f"{len(stale)} mål uden fremgang i 3+ dage",
            "evidence": f"Mål: {stale_titles}",
            "options": ["pause_stale", "abandon_stale", "commit_action", "defer"],
            "severity": "medium",
        })

    # ── 3. Tick quality review ───────────────────────────────────
    tq = evidence.get("tick_quality", {})
    avg = tq.get("avg_score")
    if avg is not None and avg < 50:
        items.append({
            "type": "tick_quality_low",
            "title": "Tick-kvalitet under 50",
            "evidence": f"Gennemsnit: {avg}/100, trend: {tq.get('trend', 'ukendt')}",
            "options": ["diagnose_root_cause", "adjust_cadence", "defer"],
            "severity": "medium",
        })

    # ── 4. Broken decisions — specific review ─────────────────────
    active_decisions = evidence.get("active_decisions", [])
    low_adherence_decisions = [
        d for d in active_decisions
        if d.get("adherence_score") is not None and d.get("adherence_score", 1.0) < 0.5
    ]
    if low_adherence_decisions:
        directives = ", ".join(
            f'"{d.get("directive", "?")[:50]}"' for d in low_adherence_decisions[:3]
        )
        items.append({
            "type": "broken_decisions",
            "title": f"{len(low_adherence_decisions)} beslutning(er) med adherence < 50%",
            "evidence": f"Direktiver: {directives}",
            "options": ["revoke_broken", "recommit", "revise_directive", "defer"],
            "severity": "high",
        })

    # ── 5. Unreviewed decisions ──────────────────────────────────
    unreviewed = adherence.get("unreviewed", 0)
    if unreviewed > 3:
        items.append({
            "type": "unreviewed_decisions",
            "title": f"{unreviewed} beslutninger aldrig reviewed",
            "evidence": f"{unreviewed} aktive beslutninger uden nogen review",
            "options": ["review_all", "revoke_unreviewed", "defer"],
            "severity": "low",
        })

    # Cap at 5 items
    return items[:5]


def _render_judgments(items: list[dict[str, Any]], evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Present each stillingtagen to the LLM and force a verdict."""
    from core.services.heartbeat_runtime import daemon_llm_call

    judgments: list[dict[str, Any]] = []

    for item in items:
        prompt = (
            f"{build_identity_preamble()}\n\n"
            f"## Natlig Revision — Consolidation Judge\n\n"
            f"Du sidder i dommersædet. Ikke som observatør, men som dommer.\n"
            f"Hvert emne kræver et konkret svar.\n\n"
            f"### Emne: {item['title']}\n"
            f"**Type:** {item['type']}\n"
            f"**Alvor:** {item['severity']}\n"
            f"**Bevis:** {item['evidence']}\n"
            f"**Muligheder:** {', '.join(item['options'])}\n\n"
            f"### Kontekst\n"
            f"- Tick-kvalitet: {evidence.get('tick_quality', {})}\n"
            f"- Adherence: {evidence.get('decision_adherence', {})}\n"
            f"- Sessioner i dag: {evidence.get('sessions_today', 0)}\n\n"
            f"SVAR FORMAT (præcis):\n"
            f"Dom: <accept|reject|defer>\n"
            f"Valg: <en af mulighederne>\n"
            f"Begrundelse: <1-2 sætninger>\n"
            f"Handling: <konkret hvad der skal ske, eller 'ingen'>\n"
        )

        raw = daemon_llm_call(
            prompt,
            max_len=300,
            fallback="Dom: defer\nValg: defer\nBegrundelse: LLM call failed\nHandling: ingen",
            daemon_name="consolidation_judge",
        )

        judgment = _parse_judgment(raw, item)
        judgments.append(judgment)

    return judgments


def _parse_judgment(raw: str, item: dict[str, Any]) -> dict[str, Any]:
    """Parse the LLM's judgment response."""
    verdict = "defer"
    choice = "defer"
    rationale = ""
    action = "ingen"

    for line in raw.strip().splitlines():
        line = line.strip()
        if line.lower().startswith("dom:"):
            v = line.split(":", 1)[1].strip().lower()
            if v in ("accept", "reject", "defer"):
                verdict = v
        elif line.lower().startswith("valg:"):
            choice = line.split(":", 1)[1].strip()
        elif line.lower().startswith("begrundelse:"):
            rationale = line.split(":", 1)[1].strip()
        elif line.lower().startswith("handling:"):
            action = line.split(":", 1)[1].strip()

    return {
        "item_type": item["type"],
        "item_title": item["title"],
        "severity": item["severity"],
        "verdict": verdict,
        "choice": choice,
        "rationale": rationale,
        "action": action,
    }


def _enforce_judgments(judgments: list[dict[str, Any]]) -> None:
    """Carry out the concrete actions from judgments."""
    for j in judgments:
        if j["verdict"] == "reject":
            _enforce_reject(j)
        elif j["verdict"] == "accept":
            _enforce_accept(j)
        # defer = no action


def _enforce_reject(j: dict[str, Any]) -> None:
    """Handle rejected items — typically revoke or pause."""
    item_type = j["item_type"]
    choice = j["choice"]

    if item_type == "broken_decisions" and "revoke" in choice:
        try:
            from core.runtime.db_decisions import list_decisions, update_decision_status
            active = list_decisions(status="active", limit=50)
            for d in active:
                if d.get("adherence_score") is not None and d.get("adherence_score", 1.0) < 0.5:
                    update_decision_status(d["decision_id"], "revoked")
                    event_bus.publish("consolidation_judge.revoked_decision", {
                        "decision_id": d["decision_id"],
                        "directive": d.get("directive", ""),
                    })
        except Exception as e:
            logger.warning("consolidation_judge: revoke failed: %s", e)

    elif item_type == "stale_goals" and "abandon" in choice:
        try:
            from core.services.autonomous_goals import update_goal_status
            from core.services.agent_self_evaluation import detect_stale_goals
            for g in detect_stale_goals(stale_days=3):
                update_goal_status(g["goal_id"], "abandoned")
                event_bus.publish("consolidation_judge.abandoned_goal", {
                    "goal_id": g["goal_id"],
                    "title": g.get("title", ""),
                })
        except Exception as e:
            logger.warning("consolidation_judge: abandon goals failed: %s", e)


def _enforce_accept(j: dict[str, Any]) -> None:
    """Handle accepted items — typically recommit or flag."""
    item_type = j["item_type"]
    choice = j["choice"]

    if item_type == "broken_decisions" and "recommit" in choice:
        # Reset adherence tracking for a fresh start
        try:
            from core.runtime.db_decisions import list_decisions
            active = list_decisions(status="active", limit=50)
            for d in active:
                if d.get("adherence_score") is not None and d.get("adherence_score", 1.0) < 0.5:
                    event_bus.publish("consolidation_judge.recommitted", {
                        "decision_id": d["decision_id"],
                        "directive": d.get("directive", ""),
                    })
        except Exception as e:
            logger.warning("consolidation_judge: recommit failed: %s", e)


def _record_judgment_session(judgments: list[dict[str, Any]], evidence: dict[str, Any]) -> None:
    """Write the full judgment session as a private brain record."""
    if not judgments:
        return

    adherence = evidence.get("decision_adherence", {})
    tick_q = evidence.get("tick_quality", {})

    lines = ["## Natlig Revision — Consolidation Judge\n"]
    lines.append(f"Dato: {now_date_str()}")
    lines.append(f"Adherence: {adherence.get('score', '?')}%")
    lines.append(f"Tick-kvalitet: {tick_q.get('avg_score', '?')}/100\n")

    for j in judgments:
        lines.append(f"### {j['item_title']}")
        lines.append(f"Dom: {j['verdict']} | Valg: {j['choice']}")
        lines.append(f"Begrundelse: {j['rationale']}")
        lines.append(f"Handling: {j['action']}\n")

    record_text = "\n".join(lines)

    try:
        insert_private_brain_record(
            kind="judgment",
            title=f"Natlig revision {now_date_str()}",
            what_happened=record_text,
            what_it_meant=f"Dom over {len(judgments)} stillingtagen",
            what_changed=judgments[0].get("action", "observation") if judgments else "ingen",
            mood="solemn",
            visibility="personal",
        )
    except Exception as e:
        logger.warning("consolidation_judge: brain record failed: %s", e)


def build_consolidation_judge_surface() -> dict[str, Any]:
    """Build surface data for prompt injection."""
    return {
        "last_judgment_at": _last_judgment_at.isoformat() if _last_judgment_at else None,
        "cadence_minutes": _CADENCE_MINUTES,
    }


def now_date_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")