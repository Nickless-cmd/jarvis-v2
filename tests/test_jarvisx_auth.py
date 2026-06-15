from __future__ import annotations

import pytest


@pytest.fixture
def _isolated_auth(tmp_path, monkeypatch):
    """Isolér auth-secret + override-store til tmp."""
    monkeypatch.setenv("JARVISX_AUTH_SECRET", "x" * 48)
    monkeypatch.setattr("core.runtime.jarvisx_auth.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.jarvisx_auth._SETTINGS_FILE", tmp_path / "runtime.json")
    yield tmp_path


def test_token_carries_app_id(_isolated_auth) -> None:
    from core.runtime.jarvisx_auth import issue_token, verify_token

    res = issue_token(user_id="bjorn", role="owner", app_id="app-uuid-1")
    claims = verify_token(res["token"])
    assert claims["app_id"] == "app-uuid-1"


def test_token_without_app_id_defaults_empty(_isolated_auth) -> None:
    from core.runtime.jarvisx_auth import issue_token, verify_token

    res = issue_token(user_id="bjorn", role="owner")
    claims = verify_token(res["token"])
    assert claims.get("app_id", "") == ""


def test_bound_owner_session_needs_no_override(_isolated_auth) -> None:
    from core.runtime.jarvisx_auth import issue_token, session_needs_override, verify_token

    claims = verify_token(issue_token(user_id="bjorn", role="owner", app_id="owner-app")["token"])
    # App-ID matcher den registrerede owner-app → ingen TOTP
    assert session_needs_override(claims, owner_app_id="owner-app", session_id="s1") is False


def test_mismatched_app_id_needs_override(_isolated_auth) -> None:
    from core.runtime.jarvisx_auth import issue_token, session_needs_override, verify_token

    claims = verify_token(issue_token(user_id="bjorn", role="owner", app_id="other-app")["token"])
    # App-ID matcher ikke → TOTP krævet for owner-autoritet
    assert session_needs_override(claims, owner_app_id="owner-app", session_id="s1") is True


def test_active_override_satisfies_foreign_session(_isolated_auth, isolated_runtime) -> None:
    from core.runtime.jarvisx_auth import issue_token, session_needs_override, verify_token
    from core.services.override_store import grant

    # Fremmed session (member-token, fx Mikkels Discord)
    claims = verify_token(issue_token(user_id="mikkel", role="member", app_id="mikkel-app")["token"])
    assert session_needs_override(claims, owner_app_id="owner-app", session_id="s9", now=1000) is True
    # Efter gyldig TOTP-override → ikke længere krævet
    grant("s9", now=1000)
    assert session_needs_override(claims, owner_app_id="owner-app", session_id="s9", now=1010) is False


def test_revoked_api_key_jti_is_rejected(isolated_runtime) -> None:
    """En API-nøgle (token m. jti) der revokeres afvises live af verify_token."""
    import pytest
    from core.runtime.jarvisx_auth import issue_token, verify_token, AuthError
    from core.identity import user_db

    u = user_db.add_user(email="rv@b.dk", name="RV", password="x", role="owner", tier="owner")
    jti = user_db.get_user(u["user_id"])["api_key_jti"]
    # Frisk token m. samme jti verificerer fint før revocation
    minted = issue_token(user_id=u["user_id"], role="owner", extra_claims={"jti": jti})
    assert verify_token(minted["token"])["sub"] == u["user_id"]
    # Revokér → samme token afvises nu
    assert user_db.revoke_api_key(u["user_id"]) is True
    with pytest.raises(AuthError):
        verify_token(minted["token"])


def test_token_without_jti_unaffected(isolated_runtime) -> None:
    """Almindelige tokens uden jti påvirkes ikke af revocation-tjekket."""
    from core.runtime.jarvisx_auth import issue_token, verify_token
    minted = issue_token(user_id="plain", role="member")
    assert verify_token(minted["token"])["sub"] == "plain"
