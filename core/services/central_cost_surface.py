"""Central cost-surface (WS3, 13. jul 2026) — gør det nyfixede cost-regnskab synligt.

Læser `costs`-aggregat (today / 7d / 30d): total $, tokens ind/ud, cache-hit%,
fordelt på provider/model/lane. Plus DeepSeek-saldo (live API, cachet 5 min,
fejl-tolerant → None). Owner-only surface; serves via /central/cost + `jc cost`.

Efter WS2 er DeepSeek fuldt sporet; andre providers' cost fanges først med WS8
(deres rækker vises men med cost_usd=0 indtil da).
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import UTC, datetime, timedelta

from core.runtime.db import connect

_WINDOWS = {"today": None, "7d": 7, "30d": 30}

# ── DeepSeek-saldo cache (5 min) ────────────────────────────────────────────
_BAL_CACHE: dict[str, object] = {"ts": 0.0, "value": None}
_BAL_TTL_S = 300.0


def _window_threshold(window: str) -> str:
    """ISO8601-tærskel for et vindue (samme format som costs.created_at → lex-sammenlignelig)."""
    now = datetime.now(UTC)
    if window == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now - timedelta(days=_WINDOWS[window])
    return start.isoformat()


def _agg_for_window(conn, window: str, provider: str | None) -> dict:
    thr = _window_threshold(window)
    where = "created_at >= ?"
    params: list = [thr]
    if provider:
        where += " AND provider = ?"
        params.append(provider)
    row = conn.execute(
        f"""SELECT COUNT(*) AS calls,
                   COALESCE(SUM(input_tokens),0) AS inp,
                   COALESCE(SUM(output_tokens),0) AS outp,
                   COALESCE(SUM(cache_hit_tokens),0) AS chit,
                   COALESCE(SUM(cache_miss_tokens),0) AS cmiss,
                   COALESCE(SUM(cost_usd),0.0) AS cost
            FROM costs WHERE {where}""",
        params,
    ).fetchone()
    chit, cmiss = int(row["chit"]), int(row["cmiss"])
    denom = chit + cmiss
    return {
        "calls": int(row["calls"]),
        "input_tokens": int(row["inp"]),
        "output_tokens": int(row["outp"]),
        "cache_hit_tokens": chit,
        "cache_miss_tokens": cmiss,
        "cache_hit_pct": round(100.0 * chit / denom, 1) if denom else 0.0,
        "cost_usd": round(float(row["cost"]), 4),
    }


def _breakdown(conn, window: str, provider: str | None) -> list[dict]:
    thr = _window_threshold(window)
    where = "created_at >= ?"
    params: list = [thr]
    if provider:
        where += " AND provider = ?"
        params.append(provider)
    rows = conn.execute(
        f"""SELECT provider, model, COALESCE(lane,'') AS lane,
                   COUNT(*) AS calls,
                   COALESCE(SUM(input_tokens),0) AS inp,
                   COALESCE(SUM(output_tokens),0) AS outp,
                   COALESCE(SUM(cache_hit_tokens),0) AS chit,
                   COALESCE(SUM(cache_miss_tokens),0) AS cmiss,
                   COALESCE(SUM(cost_usd),0.0) AS cost
            FROM costs WHERE {where}
            GROUP BY provider, model, lane
            ORDER BY cost DESC, calls DESC""",
        params,
    ).fetchall()
    out = []
    for r in rows:
        chit, cmiss = int(r["chit"]), int(r["cmiss"])
        denom = chit + cmiss
        out.append({
            "provider": str(r["provider"] or ""),
            "model": str(r["model"] or ""),
            "lane": str(r["lane"] or ""),
            "calls": int(r["calls"]),
            "input_tokens": int(r["inp"]),
            "output_tokens": int(r["outp"]),
            "cache_hit_pct": round(100.0 * chit / denom, 1) if denom else 0.0,
            "cost_usd": round(float(r["cost"]), 4),
        })
    return out


def _deepseek_balance() -> str | None:
    """Live DeepSeek-saldo (USD, streng), cachet 5 min. Fejl/offline → None."""
    now = time.time()
    if now - float(_BAL_CACHE["ts"]) < _BAL_TTL_S:
        return _BAL_CACHE["value"]  # type: ignore[return-value]
    val: str | None = None
    try:
        cfg = json.load(open(os.path.expanduser("~/.jarvis-v2/config/runtime.json")))

        def _find(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if "deepseek" in k.lower() and isinstance(v, str) and v.startswith("sk-"):
                        return v
                    r = _find(v)
                    if r:
                        return r
            return None

        key = _find(cfg)
        if key:
            req = urllib.request.Request(
                "https://api.deepseek.com/user/balance",
                headers={"Authorization": "Bearer " + key},
            )
            d = json.load(urllib.request.urlopen(req, timeout=10))
            infos = d.get("balance_infos") or []
            if infos:
                val = str(infos[0].get("total_balance"))
    except Exception:
        val = None
    _BAL_CACHE["ts"] = now
    _BAL_CACHE["value"] = val
    return val


def build_cost_surface(*, window: str = "today", provider: str | None = None) -> dict:
    """Cost-aggregat til /central/cost + `jc cost`.

    window: hvilket vindue breakdown'et vises for (today/7d/30d). Totaler for alle
    tre vinduer returneres altid. provider: valgfrit filter (fx 'deepseek').
    """
    if window not in _WINDOWS:
        window = "today"
    with connect() as conn:
        windows = {w: _agg_for_window(conn, w, provider) for w in _WINDOWS}
        breakdown = _breakdown(conn, window, provider)
    try:
        balance = _deepseek_balance()
    except Exception:
        balance = None
    return {
        "windows": windows,
        "breakdown": breakdown,
        "breakdown_window": window,
        "provider_filter": provider,
        "deepseek_balance_usd": balance,
        "note": "WS2: kun DeepSeek fuldt prissat; andre providers cost_usd=0 indtil WS8.",
        "generated_at": datetime.now(UTC).isoformat(),
    }
