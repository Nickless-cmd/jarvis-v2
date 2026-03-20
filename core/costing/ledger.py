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
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO costs (
                lane, provider, model, input_tokens, output_tokens, cost_usd, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lane,
                provider,
                model,
                int(input_tokens),
                int(output_tokens),
                float(cost_usd),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()


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
