import pytest
from core.services import counterfactual_triggers as ct


def test_cf_key_is_deterministic():
    a = ct.cf_key("default", "self_review_outcome.created", "rev_abc")
    b = ct.cf_key("default", "self_review_outcome.created", "rev_abc")
    assert a == b


def test_cf_key_differs_per_workspace():
    a = ct.cf_key("default", "conflict.detected", "conflict_1")
    b = ct.cf_key("mikkel", "conflict.detected", "conflict_1")
    assert a != b


def test_cf_key_differs_per_event_type():
    a = ct.cf_key("default", "self_review_outcome.created", "rev_1")
    b = ct.cf_key("default", "conflict.detected", "rev_1")
    assert a != b


def test_key_self_review_uses_review_id():
    payload = {"review_id": "rev_xyz", "run_id": "visible-1"}
    assert ct._key_self_review(payload) == "rev_xyz"


def test_key_self_review_falls_back_to_run_id():
    payload = {"run_id": "visible-1"}
    assert ct._key_self_review(payload) == "visible-1"


def test_key_self_review_returns_empty_when_both_missing():
    assert ct._key_self_review({}) == ""


def test_key_conflict_prefers_conflict_id():
    assert ct._key_conflict({"conflict_id": "c1", "run_id": "r1"}) == "c1"


def test_key_conflict_falls_back_to_run_id():
    assert ct._key_conflict({"run_id": "r1"}) == "r1"


def test_key_decision_uses_decision_id():
    assert ct._key_decision({"decision_id": "dec_xxx"}) == "dec_xxx"


def test_key_review_uses_review_id():
    assert ct._key_review({"review_id": "rev_xxx"}) == "rev_xxx"


def test_fetch_recent_triggers_returns_trigger_events(monkeypatch):
    """When events match, return TriggerEvent objects."""
    import json
    sample_rows = [
        {
            "id": 1001,
            "kind": "self_review_outcome.created",
            "payload_json": json.dumps({
                "review_id": "rev_abc",
                "run_id": "visible-xyz",
                "summary": "I missed something",
            }),
            "created_at": "2026-05-07T12:30:00+00:00",
        },
        {
            "id": 1002,
            "kind": "conflict.detected",
            "payload_json": json.dumps({
                "conflict_id": "conf-1",
                "summary": "two daemons disagreed",
            }),
            "created_at": "2026-05-07T12:35:00+00:00",
        },
    ]

    class _FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            class _R:
                def fetchall(self_inner): return [dict(r) for r in sample_rows]
            return _R()

    monkeypatch.setattr(ct, "connect", _FakeConn)
    out = ct.fetch_recent_triggers(workspace_id="default", lookback_minutes=60)
    assert len(out) == 2
    assert isinstance(out[0], ct.TriggerEvent)
    assert out[0].source_event_id == 1001
    assert out[0].event_type == "self_review_outcome.created"
    assert out[0].primary_key == "rev_abc"


def test_fetch_skips_events_with_no_primary_key(monkeypatch):
    """Events whose key extractor returns empty string get dropped."""
    import json
    sample_rows = [
        {
            "id": 2001,
            "kind": "decision_revoked",
            "payload_json": json.dumps({}),  # no decision_id, no fallback
            "created_at": "2026-05-07T12:30:00+00:00",
        },
    ]

    class _FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            class _R:
                def fetchall(self_inner): return [dict(r) for r in sample_rows]
            return _R()

    monkeypatch.setattr(ct, "connect", _FakeConn)
    out = ct.fetch_recent_triggers(workspace_id="default", lookback_minutes=60)
    assert out == []
