from __future__ import annotations

import json


def test_build_openai_launch_intent_stores_pkce_material(isolated_runtime) -> None:
    openai_oauth = isolated_runtime.openai_oauth
    auth_profiles = isolated_runtime.auth_profiles

    openai_oauth.save_openai_oauth_config(
        client_id="client_test_123",
        authorize_url="https://auth.example.test/authorize",
        token_url="https://auth.example.test/token",
        scopes="openid offline_access",
        audience="https://api.openai.com/v1",
        redirect_base_url="http://127.0.0.1:1455",
        callback_path="/auth/callback",
    )

    intent = openai_oauth.build_openai_launch_intent(profile="default")
    credentials = auth_profiles.get_provider_credentials(profile="default", provider="openai-codex")

    assert intent["launch_url"].startswith("https://auth.example.test/authorize?")
    assert credentials is not None
    assert credentials["oauth_state"] == "launch-intent-created"
    assert credentials["oauth_pkce_code_verifier"]
    assert credentials["oauth_expected_state"]
    assert credentials["oauth_redirect_uri"].endswith("/auth/callback")


def test_openai_refresh_reuses_refresh_token_and_updates_expiry(
    isolated_runtime,
    monkeypatch,
) -> None:
    openai_oauth = isolated_runtime.openai_oauth
    auth_profiles = isolated_runtime.auth_profiles

    openai_oauth.save_openai_oauth_config(
        client_id="client_test_123",
        authorize_url="https://auth.example.test/authorize",
        token_url="https://auth.example.test/token",
        scopes="openid offline_access",
        audience="https://api.openai.com/v1",
        redirect_base_url="http://127.0.0.1:1455",
        callback_path="/auth/callback",
    )
    auth_profiles.save_provider_credentials(
        profile="default",
        provider="openai-codex",
        credentials={
            "oauth_state": "real-stored",
            "access_token": "expired_token",
            "refresh_token": "refresh_123",
            "expires_at": "2000-01-01T00:00:00+00:00",
            "real_oauth": True,
        },
    )

    def _post_openai_token_request(*, token_url: str, payload: dict[str, str]) -> dict[str, object]:
        assert token_url == "https://auth.example.test/token"
        assert payload["grant_type"] == "refresh_token"
        assert payload["refresh_token"] == "refresh_123"
        return {
            "access_token": "fresh_access_token",
            "refresh_token": "refresh_123",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    monkeypatch.setattr(
        openai_oauth,
        "_post_openai_token_request",
        _post_openai_token_request,
    )

    token = openai_oauth.get_openai_bearer_token(profile="default")
    credentials = auth_profiles.get_provider_credentials(profile="default", provider="openai-codex")

    assert token == "fresh_access_token"
    assert credentials is not None
    assert credentials["access_token"] == "fresh_access_token"
    assert credentials["oauth_state"] == "real-stored"


# ── Udfalds-cache (6/9-2026) ─────────────────────────────────────────────

def test_negativt_svar_huskes_saa_vi_ikke_hamrer(monkeypatch):
    """Et readiness-tjek udfoerte en NETVAERKS-fornyelse.

    Kandidat-listen spoerger én gang pr. udbyder, saa ét daemon-kald gav 22
    forsoeg mod auth.openai.com i traek — alle med samme svar. Maalt paa
    CT105 foer fixet: 22 tjek = 22 kald.
    """
    from core.auth import openai_oauth as oo
    oo._glem_token_cache()
    forsoeg = {"n": 0}

    def _fejler(*, profile):
        forsoeg["n"] += 1
        raise RuntimeError("no refresh_token")

    monkeypatch.setattr(oo, "get_provider_credentials", lambda **k: {})
    monkeypatch.setattr(oo, "refresh_openai_access_token", _fejler)

    for _ in range(22):
        try:
            oo.get_openai_bearer_token(profile="p", auto_reimport=False)
        except Exception:
            pass
    assert forsoeg["n"] == 1, f"forsøgte {forsoeg['n']} gange — skulle huske det første nej"


def test_positivt_svar_huskes_ogsaa(monkeypatch):
    from core.auth import openai_oauth as oo
    oo._glem_token_cache()
    forsoeg = {"n": 0}

    def _virker(*, profile):
        forsoeg["n"] += 1
        return {"access_token": "tok-123"}

    monkeypatch.setattr(oo, "get_provider_credentials", lambda **k: {})
    monkeypatch.setattr(oo, "refresh_openai_access_token", _virker)

    assert oo.get_openai_bearer_token(profile="p") == "tok-123"
    assert oo.get_openai_bearer_token(profile="p") == "tok-123"
    assert forsoeg["n"] == 1


def test_cachen_er_pr_profil(monkeypatch):
    from core.auth import openai_oauth as oo
    oo._glem_token_cache()
    monkeypatch.setattr(oo, "get_provider_credentials", lambda **k: {})
    monkeypatch.setattr(oo, "refresh_openai_access_token",
                        lambda *, profile: {"access_token": f"tok-{profile}"})
    assert oo.get_openai_bearer_token(profile="a") == "tok-a"
    assert oo.get_openai_bearer_token(profile="b") == "tok-b"


def test_cachen_udloeber(monkeypatch):
    """En genoprettet legitimation skal opdages af sig selv."""
    from core.auth import openai_oauth as oo
    oo._glem_token_cache()
    forsoeg = {"n": 0}

    def _fejler(*, profile):
        forsoeg["n"] += 1
        raise RuntimeError("nej")

    monkeypatch.setattr(oo, "get_provider_credentials", lambda **k: {})
    monkeypatch.setattr(oo, "refresh_openai_access_token", _fejler)
    monkeypatch.setattr(oo, "_TOKEN_CACHE_FEJL_TTL_S", 0.0)
    for _ in range(3):
        try:
            oo.get_openai_bearer_token(profile="p", auto_reimport=False)
        except Exception:
            pass
    assert forsoeg["n"] == 3, "med TTL=0 skal hvert kald prøve igen"


def test_ny_token_rydder_et_gammelt_nej(monkeypatch):
    """Ellers ville en vellykket import være usynlig i op til et minut."""
    from core.auth import openai_oauth as oo
    oo._token_cache["p"] = (0.0, None)
    monkeypatch.setattr(oo, "get_provider_credentials", lambda **k: {"refresh_token": "r"})
    monkeypatch.setattr(oo, "load_openai_oauth_config", lambda: {"client_id": "c"})
    monkeypatch.setattr(oo, "_post_openai_token_request", lambda **k: {"access_token": "ny"})
    try:
        oo.refresh_openai_access_token(profile="p")
    except Exception:
        pass
    assert "p" not in oo._token_cache
