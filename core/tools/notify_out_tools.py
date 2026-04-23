"""Unified outgoing notification pipeline — ntfy, Discord, Slack, generic webhooks."""
from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_STATE_PATH = Path.home() / ".jarvis-v2" / "state" / "notify_channels.json"

# ── Channel state ─────────────────────────────────────────────────────────────

def _load() -> dict:
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"channels": {}}


def _save(data: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Channel adapters ──────────────────────────────────────────────────────────

def _send_ntfy(message: str, title: str, priority: str) -> dict:
    try:
        from core.services.ntfy_gateway import send_notification
        return send_notification(message, title=title, priority=priority)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _send_discord(url: str, message: str, title: str) -> dict:
    payload = {"content": f"**{title}**\n{message}" if title else message}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "ok", "http_status": resp.status}
    except urllib.error.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _send_slack(url: str, message: str, title: str) -> dict:
    text = f"*{title}*\n{message}" if title else message
    payload = {"text": text}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "ok", "http_status": resp.status}
    except urllib.error.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _send_generic(url: str, message: str, title: str, extra: dict) -> dict:
    payload = {"message": message, "title": title, "timestamp": datetime.now(UTC).isoformat(), **extra}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Jarvis-Notify/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "ok", "http_status": resp.status}
    except urllib.error.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _dispatch(channel_cfg: dict, message: str, title: str, priority: str) -> dict:
    kind = str(channel_cfg.get("type") or "generic").lower()
    url = str(channel_cfg.get("url") or "")
    extra = {k: v for k, v in channel_cfg.items() if k not in ("type", "url", "name", "created_at")}

    if kind == "ntfy":
        return _send_ntfy(message, title, priority)
    elif kind == "discord":
        return _send_discord(url, message, title)
    elif kind == "slack":
        return _send_slack(url, message, title)
    else:
        return _send_generic(url, message, title, extra)


# ── Tool executors ────────────────────────────────────────────────────────────

def _exec_notify_out(args: dict[str, Any]) -> dict[str, Any]:
    message = str(args.get("message") or "").strip()
    if not message:
        return {"status": "error", "error": "message is required"}

    title = str(args.get("title") or "Jarvis").strip()
    priority = str(args.get("priority") or "default").strip()
    channels = args.get("channels") or ["ntfy"]
    if isinstance(channels, str):
        channels = [channels]

    data = _load()
    results = {}
    errors = []

    for ch in channels:
        if ch == "ntfy":
            r = _send_ntfy(message, title, priority)
        elif ch in data["channels"]:
            r = _dispatch(data["channels"][ch], message, title, priority)
        else:
            r = {"status": "error", "error": f"Channel '{ch}' not registered. Use notify_channel_add."}

        results[ch] = r
        if r.get("status") != "ok":
            errors.append(f"{ch}: {r.get('error')}")

    overall = "ok" if not errors else ("partial" if len(errors) < len(channels) else "error")
    return {
        "status": overall,
        "results": results,
        "errors": errors or None,
        "text": f"Sent to {len(channels) - len(errors)}/{len(channels)} channels.",
    }


def _exec_notify_channel_add(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    kind = str(args.get("type") or "generic").strip().lower()
    url = str(args.get("url") or "").strip()

    if not name:
        return {"status": "error", "error": "name is required"}
    valid_types = ("ntfy", "discord", "slack", "generic")
    if kind not in valid_types:
        return {"status": "error", "error": f"type must be one of: {', '.join(valid_types)}"}
    if kind != "ntfy" and not url:
        return {"status": "error", "error": "url is required for non-ntfy channels"}

    data = _load()
    data["channels"][name] = {
        "name": name,
        "type": kind,
        "url": url,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _save(data)
    return {"status": "ok", "name": name, "type": kind, "text": f"Channel '{name}' ({kind}) registered."}


def _exec_notify_channel_list(args: dict[str, Any]) -> dict[str, Any]:
    data = _load()
    channels = [
        {"name": n, "type": c.get("type"), "url": c.get("url", ""), "created_at": c.get("created_at", "")}
        for n, c in data["channels"].items()
    ]
    # Always show ntfy as built-in
    builtin = [{"name": "ntfy", "type": "ntfy", "url": "(configured in runtime.json)", "builtin": True}]
    return {"status": "ok", "channels": builtin + channels, "count": len(channels) + 1}


def _exec_notify_channel_delete(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    if name == "ntfy":
        return {"status": "error", "error": "Cannot delete built-in ntfy channel."}
    data = _load()
    if name not in data["channels"]:
        return {"status": "error", "error": f"Channel '{name}' not found."}
    del data["channels"][name]
    _save(data)
    return {"status": "ok", "deleted": name}


NOTIFY_OUT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "notify_out",
            "description": (
                "Send a notification to one or more channels. Built-in: 'ntfy'. "
                "Add Discord/Slack/custom channels with notify_channel_add first. "
                "Use for urgent alerts, status updates, and proactive outreach."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Notification body."},
                    "title": {"type": "string", "description": "Notification title (default 'Jarvis')."},
                    "priority": {
                        "type": "string",
                        "description": "Priority: min / low / default / high / urgent.",
                        "enum": ["min", "low", "default", "high", "urgent"],
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of channel names to send to. Default ['ntfy'].",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_channel_add",
            "description": "Register a notification channel (Discord webhook, Slack webhook, or generic HTTP endpoint).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short identifier for this channel."},
                    "type": {
                        "type": "string",
                        "description": "Channel type: ntfy, discord, slack, or generic.",
                        "enum": ["ntfy", "discord", "slack", "generic"],
                    },
                    "url": {"type": "string", "description": "Webhook URL (required for all except ntfy)."},
                },
                "required": ["name", "type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_channel_list",
            "description": "List all configured notification channels.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_channel_delete",
            "description": "Remove a registered notification channel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Channel name to remove."},
                },
                "required": ["name"],
            },
        },
    },
]
