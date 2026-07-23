"""Central-ejet unified router (spec §5.5). ÉT beslutnings-punkt for alle lanes.

Invariant: route() returnerer ALTID et target eller den garanterede bund — rejser
ALDRIG. Kandidat-rangering samles her; lanes' lokale hot-path-failover bevares.
Bygges shadow→live via central_switches ('central_route_live')."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


import re as _re

# Static capability estimate so the AGENT lane prefers strong reasoners
# (deepseek / 70B / qwen3-32b / gpt-oss-120b) over weak 8B chat models for
# research/reasoning work. Root cause (Bjørn 2026-07-23): explore/research agents
# routed to nvidia-nim llama-3.1-8b and HALLUCINATED — the pool had far stronger
# free models sitting idle, but ranking was priority-only (no quality signal).
# Heuristic on the model name — no network, no state. Only consulted for lane="agent".
_STRONG_FAMILIES = (
    "deepseek", "qwen3", "qwen2.5-coder", "qwen-coder", "glm-5", "glm-4.7",
    "minimax", "gpt-oss-120", "nemotron-3-ultra", "nemotron-3-super", "-coder",
)
_PREMIUM_NAMES = ("claude", "sonnet", "opus", "gpt-5", "gpt-4", "o4-", "o3-", "gemini-pro")
_WEAK_MARKERS = ("mini", "nano", "lite", "small", "instant", "edge", "-8b", "-7b", "-3b", "1.8b")


def _model_capability(provider: str, model: str) -> float:
    """Capability estimate in [0,1] from the model name. Higher = stronger reasoner."""
    m = (model or "").lower()
    best = 0.0
    # Param-size hints (billions): 120b+→.95, 70b→.85, 30b→.72, 12b→.55, 7b→.42, <7b→.28
    for num, unit in _re.findall(r"(\d+(?:\.\d+)?)\s*([bm])\b", m):
        try:
            b = float(num) * (0.001 if unit == "m" else 1.0)
        except ValueError:
            continue
        s = (0.95 if b >= 100 else 0.85 if b >= 60 else 0.72 if b >= 27
             else 0.55 if b >= 12 else 0.42 if b >= 7 else 0.28)
        best = max(best, s)
    if any(k in m for k in _PREMIUM_NAMES):
        best = max(best, 0.95)
    elif any(k in m for k in _STRONG_FAMILIES):
        best = max(best, 0.80)
    if best == 0.0:
        best = 0.45  # unknown → neutral
    if any(k in m for k in _WEAK_MARKERS) and best < 0.80:
        best = min(best, 0.45)  # weak marker caps non-strong models
    return best


def _rank_candidates(lane: str, task: Any, exclude: frozenset[str]) -> list[tuple[str, str]]:
    """Rangerede (provider, model) for en lane. Genbruger den eksisterende
    selection-kandidat-bygger + task_kind-semantik + proaktiv headroom (Task 8).

    task_kind-semantik SKAL matche select_cheap_lane_target (ellers router den
    fx background til BETALT deepseek i stedet for gratis proxies):
      - important  → drop public proxies (kun betalte/private, høj kvalitet)
      - background → public proxies FØRST (spar de betalte til vigtige tasks)
      - default    → ren priority-orden
    """
    from core.services.cheap_provider_runtime_selection import (
        _configured_cheap_candidates, _is_public_proxy)
    from core.services.central_route_headroom import headroom_ok, headroom_weight
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, provider_cost_class)
    kind = str((task or {}).get("kind") or "default") if isinstance(task, dict) else "default"
    # Cost-gate (Bjørn 15. jul): betalte modeller (Copilot-premium) må KUN vælges når
    # task'en eksplicit tillader det — "gratis = frit valg, betalt = rigtige opgaver".
    allow_paid = bool((task or {}).get("allow_paid")) if isinstance(task, dict) else False
    cands = _configured_cheap_candidates(include_public_proxy=(kind != "important"))
    out: list[tuple[float, str, str]] = []
    for c in cands:
        p, m = str(c.get("provider") or ""), str(c.get("model") or "")
        if not p or not m or p in exclude or not c.get("credentials_ready"):
            continue
        if not allow_paid and provider_cost_class(p) == "paid":
            continue                      # betalt kræver allow_paid (rigtig opgave)
        # Agent-lanen kalder /v1/agent/step som KUN kan openai-chat. Route aldrig til
        # inkompatible providers (gemini-native/codex/cloudflare/arko/ollamafreeapi) —
        # de ville trigge deepseek-fallback (BETALT). De hører til daemon-lanen hvor
        # balanceren håndterer deres protokoller.
        if lane == "agent" and (CHEAP_PROVIDER_DEFAULTS.get(p) or {}).get("protocol") != "openai-chat":
            continue
        if kind == "important" and _is_public_proxy(p):
            continue                      # vigtige tasks bruger ikke public proxies
        if not headroom_ok(p):            # >=95% kvote → skip proaktivt
            continue
        prio = float(c.get("priority") or 9999)
        # background: skub public proxies foran (træk 1000 fra så de vinder)
        proxy_bonus = -1000.0 if (kind == "background" and _is_public_proxy(p)) else 0.0
        rank = proxy_bonus + prio / max(headroom_weight(p), 1e-3)
        # AGENT-lanen: kvalitet FØRST (stærke reasoners før svage 8B) — priority/
        # headroom er kun tiebreaker. Andre lanes uændret (cap=0 → ren priority-orden).
        cap = _model_capability(p, m) if lane == "agent" else 0.0
        out.append((-cap, rank, p, m))
    out.sort(key=lambda x: (x[0], x[1]))
    return [(p, m) for _, _, p, m in out]


def route(*, lane: str, task: Any = None,
          exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Vælg (provider, model) for en lane. Aldrig tør."""
    try:
        ranked = _rank_candidates(lane, task, exclude)
    except Exception:
        logger.debug("central_route: kandidat-rangering fejlede", exc_info=True)
        ranked = []
    if ranked:
        p, m = ranked[0]
        return {"provider": p, "model": m, "lane": lane,
                "reason": "central-route:ranked", "is_floor": False}
    from core.services.cheap_lane_floor import floor_targets
    ft = floor_targets()
    if ft:
        p, m = ft[0]
        return {"provider": p, "model": m, "lane": lane,
                "reason": "central-route:floor", "is_floor": True}
    return {"provider": "floor", "model": "", "lane": lane,
            "reason": "central-route:degraded", "is_floor": True}


def _fetch_invocations(provider: str, since: str) -> list[tuple[str, int]]:
    """(status, latency_ms) for provider siden 'since' fra SQLite. Self-safe."""
    from core.runtime.db_core import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT status, latency_ms FROM cheap_provider_invocations "
            "WHERE provider = ? AND created_at >= ?", (provider, since)).fetchall()
    return [(str(r[0]), int(r[1] or 0)) for r in rows]


def provider_history(provider: str, hours: int = 24) -> dict[str, Any]:
    """Task 10: fejlrate, latency-p50, oppetid for en provider over N timer
    (fra cheap_provider_invocations). Query-surface til central_query."""
    empty = {"provider": provider, "hours": hours, "calls": 0,
             "error_rate": 0.0, "latency_p50_ms": 0, "uptime_pct": 100.0}
    try:
        from datetime import datetime, timedelta, UTC
        since = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
        rows = _fetch_invocations(provider, since)
    except Exception:
        return empty
    total = len(rows)
    if not total:
        return empty
    fails = sum(1 for status, _ in rows if status not in ("ok", "completed"))
    lats = sorted(lat for _, lat in rows)
    p50 = lats[len(lats) // 2]
    return {"provider": provider, "hours": hours, "calls": total,
            "error_rate": round(fails / total, 4), "latency_p50_ms": p50,
            "uptime_pct": round(100.0 * (total - fails) / total, 2)}
