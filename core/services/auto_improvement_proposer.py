"""Auto improvement proposer — close the self-improvement loop SAFELY.

Reads tick quality data + stale goals + decision adherence and generates
CONCRETE, BOUNDED improvement proposals that go through the existing
propose_plan infrastructure. NO auto-mutation — every proposal needs
explicit user approval.

What CAN be proposed (bounded scope):
- Tool description tweaks (low risk: worse description = fewer calls, not wrong calls)
- Awareness section priority adjustments (cosmetic ordering)
- Daemon cadence tuning (e.g., chronicle every 36h instead of 24h)
- Prompt fragment refinements (specific awareness sections, NOT identity)
- Stale goal status changes (mark blocked/archived)

What CANNOT be proposed (hard guards):
- SOUL.md, IDENTITY.md, MANIFEST.md, STANDING_ORDERS.md changes
- Approval-path logic
- Council deliberation logic
- Memory write/delete logic
- Self-modification of THIS module

Trigger:
- Tick quality trend = degrading → propose context/cadence tweak
- Stale goals ≥3 days → propose status update
- Decision adherence < 60% → propose review session

Each proposal lands in plan_proposals as awaiting_approval. User approves
or dismisses via existing tools (approve_plan, dismiss_plan).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# 2026-04-27: User explicitly authorized Tier 3 (identity-level) auto-mutation.
# See ~/.jarvis-v2/config/identity_mutation_authorization.json
# Identity files are no longer hard-blocked here — they go via
# identity_mutation_log for full audit + rollback.
# Infrastructure modules remain blocked for STABILITY (not safety):
# auto-modifying the auto-improver / plan_proposals / approvals would create
# recursive bugs that could brick the system.
_INFRASTRUCTURE_BLOCKED_MODULES: frozenset[str] = frozenset({
    "core.services.auto_improvement_proposer",
    "core.services.plan_proposals",
    "core.services.approvals",
    "core.services.identity_mutation_log",
    "core.runtime.policy",
})


def _is_safe_target(target: str) -> bool:
    """Reject only infrastructure-protected modules. Identity files now allowed
    per user authorization 2026-04-27 — those route via identity_mutation_log.
    """
    target = str(target or "")
    if not target:
        return False
    for module in _INFRASTRUCTURE_BLOCKED_MODULES:
        if module in target:
            return False
    return True


# ── Trigger logic ──────────────────────────────────────────────────


def _check_tick_quality_degraded() -> dict[str, Any] | None:
    """Returns proposal payload if tick quality is degrading."""
    try:
        from core.services.agent_self_evaluation import tick_quality_summary
        summary = tick_quality_summary(days=7)
    except Exception:
        return None
    if summary.get("trend") != "degrading":
        return None
    if summary.get("count", 0) < 5:
        return None
    avg = summary.get("avg_score") or 0
    return {
        "title": f"Heartbeat tick-kvalitet er degraderende ({avg}/100)",
        "why": (
            f"Sidste 5 ticks gennemsnit lavere end 7-dages baseline. "
            f"Trend: degrading. Avg score: {avg}/100."
        ),
        "steps": [
            "Inspect recent phased_heartbeat_tick events (kind=tool.invoked, look for elapsed_ms outliers)",
            "Run context_pressure to check if context is bloating",
            "Run mine_tool_patterns to detect new looping patterns",
            "Consider: bump auto_compact threshold from 70% to 60% temporarily",
        ],
        "kind": "tick_quality_degraded",
    }


def _check_stale_goals() -> dict[str, Any] | None:
    """Returns proposal payload if stale goals exist."""
    try:
        from core.services.agent_self_evaluation import detect_stale_goals
        stale = detect_stale_goals()
    except Exception:
        return None
    if not stale:
        return None
    titles = [g.get("title", "?") for g in stale[:3]]
    return {
        "title": f"{len(stale)} aktive mål uden progress i ≥3 dage",
        "why": (
            f"Goals stagnerer: {', '.join(titles)}. Enten har tidsbudgettet "
            "været forkert estimeret, motivationen er faldet, eller målene er "
            "blevet overhalet af nye prioriteter."
        ),
        "steps": [
            f"goal_update_status(goal_id='{g.get('goal_id', '?')}', status='blocked|achieved|archived')"
            for g in stale[:3]
        ] + [
            "Eller: lav et nyt sub-goal med konkret action for at unblocke",
        ],
        "kind": "stale_goals",
    }


def _check_decision_adherence() -> dict[str, Any] | None:
    try:
        from core.services.agent_self_evaluation import decision_adherence_summary
        summary = decision_adherence_summary()
    except Exception:
        return None
    if not summary.get("flag"):
        return None
    score = summary.get("score") or 0
    return {
        "title": f"Decision adherence er lav ({score}%)",
        "why": (
            f"Kun {summary.get('adhered', 0)}/{summary.get('total', 0)} recent "
            f"decisions blev faktisk applied. {summary.get('revoked', 0)} blev "
            "revoked. Mønster: enten dårlige decisions tages, eller gode "
            "decisions ikke følges igennem."
        ),
        "steps": [
            "Kør decision_review på de seneste 5 revoked decisions",
            "Identifér: er det same kategori der revokes? (timing, scope, kvalitet?)",
            "Overvej at hæve approval-tærsklen for den kategori",
            "Hvis det er pending der hober sig op: tag dem op én efter én",
        ],
        "kind": "decision_adherence_low",
    }


def _check_provider_health_chronic() -> dict[str, Any] | None:
    """If a provider is chronically down (>30 min), propose explicit demotion."""
    try:
        from core.services.provider_health_check import latest_health_snapshot
        snap = latest_health_snapshot()
    except Exception:
        return None
    unreachable = snap.get("unreachable") or []
    if not unreachable:
        return None
    return {
        "title": f"{len(unreachable)} provider(e) kronisk ikke-tilgængelige",
        "why": (
            f"Providers nede ved sidste health check: {', '.join(unreachable)}. "
            "Kæden falder igennem, men hvert kald spilder ~5s på at forsøge "
            "den primære først. Permanent demotion ville fjerne det spild."
        ),
        "steps": [
            f"Overvej at sætte enabled=false i provider_router.json for: {', '.join(unreachable)}",
            "Eller: bump deres priority til 95+ så de kun er last-resort",
            "Re-aktivér når health_check viser dem reachable igen",
        ],
        "kind": "chronic_provider_outage",
    }


# ── Generator ──────────────────────────────────────────────────────


def generate_improvement_proposals(*, session_id: str | None = None) -> dict[str, Any]:
    """Run all checks, file plans for any that fire."""
    proposed: list[dict[str, Any]] = []
    skipped_unsafe: list[str] = []

    checks = [
        ("tick_quality", _check_tick_quality_degraded),
        ("stale_goals", _check_stale_goals),
        ("decision_adherence", _check_decision_adherence),
        ("provider_health", _check_provider_health_chronic),
    ]

    for check_name, check_fn in checks:
        try:
            payload = check_fn()
        except Exception as exc:
            logger.debug("auto_improver: check %s failed: %s", check_name, exc)
            continue
        if payload is None:
            continue

        # Guard: only infrastructure-protected modules blocked.
        # Identity files (SOUL/IDENTITY/MANIFEST) now allowed per user auth —
        # those route via identity_mutation_log for audit + rollback.
        steps = payload.get("steps") or []
        if any(not _is_safe_target(s) for s in steps):
            skipped_unsafe.append(check_name)
            continue

        try:
            from core.services.plan_proposals import propose_plan
            result = propose_plan(
                session_id=session_id,
                title=payload["title"],
                why=payload["why"],
                steps=steps,
            )
            if result.get("status") == "ok":
                proposed.append({
                    "kind": payload["kind"],
                    "plan_id": result.get("plan_id"),
                    "title": payload["title"],
                })
        except Exception as exc:
            logger.warning("auto_improver: propose_plan failed for %s: %s", check_name, exc)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "auto_improvement.proposals_generated",
            {"count": len(proposed), "kinds": [p["kind"] for p in proposed]},
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "proposed": proposed,
        "count": len(proposed),
        "skipped_unsafe": skipped_unsafe,
    }


def _exec_generate_improvement_proposals(args: dict[str, Any]) -> dict[str, Any]:
    return generate_improvement_proposals(session_id=args.get("session_id"))


AUTO_IMPROVEMENT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "generate_improvement_proposals",
            "description": (
                "Read self-evaluation data (tick quality, stale goals, decision "
                "adherence, provider health) and file CONCRETE improvement "
                "proposals via plan_proposals. NO auto-mutation — each proposal "
                "needs approve_plan to take effect. Hard guards prevent any "
                "proposal touching SOUL/IDENTITY/MANIFEST/approval paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": [],
            },
        },
    },
]
