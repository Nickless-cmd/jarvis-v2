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
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _parse_iso(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp leniently; None on garbage."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# 2026-04-27: User explicitly authorized Tier 3 (identity-level) auto-mutation.
# See ~/.jarvis-v2/config/identity_mutation_authorization.json
# Sikkerhedslisten ejes nu KANONISK af gate_mutation (var dual-truth — byte-identisk
# kopi af identity_mutation_log's). Re-eksporteret for bagudkompat.
from core.services.gate_mutation import (
    INFRASTRUCTURE_BLOCKED_MODULES as _INFRASTRUCTURE_BLOCKED_MODULES,
)


def _is_safe_target(target: str) -> bool:
    """Reject only infrastructure-protected modules. Identity files now allowed
    per user authorization 2026-04-27 — those route via identity_mutation_log.
    Mutation-cluster 🔒 GENNEM Den Intelligente Central (SECURITY, traced)."""
    from core.services.gate_mutation import check_module
    return check_module(target)


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
        # Titel UDEN scoren (fix 13/9-2026): tallet ændrer sig fra kørsel til
        # kørsel, og dedup'en i plan_proposals matcher på EKSAKT titel. Med
        # `(85.0/100)` i titlen slap en dismissed plan igennem som "ny" så snart
        # scoren blev 83.2 — og genopstod ved hver genstart. Scoren lever i `why`.
        "title": "Heartbeat tick-kvalitet er degraderende",
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
        # Titel uden antallet (fix 13/9-2026): samme grund som tick-kvalitet
        # ovenfor — dedup'en matcher eksakt, så "2 aktive mål" blev en "ny" plan
        # i det øjeblik tallet blev 3. Antallet lever nu i `why`.
        "title": "Aktive mål uden progress i ≥3 dage",
        "why": (
            f"{len(stale)} mål stagnerer: {', '.join(titles)}. Enten har tidsbudgettet "
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
        # Titel uden procenten (fix 13/9-2026): dedup matcher eksakt, så `(55%)`
        # slap igennem som "ny" i det øjeblik den blev `(48%)`. Scoren er i `why`.
        "title": "Decision adherence er lav",
        "why": (
            f"Adherence: {score}%. Kun {summary.get('adhered', 0)}/{summary.get('total', 0)} recent "
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


def _already_disabled_providers() -> set[str]:
    """Providers der eksplicit er slaaet fra paa provider-niveau.

    Laeser `providers[]` i provider_router.json og returnerer navnene med
    ``enabled: false``. Ukendte navne (slet ikke i registret) udelades med
    vilje — vi kan ikke haevde at de er slaaet fra, saa et reelt signal maa
    gerne fyre for dem.
    """
    try:
        from core.runtime.provider_router import load_provider_router_registry
        registry = load_provider_router_registry()
    except Exception as exc:
        logger.debug("auto_improver: kunne ikke laese provider-registret: %s", exc)
        return set()
    disabled: set[str] = set()
    for entry in registry.get("providers") or []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("provider") or "").strip()
        if name and entry.get("enabled") is False:
            disabled.add(name)
    return disabled


def _check_provider_health_chronic() -> dict[str, Any] | None:
    """If a provider is chronically down (>30 min), propose explicit demotion.

    2026-08-30: require a FRESH snapshot. The stored snapshot may be hours
    old (e.g. from the night before a restart), and proposing demotion on
    stale data re-creates the same plan on every restart even after the
    provider recovered. A stale snapshot means "unknown", not "down".

    2026-09-20: skip providers that are ALREADY disabled in the registry.
    The health check pings every endpoint in ``_PING_ENDPOINTS`` regardless
    of enabled-state, so an already-demoted provider (e.g. sambanova,
    ``enabled: false`` since 21/6) keeps landing in ``unreachable`` — and
    the proposer filed a demotion plan whose step 1 was a no-op.
    """
    try:
        from core.services.provider_health_check import latest_health_snapshot
        snap = latest_health_snapshot()
    except Exception:
        return None
    checked_at = _parse_iso(str(snap.get("checked_at") or ""))
    if checked_at is None or checked_at < datetime.now(UTC) - timedelta(hours=2):
        return None
    unreachable = snap.get("unreachable") or []
    if not unreachable:
        return None
    # 2026-09-20: fjern providers der allerede er slaaet fra i registret.
    # Uden dette fyrer planen paa en no-op (trin 1 er allerede gjort) og
    # genopstaar ved hver forbigaaende blip paa en doed provider.
    already_disabled = _already_disabled_providers()
    unreachable = [p for p in unreachable if p not in already_disabled]
    if not unreachable:
        return None
    return {
        # Titel uden antallet (fix 13/9-2026): dedup matcher eksakt, så
        # `1 provider(e)` blev en "ny" plan da den blev `2` — og genopstod ved
        # hver genstart. Listen af navne lever i `why` (2026-08-30-fixet ramte
        # kun friskheden af snapshot'et, ikke denne titel-volatilitet).
        "title": "Provider(e) kronisk ikke-tilgængelige",
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
