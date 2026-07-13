"""WS2: daemon-lanens DeepSeek-kald skal skrive en costs-række via record_cost.

quality_daemon_llm_call rammer inner_enrichment-lanen (deepseek-v4-flash) direkte
via _execute_openai_compatible_chat. Før WS2 skrev den KUN et egress-observe og
INGEN costs-række → regnskabs-hul. record_cost egress-observer selv internt, så vi
må IKKE beholde det separate egress-kald (dobbelt-tælling).
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.daemon_llm as dl


def _fake_result():
    return {
        "text": "hej verden",
        "tool_calls": [],
        "input_tokens": 100,
        "output_tokens": 40,
        "cache_hit_tokens": 30,
        "cache_miss_tokens": 70,
        "cost_usd": 0.0,
    }


def _fake_target():
    return {
        "active": True,
        "credentials_ready": True,
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "auth_profile": "default",
        "base_url": "https://api.deepseek.com",
    }


def test_quality_daemon_deepseek_routes_through_record_cost():
    with patch(
        "core.runtime.provider_router.resolve_provider_router_target",
        return_value=_fake_target(),
    ), patch(
        "core.services.cheap_provider_runtime._execute_openai_compatible_chat",
        return_value=_fake_result(),
    ), patch(
        "core.services.cheap_provider_runtime._OPENAI_COMPATIBLE_PROVIDERS",
        {"deepseek"},
    ), patch(
        "core.costing.ledger.record_cost",
    ) as mock_rc, patch(
        "core.services.central_llm_egress.observe",
    ) as mock_egress, patch(
        "core.runtime.db.daemon_output_log_insert",
    ):
        out = dl.quality_daemon_llm_call("prompt here", daemon_name="")

    assert out == "hej verden"

    # Præcis én costs-række skrives for dette DeepSeek-kald.
    assert mock_rc.call_count == 1
    kwargs = mock_rc.call_args.kwargs
    assert kwargs["provider"] == "deepseek"
    assert kwargs["model"] == "deepseek-v4-flash"
    assert kwargs["input_tokens"] == 100
    assert kwargs["output_tokens"] == 40
    assert kwargs["cache_hit_tokens"] == 30
    assert kwargs["cache_miss_tokens"] == 70
    assert kwargs.get("lane")  # en lane-label er sat

    # Det separate egress-observe må IKKE længere fyre på denne sti —
    # record_cost egress-observer internt (ellers dobbelt-tælling).
    assert mock_egress.call_count == 0
