# tests/test_tool_result_aging.py
from core.services.visible_followup_events import ToolExchange, ToolResult
from core.services.tool_result_aging import age_tool_results, tool_result_aging_mode


def _ex(content: str) -> ToolExchange:
    return ToolExchange(
        text="t", tool_calls=[{"id": "1"}],
        results=[ToolResult(tool_call_id="1", tool_name="read_file", content=content)],
        reasoning_content="r",
    )


def _exchanges(n: int, content: str = "x" * 500) -> list[ToolExchange]:
    return [_ex(content) for _ in range(n)]


def test_weak_lane_never_ages():
    ex = _exchanges(20)
    out, m = age_tool_results(ex, mode="active", strength="weak", round_index=30)
    assert out is ex and m["changed"] is False


def test_below_round_threshold_never_ages():
    ex = _exchanges(20)
    out, m = age_tool_results(ex, mode="active", strength="strong", round_index=3)
    assert out is ex and m["changed"] is False


def test_keeps_five_most_recent_full():
    ex = _exchanges(8, content="y" * 500)
    out, m = age_tool_results(ex, mode="active", strength="strong", round_index=7)
    # last 5 untouched, first 3 cleared
    assert m["changed"] is True and m["aged_exchanges"] == 3
    for e in out[-5:]:
        assert e.results[0].content == "y" * 500
    for e in out[:3]:
        assert e.results[0].content.startswith("[tool-resultat ryddet")


def test_clear_is_deterministic():
    ex = _exchanges(8, content="z" * 500)
    out1, _ = age_tool_results(ex, mode="active", strength="strong", round_index=7)
    out2, _ = age_tool_results(_exchanges(8, content="z" * 500),
                               mode="active", strength="strong", round_index=7)
    assert out1[0].results[0].content == out2[0].results[0].content


def test_idempotent_second_pass_is_noop():
    ex = _exchanges(8, content="w" * 500)
    out1, _ = age_tool_results(ex, mode="active", strength="strong", round_index=7)
    out2, m2 = age_tool_results(out1, mode="active", strength="strong", round_index=7)
    assert out2 is out1 and m2["changed"] is False


def test_shadow_does_not_mutate_but_reports():
    ex = _exchanges(8, content="s" * 500)
    out, m = age_tool_results(ex, mode="shadow", strength="strong", round_index=7)
    assert out is ex and m["changed"] is False
    assert m["aged_exchanges"] == 3 and m["would_free_tokens"] > 0


def test_off_is_passthrough():
    ex = _exchanges(8)
    out, m = age_tool_results(ex, mode="off", strength="strong", round_index=7)
    assert out is ex and m["changed"] is False


def test_compress_only_when_deep_and_large():
    # deep round + large result + compress_fn → compressed, not cleared
    ex = _exchanges(8, content="q" * 3000)
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=12, compress_fn=lambda c: "SUMMARY")
    assert m["compressed"] == 3 and m["cleared"] == 0
    assert out[0].results[0].content == "SUMMARY"


def test_no_compress_when_shallow_even_if_large():
    ex = _exchanges(8, content="q" * 3000)
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=7, compress_fn=lambda c: "SUMMARY")
    assert m["cleared"] == 3 and m["compressed"] == 0


def test_compress_failure_falls_back_to_clear():
    ex = _exchanges(8, content="q" * 3000)
    def _boom(c):
        raise RuntimeError("llm down")
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=12, compress_fn=_boom)
    assert m["cleared"] == 3 and out[0].results[0].content.startswith("[tool-resultat ryddet")


def test_mode_helper_defaults_shadow(monkeypatch):
    monkeypatch.delenv("JARVIS_TOOL_RESULT_AGING_MODE", raising=False)
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: type("S", (), {"extra": {}})())
    assert tool_result_aging_mode() == "shadow"


def test_mode_helper_env_wins(monkeypatch):
    monkeypatch.setenv("JARVIS_TOOL_RESULT_AGING_MODE", "active")
    assert tool_result_aging_mode() == "active"


# ── Safety-valve: token-trigger makes aging STEPPED, not per-round (2026-07-17) ──

def test_trigger_tokens_gate_blocks_small_runs():
    # 8 exchanges of 500 chars ≈ 1000 tok, well under a 120k trigger → NO aging.
    # This preserves the append-only intra-run cache for the common case.
    ex = _exchanges(8, content="x" * 500)
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=7, trigger_tokens=120_000)
    assert out is ex and m["changed"] is False


def test_trigger_tokens_gate_fires_when_over_budget():
    # 8 exchanges of 80k chars = 640k chars ≈ 160k tok > 120k trigger → aging fires.
    ex = _exchanges(8, content="x" * 80_000)
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=7, trigger_tokens=120_000)
    assert m["changed"] is True and m["aged_exchanges"] == 3


def test_trigger_zero_preserves_legacy_behavior():
    # trigger_tokens=0 (default) → no token gate → ages exactly as before.
    ex = _exchanges(8, content="y" * 500)
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=7, trigger_tokens=0)
    assert m["changed"] is True and m["aged_exchanges"] == 3


def test_trigger_helper_default(monkeypatch):
    from core.services.tool_result_aging import aging_trigger_tokens
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: type("S", (), {"extra": {}})())
    assert aging_trigger_tokens() == 120_000
