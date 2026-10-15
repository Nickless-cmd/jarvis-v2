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
    """Live DeepSeek-saldo (USD, streng), cachet 5 min. Fejl/offline → None.

    Bagudkompatibel wrapper om `_deepseek_balance_detail()`: returnerer kun
    total_balance som før. Brug detail-varianten når granted/topped_up skal ses.
    """
    return _deepseek_balance_detail().get("total")


def _deepseek_balance_detail() -> dict:
    """Live DeepSeek-saldo opdelt: total/granted/topped_up (USD-strenge), cachet 5 min.

    DeepSeek skelner mellem `granted_balance` (gratis-credits, fx kompensation ved
    nedbrud) og `topped_up_balance` (egne indbetalinger). API'et trækker fra
    granted FØRST. Uden denne opdeling er en kompensation usynlig i vores egen
    cost-surface — man ser kun at totalen stiger. Fejl/offline → alle None.
    """
    now = time.time()
    if now - float(_BAL_CACHE["ts"]) < _BAL_TTL_S:
        return dict(_BAL_CACHE["value"] or {})  # type: ignore[arg-type]
    val: dict = {"total": None, "granted": None, "topped_up": None}
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
                info = infos[0]
                val = {
                    "total": str(info.get("total_balance")),
                    "granted": str(info.get("granted_balance")),
                    "topped_up": str(info.get("topped_up_balance")),
                }
    except Exception:
        val = {"total": None, "granted": None, "topped_up": None}
    _BAL_CACHE["ts"] = now
    _BAL_CACHE["value"] = val
    return dict(val)


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
        balance_detail = _deepseek_balance_detail()
    except Exception:
        balance_detail = {"total": None, "granted": None, "topped_up": None}
    return {
        "windows": windows,
        "breakdown": breakdown,
        "breakdown_window": window,
        "provider_filter": provider,
        "deepseek_balance_usd": balance_detail.get("total"),
        # Opdelingen er nødvendig for at en kompensation (granted) kan SES: uden
        # den ser et nedbruds-credit bare ud som en stigende total. Granted trækkes først.
        "deepseek_balance_detail": balance_detail,
        "note": "WS2: kun DeepSeek fuldt prissat; andre providers cost_usd=0 indtil WS8.",
        "generated_at": datetime.now(UTC).isoformat(),
    }
