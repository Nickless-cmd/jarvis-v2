"""Tests for self_review_unified — Review-cluster central-routing."""
from __future__ import annotations

import inspect


def test_module_imports():
    import core.services.self_review_unified as sru
    assert hasattr(sru, "run_self_review")
    assert hasattr(sru, "maybe_run_self_review")


def test_review_routed_through_central_gate():
    # Review-cluster: selv-review-vurderingen skal ruttes gennem central().decide(gate_review)
    import core.services.self_review_unified as sru
    src = inspect.getsource(sru.run_self_review)
    assert "gate_review import review_gate" in src
    assert 'cluster="review"' in src
    # høj-risiko (RED) flagges som incident
    assert "record_central_incident" in src
