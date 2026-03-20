from __future__ import annotations

from datetime import UTC, datetime

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
