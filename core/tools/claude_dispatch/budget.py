from __future__ import annotations

from datetime import datetime, timezone

from core.runtime.db import connect

MAX_DISPATCHES_PER_HOUR = 5
MAX_TOKENS_PER_HOUR = 250_000


class BudgetExceeded(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _hour_bucket(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H")


class BudgetTracker:
    def check_and_reserve(self) -> None:
        bucket = _hour_bucket(_now())
        with connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO claude_dispatch_budget (hour_bucket, dispatch_count, tokens_used) VALUES (?, 0, 0)",
                (bucket,),
            )
            row = conn.execute(
                "SELECT dispatch_count, tokens_used FROM claude_dispatch_budget WHERE hour_bucket=?",
                (bucket,),
            ).fetchone()
            count, tokens = int(row["dispatch_count"]), int(row["tokens_used"])
            if count >= MAX_DISPATCHES_PER_HOUR:
                raise BudgetExceeded(
                    f"max {MAX_DISPATCHES_PER_HOUR} dispatches/hour reached"
                )
            if tokens >= MAX_TOKENS_PER_HOUR:
                raise BudgetExceeded(
                    f"max {MAX_TOKENS_PER_HOUR} tokens/hour reached"
                )
            conn.execute(
                "UPDATE claude_dispatch_budget SET dispatch_count = dispatch_count + 1 WHERE hour_bucket=?",
                (bucket,),
            )
            conn.commit()

    def record_usage(self, tokens: int) -> None:
        bucket = _hour_bucket(_now())
        with connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO claude_dispatch_budget (hour_bucket, dispatch_count, tokens_used) VALUES (?, 0, 0)",
                (bucket,),
            )
            conn.execute(
                "UPDATE claude_dispatch_budget SET tokens_used = tokens_used + ? WHERE hour_bucket=?",
                (int(tokens), bucket),
            )
            conn.commit()

    def current_dispatch_count(self) -> int:
        bucket = _hour_bucket(_now())
        with connect() as conn:
            row = conn.execute(
                "SELECT dispatch_count FROM claude_dispatch_budget WHERE hour_bucket=?",
                (bucket,),
            ).fetchone()
        return int(row["dispatch_count"]) if row else 0
