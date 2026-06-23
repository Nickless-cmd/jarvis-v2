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
# 2026-06-13: ollamafreeapi fjernet fra ping-rotationen — provideren er død
# (sidste succes ~14. maj; runtime-state viste 'Failed to connect / connection
# timed out / 503 server busy' — IKKE DNS NXDOMAIN, jf. Jarvis' kommentar). De
# 10 døde model-entries er også fjernet fra provider_router.json. Relevance-
# referencen i runtime.json er nu en inert forældreløs.
_PING_ENDPOINTS: dict[str, str] = {
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

    # B7: provider-helbred synlig i Centralen (degraderede providers var kun i en JSON-fil).
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "provider_health",
                           "reachable": snapshot["reachable_count"],
                           "total": snapshot["total_count"], "unreachable": unreachable})
    except Exception:
        pass

    return snapshot


_PREV_MODELS_KEY = "provider_health:model_counts"
_LATENCY_WARN_MS = 8000


def _cheap_dry_providers() -> list[str]:
    """Providers i cheap-lane-cooldown (tør/quota-blokeret) — fra runtime-state. Self-safe.
    Det er DENNE tilstand der frøs alle daemons i 53t da DeepSeek løb tør (Jarvis-spec)."""
    try:
        from core.runtime.db import list_cheap_provider_runtime_states
        now = datetime.now(UTC)
        dry: list[str] = []
        for s in (list_cheap_provider_runtime_states(lane="cheap") or []):
            cu = str(s.get("cooldown_until") or "").strip()
            if cu:
                try:
                    if datetime.fromisoformat(cu) > now:
                        dry.append(str(s.get("provider") or ""))
                except Exception:
                    pass
        return [d for d in dry if d]
    except Exception:
        return []


def _model_drift() -> list[dict[str, Any]]:
    """Model-drift: en provider der FØR havde modeller men nu har 0 (model udfaset/omdøbt — den
    risiko der har deaktiveret providers). Henter model-lister via list_provider_models, sammen-
    ligner med sidste-set antal i shared_cache. Self-safe → []."""
    drift: list[dict[str, Any]] = []
    try:
        from core.services.cheap_provider_runtime import list_provider_models
        from core.services import shared_cache
        prev = shared_cache.get(_PREV_MODELS_KEY)
        prev = prev if isinstance(prev, dict) else {}
        cur: dict[str, int] = {}
        for provider in _PING_ENDPOINTS:
            try:
                r = list_provider_models(provider=provider) or {}
                models = r.get("models") if isinstance(r.get("models"), list) else []
                status = str(r.get("status") or "").lower()
            except Exception:
                continue
            n = len(models)
            cur[provider] = n
            before = int(prev.get(provider) or 0)
            if before > 0 and n == 0 and status != "error":
                drift.append({"provider": provider, "had": before, "now": 0})
        if cur:
            merged = {**prev, **cur}
            shared_cache.set(_PREV_MODELS_KEY, merged, ttl_seconds=7 * 24 * 3600)
    except Exception:
        pass
    return drift


_PROACTIVE_CODE = "proactive_health"        # mærker cooldowns VI satte (så vi kun rydder vores egne)
_PROACTIVE_COOLDOWN_S = 360                 # 6 min — lige forbi næste 5-min-check (self-korrigerer)


def _spread_load_proactively(reports: dict[str, dict], unreachable: list[str]) -> int:
    """Daemon-load-spredning (Jarvis-spec): sæt PROAKTIVT en kort cooldown på nede providers, så
    cheap-lane-pool'en (der allerede roterer på cooldown) skipper dem FØR en daemon rammer fejlen
    — i stedet for at alle 50 daemons fryser på en tør primær. Ved recovery ryddes KUN vores egen
    proaktive cooldown (ægte quota-cooldowns røres ikke). Self-safe → 0."""
    changed = 0
    try:
        from datetime import timedelta
        from core.runtime.db import (
            get_cheap_provider_runtime_state,
            upsert_cheap_provider_runtime_state,
        )
        now = datetime.now(UTC)
        for provider in reports:
            st = get_cheap_provider_runtime_state(provider=provider) or {}
            cur_cd = str(st.get("cooldown_until") or "").strip()
            cur_code = str(st.get("last_error_code") or "")
            if provider in unreachable:
                # sæt kun proaktiv cooldown hvis der IKKE allerede er en (ægte) cooldown
                if not cur_cd:
                    upsert_cheap_provider_runtime_state(
                        provider=provider, lane="cheap", status="unreachable",
                        cooldown_until=(now + timedelta(seconds=_PROACTIVE_COOLDOWN_S)).isoformat(),
                        last_error_code=_PROACTIVE_CODE,
                        last_error_message="proaktiv health-cooldown: ping fejlede → rut udenom",
                    )
                    changed += 1
            else:
                # genoprettet → ryd KUN hvis det var VORES proaktive cooldown
                if cur_cd and cur_code == _PROACTIVE_CODE:
                    upsert_cheap_provider_runtime_state(
                        provider=provider, lane="cheap", status="ok",
                        cooldown_until=None, last_error_code="",
                        last_error_message="", last_success_at=now.isoformat(),
                    )
                    changed += 1
    except Exception:
        pass
    return changed


def observe_and_flag() -> dict[str, Any]:
    """Kadence-entry (Jarvis-spec 2026-06-23): ping + model-drift + cheap-dry → observe + FLAG
    (nede/degraderet/tør/model-drift) + auto-resolve genoprettede. Bygger på config_drift-mekanik.
    ALDRIG destruktiv — retter ikke config selv. Self-safe."""
    snap = health_check_all_providers()  # eksisterende ping + observe
    results = snap.get("results") or {}
    unreachable = list(snap.get("unreachable") or [])
    degraded = [p for p, r in results.items()
                if isinstance(r, dict) and r.get("reachable") and int(r.get("latency_ms") or 0) > _LATENCY_WARN_MS]
    dry = _cheap_dry_providers()
    drift = _model_drift()
    spread = _spread_load_proactively(results, unreachable)

    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "provider_health",
                           "unreachable": unreachable, "degraded": degraded,
                           "dry_cheap": dry, "model_drift": [d["provider"] for d in drift],
                           "proactive_cooldowns": spread})
    except Exception:
        pass

    # ── flag + auto-resolve (config_drift-mønster) ──────────────────────
    try:
        from core.runtime.db_central_incidents import (
            has_unresolved_message, record_central_incident, resolve_central_incidents,
        )
        for p in unreachable:
            msg = f"provider {p} unreachable — proaktiv ping fejlede (før et brugervendt kald)"
            if not has_unresolved_message(cluster="system", nerve="provider_health", message=msg):
                record_central_incident(cluster="system", nerve="provider_health",
                                        kind="provider_down", severity="error", message=msg)
        if not unreachable:
            resolve_central_incidents(cluster="system", nerve="provider_health")
        for d in drift:
            msg = (f"model-drift: provider {d['provider']} havde {d['had']} modeller, nu 0 "
                   f"— model muligvis udfaset/omdøbt; tjek runtime-config")
            if not has_unresolved_message(cluster="system", nerve="provider_health", message=msg):
                record_central_incident(cluster="system", nerve="provider_health",
                                        kind="model_drift", severity="error", message=msg)
    except Exception:
        pass

    return {"status": "ok", "checked": snap.get("total_count"),
            "unreachable": len(unreachable), "degraded": len(degraded),
            "dry_cheap": len(dry), "model_drift": len(drift),
            "proactive_cooldowns": spread}


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
    """Awareness section listing currently unreachable providers.

    2026-05-22 (Claude): dropped the `(check HH:MM:SS)` timestamp suffix.
    It was unique per build and broke DeepSeek's prompt cache at exactly
    the boundary where this section landed in the prompt. The model
    doesn't need the wall-clock time of the check — only the result.
    Time Pin gives the model wall time globally.
    """
    snap = latest_health_snapshot()
    unreachable = snap.get("unreachable") or []
    if not unreachable:
        return None
    return (
        f"Provider health: "
        f"{len(unreachable)} unreachable ({', '.join(unreachable)}). "
        "Cheap-lane fallback chain håndterer routing."
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
