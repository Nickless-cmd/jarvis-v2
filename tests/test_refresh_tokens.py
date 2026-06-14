"""Tests for refresh-token-rotation (§22.6)."""
from __future__ import annotations


def test_issue_and_verify(isolated_runtime) -> None:
    from core.runtime.refresh_tokens import issue_refresh_token, verify_refresh_token
    tok = issue_refresh_token("d-mikkel")
    assert isinstance(tok, str) and len(tok) > 20
    assert verify_refresh_token(tok) == "d-mikkel"
    assert verify_refresh_token("forkert") is None


def test_rotation_invalidates_old(isolated_runtime) -> None:
    from core.runtime.refresh_tokens import issue_refresh_token, rotate_refresh_token, verify_refresh_token
    tok = issue_refresh_token("d-mikkel")
    res = rotate_refresh_token(tok)
    assert res["ok"] is True
    assert res["access_token"] and res["refresh_token"]
    assert verify_refresh_token(tok) is None                      # gammel ugyldig
    assert verify_refresh_token(res["refresh_token"]) == "d-mikkel"  # ny gyldig


def test_rotate_invalid_token(isolated_runtime) -> None:
    from core.runtime.refresh_tokens import rotate_refresh_token
    assert rotate_refresh_token("nonsens")["ok"] is False


def test_revoke_all(isolated_runtime) -> None:
    from core.runtime.refresh_tokens import issue_refresh_token, revoke_all, verify_refresh_token
    t1 = issue_refresh_token("d-mikkel")
    t2 = issue_refresh_token("d-mikkel")
    n = revoke_all("d-mikkel")
    assert n >= 2
    assert verify_refresh_token(t1) is None and verify_refresh_token(t2) is None


def test_access_token_is_short_lived(isolated_runtime) -> None:
    # §22.6: access-token skal udløbe ~30 min, ikke 30 dage.
    import jwt as _jwt
    from core.runtime.refresh_tokens import issue_refresh_token, rotate_refresh_token
    from core.runtime.jarvisx_auth import verify_token
    res = rotate_refresh_token(issue_refresh_token("d-mikkel"))
    claims = verify_token(res["access_token"])
    ttl = claims["exp"] - claims["iat"]
    assert 1700 <= ttl <= 1900     # ~1800s (30 min)
