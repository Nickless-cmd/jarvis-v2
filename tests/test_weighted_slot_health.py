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


def test_provider_block_applies_to_all_models_on_one_profile(isolated_runtime, monkeypatch):
    import core.services.shared_cache as cache
    from core.services.weighted_slot_health import (
        active_account_block, clear_account_block, quota_snapshot, record_account_block,
    )

    monkeypatch.setattr(cache, "get", lambda _key: None)
    monkeypatch.setattr(cache, "set", lambda *_args, **_kw: None)
    record_account_block("chatanywhere", "account2", "provider-blocked", 0)
    import time
    assert active_account_block("chatanywhere", "account2", time.time())["reason"] == "provider-blocked"
    base = {"provider": "chatanywhere", "rpm_limit": 10, "daily_limit": 100}

    def health(model, profile):
        return quota_snapshot(
            {**base, "model": model, "auth_profile": profile},
            get_state=lambda **_kw: None, count_invocations=lambda **_kw: 0,
            decode_metadata=decode_state_metadata, cache_prefix="test-account-block:",
            cache_ttl_seconds=1, reset_hours=24,
        )

    assert health("m1", "account2")["status"] == "account-cooldown"
    assert health("m2", "account2")["blocked"] is True
    assert health("m1", "default")["blocked"] is False
    clear_account_block("chatanywhere", "account2")
    assert active_account_block("chatanywhere", "account2", time.time()) is None
    assert health("m1", "account2")["blocked"] is False


def test_tom_batch_state_udloeser_ikke_db_opslag():
    """`state={}` betyder «batch-læsningen fandt ingen række» — ikke «hent selv».

    Målt 12/10-2026: `state or get_state(...)` tvang ét SQLite-opslag pr. kandidat
    uden række, 245 gange pr. route(). Med `state is not None` springes det over.
    """
    kaldt = {"n": 0}

    def get_state(**_kw):
        kaldt["n"] += 1
        return {"metadata_json": json.dumps({"success_count": 9})}

    result = adaptive_snapshot(
        {"provider": "groq", "model": "shared", "priority": 20},
        state={}, get_state=get_state, decode_metadata=decode_state_metadata,
    )

    assert kaldt["n"] == 0, "et tomt batch-state må ikke give et DB-opslag"
    assert result["success_count"] == 0        # tom state → ingen metadata
    assert result["effective_priority"] == 20


def test_none_state_henter_som_foer():
    """Callers der IKKE sender state (None) skal stadig hente selv."""
    kaldt = {"n": 0}

    def get_state(**_kw):
        kaldt["n"] += 1
        return {"metadata_json": json.dumps({"success_count": 9})}

    result = adaptive_snapshot(
        {"provider": "groq", "model": "shared", "priority": 20},
        state=None, get_state=get_state, decode_metadata=decode_state_metadata,
    )

    assert kaldt["n"] == 1, "state=None skal hente state selv"
    assert result["success_count"] == 9
