"""Webhook tools — send to and manage external HTTP endpoints."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_STATE_PATH = Path.home() / ".jarvis-v2" / "state" / "webhooks.json"


def _load() -> dict:
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"webhooks": {}}


def _save(data: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def _do_post(url: str, payload: dict, secret: str = "") -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Jarvis-Webhook/1.0",
        "X-Jarvis-Timestamp": str(int(time.time())),
    }
    if secret:
        headers["X-Hub-Signature-256"] = _sign_payload(body, secret)

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            response_body = resp.read(4096).decode("utf-8", errors="replace")
            return {"status": "ok", "http_status": resp.status, "response": response_body[:500]}
    except urllib.error.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_webhook_register(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    url = str(args.get("url") or "").strip()
    secret = str(args.get("secret") or "").strip()
    description = str(args.get("description") or "").strip()

    if not name:
        return {"status": "error", "error": "name is required"}
    if not url or not url.startswith(("http://", "https://")):
        return {"status": "error", "error": "url must be a valid http/https URL"}

    data = _load()
    data["webhooks"][name] = {
        "url": url,
        "secret": secret,
        "description": description,
        "created_at": datetime.now(UTC).isoformat(),
        "last_used_at": "",
    }
    _save(data)
    return {"status": "ok", "name": name, "url": url, "text": f"Webhook '{name}' registered → {url}"}


def _exec_webhook_send(args: dict[str, Any]) -> dict[str, Any]:
    name_or_url = str(args.get("name") or args.get("url") or "").strip()
    payload = args.get("payload") or {}
    if not isinstance(payload, dict):
        try:
            payload = json.loads(str(payload))
        except Exception:
            payload = {"message": str(payload)}

    if not name_or_url:
        return {"status": "error", "error": "name or url is required"}

    data = _load()
    if name_or_url.startswith(("http://", "https://")):
        url, secret = name_or_url, ""
    else:
        hook = data["webhooks"].get(name_or_url)
        if not hook:
            return {"status": "error", "error": f"Webhook '{name_or_url}' not registered. Use webhook_register first."}
        url = hook["url"]
        secret = hook.get("secret", "")
        data["webhooks"][name_or_url]["last_used_at"] = datetime.now(UTC).isoformat()
        _save(data)

    result = _do_post(url, payload, secret)
    result["url"] = url
    return result


def _exec_webhook_list(args: dict[str, Any]) -> dict[str, Any]:
    data = _load()
    hooks = [
        {
            "name": name,
            "url": hook["url"],
            "description": hook.get("description", ""),
            "has_secret": bool(hook.get("secret")),
            "created_at": hook.get("created_at", ""),
            "last_used_at": hook.get("last_used_at", ""),
        }
        for name, hook in data["webhooks"].items()
    ]
    return {"status": "ok", "webhooks": hooks, "count": len(hooks)}


def _exec_webhook_test(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    data = _load()
    hook = data["webhooks"].get(name)
    if not hook:
        return {"status": "error", "error": f"Webhook '{name}' not registered"}

    test_payload = {
        "event": "ping",
        "source": "jarvis",
        "timestamp": datetime.now(UTC).isoformat(),
        "message": "Test ping from Jarvis webhook tool",
    }
    result = _do_post(hook["url"], test_payload, hook.get("secret", ""))
    result["name"] = name
    result["url"] = hook["url"]
    return result


def _exec_webhook_delete(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    data = _load()
    if name not in data["webhooks"]:
        return {"status": "error", "error": f"Webhook '{name}' not found"}
    del data["webhooks"][name]
    _save(data)
    return {"status": "ok", "deleted": name}


WEBHOOK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "webhook_register",
            "description": "Register a named webhook endpoint for later use with webhook_send.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short identifier for this webhook, e.g. 'slack-alerts'."},
                    "url": {"type": "string", "description": "The full https:// URL to POST to."},
                    "secret": {"type": "string", "description": "Optional shared secret for HMAC-SHA256 signature header."},
                    "description": {"type": "string", "description": "Human-readable description of what this webhook does."},
                },
                "required": ["name", "url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "webhook_send",
            "description": "Send a POST request to a registered webhook or a direct URL. Signs payload if secret is configured.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of a registered webhook (from webhook_register)."},
                    "url": {"type": "string", "description": "Direct https:// URL (alternative to name)."},
                    "payload": {"type": "object", "description": "JSON payload to send as the request body."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "webhook_list",
            "description": "List all registered webhooks.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "webhook_test",
            "description": "Send a test ping to a registered webhook to verify it is reachable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the registered webhook to test."},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "webhook_delete",
            "description": "Remove a registered webhook by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the webhook to delete."},
                },
                "required": ["name"],
            },
        },
    },
]
