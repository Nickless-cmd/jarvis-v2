"""Autonomous Work Daemon — Jarvis works on his own when Bjørn is away.

Jarvis' PLAN_WILD_IDEAS #12 (2026-04-20). Activates during low-activity
periods. Proposes work from a whitelist of allowed activities — never
direct mutation outside the proposal system.

Philosophy: this daemon *plans* and *logs*. It does not execute
destructive actions. It files work-proposals that Bjørn/Jarvis can
inspect and approve. For tiny self-contained actions (like incubator
seed creation), it calls through to the existing services.

Whitelist (allowed proposal types):
- memory_consolidate  — summarize recent day into consolidated notes
- incubator_seed      — nudge creative_instinct to generate seeds
- research            — queue a web_search for an incubator topic (proposal)
- workspace_refactor  — propose edits to evolvable work-prompt files
- blog_draft          — if Bjørn asked for one, draft outline

Rate limit: max 3 proposals per hour, with low-activity detection gating
the daemon itself.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/autonomous_work_log.json"
_LOG_MAX = 300
_MAX_PROPOSALS_PER_HOUR = 3
_LOW_ACTIVITY_MINUTES = 15

_ALLOWED_TYPES: tuple[str, ...] = (
    "memory_consolidate",
    "incubator_seed",
    "research",
    "workspace_refactor",
    "blog_draft",
)


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("autonomous_work: load failed: %s", exc)
    return []


def _save(items: list[dict[str, Any]]) -> None:
    if len(items) > _LOG_MAX:
        items = items[-_LOG_MAX:]
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("autonomous_work: save failed: %s", exc)


def _proposals_last_hour() -> int:
    log = _load()
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    count = 0
    for entry in reversed(log):
        try:
            ts = datetime.fromisoformat(str(entry.get("at")).replace("Z", "+00:00"))
            if ts >= cutoff:
                count += 1
            else:
                break
        except Exception:
            continue
    return count


def _is_low_activity() -> tuple[bool, str]:
    """Low-activity = no visible runs in last _LOW_ACTIVITY_MINUTES."""
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=5) or []
        if not runs:
            return True, "no-runs"
        latest = runs[0]
        ts = str(latest.get("started_at") or "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            minutes_since = (datetime.now(UTC) - dt).total_seconds() / 60
            if minutes_since >= _LOW_ACTIVITY_MINUTES:
                return True, f"idle-{int(minutes_since)}m"
            return False, f"active-{int(minutes_since)}m-ago"
        except Exception:
            return True, "cannot-parse-ts"
    except Exception:
        return True, "db-unavailable"


def _pending_initiatives() -> list[dict[str, Any]]:
    try:
        from core.services.initiative_queue import get_pending_initiatives
        return list(get_pending_initiatives() or [])
    except Exception:
        return []


def _log_entry(entry: dict[str, Any]) -> None:
    log = _load()
    log.append(entry)
    _save(log)


def _file_proposal(
    *,
    proposal_type: str,
    title: str,
    details: dict[str, Any],
    rationale: str,
) -> str:
    """Record a work proposal for later execution/approval."""
    if proposal_type not in _ALLOWED_TYPES:
        raise ValueError(f"proposal_type not whitelisted: {proposal_type}")
    prop_id = f"aw-{uuid4().hex[:12]}"
    entry = {
        "proposal_id": prop_id,
        "at": datetime.now(UTC).isoformat(),
        "type": proposal_type,
        "title": str(title)[:160],
        "details": dict(details),
        "rationale": str(rationale)[:400],
        "status": "pending",
    }
    _log_entry(entry)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "autonomous_work.proposal",
            "payload": {
                "proposal_id": prop_id,
                "type": proposal_type,
                "title": entry["title"],
            },
        })
    except Exception:
        pass
    return prop_id


# --- Individual planners ---

def _maybe_propose_memory_consolidate() -> str | None:
    """Propose a daily memory consolidation when ~end of day locally."""
    now_local = datetime.now().astimezone()
    # Trigger window: 22:00-00:00 local, once per day
    if not (22 <= now_local.hour):
        return None
    log = _load()
    today_key = now_local.date().isoformat()
    for e in log:
        if e.get("type") == "memory_consolidate" and str(e.get("at", ""))[:10] == today_key:
            return None  # already proposed today
    return _file_proposal(
        proposal_type="memory_consolidate",
        title="Consolidate today's memory notes",
        details={"date": today_key},
        rationale="End-of-day window; roll up today's private-brain fragments.",
    )


def _maybe_nudge_incubator() -> str | None:
    """If incubator is sparse, nudge creative_instinct to generate."""
    try:
        from core.services.creative_instinct_daemon import build_creative_instinct_surface
        s = build_creative_instinct_surface()
        active_seeds = int(s.get("active_seeds") or 0)
        if active_seeds >= 3:
            return None
    except Exception:
        return None
    # Trigger creative_instinct tick directly (it has its own cadence gate)
    try:
        from core.services.creative_instinct_daemon import tick as ci_tick
        ci_tick(0.0)
    except Exception:
        pass
    return _file_proposal(
        proposal_type="incubator_seed",
        title="Nudged creative_instinct for fresh idea seeds",
        details={},
        rationale="Incubator had <3 active seeds.",
    )


def _maybe_propose_research() -> str | None:
    """Pick one maturing incubator seed and propose a research topic for it."""
    try:
        from core.services.creative_instinct_daemon import list_seeds
        maturing = [s for s in list_seeds(status="maturing")][:1]
    except Exception:
        return None
    if not maturing:
        return None
    seed = maturing[0]
    return _file_proposal(
        proposal_type="research",
        title=f"Research for seed: {seed.get('spark', '')[:80]}",
        details={"seed_id": seed.get("seed_id"), "spark": seed.get("spark")},
        rationale="Maturing seed would benefit from external research.",
    )


def _plan_once() -> list[str]:
    """Run planning passes and return list of created proposal_ids."""
    created: list[str] = []
    remaining = max(0, _MAX_PROPOSALS_PER_HOUR - _proposals_last_hour())
    planners = (
        _maybe_propose_memory_consolidate,
        _maybe_nudge_incubator,
        _maybe_propose_research,
    )
    for planner in planners:
        if remaining <= 0:
            break
        try:
            pid = planner()
            if pid:
                created.append(pid)
                remaining -= 1
        except Exception as exc:
            logger.debug("autonomous_work planner %s failed: %s", planner.__name__, exc)
    return created


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    low, reason = _is_low_activity()
    if not low:
        return {"skipped": True, "reason": reason}
    if _proposals_last_hour() >= _MAX_PROPOSALS_PER_HOUR:
        return {"skipped": True, "reason": "rate-limited"}
    created = _plan_once()
    return {
        "skipped": False,
        "activity_reason": reason,
        "proposals_created": len(created),
        "proposal_ids": created,
    }


def list_proposals(*, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [e for e in items if e.get("status") == status]
    return items[-limit:][::-1]


def resolve_proposal(proposal_id: str, *, outcome: str, note: str = "") -> bool:
    """Close a proposal. outcome in {'approved', 'rejected', 'completed'}."""
    if outcome not in ("approved", "rejected", "completed"):
        return False
    items = _load()
    for e in items:
        if e.get("proposal_id") == proposal_id and e.get("status") == "pending":
            e["status"] = outcome
            e["resolved_at"] = datetime.now(UTC).isoformat()
            if note:
                e["resolution_note"] = str(note)[:300]
            _save(items)
            return True
    return False


def build_autonomous_work_surface() -> dict[str, Any]:
    items = _load()
    pending = [e for e in items if e.get("status") == "pending"]
    by_type: dict[str, int] = {}
    for e in pending:
        t = str(e.get("type") or "")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "active": len(items) > 0,
        "pending_count": len(pending),
        "total_proposals": len(items),
        "by_type_pending": by_type,
        "allowed_types": list(_ALLOWED_TYPES),
        "max_per_hour": _MAX_PROPOSALS_PER_HOUR,
        "recent": items[-5:][::-1],
        "summary": _surface_summary(pending, items),
    }


def _surface_summary(pending: list[dict[str, Any]], all_items: list[dict[str, Any]]) -> str:
    if not all_items:
        return "Ingen autonomous-work forslag endnu"
    if pending:
        return f"{len(pending)} afventende forslag af {len(all_items)} total"
    return f"0 afventende ({len(all_items)} behandlet)"


def build_autonomous_work_prompt_section() -> str | None:
    items = _load()
    pending = [e for e in items if e.get("status") == "pending"]
    if not pending:
        return None
    top = pending[-1]
    return (
        f"Mens du var væk foreslog jeg: '{top.get('title')}' "
        f"({top.get('type')}). {len(pending)} forslag afventer."
    )
