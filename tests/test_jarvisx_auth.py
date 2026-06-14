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
