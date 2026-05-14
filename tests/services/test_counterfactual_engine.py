import pytest
from core.services import counterfactual_engine as ce
from core.services.counterfactual_triggers import TriggerEvent


def _trigger(**overrides):
    base = dict(
        source_event_id=1,
        workspace_id="default",
        event_type="self_review_outcome.created",
        primary_key="rev_abc",
        summary="something went wrong",
        payload={"review_id": "rev_abc", "summary": "something went wrong"},
        created_at="2026-05-07T12:00:00+00:00",
    )
    base.update(overrides)
    return TriggerEvent(**base)


def test_run_returns_summary_dict(monkeypatch):
    """run() always returns a summary, never raises."""
    monkeypatch.setattr(ce, "fetch_recent_triggers", lambda **kwargs: [])
    out = ce.run(workspace_id="default")
    assert isinstance(out, dict)
    assert out["workspace_id"] == "default"
    assert "triggers_fetched" in out
    assert "elapsed_ms" in out


def test_run_with_no_triggers_is_clean_noop(monkeypatch):
    monkeypatch.setattr(ce, "fetch_recent_triggers", lambda **kwargs: [])
    out = ce.run(workspace_id="default")
    assert out["triggers_fetched"] == 0
    assert out["triggers_unique"] == 0
    assert out["counterfactuals_generated"] == 0
    assert out["llm_generation_failures"] == 0


def test_run_dry_run_stores_placeholder_values(monkeypatch):
    """Phase 1 default: dry_run=True → what_if='TODO', llm_confidence=0.0."""
    triggers = [_trigger()]
    monkeypatch.setattr(ce, "fetch_recent_triggers", lambda **kwargs: triggers)
    monkeypatch.setattr(ce, "_dedup_filter", lambda triggers: triggers)

    captured = []
    monkeypatch.setattr(
        ce, "_store_counterfactual",
        lambda **kwargs: captured.append(kwargs) or None,
    )
    monkeypatch.setattr(ce, "_publish_event", lambda **kwargs: None)

    out = ce.run(workspace_id="default", dry_run=True)
    assert out["counterfactuals_generated"] == 1
    assert len(captured) == 1
    cf = captured[0]
    assert cf["what_if"] == "TODO"
    assert cf["llm_confidence"] == 0.0
    # apophenia_score is now data-dependent (Phase 3, 2026-05-14) — was
    # a fixed 1.0 in the stub-era. The invariant that still holds for
    # a TODO placeholder is that final_confidence stays 0.0 regardless
    # of apophenia's verdict, because llm_confidence is 0.
    assert 0.0 <= cf["apophenia_score"] <= 1.0
    assert cf["final_confidence"] == 0.0
    assert cf["status"] == "generated"


def test_run_skipped_when_killswitch_off(monkeypatch):
    class FakeS:
        counterfactual_engine_enabled = False
        counterfactual_engine_lookback_minutes = 60
        counterfactual_engine_promotion_threshold = 0.6
    monkeypatch.setattr(ce, "RuntimeSettings", lambda: FakeS())
    out = ce.run(workspace_id="default")
    assert out["skipped"] is True
    assert out["skipped_reason"] == "killswitch-off"


def test_run_includes_trigger_breakdown(monkeypatch):
    """Phase 1 must report per-event-type counts in summary."""
    triggers = [
        _trigger(event_type="self_review_outcome.created", primary_key="r1"),
        _trigger(event_type="self_review_outcome.created", primary_key="r2"),
        _trigger(event_type="conflict.detected", primary_key="c1"),
    ]
    monkeypatch.setattr(ce, "fetch_recent_triggers", lambda **kwargs: triggers)
    monkeypatch.setattr(ce, "_dedup_filter", lambda triggers: triggers)
    monkeypatch.setattr(ce, "_store_counterfactual", lambda **kwargs: None)
    monkeypatch.setattr(ce, "_publish_event", lambda **kwargs: None)

    out = ce.run(workspace_id="default", dry_run=True)
    bd = out["trigger_breakdown"]
    assert bd["self_review_outcome.created"] == 2
    assert bd["conflict.detected"] == 1


def test_dedup_filter_removes_already_stored(monkeypatch):
    """First-pass dedup: cf_keys already in DB are filtered out."""
    triggers = [
        _trigger(event_type="self_review_outcome.created", primary_key="rev_a"),
        _trigger(event_type="self_review_outcome.created", primary_key="rev_b"),
    ]

    # Mock that "rev_a" is already stored
    from core.services.counterfactual_triggers import cf_key
    existing_key = cf_key("default", "self_review_outcome.created", "rev_a")

    class _FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            class _R:
                def fetchall(self_inner): return [{"cf_key": existing_key}]
            return _R()

    monkeypatch.setattr(ce, "connect", _FakeConn)
    out = ce._dedup_filter(triggers)
    assert len(out) == 1
    assert out[0].primary_key == "rev_b"


def test_run_handles_fetch_exception_gracefully(monkeypatch):
    """If fetch_recent_triggers raises, return error summary, not exception."""
    def boom(**kwargs):
        raise RuntimeError("DB unreachable")
    monkeypatch.setattr(ce, "fetch_recent_triggers", boom)
    out = ce.run(workspace_id="default")
    assert out["triggers_fetched"] == 0
    assert "error" in out or out.get("counterfactuals_generated") == 0
