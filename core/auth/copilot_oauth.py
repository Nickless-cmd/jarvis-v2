from __future__ import annotations

from typing import Any

from core.auth.profiles import (
    get_provider_auth_material_kind,
    get_provider_callback_intent_consistency,
    get_provider_callback_validation_state,
    get_provider_credentials,
    get_provider_exchange_readiness,
    get_provider_launch_freshness,
    get_provider_launch_result_state,
    get_provider_oauth_state,
    get_provider_state_view,
    provider_has_real_credentials,
    save_provider_credentials,
)

PROVIDER_ID = "github-copilot"


def get_copilot_oauth_truth(*, profile: str) -> dict[str, Any]:
    oauth_state = get_provider_oauth_state(profile=profile, provider=PROVIDER_ID)
    auth_material_kind = get_provider_auth_material_kind(
        profile=profile,
        provider=PROVIDER_ID,
    )
    exchange_readiness = get_provider_exchange_readiness(
        profile=profile,
        provider=PROVIDER_ID,
    )
    return {
        "provider": PROVIDER_ID,
        "profile": profile,
        "oauth_state": oauth_state,
        "auth_material_kind": auth_material_kind,
        "has_real_credentials": provider_has_real_credentials(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "launch_result_state": get_provider_launch_result_state(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "launch_freshness": get_provider_launch_freshness(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "callback_validation_state": get_provider_callback_validation_state(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "exchange_readiness": exchange_readiness,
        "callback_intent_consistency": get_provider_callback_intent_consistency(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "profile_state": get_provider_state_view(
            profile=profile,
            provider=PROVIDER_ID,
        ),
    }


def save_copilot_oauth_credentials(
    *, profile: str, credentials: dict[str, Any]
) -> dict[str, Any]:
    return save_provider_credentials(
        profile=profile,
        provider=PROVIDER_ID,
        credentials=credentials,
    )


def get_copilot_oauth_credentials(*, profile: str) -> dict[str, Any] | None:
    return get_provider_credentials(profile=profile, provider=PROVIDER_ID)
