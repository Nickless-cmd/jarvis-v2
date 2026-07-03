"""Tests for core/services/world_model_auto_extraction.py — egress-fri central-binding + rate-limit.

Verificér (§5a, 3. jul): auto-extraction er nu synlig for Centralen (observe ved succes),
rate-limit bounder cost, og JSON-parsing er robust. Hermetisk — state-store i hukommelsen,
INGEN netværk/LLM.
"""
from __future__ import annotations

import pytest

from core.services import world_model_auto_extraction as wm


@pytest.fixture(autouse=True)
def _mem_state(monkeypatch):
    store: dict[str, object] = {}
    monkeypatch.setattr(wm, "load_json", lambda k, default=None: store.get(k, default))
    monkeypatch.setattr(wm, "save_json", lambda k, v: store.__setitem__(k, v))
    yield store


def test_extract_json_handles_fence_and_braces():
    assert '"is_prediction"' in wm._extract_json('```json\n{"is_prediction": true}\n```')
    assert wm._extract_json('preamble {"a": 1} tail') == '{"a": 1}'


def test_rate_limit_blocks_after_max(_mem_state):
    for _ in range(wm._MAX_AUTO_EXTRACTIONS_PER_DAY):
        assert wm._under_rate_limit() is True
        wm._increment_rate()
    assert wm._under_rate_limit() is False


def test_extract_skipped_when_rate_limited(monkeypatch):
    # Over dagsgrænsen → ingen cheap-lane-kald, tidligt exit.
    monkeypatch.setattr(wm, "_under_rate_limit", lambda: False)
    res = wm.auto_extract_and_record(matched_phrase="jeg tror", context_excerpt="...")
    assert res["status"] == "skipped" and res["reason"] == "daily-limit"


def test_extract_records_and_observes_on_success(monkeypatch, _mem_state):
    # Mock cheap-lane til en gyldig prediction + fang record + observe.
    monkeypatch.setattr(wm, "_under_rate_limit", lambda: True)
    import core.services.cheap_provider_runtime as cpr
    monkeypatch.setattr(cpr, "execute_public_safe_cheap_lane",
                        lambda *, message: {"text": '{"is_prediction": true, "subject": "deploy", '
                                                    '"expectation": "virker", "confidence": "high"}'})
    import core.services.world_model_signal_tracking as wmst
    monkeypatch.setattr(wmst, "record_runtime_world_model_prediction",
                        lambda **kw: {"prediction_id": "p1"})
    observed = {}
    import core.services.central_private_observe as cpo
    monkeypatch.setattr(cpo, "record_private",
                        lambda cluster, nerve, **kw: observed.update({"nerve": nerve, **kw}) or True)
    res = wm.auto_extract_and_record(matched_phrase="jeg tror", context_excerpt="vi deployer")
    assert res["status"] == "ok" and res["subject"] == "deploy"
    assert observed.get("nerve") == "world_model_extraction"  # egress-fri binding fyrede
