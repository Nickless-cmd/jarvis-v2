"""Daemon health alert — detects inactive/crashed daemons and sends notifications."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ALERT_STATE_PATH = Path.home() / ".jarvis-v2" / "state" / "daemon_alerts.json"
_DEFAULT_THRESHOLD = 2.5  # alert if hours_since_last_run > threshold * cadence_hours
_ALERT_COOLDOWN_HOURS = 2.0  # don't re-alert for same daemon within this window


def _load_alert_state() -> dict:
    try:
        return json.loads(_ALERT_STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_alerted": {}}


def _save_alert_state(data: dict) -> None:
    _ALERT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ALERT_STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _hours_since(iso_str: str) -> float | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return (datetime.now(UTC) - dt).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def _exec_daemon_health_alert(args: dict[str, Any]) -> dict[str, Any]:
    threshold_multiplier = float(args.get("threshold_multiplier") or _DEFAULT_THRESHOLD)
    notify = bool(args.get("notify", True))
    channels = args.get("channels") or ["ntfy"]

    try:
        from core.services.daemon_manager import get_all_daemon_states
        daemons = get_all_daemon_states()
    except Exception as e:
        return {"status": "error", "error": f"Could not get daemon states: {e}"}

    alert_state = _load_alert_state()
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    overdue = []
    for d in daemons:
        if not d.get("enabled"):
            continue
        cadence_min = int(d.get("effective_cadence_minutes") or 0)
        if cadence_min <= 0:
            continue
        hours_since = d.get("hours_since_last_run")
        if hours_since is None:
            continue  # never run — not an alert condition (daemon may not have fired yet)

        cadence_hours = cadence_min / 60
        threshold_hours = threshold_multiplier * cadence_hours

        if hours_since > threshold_hours:
            name = str(d["name"])
            last_alerted_iso = alert_state["last_alerted"].get(name, "")
            last_alerted_hours = _hours_since(last_alerted_iso)

            # Skip if we already alerted within cooldown window
            if last_alerted_hours is not None and last_alerted_hours < _ALERT_COOLDOWN_HOURS:
                continue

            overdue.append({
                "name": name,
                "hours_since_last_run": round(hours_since, 1),
                "cadence_hours": round(cadence_hours, 2),
                "threshold_hours": round(threshold_hours, 2),
                "description": d.get("description", ""),
            })

    if overdue and notify:
        names = ", ".join(d["name"] for d in overdue)
        message = f"⚠️ Inaktive daemons: {names}\n" + "\n".join(
            f"  • {d['name']}: {d['hours_since_last_run']}h siden sidst (forventet <{d['threshold_hours']:.1f}h)"
            for d in overdue
        )
        try:
            from core.tools.notify_out_tools import _exec_notify_out
            _exec_notify_out({
                "message": message,
                "title": "Jarvis Daemon Alert",
                "priority": "high",
                "channels": channels,
            })
        except Exception as e:
            pass  # best-effort — don't fail the check itself

        # Record alert times
        for d in overdue:
            alert_state["last_alerted"][d["name"]] = now_iso
        _save_alert_state(alert_state)

    return {
        "status": "ok",
        "overdue_daemons": overdue,
        "overdue_count": len(overdue),
        "threshold_multiplier": threshold_multiplier,
        "text": (
            f"{len(overdue)} daemon(s) overdue: {', '.join(d['name'] for d in overdue)}"
            if overdue else "All enabled daemons are running on schedule."
        ),
    }


def _exec_daemon_alert_status(args: dict[str, Any]) -> dict[str, Any]:
    """Show when each daemon was last alerted."""
    state = _load_alert_state()
    entries = [
        {
            "daemon": name,
            "last_alerted_at": ts,
            "hours_ago": round(_hours_since(ts) or 0, 1),
        }
        for name, ts in state["last_alerted"].items()
    ]
    entries.sort(key=lambda x: x.get("last_alerted_at", ""), reverse=True)
    return {"status": "ok", "alerts": entries, "count": len(entries)}


DAEMON_ALERT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "daemon_health_alert",
            "description": (
                "Check all enabled daemons for inactivity. Sends a notification if any daemon "
                "has not run in more than threshold_multiplier × its normal cadence. "
                "Respects a 2-hour cooldown to avoid notification spam."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold_multiplier": {
                        "type": "number",
                        "description": "Alert if hours_since_last_run > multiplier × cadence_hours. Default 2.5.",
                    },
                    "notify": {
                        "type": "boolean",
                        "description": "Send notification for overdue daemons (default true).",
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Notification channels to use (default ['ntfy']).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "daemon_alert_status",
            "description": "Show when each daemon was last alerted for inactivity.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
