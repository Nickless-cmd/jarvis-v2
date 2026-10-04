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


# ── En ULÆSELIG runtime.json er ikke det samme som en TOM ────────────────────


def test_en_ULAESELIG_runtime_json_maa_ikke_overskrives(tmp_path, monkeypatch) -> None:
    """`_read_secret` skriver HELE runtime.json tilbage — og ved en korrupt fil er
    det læste dict TOMT. Så genereres en ny secret, og filen erstattes af én nøgle.

    Målt 4/10-2026: runtime.json bærer 163 nøgler (alle API-nøgler). Ét u-parsbart
    tegn — fx en afbrudt skrivning — ville slette dem alle sammen i det stille.

    En fil der FINDES men ikke kan læses er ikke en fil der ikke findes. Den
    første må ikke skrives over: nøglerne er stadig i den, og nogen kan måske
    redde dem. Den anden har intet at tabe.
    """
    monkeypatch.delenv("JARVISX_AUTH_SECRET", raising=False)
    fil = tmp_path / "runtime.json"
    monkeypatch.setattr("core.runtime.jarvisx_auth.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.jarvisx_auth._SETTINGS_FILE", fil)

    korrupt = '{"agnes_api_key": "hemmelig", "app_name": "jarvis", "trailing": '  # pragma: allowlist secret
    fil.write_text(korrupt, encoding="utf-8")

    from core.runtime import jarvisx_auth as ja

    ja._read_secret()

    assert fil.read_text(encoding="utf-8") == korrupt, (
        "en ulæselig runtime.json blev overskrevet af secret-genereringen — "
        "konfigurationen er tabt"
    )


def test_en_MANGLENDE_runtime_json_oprettes_med_secret(tmp_path, monkeypatch) -> None:
    """Modprøven: findes filen slet ikke, er der intet at tabe — så må den oprettes.

    Uden denne kunne rettelsen gøre enhver skrivning umulig og stadig være grøn.
    """
    import json

    monkeypatch.delenv("JARVISX_AUTH_SECRET", raising=False)
    fil = tmp_path / "runtime.json"
    monkeypatch.setattr("core.runtime.jarvisx_auth.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.jarvisx_auth._SETTINGS_FILE", fil)

    from core.runtime import jarvisx_auth as ja

    s = ja._read_secret()

    assert len(s) >= 32
    assert json.loads(fil.read_text(encoding="utf-8"))["jarvisx_auth_secret"] == s


def test_en_ULAESELIG_runtime_json_slaar_ikke_auth_fra(tmp_path, monkeypatch) -> None:
    """En fil vi ikke kan læse er ikke et svar på om auth er slået til.

    `auth_required()` faldt tilbage til `False` når `_load_settings()` gav `{}`
    — og `{}` er også hvad en KORRUPT fil giver. Så ét u-parsbart tegn slog
    stille auth fra: API'et ville acceptere `X-JarvisX-User`-headere uden
    verifikation, hvilket er præcis det modulet er skrevet for at forhindre.

    Fail-closed er det sikre svar: vi kan ikke bekræfte nogen, så vi afviser.
    """
    monkeypatch.delenv("JARVISX_AUTH_REQUIRED", raising=False)
    fil = tmp_path / "runtime.json"
    monkeypatch.setattr("core.runtime.jarvisx_auth.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.jarvisx_auth._SETTINGS_FILE", fil)
    fil.write_text('{"jarvisx_auth_required": true, "trailing": ', encoding="utf-8")

    from core.runtime.jarvisx_auth import auth_required

    assert auth_required() is True


def test_en_MANGLENDE_runtime_json_slaar_ikke_auth_til(tmp_path, monkeypatch) -> None:
    """Modprøven: en fil der slet ikke findes er det dokumenterede dev-default.

    Uden denne kunne rettelsen gøre enhver manglende fil til «auth påkrævet»
    og låse en frisk installation ude.
    """
    monkeypatch.delenv("JARVISX_AUTH_REQUIRED", raising=False)
    fil = tmp_path / "findes-ikke.json"
    monkeypatch.setattr("core.runtime.jarvisx_auth.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.jarvisx_auth._SETTINGS_FILE", fil)

    from core.runtime.jarvisx_auth import auth_required

    assert auth_required() is False


def test_en_GYLDIG_men_forkert_formet_json_er_ogsaa_ulaeselig(tmp_path, monkeypatch) -> None:
    """`[1, 2, 3]` er gyldig JSON og ikke et settings-dokument.

    Uden skelnen ville `data.get(...)` kaste AttributeError — eller, værre,
    `_read_secret` ville skrive en liste tilbage med én nøgle i.
    """
    monkeypatch.delenv("JARVISX_AUTH_SECRET", raising=False)
    fil = tmp_path / "runtime.json"
    monkeypatch.setattr("core.runtime.jarvisx_auth.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.jarvisx_auth._SETTINGS_FILE", fil)
    fil.write_text("[1, 2, 3]", encoding="utf-8")

    from core.runtime import jarvisx_auth as ja

    s = ja._read_secret()

    assert len(s) >= 32
    assert fil.read_text(encoding="utf-8") == "[1, 2, 3]"
