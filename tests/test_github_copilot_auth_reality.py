from __future__ import annotations


def test_copilot_placeholder_state_is_not_credentials_ready(isolated_runtime) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router
    lanes = isolated_runtime.non_visible_lane_execution

    auth_profiles.save_provider_credentials(
        profile="copilot",
        provider="github-copilot",
        credentials={
            "placeholder": True,
            "kind": "github-copilot-oauth-placeholder",
            "oauth_state": "placeholder-stored",
            "real_oauth": False,
            "created_by": "test",
        },
    )
    provider_router.configure_provider_router_entry(
        provider="github-copilot",
        model="gpt-4.1",
        auth_mode="oauth",
        auth_profile="copilot",
        base_url="",
        api_key="",
        lane="coding",
        set_visible=False,
    )

    truth = lanes.coding_lane_execution_truth()

    assert truth["credentials_ready"] is False
    assert truth["auth_material_kind"] == "placeholder"
    assert truth["auth_status"] == "placeholder-only"
    assert truth["exchange_readiness"] == "not-applicable"
    assert truth["target"]["credentials_ready"] is False


def test_copilot_real_token_material_is_now_executable(
    isolated_runtime,
) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router
    lanes = isolated_runtime.non_visible_lane_execution

    auth_profiles.save_provider_credentials(
        profile="copilot-real",
        provider="github-copilot",
        credentials={
            "access_token": "ghu_test_token",
            "token_type": "bearer",
            "oauth_state": "real-stored",
            "token_exchange_completed": True,
            "real_oauth": True,
            "created_by": "test",
        },
    )
    provider_router.configure_provider_router_entry(
        provider="github-copilot",
        model="gpt-4.1",
        auth_mode="oauth",
        auth_profile="copilot-real",
        base_url="",
        api_key="",
        lane="coding",
        set_visible=False,
    )

    truth = lanes.coding_lane_execution_truth()

    assert truth["credentials_ready"] is True
    assert truth["auth_material_kind"] == "real"
    assert truth["exchange_readiness"] == "exchange-complete"
    assert truth["auth_status"] == "exchange-complete"
    assert truth["provider_status"] == "ready"
    assert truth["can_execute"] is True
    assert truth["status"] == "ready"
    assert truth["target"]["credentials_ready"] is True


def test_provider_router_summary_does_not_mark_copilot_scaffold_as_auth_ready(
    isolated_runtime,
) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router

    auth_profiles.save_provider_credentials(
        profile="copilot-scaffold",
        provider="github-copilot",
        credentials={
            "oauth_launch_intent": True,
            "kind": "github-copilot-oauth-launch-intent",
            "oauth_state": "launch-intent-created",
            "real_oauth": False,
            "created_by": "test",
        },
    )
    provider_router.configure_provider_router_entry(
        provider="github-copilot",
        model="gpt-4.1",
        auth_mode="oauth",
        auth_profile="copilot-scaffold",
        base_url="",
        api_key="",
        lane="coding",
        set_visible=False,
    )

    summary = provider_router.provider_router_summary()
    targets = summary["main_agent_selection"]["available_configured_targets"]
    copilot_target = next(
        item for item in targets if item["provider"] == "github-copilot"
    )

    assert copilot_target["credentials_ready"] is False
    assert copilot_target["readiness_hint"] == "auth-required"


def test_copilot_can_be_set_as_visible_provider(isolated_runtime) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router

    auth_profiles.save_provider_credentials(
        profile="copilot-visible",
        provider="github-copilot",
        credentials={
            "access_token": "ghu_test_token",
            "token_type": "bearer",
            "oauth_state": "real-stored",
            "token_exchange_completed": True,
            "real_oauth": True,
            "created_by": "test",
        },
    )
    result = provider_router.configure_provider_router_entry(
        provider="github-copilot",
        model="gpt-4.1",
        auth_mode="oauth",
        auth_profile="copilot-visible",
        base_url="",
        api_key="",
        lane="visible",
        set_visible=True,
    )

    assert result["visible_updated"] is True
    summary = provider_router.provider_router_summary()
    assert summary["router"]["visible_primary"]["provider"] == "github-copilot"
    assert summary["router"]["visible_primary"]["model"] == "gpt-4.1"


def test_copilot_device_flow_state_tracking(isolated_runtime) -> None:
    auth_profiles = isolated_runtime.auth_profiles

    auth_profiles.save_provider_credentials(
        profile="copilot-device",
        provider="github-copilot",
        credentials={
            "kind": "github-copilot-oauth-device-flow",
            "oauth_state": "device-flow-started",
            "device_code": "test-device-code-123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "verification_uri_complete": "https://github.com/login/device/code=ABCD-1234",
            "expires_in": 600,
            "interval": 5,
            "device_flow_started_at": "2024-01-01T00:00:00+00:00",
            "device_authorization_completed": False,
            "token_exchange_completed": False,
            "real_oauth": False,
            "created_by": "test",
        },
    )

    credentials = auth_profiles.get_provider_credentials(
        profile="copilot-device",
        provider="github-copilot",
    )

    assert credentials is not None
    assert credentials["oauth_state"] == "device-flow-started"
    assert credentials["device_code"] == "test-device-code-123"
    assert credentials["user_code"] == "ABCD-1234"
    assert credentials["verification_uri"] == "https://github.com/login/device"
    assert credentials["device_authorization_completed"] is False
    assert credentials["token_exchange_completed"] is False

    has_real = auth_profiles.provider_has_real_credentials(
        profile="copilot-device",
        provider="github-copilot",
    )
    assert has_real is False


def test_copilot_device_flow_complete_becomes_ready(isolated_runtime) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router
    lanes = isolated_runtime.non_visible_lane_execution

    auth_profiles.save_provider_credentials(
        profile="copilot-complete",
        provider="github-copilot",
        credentials={
            "kind": "github-copilot-oauth-device-flow-complete",
            "oauth_state": "real-stored",
            "access_token": "ghu_real_token_abc123",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "ghr_refresh_token",
            "refresh_token_expires_in": 15811200,
            "device_authorization_completed": True,
            "token_exchange_completed": True,
            "token_exchange_completed_at": "2024-01-01T00:01:00+00:00",
            "real_oauth": True,
            "created_by": "test",
        },
    )
    provider_router.configure_provider_router_entry(
        provider="github-copilot",
        model="gpt-4.1",
        auth_mode="oauth",
        auth_profile="copilot-complete",
        base_url="",
        api_key="",
        lane="coding",
        set_visible=False,
    )

    has_real = auth_profiles.provider_has_real_credentials(
        profile="copilot-complete",
        provider="github-copilot",
    )
    assert has_real is True

    truth = lanes.coding_lane_execution_truth()

    assert truth["credentials_ready"] is True
    assert truth["can_execute"] is True
