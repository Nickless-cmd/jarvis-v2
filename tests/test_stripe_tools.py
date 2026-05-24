"""Tests for stripe_tools — focus on the optional-dependency contract.

2026-05-24 (Claude, after Codex audit): the stripe SDK is an optional
dependency. The module must import cleanly in environments without it,
and every _exec_* function must return an error dict (never crash) when
stripe isn't available.
"""
from unittest.mock import patch

import core.tools.stripe_tools as st


def test_module_exposes_availability_flag():
    """Public flag lets callers (or tests) check whether stripe loaded."""
    assert hasattr(st, "_STRIPE_AVAILABLE")
    assert isinstance(st._STRIPE_AVAILABLE, bool)


def test_unavailable_response_shape():
    """The shared error response is consistent and self-describing."""
    resp = st._stripe_unavailable_response()
    assert resp["status"] == "error"
    assert "stripe Python package not installed" in resp["error"]


def test_exec_balance_returns_error_when_unavailable():
    with patch.object(st, "_STRIPE_AVAILABLE", False):
        result = st._exec_stripe_balance({})
    assert result["status"] == "error"
    assert "stripe Python package not installed" in result["error"]


def test_exec_transactions_returns_error_when_unavailable():
    with patch.object(st, "_STRIPE_AVAILABLE", False):
        result = st._exec_stripe_transactions({})
    assert result["status"] == "error"
    assert "not installed" in result["error"]


def test_exec_payouts_returns_error_when_unavailable():
    with patch.object(st, "_STRIPE_AVAILABLE", False):
        result = st._exec_stripe_payouts({})
    assert result["status"] == "error"
    assert "not installed" in result["error"]


def test_exec_create_issuing_card_returns_error_when_unavailable():
    with patch.object(st, "_STRIPE_AVAILABLE", False):
        result = st._exec_stripe_create_issuing_card({"holder_name": "x"})
    assert result["status"] == "error"
    assert "not installed" in result["error"]


def test_init_stripe_returns_none_when_unavailable():
    """Guard at init-level so callers' existing 'if not mode' branches
    handle the missing-SDK case (legacy callers used that branch for
    'no API key' — both should fail gracefully)."""
    with patch.object(st, "_STRIPE_AVAILABLE", False):
        assert st._init_stripe() is None
