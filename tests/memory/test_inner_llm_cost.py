"""WS2 (13. jul): inner-LLM-enrichment's direct-urlopen DeepSeek path must write
a costs row via record_cost (which egress-observes internally) and NOT keep a
separate egress-observe → so egress is counted exactly once.

Critically: DeepSeek's `completion_tokens` already INCLUDES reasoning_tokens
(reasoning_content is billed as output). So output_tokens == completion_tokens —
reasoning counted exactly once, never double-added.
"""
from __future__ import annotations

import json

import core.memory.inner_llm_enrichment as ile


class _FakeResp:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


def _install_fake_http(monkeypatch, response: dict) -> None:
    def _fake_urlopen(req, timeout=None):  # noqa: ARG001
        return _FakeResp(json.dumps(response).encode("utf-8"))

    monkeypatch.setattr(ile.urllib_request, "urlopen", _fake_urlopen)


def test_deepseek_call_records_cost_with_reasoning_as_output(monkeypatch):
    # DeepSeek-style usage: completion_tokens (100) ALREADY includes the
    # reasoning_tokens (40). Output must be 100, NOT 140.
    response = {
        "choices": [{"message": {"content": "en rolig indre refleksion"}}],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 100,
            "prompt_cache_hit_tokens": 30,
            "prompt_cache_miss_tokens": 90,
            "completion_tokens_details": {"reasoning_tokens": 40},
        },
    }
    _install_fake_http(monkeypatch, response)

    calls: list[dict] = []

    def _fake_record_cost(**kwargs):
        calls.append(kwargs)

    import core.costing.ledger as ledger

    monkeypatch.setattr(ledger, "record_cost", _fake_record_cost)

    # The separate egress-observe must be GONE from this path. record_cost is
    # patched (so its internal observe won't fire) → egress.observe must see 0
    # direct calls, proving the redundant site was removed.
    egress_calls: list[dict] = []

    import core.services.central_llm_egress as egress

    monkeypatch.setattr(
        egress, "observe", lambda **kw: egress_calls.append(kw)
    )

    target = {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com/v1",
        "auth_profile": "deepseek",
    }

    text = ile._call_remote_chat(
        target=target,
        system_prompt="sys",
        user_message="hej",
        timeout=5,
    )

    assert text == "en rolig indre refleksion"

    # Exactly one costs row.
    assert len(calls) == 1
    kw = calls[0]
    assert kw["lane"] == "inner"
    assert kw["provider"] == "deepseek"
    assert kw["model"] == "deepseek-v4-flash"
    assert kw["input_tokens"] == 120
    # reasoning counted ONCE inside completion_tokens — output is 100, not 140.
    assert kw["output_tokens"] == 100
    assert kw["cache_hit_tokens"] == 30
    assert kw["cache_miss_tokens"] == 90

    # No separate direct egress-observe on this path.
    assert egress_calls == []
