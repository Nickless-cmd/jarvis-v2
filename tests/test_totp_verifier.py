from __future__ import annotations

import pytest

# Fast seed til determinisme (base32, 16 bytes værd).
SEED = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
T0 = 1_700_000_000  # fast unix-tid


def test_valid_code_passes() -> None:
    from core.services.totp_verifier import generate_code, verify

    code = generate_code(SEED, timestamp=T0)
    assert verify(code, seed=SEED, now=T0) is True


def test_wrong_code_rejected() -> None:
    from core.services.totp_verifier import verify

    assert verify("000000", seed=SEED, now=T0) is False
    assert verify("999999", seed=SEED, now=T0) is False


def test_pm_one_window_accepted() -> None:
    from core.services.totp_verifier import generate_code, verify

    prev = generate_code(SEED, timestamp=T0 - 30)
    nxt = generate_code(SEED, timestamp=T0 + 30)
    assert verify(prev, seed=SEED, now=T0, valid_window=1) is True
    assert verify(nxt, seed=SEED, now=T0, valid_window=1) is True


def test_expired_code_rejected() -> None:
    from core.services.totp_verifier import generate_code, verify

    # To vinduer væk → uden for ±1
    old = generate_code(SEED, timestamp=T0 - 90)
    assert verify(old, seed=SEED, now=T0, valid_window=1) is False


def test_no_seed_blocks_everything() -> None:
    from core.services.totp_verifier import generate_code, verify

    code = generate_code(SEED, timestamp=T0)
    assert verify(code, seed="", now=T0) is False
    assert verify(code, seed=None, now=T0) is False


def test_generate_seed_is_base32_and_unique() -> None:
    import base64

    from core.services.totp_verifier import generate_seed

    s1 = generate_seed()
    s2 = generate_seed()
    assert s1 != s2
    # Skal kunne base32-dekodes (padding tilføjes ved behov)
    pad = "=" * (-len(s1) % 8)
    assert base64.b32decode(s1 + pad)


def test_revoke_returns_new_seed_old_code_fails() -> None:
    from core.services.totp_verifier import generate_code, revoke, verify

    new_seed = revoke(SEED)
    assert new_seed != SEED
    old_code = generate_code(SEED, timestamp=T0)
    # Gammel kode virker ikke mod ny nøgle
    assert verify(old_code, seed=new_seed, now=T0) is False


def test_rate_limit_three_per_five_min() -> None:
    from core.services.totp_verifier import record_attempt

    sid = "sess-rate-1"
    assert record_attempt(sid, now=T0) is True
    assert record_attempt(sid, now=T0 + 1) is True
    assert record_attempt(sid, now=T0 + 2) is True
    # 4. forsøg inden for 5 min → blokeret
    assert record_attempt(sid, now=T0 + 3) is False
    # Efter vinduet (>300s) → tilladt igen
    assert record_attempt(sid, now=T0 + 400) is True


def test_rate_limit_is_per_session() -> None:
    from core.services.totp_verifier import record_attempt

    assert record_attempt("sess-A", now=T0) is True
    assert record_attempt("sess-A", now=T0 + 1) is True
    assert record_attempt("sess-A", now=T0 + 2) is True
    assert record_attempt("sess-A", now=T0 + 3) is False
    # Anden session er upåvirket
    assert record_attempt("sess-B", now=T0 + 3) is True
