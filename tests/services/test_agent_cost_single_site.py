"""A4b: cost is logged at exactly ONE site per model call — the execution
chokepoint — with the correct lane threaded in as a parameter.

Before this change agent spend was double-counted: the dispatch seam in
``agent_runtime_spawn`` logged ``record_cost(lane="agent")`` AND, when the
dispatch fell back to the cheap-lane pool, ``execute_cheap_lane_via_pool``
logged a second ``record_cost(lane="cheap")`` for the same tokens.
Meanwhile the ``role-primary-direct`` success path logged nothing (a hole).

The fix threads a ``lane`` param through ``execute_with_role_or_fallback``
and ``execute_cheap_lane_via_pool`` so cost logs exactly once at the
execution site, attributed to the caller's lane. The seam logs are removed.

These tests assert the four paths each log exactly once with the right lane:
  * role-primary-direct  → lane threaded (agent)
  * pool fallback        → lane threaded (agent), NOT twice
  * council caller       → lane="council"
  * daemon default       → lane="cheap" (backward compat)
"""
from __future__ import annotations

from unittest.mock import patch

import core.costing.ledger as ledger
import core.services.cheap_provider_runtime_selection as selection
from core.services.non_visible_lane_execution import execute_with_role_or_fallback


def _capture(target_module):
    calls: list[dict] = []
    return calls, patch.object(
        target_module, "record_cost", lambda **kw: calls.append(kw)
    )


def test_primary_direct_logs_once_lane_agent():
    """Primary succeeds → record_cost fires exactly once with the threaded
    lane (agent). Closes the former primary-direct hole."""
    primary_result = {
        "text": "primary OK", "input_tokens": 100, "output_tokens": 50,
        "cost_usd": 0.0,
    }
    calls, cost_patch = _capture(ledger)
    with patch(
        "core.services.cheap_provider_runtime._execute_provider_chat",
        return_value=primary_result,
    ), cost_patch:
        result = execute_with_role_or_fallback(
            message="ping", provider="ollamafreeapi", model="gpt-oss:20b",
            lane="agent",
        )

    assert result["execution_mode"] == "role-primary-direct"
    assert len(calls) == 1, f"expected exactly one record_cost, got {len(calls)}"
    assert calls[0]["lane"] == "agent"
    assert calls[0]["provider"] == "ollamafreeapi"
    assert calls[0]["input_tokens"] == 100
    assert calls[0]["output_tokens"] == 50


def test_pool_fallback_logs_once_not_twice():
    """Empty provider → straight to the pool, which logs exactly once with
    the threaded lane (agent). Proves the agent→pool double-count is gone
    (no seam log, no second pool log)."""
    calls, cost_patch = _capture(selection)
    with patch.object(
        selection, "select_cheap_lane_target",
        lambda **kw: {
            "active": True, "provider": "deepseek", "model": "deepseek-chat",
            "auth_profile": "", "base_url": "",
        },
    ), patch.object(
        selection, "_execute_provider_chat",
        lambda **kw: {"text": "ok", "output_tokens": 50, "cost_usd": 0.0},
    ), patch.object(
        selection, "record_cheap_provider_invocation", lambda **kw: None,
    ), patch.object(
        selection, "_record_provider_success", lambda **kw: None,
    ), cost_patch:
        execute_with_role_or_fallback(
            message="ping", provider="", model="", lane="agent",
        )

    assert len(calls) == 1, f"expected exactly one record_cost, got {len(calls)}"
    assert calls[0]["lane"] == "agent"


def test_council_lane():
    """A council call site passes lane="council" → record_cost lane="council"."""
    primary_result = {
        "text": "position", "input_tokens": 40, "output_tokens": 20,
        "cost_usd": 0.0,
    }
    calls, cost_patch = _capture(ledger)
    with patch(
        "core.services.cheap_provider_runtime._execute_provider_chat",
        return_value=primary_result,
    ), cost_patch:
        execute_with_role_or_fallback(
            message="deliberate", provider="ollamafreeapi", model="gpt-oss:20b",
            lane="council",
        )

    assert len(calls) == 1, f"expected exactly one record_cost, got {len(calls)}"
    assert calls[0]["lane"] == "council"


def test_daemon_default_lane_cheap():
    """Calling execute_cheap_lane_via_pool directly with no lane still logs
    lane="cheap" — backward compat for daemons."""
    calls, cost_patch = _capture(selection)
    with patch.object(
        selection, "select_cheap_lane_target",
        lambda **kw: {
            "active": True, "provider": "deepseek", "model": "deepseek-chat",
            "auth_profile": "", "base_url": "",
        },
    ), patch.object(
        selection, "_execute_provider_chat",
        lambda **kw: {"text": "ok", "output_tokens": 50, "cost_usd": 0.0},
    ), patch.object(
        selection, "record_cheap_provider_invocation", lambda **kw: None,
    ), patch.object(
        selection, "_record_provider_success", lambda **kw: None,
    ), cost_patch:
        selection.execute_cheap_lane_via_pool(message="daemon job")

    assert len(calls) == 1, f"expected exactly one record_cost, got {len(calls)}"
    assert calls[0]["lane"] == "cheap"
