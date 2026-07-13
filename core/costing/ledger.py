from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


def record_cost(
    *,
    lane: str,
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    cache_hit_tokens: int = 0,
    cache_miss_tokens: int = 0,
) -> None:
    """Insert a row into the costs ledger.

    2026-06-09: cache_hit_tokens + cache_miss_tokens added so DeepSeek
    prompt-cache utilization can be measured historically. Older call
    sites that don't pass them default to 0 (no cache info known).

    2026-07-13: DeepSeeks dødende aliaser (deepseek-chat / deepseek-reasoner,
    deadline 2026-07-24) rewrites til v4-flash på wire-laget. record_cost er
    regnskabs-chokepointet, så vi normaliserer LABELEN her ét sted → costs
    afspejler det ærlige wire-navn i stedet for aliaset, uanset call-site.
    """
    if provider == "deepseek" and model in ("deepseek-chat", "deepseek-reasoner"):
        model = "deepseek-v4-flash"
    # WS2 (13. jul): DeepSeek returnerer tokens men IKKE pris → cost_usd lander som 0.
    # Beregn den fra pris-tabellen ved skrivning når kalderen ikke gav en ægte pris.
    if float(cost_usd) <= 0.0:
        try:
            from core.services.llm_pricing import compute_cost_usd
            cost_usd = compute_cost_usd(
                provider, model,
                cache_hit_tokens=cache_hit_tokens, cache_miss_tokens=cache_miss_tokens,
                output_tokens=output_tokens, input_tokens=input_tokens,
            )
        except Exception:
            pass
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO costs (
                lane, provider, model, input_tokens, output_tokens, cost_usd,
                cache_hit_tokens, cache_miss_tokens, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lane,
                provider,
                model,
                int(input_tokens),
                int(output_tokens),
                float(cost_usd),
                int(cache_hit_tokens),
                int(cache_miss_tokens),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    # ── SAMLET LLM-EGRESS-OBSERVATION (Bjørn 4. jul) ────────────────────────────
    # record_cost er regnskabs-chokepointet for visible/primary/cheap. Rapportér
    # HVERT af dem til det samlede egress-billede (nerve cost/llm_egress) med Bölge-3
    # cheap-eligibility. Daemon-lanen + direkte-urlopen-sites rapporterer separat.
    try:
        from core.services.central_llm_egress import observe as _egress_observe
        _egress_observe(
            lane=lane, provider=provider, model=model,
            purpose=("visible" if str(lane) in ("visible", "primary") else "internal"),
            input_tokens=int(input_tokens), output_tokens=int(output_tokens),
            cost_usd=float(cost_usd), autonomous=(str(lane) not in ("visible", "primary")),
            source="record_cost")
    except Exception:
        pass


def telemetry_summary() -> dict[str, int | float]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS cost_rows,
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(cost_usd), 0) AS total_cost_usd
            FROM costs
            """
        ).fetchone()
    return {
        "cost_rows": int(row["cost_rows"]),
        "input_tokens": int(row["input_tokens"]),
        "output_tokens": int(row["output_tokens"]),
        "total_cost_usd": float(row["total_cost_usd"]),
    }


def recent_costs(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, lane, provider, model, input_tokens, output_tokens, cost_usd, created_at
            FROM costs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "input_tokens": int(row["input_tokens"]),
            "output_tokens": int(row["output_tokens"]),
            "cost_usd": float(row["cost_usd"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


# ── D5: Cost optimization utilities ──────────────────────────────────


def daily_cost_summary() -> list[dict[str, Any]]:
    """Cost per day for the last 30 days, broken down by lane."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                SUBSTR(created_at, 1, 10) AS day,
                lane,
                COUNT(*) AS calls,
                SUM(input_tokens + output_tokens) AS total_tokens,
                ROUND(SUM(cost_usd), 6) AS total_cost
            FROM costs
            WHERE created_at >= DATE('now', '-30 days')
            GROUP BY day, lane
            ORDER BY day DESC, lane
            """
        ).fetchall()
    return [
        {
            "day": row["day"],
            "lane": row["lane"],
            "calls": int(row["calls"]),
            "total_tokens": int(row["total_tokens"]),
            "total_cost": float(row["total_cost"]),
        }
        for row in rows
    ]


def weekly_cost_summary() -> list[dict[str, Any]]:
    """Cost per ISO week for all time."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                STRFTIME('%Y-W%W', created_at) AS week,
                lane,
                COUNT(*) AS calls,
                SUM(input_tokens + output_tokens) AS total_tokens,
                ROUND(SUM(cost_usd), 6) AS total_cost
            FROM costs
            GROUP BY week, lane
            ORDER BY week DESC, lane
            """
        ).fetchall()
    return [
        {
            "week": row["week"],
            "lane": row["lane"],
            "calls": int(row["calls"]),
            "total_tokens": int(row["total_tokens"]),
            "total_cost": float(row["total_cost"]),
        }
        for row in rows
    ]


def today_cost() -> float:
    """Total cost in USD for today (UTC)."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd), 0) AS total
            FROM costs
            WHERE DATE(created_at) = DATE('now')
            """
        ).fetchone()
    return float(row["total"])


def this_week_cost() -> float:
    """Total cost in USD for this ISO week."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd), 0) AS total
            FROM costs
            WHERE STRFTIME('%Y-W%W', created_at) = STRFTIME('%Y-W%W', 'now')
            """
        ).fetchone()
    return float(row["total"])


def estimate_savings_if_cheap(*, days: int = 7) -> dict[str, object]:
    """Estimate how much would be saved by routing primary-lane calls to cheap lane.

    Returns dict with estimated savings, calls affected, and token volume.
    """
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                COUNT(*) AS calls,
                SUM(input_tokens + output_tokens) AS total_tokens,
                ROUND(SUM(cost_usd), 6) AS total_cost
            FROM costs
            WHERE lane = 'primary'
              AND created_at >= DATE('now', ?)
            """,
            (f"-{days} days",),
        ).fetchall()
    row = rows[0]
    # 2026-06-09: defend against NULL aggregates when no primary rows exist
    # (SUM(NULL) returns NULL, not 0). Previously crashed on fresh DBs.
    calls = int(row["calls"] or 0)
    total_tokens = int(row["total_tokens"] or 0)
    total_cost = float(row["total_cost"] or 0.0)
    return {
        "period_days": days,
        "primary_calls": calls,
        "primary_tokens": total_tokens,
        "primary_cost": total_cost,
        "estimated_cheap_cost": total_cost * 0.02,  # cheap lane is ~98% cheaper
        "potential_savings": round(total_cost * 0.98, 6),
    }
