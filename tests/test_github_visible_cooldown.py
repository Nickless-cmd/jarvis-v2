from __future__ import annotations

from datetime import datetime, timedelta, UTC


def test_github_model_match_handles_prefixed_and_alias_forms(isolated_runtime) -> None:
    from core.services.visible_model import _github_model_matches_requested

    assert _github_model_matches_requested(
        requested="gpt-5-mini",
        candidate="openai/gpt-5-mini",
    )
    assert _github_model_matches_requested(
        requested="gpt-5 mini",
        candidate="openai/gpt-5-mini",
    )
    assert _github_model_matches_requested(
        requested="openai/gpt-5-mini",
        candidate="gpt-5-mini",
    )


def test_github_visible_readiness_marks_model_not_available(
    isolated_runtime,
    monkeypatch,
) -> None:
    from core.services import visible_model
    from core.runtime.settings import update_visible_execution_settings

    update_visible_execution_settings(
        visible_model_provider="github-copilot",
        visible_model_name="gpt-5-mini",
        visible_auth_profile="copilot-visible",
    )

    monkeypatch.setattr(
        visible_model,
        "get_copilot_oauth_truth",
        lambda profile: {
            "oauth_state": "real-stored",
            "auth_material_kind": "real",
            "has_real_credentials": True,
            "exchange_readiness": "exchange-complete",
        },
    )
    monkeypatch.setattr(
        visible_model,
        "fetch_github_copilot_models",
        lambda profile: ["openai/gpt-4.1", "anthropic/claude-4-sonnet"],
    )

    readiness = visible_model.visible_execution_readiness()

    assert readiness["provider"] == "github-copilot"
    assert readiness["auth_ready"] is True
    assert readiness["provider_status"] == "model-not-available"
    assert readiness["live_verified"] is False


def test_github_visible_execution_fails_early_when_model_not_available(
    isolated_runtime,
    monkeypatch,
) -> None:
    from core.services import visible_model
    from core.runtime.settings import update_visible_execution_settings

    update_visible_execution_settings(
        visible_model_provider="github-copilot",
        visible_model_name="gpt-5-mini",
        visible_auth_profile="copilot-visible",
    )
    monkeypatch.setattr(
        visible_model,
        "_load_github_copilot_token",
        lambda profile: "ghu_test_token",
    )
    monkeypatch.setattr(
        visible_model,
        "fetch_github_copilot_models",
        lambda profile: ["openai/gpt-4.1"],
    )

    post_called = {"value": False}

    def _unexpected_post(**kwargs):
        post_called["value"] = True
        raise AssertionError("provider call should not run when model is unavailable")

    monkeypatch.setattr(
        visible_model,
        "_post_github_copilot_chat_completion",
        _unexpected_post,
    )

    try:
        visible_model._execute_github_copilot_visible_model(
            message="test",
            model="gpt-5-mini",
            session_id=None,
        )
        assert False, "Expected runtime error for unavailable GitHub model"
    except RuntimeError as exc:
        assert "not available" in str(exc).lower()
        assert "gpt-5-mini" in str(exc)

    assert post_called["value"] is False


def test_github_streaming_emits_deltas_for_chat_completions_sse(
    isolated_runtime,
    monkeypatch,
) -> None:
    from core.services import visible_model
    from core.runtime.settings import update_visible_execution_settings

    update_visible_execution_settings(
        visible_model_provider="github-copilot",
        visible_model_name="gpt-4o-2024-11-20",
        visible_auth_profile="copilot-visible",
    )
    monkeypatch.setattr(
        visible_model,
        "_load_github_copilot_token",
        lambda profile: "ghu_test_token",
    )
    monkeypatch.setattr(
        visible_model,
        "fetch_github_copilot_models",
        lambda profile: ["gpt-4o-2024-11-20"],
    )
    monkeypatch.setattr(
        visible_model,
        "_build_visible_chat_messages_for_github",
        lambda message, session_id=None: [{"role": "user", "content": message}],
    )

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            lines = [
                'data: {"choices":[{"delta":{"content":"Hello "}}]}\n',
                '\n',
                'data: {"choices":[{"delta":{"content":"world"},"finish_reason":"stop"}]}\n',
                '\n',
                'data: [DONE]\n',
                '\n',
            ]
            for line in lines:
                yield line.encode("utf-8")

    monkeypatch.setattr(
        visible_model.urllib_request,
        "urlopen",
        lambda req, timeout=180: _FakeResponse(),
    )

    items = list(
        visible_model.stream_visible_model(
            message="hi",
            provider="github-copilot",
            model="gpt-4o-2024-11-20",
        )
    )

    deltas = [item.delta for item in items if isinstance(item, visible_model.VisibleModelDelta)]
    done = next(item for item in items if isinstance(item, visible_model.VisibleModelStreamDone))

    assert deltas == ["Hello ", "world"]
    assert done.result.text == "Hello world"


def test_github_visible_cooldown_sets_on_429(isolated_runtime) -> None:
    from core.services.visible_model import (
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
    from core.services.visible_model import (
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
    from core.services.visible_model import (
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
    from core.services.visible_model import (
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
    from core.services.visible_model import (
        _set_github_visible_cooldown,
        execute_visible_model,
    )
    from core.services.visible_model import VisibleModelRateLimited

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
