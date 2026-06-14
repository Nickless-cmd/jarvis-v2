from __future__ import annotations

T0 = 1_700_000_000
SEED = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


def _code(ts=T0):
    from core.services.totp_verifier import generate_code
    return generate_code(SEED, timestamp=ts)


def test_non_override_text_returns_none(isolated_runtime) -> None:
    from core.services.override_command import handle_override_command

    assert handle_override_command("hej Jarvis", session_id="s1", owner_seed=SEED, now=T0) is None


def test_valid_code_grants_override(isolated_runtime) -> None:
    from core.services.override_command import handle_override_command
    from core.services.override_store import is_active

    res = handle_override_command(f"!override {_code()}", session_id="s-valid", owner_seed=SEED, now=T0)
    assert res is not None and res["ok"] is True and res["action"] == "granted"
    assert is_active("s-valid", now=T0) is True


def test_invalid_code_rejected(isolated_runtime) -> None:
    from core.services.override_command import handle_override_command
    from core.services.override_store import is_active

    res = handle_override_command("!override 000000", session_id="s-invalid", owner_seed=SEED, now=T0)
    assert res["ok"] is False and res["reason"] == "invalid_code"
    assert is_active("s-invalid", now=T0) is False


def test_no_seed_blocks(isolated_runtime) -> None:
    from core.services.override_command import handle_override_command

    res = handle_override_command(f"!override {_code()}", session_id="s1", owner_seed="", now=T0)
    assert res["ok"] is False and res["reason"] == "no_seed"


def test_rate_limit_after_three_attempts(isolated_runtime) -> None:
    from core.services.override_command import handle_override_command

    for i in range(3):
        handle_override_command("!override 000000", session_id="s-rate", owner_seed=SEED, now=T0 + i)
    res = handle_override_command(f"!override {_code()}", session_id="s-rate", owner_seed=SEED, now=T0 + 3)
    assert res["ok"] is False and res["reason"] == "rate_limited"


def test_revoke_clears_override(isolated_runtime) -> None:
    from core.services.override_command import handle_override_command
    from core.services.override_store import grant, is_active

    grant("s-revoke", now=T0)
    res = handle_override_command("!revoke-override", session_id="s-revoke", owner_seed=SEED, now=T0)
    assert res is not None and res["action"] == "revoked"
    assert is_active("s-revoke", now=T0) is False


def test_debug_level_grant(isolated_runtime) -> None:
    from core.services.override_command import handle_override_command
    from core.services.override_store import level

    res = handle_override_command(f"!override {_code()}", session_id="s-debug", owner_seed=SEED, level="debug", now=T0)
    assert res["ok"] is True and res["level"] == "debug"
    assert level("s-debug", now=T0) == "debug"
