"""Candidate health calculations stay stable across the selection seam."""
from __future__ import annotations

import json

from core.services.weighted_slot_health import (
    adaptive_snapshot, decode_state_metadata,
)


def test_adaptive_priority_reflects_failures_and_latency():
    state = {"metadata_json": json.dumps({
        "success_count": 1, "failure_count": 1, "avg_latency_ms": 1200,
    })}

    result = adaptive_snapshot(
        {"provider": "groq", "model": "shared", "priority": 20},
        state=state, get_state=lambda **_kw: None,
        decode_metadata=decode_state_metadata,
    )

    assert result["success_ratio"] == 0.5
    assert result["adaptive_penalty"] == 6
    assert result["effective_priority"] == 26


def test_malformed_runtime_metadata_is_ignored():
    assert decode_state_metadata({"metadata_json": "[not-json"}) == {}
