"""Mission Control: tool/skill/hardening/lab-hjælpere.

Flyttet uændret fra mission_control.py (god-fil-snit). Adskilt fra
mission_control_common for at holde begge filer under 1500 linjer."""
from __future__ import annotations

from .mission_control_imports import *  # noqa: F401,F403 (delt import-flade)

def _get_all_tools() -> list[dict]:
    """Return the OpenAI-style tool definitions registered in the runtime.

    The symbol was renamed from `_TOOLS` to `TOOL_DEFINITIONS` and the
    silent except above hid the resulting ImportError, leaving the Skills
    tab showing 0/0/0 even though tools were registered.
    """
    try:
        from core.tools.simple_tools import TOOL_DEFINITIONS
        return list(TOOL_DEFINITIONS)
    except Exception:
        return []


def _skills_recent_invocations(limit: int = 10) -> list[dict]:
    """Return the most recent tool/capability invocations.

    Reads tool.completed events first (the live channel for simple_tools),
    falling back to the legacy capability_invocations table when there are
    fewer than `limit` recent events. Each row is normalised to the same
    {capability_name, status, invoked_at} shape the UI expects.
    """
    import json as _json

    items: list[dict] = []
    try:
        with connect() as conn:
            # tool.completed always carries a `tool` field with the
            # actual tool name. tool.error events are reused by unrelated
            # subsystems (attention_blink research) with a different
            # payload shape — excluded here to avoid muddying the list.
            event_rows = conn.execute(
                """
                SELECT kind, payload_json, created_at
                FROM events
                WHERE kind = 'tool.completed'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            for row in event_rows:
                try:
                    payload = _json.loads(row["payload_json"] or "{}")
                except Exception:
                    payload = {}
                name = str(
                    payload.get("tool")
                    or payload.get("name")
                    or payload.get("tool_name")
                    or "tool"
                )
                status = str(payload.get("status") or "ok")
                items.append({
                    "capability_name": name,
                    "status": status,
                    "invoked_at": row["created_at"] or "",
                })
            if len(items) < limit:
                legacy_rows = conn.execute(
                    """
                    SELECT capability_name, status, invoked_at
                    FROM capability_invocations
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit - len(items),),
                ).fetchall()
                for row in legacy_rows:
                    items.append({
                        "capability_name": row["capability_name"] or "",
                        "status": row["status"] or "",
                        "invoked_at": row["invoked_at"] or "",
                    })
    except Exception:
        return []
    return items[:limit]


def _skills_calls_today() -> int:
    """Count tool invocations made today.

    The legacy capability_invocations table only covers workspace_capabilities,
    which was effectively retired around April 9 2026 in favour of simple_tools
    (OpenAI tool_calls). Today's actual tool activity lives in the events table
    as `tool.invoked` events. Sum both so this metric reflects reality across
    the migration boundary.
    """
    total = 0
    try:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM capability_invocations
                WHERE date(invoked_at) = date('now')
                """
            ).fetchone()
            total += int(row["n"]) if row else 0
            row2 = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM events
                WHERE kind = 'tool.invoked'
                  AND date(created_at) = date('now')
                """
            ).fetchone()
            total += int(row2["n"]) if row2 else 0
    except Exception:
        pass
    return total



def _hardening_approval_counts() -> dict:
    try:
        with connect() as conn:
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM tool_intent_approval_requests WHERE approval_state = 'pending'"
            ).fetchone()["n"]
            approved = conn.execute(
                "SELECT COUNT(*) AS n FROM tool_intent_approval_requests WHERE approval_state = 'approved' AND date(resolved_at) = date('now')"
            ).fetchone()["n"]
            denied = conn.execute(
                "SELECT COUNT(*) AS n FROM tool_intent_approval_requests WHERE approval_state = 'denied' AND date(resolved_at) = date('now')"
            ).fetchone()["n"]
        return {"pending": int(pending), "approved_today": int(approved), "denied_today": int(denied)}
    except Exception:
        return {"pending": 0, "approved_today": 0, "denied_today": 0}


def _hardening_autonomy_level() -> str:
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT value FROM runtime_state_kv WHERE key = 'autonomy_level' LIMIT 1"
            ).fetchone()
        return str(row["value"]) if row else "direct"
    except Exception:
        return "direct"


def _hardening_integrations() -> dict:
    """Report which external integrations are configured.

    Each integration stores credentials in its own canonical location —
    not all in runtime.json. Mission Control was checking the wrong
    fields and reporting "Ikke sat op" for live integrations:
    - Discord uses ~/.jarvis-v2/config/discord.json (bot_token + guild_id)
    - Home Assistant uses home_assistant_url + home_assistant_token in runtime.json
    - Telegram uses telegram_bot_token in runtime.json
    - Anthropic uses anthropic_api_key in runtime.json (most users won't have one)
    """
    import json as _json
    from pathlib import Path as _Path

    result = {
        "telegram": False,
        "discord": False,
        "home_assistant": False,
        "anthropic": False,
    }
    try:
        cfg_path = _Path.home() / ".jarvis-v2" / "config" / "runtime.json"
        cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
        result["telegram"] = bool(cfg.get("telegram_bot_token"))
        result["home_assistant"] = bool(
            cfg.get("home_assistant_url") and cfg.get("home_assistant_token")
        )
        result["anthropic"] = bool(cfg.get("anthropic_api_key"))
    except Exception:
        pass

    # Discord lives in its own config file with its own validation.
    try:
        from core.services.discord_config import is_discord_configured

        result["discord"] = bool(is_discord_configured())
    except Exception:
        result["discord"] = False

    return result


def _hardening_recent_approvals(limit: int = 10) -> list[dict]:
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT intent_type, intent_target, approval_state, requested_at
                FROM tool_intent_approval_requests
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "intent_type": row["intent_type"] or "",
                "intent_target": str(row["intent_target"] or "")[:80],
                "approval_state": row["approval_state"] or "",
                "requested_at": row["requested_at"] or "",
            }
            for row in rows
        ]
    except Exception:
        return []



def _lab_costs_today() -> dict:
    try:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS calls,
                    COALESCE(SUM(input_tokens), 0) AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens,
                    COALESCE(SUM(cost_usd), 0) AS total_usd
                FROM costs
                WHERE date(created_at) = date('now')
                """
            ).fetchone()
        return {
            "total_usd": round(float(row["total_usd"]), 6),
            "input_tokens": int(row["input_tokens"]),
            "output_tokens": int(row["output_tokens"]),
            "calls": int(row["calls"]),
        }
    except Exception:
        return {"total_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "calls": 0}


def _lab_providers_today() -> list[dict]:
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    provider,
                    COUNT(*) AS calls,
                    COALESCE(SUM(input_tokens), 0) AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens,
                    COALESCE(SUM(cost_usd), 0) AS cost_usd
                FROM costs
                WHERE date(created_at) = date('now')
                GROUP BY provider
                ORDER BY cost_usd DESC
                """
            ).fetchall()
        return [
            {
                "provider": row["provider"] or "unknown",
                "cost_usd": round(float(row["cost_usd"]), 6),
                "input_tokens": int(row["input_tokens"]),
                "output_tokens": int(row["output_tokens"]),
                "calls": int(row["calls"]),
            }
            for row in rows
        ]
    except Exception:
        return []


def _lab_db_stats() -> dict:
    try:
        with connect() as conn:
            events = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
            runs = conn.execute("SELECT COUNT(*) AS n FROM visible_runs").fetchone()["n"]
            sessions = conn.execute("SELECT COUNT(*) AS n FROM chat_sessions").fetchone()["n"]
            approvals = conn.execute("SELECT COUNT(*) AS n FROM tool_intent_approval_requests").fetchone()["n"]
        return {
            "events": int(events),
            "runs": int(runs),
            "sessions": int(sessions),
            "approvals": int(approvals),
        }
    except Exception:
        return {"events": 0, "runs": 0, "sessions": 0, "approvals": 0}


def _lab_recent_events(limit: int = 15) -> list[dict]:
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id, kind, family, created_at FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "kind": str(row["kind"] or ""),
                "family": str(row["family"] or ""),
                "created_at": str(row["created_at"] or ""),
            }
            for row in rows
        ]
    except Exception:
        return []




# Eksportér ALT (inkl. underscore-hjælpere) så route-moduler kan bruge
