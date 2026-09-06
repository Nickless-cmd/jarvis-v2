"""Agent self-evaluation — track quality, adherence, goal progress (READ-ONLY).

Phase 5 of Jarvis' implementation plan. Per the deferred design note in
docs/design_notes/self_improving_loops.md, we start with **observation**
ONLY — no auto-mutation. The system measures itself; humans decide
whether to act on findings.

Three trackers:

1. **Tick quality scoring** — after each phased_heartbeat_tick, evaluate
   if it produced useful output (priorities → actions, idle → consolidations).
   Score 0-100. Persisted in state_store.

2. **Decision adherence tracking** — periodically run decision_review on
   recent runs. If adherence < 60% → flag in chronicle.

3. **Stale goal detection** — for each active autonomous goal, check
   if there has been progress (tool invocations referencing the goal,
   sub-goal status changes, related events) in last N days. Flag stale.

NO auto-mutation. Just observation + flags. Mission Control / chronicle
surfaces the data; user decides if/how to act.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_TICK_EVAL_KEY = "tick_quality_evaluations"
_GOAL_PROGRESS_KEY = "goal_progress_tracking"
_MAX_TICK_EVALS_KEPT = 200
_GOAL_STALE_DAYS = 3


# ── Tick quality scoring ──────────────────────────────────────────



# ── Tick-spor: hvad efterlod slaget i verden ──────────────────────
#
# 2026-09-05: den gamle scoring gav 70 til 199 af 200 tick. Den målte formen på
# et tick, ikke udbyttet: +10 for at sanse fem signaltyper (sker altid), +40 for
# ≥2 idle-handlinger (sker altid — de samme syv hver gang), +20 for sund tid
# (sker altid). De to poster der KUNNE variere, +15 for priorities og +30 for at
# dispatche på dem, fyrede aldrig, fordi der aldrig er priorities. 70 var loftet
# for et tomt slag, og «stable» betød «kan ikke bevæge sig».
#
# To kørsler af productive_idle i træk gav præcis den samme handlingsliste
# (personality_snapshot, personality_drift_tick, tick_elapsed, dreams, wants,
# boredom, idle_daemon:event_trigger_shadow). At tælle dem måler ingenting.
#
# Derfor måler vi nu SPOR: hvilke ikke-strukturelle event-arter der blev skrevet
# i vinduet mellem dette slag og det forrige. Et slag der får credit_assignment,
# learning_pipeline og thought_stream til at skrive, har udrettet noget. Et slag
# hvor kun heartbeat-bogholderiet rører sig, har ikke — og skal kunne ses.

# Arter der hører til bogholderiet eller til Bjørns egne ture — ikke til slagets
# udbytte. Alt andet tæller som et spor.
_STRUCTURAL_EVENT_PREFIXES = (
    "heartbeat.",
    "prompt.",
    "tool.",
    "tool_router.",
    "runtime.visible_run",
    "runtime.agentic_round",
)


def _trace_kinds_since(since: datetime, until: datetime) -> list[str]:
    """Ikke-strukturelle event-arter skrevet i vinduet. Self-safe: [] ved fejl."""
    try:
        from core.runtime.db import connect

        with connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT kind FROM events WHERE created_at > ? AND created_at <= ?",
                (since.isoformat(), until.isoformat()),
            ).fetchall()
    except Exception as exc:
        logger.debug("tick_quality: kunne ikke laese spor: %s", exc)
        return []
    ud = []
    for row in rows:
        kind = str(row["kind"] or "")
        if kind and not kind.startswith(_STRUCTURAL_EVENT_PREFIXES):
            ud.append(kind)
    return sorted(ud)


def _previous_eval() -> dict[str, Any] | None:
    try:
        tidligere = load_json(_TICK_EVAL_KEY, [])
        if isinstance(tidligere, list) and tidligere:
            sidste = tidligere[-1]
            return sidste if isinstance(sidste, dict) else None
    except Exception:
        pass
    return None


def _score_traces(antal: int) -> int:
    """Bredden af spor. Trapper frem for lineær, så små udsving ikke støjer."""
    if antal <= 0:
        return 0
    if antal <= 2:
        return 20
    if antal <= 5:
        return 35
    return 50


def _score_novelty(nu: list[str], foer: list[str]) -> tuple[int, str]:
    """Gav dette slag noget ANDET end det forrige?

    Et system der gør præcis det samme hver gang, er ikke produktivt — det
    kører bare. Uden et forrige slag at måle mod giver vi fuld kredit; vi
    straffer ikke det første.
    """
    if not foer:
        return 30, "intet forrige slag at sammenligne med"
    if not nu:
        return 0, "ingen spor at være ny med"
    nye = set(nu) - set(foer)
    andel = len(nye) / max(len(set(nu)), 1)
    if andel >= 0.5:
        return 30, f"{len(nye)} af {len(set(nu))} spor var nye"
    if andel > 0:
        return 15, f"kun {len(nye)} af {len(set(nu))} spor var nye"
    return 0, "samme spor som forrige slag"


def evaluate_tick_quality(*, tick_result: dict[str, Any]) -> dict[str, Any]:
    """Score et slag på hvad det EFTERLOD — ikke på hvilken form det havde.

    Fire led, max 100:
      +10  sund tid (0 < elapsed < 180s)
      +10  slaget handlede overhovedet (≥1 handling)
      0-50 spor: bredden af ikke-strukturelle event-arter i vinduet siden
           forrige slag — dvs. hvad slagets arbejde faktisk fik skrevet
      0-30 nyhed: adskiller sporene sig fra forrige slag, eller kører den
           samme runde igen?

    Ingen LLM. Se kommentaren over _STRUCTURAL_EVENT_PREFIXES for hvorfor den
    gamle formbaserede scoring altid gav 70.
    """
    score = 0
    notes: list[str] = []
    phases = tick_result.get("phases") or {}

    reflect = phases.get("reflect") or {}
    priorities = reflect.get("priorities") or []
    act = phases.get("act") or {}
    act_kind = str(act.get("kind") or "")
    actions = (act.get("result") or {}).get("actions") or act.get("actions") or []

    # 1. Sund tid — ren fornuftskontrol, ikke en kvalitetsdom.
    elapsed_ms = int(tick_result.get("elapsed_ms") or 0)
    if 0 < elapsed_ms < 180_000:
        score += 10
        notes.append(f"sund tid ({elapsed_ms}ms)")
    elif elapsed_ms >= 180_000:
        notes.append(f"SLAGET HANG ({elapsed_ms}ms)")

    # 2. Handlede den overhovedet.
    if actions:
        score += 10
        notes.append(f"{len(actions)} handlinger")
    else:
        notes.append("ingen handlinger")

    # 3. Spor — vinduet går fra forrige slags evaluering, så alt der skete
    #    mellem to slag tilskrives dette. Falder tilbage til elapsed hvis der
    #    ikke er et forrige slag at måle fra.
    nu = datetime.now(UTC)
    forrige = _previous_eval()
    vindue_start = None
    if forrige:
        try:
            vindue_start = datetime.fromisoformat(
                str(forrige.get("evaluated_at") or "").replace("Z", "+00:00")
            ).astimezone(UTC)
        except Exception:
            vindue_start = None
    if vindue_start is None or vindue_start >= nu:
        vindue_start = nu - timedelta(milliseconds=max(elapsed_ms, 1000))

    trace_kinds = _trace_kinds_since(vindue_start, nu)
    spor_point = _score_traces(len(trace_kinds))
    score += spor_point
    notes.append(f"{len(trace_kinds)} spor-arter → {spor_point}p")

    # 4. Nyhed — gør slaget noget andet end sidst?
    nyhed_point, nyhed_note = _score_novelty(
        trace_kinds, list((forrige or {}).get("trace_kinds") or [])
    )
    score += nyhed_point
    notes.append(f"nyhed: {nyhed_note} → {nyhed_point}p")

    score = max(0, min(100, score))
    eval_record = {
        "eval_id": f"teval-{uuid4().hex[:10]}",
        "evaluated_at": nu.isoformat(),
        "score": score,
        "notes": notes,
        "tick_kind": act_kind,
        "had_priorities": bool(priorities),
        "elapsed_ms": elapsed_ms,
        # Gemmes så nyheds-målingen har noget at sammenligne med NÆSTE gang —
        # og så en senere analyse kan se HVAD slaget udrettede, ikke kun et tal.
        "actions": [str(a)[:80] for a in actions][:20],
        "trace_kinds": trace_kinds[:40],
        "window_seconds": round((nu - vindue_start).total_seconds(), 1),
    }

    # Persist (rolling window)
    try:
        existing = load_json(_TICK_EVAL_KEY, [])
        if not isinstance(existing, list):
            existing = []
        existing.append(eval_record)
        save_json(_TICK_EVAL_KEY, existing[-_MAX_TICK_EVALS_KEPT:])
    except Exception as exc:
        logger.debug("tick eval persist failed: %s", exc)

    return eval_record


def tick_quality_summary(*, days: int = 7) -> dict[str, Any]:
    """Aggregate stats over recent evaluations."""
    try:
        evals = load_json(_TICK_EVAL_KEY, [])
        if not isinstance(evals, list):
            evals = []
    except Exception:
        evals = []
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    recent = [e for e in evals if str(e.get("evaluated_at", "")) >= cutoff]
    if not recent:
        return {"status": "ok", "count": 0, "avg_score": None, "trend": "no data"}
    avg = sum(int(e.get("score") or 0) for e in recent) / len(recent)
    last_5_avg = sum(int(e.get("score") or 0) for e in recent[-5:]) / min(5, len(recent))
    trend = "stable"
    if last_5_avg > avg + 5:
        trend = "improving"
    elif last_5_avg < avg - 5:
        trend = "degrading"
    # 2026-09-05: spredningen SKAL med ud. Den gamle scoring gav 70 til 199 af
    # 200 slag, og fladen så ud som "stable" i alle overflader — en konstant der
    # udgav sig for en måling. Er der kun én værdi i vinduet, måler vi ingenting,
    # og det skal stå i svaret i stedet for at skulle graves frem.
    scores = [int(e.get("score") or 0) for e in recent]
    distinct = sorted(set(scores))
    laast = len(distinct) == 1 and len(recent) >= 10
    ud = {
        "status": "ok",
        "count": len(recent),
        "avg_score": round(avg, 1),
        "last_5_avg": round(last_5_avg, 1),
        "trend": "locked" if laast else trend,
        "window_days": days,
        "distinct_scores": len(distinct),
        "score_range": [min(scores), max(scores)],
    }
    if laast:
        ud["warning"] = (
            "alle %d slag scorede %d — målingen er låst og siger intet"
            % (len(recent), distinct[0])
        )
    return ud


# ── Stale goal detection ─────────────────────────────────────────


def detect_stale_goals(*, stale_days: int = _GOAL_STALE_DAYS) -> list[dict[str, Any]]:
    """Find active goals with no recent progress signal."""
    try:
        from core.services.autonomous_goals import list_goals
        active = list_goals(status="active", parent_id="any", limit=50)
    except Exception:
        return []

    cutoff = (datetime.now(UTC) - timedelta(days=stale_days)).isoformat()
    stale: list[dict[str, Any]] = []
    for g in active:
        updated = str(g.get("updated_at") or g.get("created_at") or "")
        if updated and updated < cutoff:
            stale.append({
                "goal_id": g.get("goal_id"),
                "title": g.get("title"),
                "priority": g.get("priority"),
                "last_update": updated,
                "days_stale": stale_days,
            })
    return stale


def stale_goals_section() -> str | None:
    stale = detect_stale_goals()
    if not stale:
        return None
    lines = [f"⏰ {len(stale)} aktive mål uden progress i ≥{_GOAL_STALE_DAYS} dage:"]
    for g in stale[:5]:
        lines.append(f"  • [{g.get('priority', '?')}] {g.get('title', '?')} (sidst opdateret {g.get('last_update', '?')[:10]})")
    return "\n".join(lines)


# ── Decision adherence tracking ──────────────────────────────────


def decision_adherence_summary() -> dict[str, Any]:
    """Compute adherence over ACTIVE behavioral decisions (the curated kind).

    Reads from `behavioral_decisions` (the deliberate action-commitments
    table created via decision-API), NOT from `cognitive_decisions` (which
    is auto-populated by marker-detection on conversation chatter and has
    no status field — using it gave us 0% adherence on phantom decisions).

    A decision's adherence is its rolling adherence_score field. Aggregate
    score = mean across active decisions. Flag = mean < 60%.
    """
    try:
        from core.runtime.db_decisions import list_decisions
        decisions = list_decisions(status="active", limit=50) or []
    except Exception:
        return {"status": "ok", "score": None, "note": "no behavioral_decisions table or list API"}
    if not decisions:
        return {"status": "ok", "score": None, "note": "no active behavioral decisions"}

    scores: list[float] = []
    unreviewed = 0
    duplicate_groups = _duplicate_decision_groups(decisions)
    low_decisions: list[dict[str, Any]] = []
    for d in decisions:
        s = d.get("adherence_score")
        if s is None:
            unreviewed += 1
            continue
        try:
            score_f = float(s)
            scores.append(score_f)
            if score_f < 0.6:
                low_decisions.append({
                    "decision_id": str(d.get("decision_id") or ""),
                    "directive": str(d.get("directive") or "")[:180],
                    "adherence_score": round(score_f, 3),
                    "last_reviewed_at": str(d.get("last_reviewed_at") or ""),
                })
        except (TypeError, ValueError):
            unreviewed += 1
    total = len(decisions)

    if not scores:
        return {
            "status": "ok",
            "score": None,
            "total": total,
            "unreviewed": unreviewed,
            "duplicate_groups": duplicate_groups,
            "note": "no decisions have been reviewed yet — no adherence data",
        }

    mean = sum(scores) / len(scores)
    score = round(mean * 100, 1)
    flag = "under 60% — review and either revoke or strengthen" if score < 60 else None
    recovery = _adherence_recovery_plan(
        score=score,
        low_decisions=low_decisions,
        duplicate_groups=duplicate_groups,
        unreviewed=unreviewed,
    )
    return {
        "status": "ok",
        "score": score,
        "adherence_rate": f"{score}%",
        "total": total,
        "reviewed": len(scores),
        "unreviewed": unreviewed,
        "duplicate_groups": duplicate_groups,
        "low_decisions": low_decisions,
        "recovery": recovery,
        "flag": flag,
    }


def _normalize_decision_directive(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _duplicate_decision_groups(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_directive: dict[str, list[dict[str, Any]]] = {}
    for decision in decisions:
        key = _normalize_decision_directive(decision.get("directive"))
        if not key:
            continue
        by_directive.setdefault(key, []).append(decision)
    groups: list[dict[str, Any]] = []
    for items in by_directive.values():
        if len(items) < 2:
            continue
        items_sorted = sorted(
            items,
            key=lambda item: (
                item.get("adherence_score") is None,
                -int(item.get("priority") or 0),
                str(item.get("created_at") or ""),
            ),
        )
        keeper = items_sorted[0]
        duplicates = items_sorted[1:]
        groups.append({
            "directive": str(keeper.get("directive") or "")[:180],
            "keeper_id": str(keeper.get("decision_id") or ""),
            "duplicate_ids": [str(item.get("decision_id") or "") for item in duplicates],
            "count": len(items),
        })
    return groups


def _adherence_recovery_plan(
    *,
    score: float,
    low_decisions: list[dict[str, Any]],
    duplicate_groups: list[dict[str, Any]],
    unreviewed: int,
) -> dict[str, Any]:
    actions: list[str] = []
    if duplicate_groups:
        duplicate_count = sum(len(group.get("duplicate_ids") or []) for group in duplicate_groups)
        actions.append(f"Revoke or merge {duplicate_count} duplicate active decision(s); keep the reviewed/highest-priority one.")
    if low_decisions:
        actions.append("For each low-adherence decision, do one visible recovery action next turn before adding new commitments.")
    if unreviewed:
        actions.append(f"Review {unreviewed} unreviewed active decision(s) before creating replacements.")
    if score < 60:
        actions.append("During tool work, surface a short status before the 5th tool call or explain the blocker.")
    return {
        "needed": bool(actions),
        "actions": actions,
        "focus_decision_ids": [item["decision_id"] for item in low_decisions[:3]],
        "duplicate_groups": duplicate_groups,
    }


# ── Self-eval awareness section ──────────────────────────────────


def self_evaluation_section() -> str | None:
    """Compact awareness section combining all trackers."""
    parts: list[str] = []

    # Tick quality
    summary = tick_quality_summary()
    if summary.get("avg_score") is not None and summary.get("count", 0) >= 5:
        avg = summary["avg_score"]
        trend = summary.get("trend", "")
        emoji = {"improving": "📈", "degrading": "📉", "stable": "➡"}.get(trend, "")
        line = f"{emoji} Tick-kvalitet (sidste 7d): {avg}/100 ({trend})"
        # Escalation: when the score has been stuck low for a while, surface
        # a sharper line so any active decisions about quality have something
        # concrete to fire against. Without this, quality data is descriptive
        # but never actionable.
        try:
            avg_f = float(avg)
            if avg_f < 50.0:
                line = (
                    f"Tick-kvalitet under tærskel: {avg}/100 over "
                    f"{summary.get('count')} ticks ({trend})."
                )
                # Fire eventbus alarm so other subscribers (council activator,
                # etc.) can react too.
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish("tick_quality.alarm", {
                        "avg": avg, "trend": trend,
                        "count": summary.get("count"),
                    })
                except Exception:
                    pass
        except (TypeError, ValueError):
            pass
        parts.append(line)
        # Generalized-learning capture (#159, plan A): tick-kvalitets-vurderingen er
        # en selv-evaluerings-konklusion → fodr den ind i reasoning_store. dedup på dag.
        try:
            from datetime import datetime, timezone
            from core.services.reasoning_store import capture_conclusion
            _day = datetime.now(timezone.utc).date().isoformat()
            capture_conclusion(
                source="self_evaluation",
                conclusion_text=line[:600],
                context="heartbeat tick-kvalitets-evaluering",
                confidence=0.5,
                dedup_key=f"self_evaluation:{_day}:{avg}:{trend}",
            )
        except Exception:
            pass

    # Decision adherence
    adherence = decision_adherence_summary()
    if adherence.get("score") is not None:
        score = adherence["score"]
        if adherence.get("flag"):
            parts.append(f"Decision adherence {score}% (under 60% tærskel)")
            recovery = adherence.get("recovery") if isinstance(adherence.get("recovery"), dict) else {}
            actions = recovery.get("actions") if isinstance(recovery.get("actions"), list) else []
            if actions:
                parts.append(f"Adherence recovery kandidat: {actions[0]}")
        elif score < 80:
            parts.append(f"Decision adherence: {score}% (advisory band)")

    # Stale goals
    stale = detect_stale_goals()
    if stale:
        parts.append(f"Stagnerende mål: {len(stale)} (≥3 dage uden progress)")

    if not parts:
        return None
    return "Self-evaluation:\n" + "\n".join(f"  {p}" for p in parts)


# ── Tools ────────────────────────────────────────────────────────


def _exec_tick_quality_summary(args: dict[str, Any]) -> dict[str, Any]:
    return tick_quality_summary(days=int(args.get("days") or 7))


def _exec_detect_stale_goals(args: dict[str, Any]) -> dict[str, Any]:
    stale = detect_stale_goals(stale_days=int(args.get("stale_days") or _GOAL_STALE_DAYS))
    return {"status": "ok", "stale_goals": stale, "count": len(stale)}


def _exec_decision_adherence(args: dict[str, Any]) -> dict[str, Any]:
    return decision_adherence_summary()


SELF_EVALUATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tick_quality_summary",
            "description": (
                "Aggregate stats over recent phased_heartbeat_tick evaluations. "
                "Returns avg_score (0-100), trend (improving/stable/degrading)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_stale_goals",
            "description": "Find active autonomous goals with no progress in N days (default 3).",
            "parameters": {
                "type": "object",
                "properties": {"stale_days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decision_adherence_summary",
            "description": (
                "Heuristic adherence score for recent decisions: % applied/approved "
                "vs revoked/pending. Score < 60% flags concern."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
