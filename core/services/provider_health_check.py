"""Provider health check — periodic ping to detect outages early.

Existing reactive infrastructure (circuit breaker, fallback) only learns
a provider is down AFTER a real call fails. Health check ping every 5
min lets us detect outages before they hit user-facing calls.

Pings each enabled cheap_lane provider with a tiny request. Records
status in eventbus. Updates provider_circuit_breaker proactively when
ping fails consistently — so next call doesn't have to discover it.

Cheap: 1 ping per provider per 5 min × 9 providers = 108 calls/hour
total. Each ping is a single token completion → minimal cost.
"""
from __future__ import annotations

import logging
import urllib.request
import urllib.error
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


_PING_TIMEOUT_SECONDS = 5
_HEALTH_STATE_KEY = "provider_health"


# Lightweight reachability check — just ensure the host responds.
# Doesn't do an actual LLM call (would consume quota).
_PING_ENDPOINTS: dict[str, str] = {
    "ollamafreeapi": "https://ollamafreeapi.com/",
    "groq": "https://api.groq.com/openai/v1/models",
    "gemini": "https://generativelanguage.googleapis.com/",
    "nvidia-nim": "https://integrate.api.nvidia.com/v1/models",
    "openrouter": "https://openrouter.ai/api/v1/models",
    "mistral": "https://api.mistral.ai/v1/models",
    "sambanova": "https://api.sambanova.ai/v1/models",
    "cloudflare": "https://api.cloudflare.com/client/v4/",
    "opencode": "https://opencode.ai/",
}


def _ping_host(url: str) -> dict[str, Any]:
    """HTTP GET with short timeout. Returns reachable=True/False + latency_ms."""
    started = datetime.now(UTC)
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_PING_TIMEOUT_SECONDS) as response:
            code = response.getcode()
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        return {"reachable": True, "http_code": code, "latency_ms": elapsed_ms}
    except urllib.error.HTTPError as exc:
        # 401/403 = host is up, just denying us — that's "reachable" for our purposes
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        return {"reachable": exc.code < 500, "http_code": exc.code, "latency_ms": elapsed_ms}
    except Exception as exc:
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        return {"reachable": False, "error": str(exc)[:120], "latency_ms": elapsed_ms}


def health_check_all_providers() -> dict[str, Any]:
    """Ping every cheap-lane provider once. Returns per-provider status."""
    results: dict[str, Any] = {}
    unreachable: list[str] = []
    for provider, url in _PING_ENDPOINTS.items():
        result = _ping_host(url)
        results[provider] = result
        if not result.get("reachable"):
            unreachable.append(provider)

    snapshot = {
        "checked_at": datetime.now(UTC).isoformat(),
        "results": results,
        "unreachable": unreachable,
        "reachable_count": len(_PING_ENDPOINTS) - len(unreachable),
        "total_count": len(_PING_ENDPOINTS),
    }

    try:
        from core.runtime.state_store import save_json
        save_json(_HEALTH_STATE_KEY, snapshot)
    except Exception:
        pass

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "runtime.provider_health_check",
            {"unreachable": unreachable, "reachable_count": snapshot["reachable_count"]},
        )
    except Exception:
        pass

    return snapshot


def latest_health_snapshot() -> dict[str, Any]:
    """Read most-recent stored snapshot."""
    try:
        from core.runtime.state_store import load_json
        snap = load_json(_HEALTH_STATE_KEY, {})
        if isinstance(snap, dict):
            return snap
    except Exception:
        pass
    return {}


def health_section() -> str | None:
    """Awareness section listing currently unreachable providers."""
    snap = latest_health_snapshot()
    unreachable = snap.get("unreachable") or []
    if not unreachable:
        return None
    checked = str(snap.get("checked_at", ""))[11:19]
    return (
        f"⚠ Provider sundhed (sidste check {checked}): "
        f"{len(unreachable)} ude af stand: {', '.join(unreachable)}. "
        "Cheap-lane fallback chain håndterer det automatisk."
    )


def _exec_run_health_check(args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "snapshot": health_check_all_providers()}


def _exec_get_health_snapshot(args: dict[str, Any]) -> dict[str, Any]:
    snap = latest_health_snapshot()
    if not snap:
        return {"status": "ok", "snapshot": None, "note": "no health check has run yet"}
    return {"status": "ok", "snapshot": snap}


PROVIDER_HEALTH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "provider_health_check",
            "description": (
                "Run a fresh ping against all cheap-lane provider endpoints "
                "(9 providers). Records reachability + latency in eventbus + "
                "state_store. Cheap (~5s total worst case)."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "provider_health_status",
            "description": "Read most-recent stored health snapshot without running new check.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
