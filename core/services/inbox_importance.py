"""Shared importance and delivery policy for Jarvis' inbox surfaces."""
from __future__ import annotations

from typing import Final


LEVELS: Final[tuple[str, ...]] = ("low", "normal", "high", "critical")
RANK: Final[dict[str, int]] = {name: index for index, name in enumerate(LEVELS)}


def normalize_importance(value: object, *, default: str = "normal") -> str:
    text = str(value or "").strip().lower()
    return text if text in RANK else default


def is_round_worthy(value: object) -> bool:
    return RANK[normalize_importance(value)] >= RANK["high"]


def prompt_order(item: dict[str, object]) -> tuple[int, int, str]:
    """Unseen always wins, then importance, then durable creation order.

    This prevents an old open high-priority item from starving every unseen
    normal item forever while still ranking unseen critical work first.
    """
    unseen = 0 if not str(item.get("vist_at") or "").strip() else 1
    rank = -RANK[normalize_importance(item.get("importance"))]
    return unseen, rank, str(item.get("created_at") or item.get("id") or "")


__all__ = ["LEVELS", "RANK", "is_round_worthy", "normalize_importance", "prompt_order"]
