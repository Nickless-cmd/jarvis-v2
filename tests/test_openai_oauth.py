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
