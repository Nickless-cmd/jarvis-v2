from __future__ import annotations

from datetime import datetime, timedelta, UTC


def test_github_visible_cooldown_sets_on_429(isolated_runtime) -> None:
    from apps.api.jarvis_api.services.visible_model import (
        _set_github_visible_cooldown,
        _is_github_visible_cooled_down,
        _get_github_visible_cooldown_status,
    )

    profile = "default"
    assert _is_github_visible_cooled_down(profile) is False

    status_before = _get_github_visible_cooldown_status(profile)
    assert status_before["cooled_down"] is False

    _set_github_visible_cooldown(profile, ttl_minutes=10)

    assert _is_github_visible_cooled_down(profile) is True

    status_after = _get_github_visible_cooldown_status(profile)
    assert status_after["cooled_down"] is True
    assert status_after["seconds_remaining"] > 0
    assert status_after["cooldown_until"] is not None


def test_github_visible_cooldown_respects_ttl(isolated_runtime) -> None:
    from datetime import timedelta
    from apps.api.jarvis_api.services.visible_model import (
        _set_github_visible_cooldown,
        _is_github_visible_cooled_down,
        _GITHUB_VISIBLE_COOLDOWN_UNTIL,
    )
    from datetime import UTC

    profile = "test-profile"
    _GITHUB_VISIBLE_COOLDOWN_UNTIL[profile] = datetime.now(UTC) - timedelta(minutes=1)

    assert _is_github_visible_cooled_down(profile) is False
    assert profile not in _GITHUB_VISIBLE_COOLDOWN_UNTIL


def test_github_visible_cooldown_fails_fast_when_cooled_down(
    isolated_runtime,
) -> None:
    from apps.api.jarvis_api.services.visible_model import (
        _set_github_visible_cooldown,
        _execute_github_copilot_visible_model,
        VisibleModelRateLimited,
        VisibleModelResult,
    )
    from unittest.mock import patch

    profile = "default"
    _set_github_visible_cooldown(profile)

    try:
        _execute_github_copilot_visible_model(
            message="test",
            model="gpt-4.1",
            session_id=None,
        )
        assert False, "Expected VisibleModelRateLimited to be raised"
    except VisibleModelRateLimited as exc:
        assert "rate-limited" in str(exc).lower()
        assert "cooldown" in str(exc).lower() or "minutes" in str(exc).lower()


def test_github_visible_execution_readiness_shows_cooldown(
    isolated_runtime,
) -> None:
    from apps.api.jarvis_api.services.visible_model import (
        visible_execution_readiness,
        _set_github_visible_cooldown,
        _GITHUB_VISIBLE_COOLDOWN_UNTIL,
    )
    from core.runtime.settings import update_visible_execution_settings
    from core.auth.profiles import get_provider_state

    update_visible_execution_settings(
        visible_model_provider="github-copilot",
        visible_model_name="gpt-4.1",
        visible_auth_profile="default",
    )

    get_provider_state(profile="default", provider="github-copilot")

    readiness_before = visible_execution_readiness()
    assert readiness_before["provider"] == "github-copilot"

    profile = readiness_before["auth_profile"] or "default"
    cooldown_before = readiness_before.get("cooldown", {})
    assert cooldown_before.get("cooled_down") is False

    _set_github_visible_cooldown(profile)

    readiness_after = visible_execution_readiness()
    assert readiness_after["provider"] == "github-copilot"

    cooldown_after = readiness_after.get("cooldown", {})
    assert cooldown_after.get("cooled_down") is True
    assert cooldown_after.get("seconds_remaining") > 0


def test_github_visible_cooldown_does_not_affect_non_github_paths(
    isolated_runtime,
) -> None:
    from apps.api.jarvis_api.services.visible_model import (
        _set_github_visible_cooldown,
        execute_visible_model,
    )
    from apps.api.jarvis_api.services.visible_model import VisibleModelRateLimited

    profile = "default"
    _set_github_visible_cooldown(profile)

    try:
        result = execute_visible_model(
            message="test",
            provider="phase1-runtime",
            model="placeholder",
        )
        assert result.text is not None
    except VisibleModelRateLimited:
        assert False, "phase1-runtime should not be affected by GitHub cooldown"
