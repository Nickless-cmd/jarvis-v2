"""API health monitor tools — Jarvis can watch services and be notified of outages."""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_STATE_PATH = Path.home() / ".jarvis-v2" / "state" / "health_monitor.json"
_MAX_HISTORY = 20

_PRESET_ENDPOINTS = {
    "jarvis-api": "http://localhost:8000/health",
    "ollama": "http://10.0.0.25:11434/api/tags",
    "comfyui": "http://localhost:8188/",
}


def _load() -> dict:
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"endpoints": {}}


def _save(data: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _ping(url: str, expected_status: int = 200, timeout: int = 10) -> dict:
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis-HealthMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency_ms = round((time.monotonic() - start) * 1000)
            ok = resp.status == expected_status
            return {
                "reachable": True,
                "healthy": ok,
                "http_status": resp.status,
                "latency_ms": latency_ms,
                "error": None if ok else f"Expected {expected_status}, got {resp.status}",
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.monotonic() - start) * 1000)
        ok = e.code == expected_status
        return {
            "reachable": True,
            "healthy": ok,
            "http_status": e.code,
            "latency_ms": latency_ms,
            "error": None if ok else f"HTTP {e.code}",
        }
    except Exception as e:
        latency_ms = round((time.monotonic() - start) * 1000)
        return {"reachable": False, "healthy": False, "http_status": None, "latency_ms": latency_ms, "error": str(e)}


def _record_check(name: str, result: dict) -> None:
    data = _load()
    ep = data["endpoints"].setdefault(name, {"history": []})
    entry = {
        "checked_at": datetime.now(UTC).isoformat(),
        "healthy": result["healthy"],
        "http_status": result.get("http_status"),
        "latency_ms": result.get("latency_ms"),
        "error": result.get("error"),
    }
    ep.setdefault("history", []).insert(0, entry)
    ep["history"] = ep["history"][:_MAX_HISTORY]
    ep["last_checked_at"] = entry["checked_at"]
    ep["last_healthy"] = result["healthy"]
    _save(data)


def _exec_health_check(args: dict[str, Any]) -> dict[str, Any]:
    name_or_url = str(args.get("name") or args.get("url") or "").strip()
    if not name_or_url:
        return {"status": "error", "error": "name or url is required"}

    expected_status = int(args.get("expected_status") or 200)
    timeout = min(int(args.get("timeout") or 10), 30)

    data = _load()
    if name_or_url.startswith(("http://", "https://")):
        url = name_or_url
        name = url
    elif name_or_url in data["endpoints"]:
        url = data["endpoints"][name_or_url].get("url") or _PRESET_ENDPOINTS.get(name_or_url, "")
        name = name_or_url
    elif name_or_url in _PRESET_ENDPOINTS:
        url = _PRESET_ENDPOINTS[name_or_url]
        name = name_or_url
    else:
        return {"status": "error", "error": f"'{name_or_url}' not registered. Use health_register or pass a full URL."}

    if not url:
        return {"status": "error", "error": f"No URL configured for '{name}'"}

    result = _ping(url, expected_status, timeout)
    _record_check(name, result)

    return {
        "status": "ok",
        "name": name,
        "url": url,
        **result,
        "text": f"{'✓' if result['healthy'] else '✗'} {name}: {'healthy' if result['healthy'] else 'UNHEALTHY'} ({result.get('latency_ms')}ms)",
    }


def _exec_health_register(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    url = str(args.get("url") or "").strip()
    expected_status = int(args.get("expected_status") or 200)

    if not name:
        return {"status": "error", "error": "name is required"}
    if not url or not url.startswith(("http://", "https://")):
        return {"status": "error", "error": "url must be a valid http/https URL"}

    data = _load()
    existing = data["endpoints"].get(name, {})
    data["endpoints"][name] = {
        **existing,
        "url": url,
        "expected_status": expected_status,
        "registered_at": existing.get("registered_at", datetime.now(UTC).isoformat()),
        "history": existing.get("history", []),
    }
    _save(data)
    return {"status": "ok", "name": name, "url": url, "expected_status": expected_status,
            "text": f"Endpoint '{name}' registered for health monitoring → {url}"}


def _exec_health_status(args: dict[str, Any]) -> dict[str, Any]:
    data = _load()
    endpoints = []

    # Include presets that aren't explicitly registered
    all_names = set(data["endpoints"].keys()) | set(_PRESET_ENDPOINTS.keys())

    for name in sorted(all_names):
        ep = data["endpoints"].get(name, {})
        url = ep.get("url") or _PRESET_ENDPOINTS.get(name, "")
        endpoints.append({
            "name": name,
            "url": url,
            "last_healthy": ep.get("last_healthy"),
            "last_checked_at": ep.get("last_checked_at", "never"),
            "check_count": len(ep.get("history", [])),
            "registered": name in data["endpoints"],
        })

    healthy_count = sum(1 for e in endpoints if e["last_healthy"] is True)
    unknown_count = sum(1 for e in endpoints if e["last_healthy"] is None)
    unhealthy_count = sum(1 for e in endpoints if e["last_healthy"] is False)

    return {
        "status": "ok",
        "endpoints": endpoints,
        "summary": {"healthy": healthy_count, "unhealthy": unhealthy_count, "unknown": unknown_count},
    }


def _exec_health_history(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}

    data = _load()
    ep = data["endpoints"].get(name)
    if not ep:
        return {"status": "error", "error": f"No history for '{name}'. Run health_check first."}

    history = ep.get("history", [])
    return {
        "status": "ok",
        "name": name,
        "url": ep.get("url", ""),
        "history": history,
        "healthy_count": sum(1 for h in history if h.get("healthy")),
        "unhealthy_count": sum(1 for h in history if not h.get("healthy")),
    }


HEALTH_MONITOR_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "health_check",
            "description": (
                "Ping a service endpoint and get its health status. "
                "Supports named endpoints (jarvis-api, ollama, comfyui) and full URLs. "
                "Records result to history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Registered endpoint name or built-in preset (jarvis-api, ollama, comfyui)."},
                    "url": {"type": "string", "description": "Direct URL to check (alternative to name)."},
                    "expected_status": {"type": "integer", "description": "Expected HTTP status code (default 200)."},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 10, max 30)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_register",
            "description": "Register a service endpoint for health monitoring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short identifier, e.g. 'home-assistant'."},
                    "url": {"type": "string", "description": "Full https:// URL to monitor."},
                    "expected_status": {"type": "integer", "description": "Expected HTTP status code (default 200)."},
                },
                "required": ["name", "url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_status",
            "description": "Get an overview of all registered and preset service endpoints and their last known health.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_history",
            "description": "Get recent health check history for a specific endpoint.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Endpoint name to get history for."},
                },
                "required": ["name"],
            },
        },
    },
]
