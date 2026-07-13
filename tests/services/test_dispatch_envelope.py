from core.services.dispatch_envelope import build_envelope, validate_envelope


def test_all_seven_keys():
    env = build_envelope(status="completed", tokens_in=10, tokens_out=5, cost_usd=0.0,
                         duration_ms=42, tool_calls=2, result="ok")
    assert set(env.keys()) == {"status", "tokens_in", "tokens_out", "cost_usd", "duration_ms", "tool_calls", "result"}
    assert env["status"] == "completed" and env["tokens_out"] == 5 and env["duration_ms"] == 42


def test_types_coerced():
    env = build_envelope(status="failed", tokens_in="10", tokens_out="0", cost_usd="0.5",
                         duration_ms="100", tool_calls="0", result=None)
    assert isinstance(env["tokens_in"], int) and isinstance(env["cost_usd"], float)
    assert isinstance(env["duration_ms"], int) and isinstance(env["tool_calls"], int)


def test_plausibility_flags_completed_with_zero_output():
    env = build_envelope(status="completed", tokens_in=100, tokens_out=0, cost_usd=0.0,
                         duration_ms=10, tool_calls=0, result="")
    warns = validate_envelope(env)
    assert any("tokens_out" in w for w in warns)  # completed but produced nothing -> suspicious


def test_plausibility_clean_on_good_envelope():
    env = build_envelope(status="completed", tokens_in=100, tokens_out=50, cost_usd=0.0,
                         duration_ms=10, tool_calls=1, result="x")
    assert validate_envelope(env) == []


def test_unknown_status_flagged():
    env = build_envelope(status="weird", tokens_in=1, tokens_out=1, cost_usd=0.0,
                         duration_ms=1, tool_calls=0, result="x")
    assert any("status" in w for w in validate_envelope(env))
