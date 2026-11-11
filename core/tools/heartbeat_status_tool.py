"""User-facing heartbeat status assembled from runtime state and liveness signals."""
from __future__ import annotations

import json
import logging
from typing import Any

_log = logging.getLogger(__name__)


def _exec_heartbeat_status(_args: dict[str, Any]) -> dict[str, Any]:
    """Return heartbeat scheduler status and recent tick history."""
    try:
        from core.runtime.workspace_paths import heartbeat_state_path

        state_path = heartbeat_state_path()
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        artifact_state = raw.get("state", {})
        artifact_recent = raw.get("recent_ticks", [])

        # DB'en er procesfælles og er derfor sandhed for liveness-felterne.
        # JSON-artifaktet bevarer præsentationsfelter (bl.a. interval_minutes),
        # som endnu ikke findes som kolonne i heartbeat_runtime_state.
        from core.runtime.db_heartbeat import (
            get_heartbeat_runtime_state,
            recent_heartbeat_runtime_ticks,
        )

        shared_state = get_heartbeat_runtime_state() or {}
        state = {**artifact_state, **shared_state}
        try:
            recent = recent_heartbeat_runtime_ticks(limit=8)
        except Exception as exc:
            # Uden DB'en kan vi ikke se den nyeste tick — men vi kan stadig se
            # den delte tilstand. Fejlen logges frem for at gøre tælleren tavst
            # til nul, så en DB-fejl ikke ser ud som «ingen ticks».
            _log.warning("heartbeat status: kunne ikke laese ticks fra DB: %s", exc)
            recent = artifact_recent

        scheduler = {
            "active": state.get("scheduler_active"),
            "health": state.get("scheduler_health"),
            "started_at": state.get("scheduler_started_at"),
            "stopped_at": state.get("scheduler_stopped_at") or None,
            "currently_ticking": state.get("currently_ticking"),
            "last_tick_at": state.get("last_tick_at"),
            "next_tick_at": state.get("next_tick_at"),
            "interval_minutes": state.get("interval_minutes"),
            "last_trigger_source": state.get("last_trigger_source"),
            "last_decision_type": state.get("last_decision_type"),
            "execution_status": state.get("execution_status"),
            "parse_status": state.get("parse_status"),
        }

        from core.services import heartbeat_scheduler as _hs

        db_last = recent[0].get("started_at") if recent else None
        from core.services.central_xproc import process_role

        owner_process = process_role() == "runtime"
        local_thread_running = _hs.is_running() if owner_process else None
        local_iterations = _hs.iterations() if owner_process else None
        local_watchdog_running = _hs.watchdog_is_running() if owner_process else None
        liveness = _hs.assess_liveness(
            scheduler_active=scheduler["active"],
            scheduler_health=scheduler["health"],
            next_tick_at=scheduler["next_tick_at"],
            last_tick_at=scheduler["last_tick_at"],
            interval_minutes=scheduler["interval_minutes"],
            thread_running=local_thread_running,
            iterations_count=local_iterations,
            db_last_tick_started_at=db_last,
        )
        scheduler["verdict"] = liveness["verdict"]
        scheduler["mismatch"] = liveness["mismatch"]
        scheduler["iterations"] = liveness["iterations"]
        scheduler["thread_running"] = liveness["thread_running"]
        scheduler["thread_observation"] = liveness["thread_observation"]
        scheduler["watchdog_running"] = local_watchdog_running
        scheduler["observer_process"] = process_role()
        scheduler["liveness_source"] = "heartbeat_runtime_state"
        scheduler["overdue_minutes"] = liveness["overdue_minutes"]
        scheduler["newest_tick_started_at"] = liveness["newest_tick_started_at"]

        lines = []
        lines.append(f"Scheduler: {liveness['verdict']} (flag={scheduler['health']})")
        if liveness["thread_observation"] == "not_observed_in_this_process":
            lines.append(
                f"Thread: not observed in this process ({process_role()}); "
                f"shared DB liveness | next tick overdue: {liveness['overdue_minutes']} min"
            )
        else:
            lines.append(
                f"Thread running: {liveness['thread_running']} | "
                f"iterations: {liveness['iterations']} | "
                f"next tick overdue: {liveness['overdue_minutes']} min"
            )
            lines.append(f"Watchdog running: {local_watchdog_running}")
        if liveness["mismatch"]:
            lines.append("MISMATCH: " + ", ".join(liveness["mismatch"]))
        lines.append(f"Last tick: {scheduler['last_tick_at'] or 'never'}")
        lines.append(f"Next tick: {scheduler['next_tick_at'] or 'unknown'}")
        lines.append(f"Interval: {scheduler['interval_minutes']} min")
        lines.append(f"Last trigger: {scheduler['last_trigger_source']}")
        lines.append(f"Last decision: {scheduler['last_decision_type']}")
        if recent:
            lines.append(f"Recent ticks: {len(recent)} recorded")

        return {
            "status": "ok",
            "scheduler": scheduler,
            "recent_tick_count": len(recent),
            "text": "\n".join(lines),
        }
    except Exception as exc:
        _log.warning("heartbeat status kunne ikke samles: %s", exc)
        return {"status": "error", "error": str(exc)}
