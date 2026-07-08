"""Executable tests for the reasoning-interceptor's hard invariants (spec §3)."""
from __future__ import annotations

import asyncio

from core.services import reasoning_interceptor as ri
from core.services.gate_kernel import Decision


def test_async_wrapper_times_out_to_green(monkeypatch):
    """Invariant 4: a slow detector must not exceed the budget; the wrapper returns GREEN so the
    agentic loop is never blocked."""
    import time as _t
    monkeypatch.setattr(ri, "_run_detectors", lambda ctx: _t.sleep(5))
    out = asyncio.run(ri.intercept_round_async(
        run_id="r", round_num=1, reasoning_text="The DB has 4231 rows.",
        tool_calls_this_run=[], ctx={}, budget_ms=200))
    assert out.grade is Decision.GREEN


def test_no_reasoning_content_is_green(monkeypatch):
    """Invariant 6: no reasoning_content on this lane → GREEN no-op, never crash."""
    out = asyncio.run(ri.intercept_round_async(
        run_id="r", round_num=1, reasoning_text=None,  # type: ignore[arg-type]
        tool_calls_this_run=[], ctx={}, budget_ms=200))
    assert out.grade is Decision.GREEN


def test_ephemeral_injection_never_touches_base_parts():
    """Invariant 2: a correction lives in the exchange-text only, never in the _a_parts / base_parts
    buffer (which persist + the resolution-exit check read raw)."""
    from core.services.decision_signal_staging import stage_signal, compose_exchange_text
    active: dict[str, str] = {}
    stage_signal(active, "interceptor:fact_gate:r:1", "\n\n[interceptor] verify the number\n\n")
    base = ["real assistant answer"]
    composed = compose_exchange_text(base, active)
    assert base == ["real assistant answer"]              # base list untouched
    assert "real assistant answer" in composed and "[interceptor]" in composed


def test_cache_prefix_byte_invariant():
    """Invariant 1: a correction only APPENDS after the cached prefix — the prefix bytes are
    byte-identical with and without an active correction, so the prompt cache stays warm."""
    from core.services.decision_signal_staging import compose_exchange_text
    base = ["SYSTEM+TOOLS cached prefix\n\nassistant answer"]
    plain = compose_exchange_text(base, {})
    injected = compose_exchange_text(base, {"k": "\n\n[interceptor] note\n\n"})
    assert injected.startswith(plain)                     # prefix unchanged; correction only appends
