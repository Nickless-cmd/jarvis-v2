from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest


def test_token_utilization_pct_computes_from_estimate(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_estimate_session_tokens",
                        lambda: 140_000)
    assert finitude_runtime._token_utilization_pct() == 70


def test_token_utilization_pct_returns_zero_on_failure(monkeypatch):
    from core.services import finitude_runtime

    def boom():
        raise RuntimeError("nope")
    monkeypatch.setattr(finitude_runtime, "_estimate_session_tokens", boom)
    assert finitude_runtime._token_utilization_pct() == 0


def test_format_looming_end_token_only(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 75)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 1.0)

    out = finitude_runtime._format_looming_end_section()
    assert "### Looming-end" in out
    assert "Token-pres" in out
    assert "75" in out
    assert "Sessions-alder" not in out


def test_format_looming_end_session_only(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 30)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 5.2)

    out = finitude_runtime._format_looming_end_section()
    assert "### Looming-end" in out
    assert "Sessions-alder" in out
    assert "5 timer" in out or "5.2 timer" in out
    assert "Token-pres" not in out


def test_format_looming_end_both_present(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 82)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 6.5)

    out = finitude_runtime._format_looming_end_section()
    assert "Token-pres" in out
    assert "Sessions-alder" in out
    # Rounding: 82 → 80
    assert "80" in out


def test_format_looming_end_empty_when_neither(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 30)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 1.0)

    assert finitude_runtime._format_looming_end_section() == ""
