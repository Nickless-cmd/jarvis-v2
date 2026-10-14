"""Scalar-only outcome telemetry for scoped recall."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

ALLOWED_FIELDS = frozenset({
    "path", "delivery_status", "result_count", "latency_ms", "top_score",
    "filtered_scope", "filtered_status", "source_count", "cache_hit",
})


def emit_recall_outcome(**metadata: object) -> None:
    payload = {key: metadata[key] for key in ALLOWED_FIELDS if key in metadata}
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish("memory.recall", payload)
    except Exception as exc:
        logger.debug("recall outcome emission failed: %s", exc)


__all__ = ["ALLOWED_FIELDS", "emit_recall_outcome"]
