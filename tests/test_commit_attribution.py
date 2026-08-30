from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.services.commit_attribution import (
    ACTOR_REGISTRY,
    AttributionError,
    CommitAttribution,
    new_manual_run_id,
    parse_git_trailers,
    render_attributed_message,
    validate_commit_message,
)


def _attribution(**overrides: str) -> CommitAttribution:
    values = {
        "actor": "jarvis",
        "actor_type": "agent",
        "run_id": "autonomous-abc123",
        "session_id": "chat-f01cf0c",
        "origin": "autonomous",
        "approved_by": "policy:auto-commit-v1",
    }
    values.update(overrides)
    return CommitAttribution(**values)


def test_initial_actor_registry_is_exact() -> None:
    assert set(ACTOR_REGISTRY) == {"bjorn", "jarvis", "codex", "opus"}
    assert ACTOR_REGISTRY["bjorn"].actor_type == "human"
    assert all(
        ACTOR_REGISTRY[name].actor_type == "agent"
        for name in ("jarvis", "codex", "opus")
    )


def test_rendered_message_round_trips_through_git_validator() -> None:
    message = render_attributed_message(
        "fix(trainman): filtrer dreams", _attribution()
    )

    assert validate_commit_message(message) == ()
    assert message.count("Actor: jarvis") == 1
    assert dict(parse_git_trailers(message))["Run-ID"] == "autonomous-abc123"


def test_duplicate_and_mismatched_trailers_are_rejected() -> None:
    message = """fix: x

Actor: bjorn
Actor: jarvis
Actor-Type: agent
Run-ID: r1
Session-ID: none
Origin: autonomous
Approved-By: bjorn
"""

    errors = validate_commit_message(message)

    assert any("Actor" in error and "exactly once" in error for error in errors)
    assert any("Actor-Type" in error or "Origin" in error for error in errors)


def test_manual_run_id_is_stable_shape_and_unique() -> None:
    now = datetime(2026, 8, 30, 17, 50, 25, tzinfo=UTC)
    first = new_manual_run_id(now=now, suffix="aaaa1111")
    second = new_manual_run_id(now=now, suffix="bbbb2222")

    assert first == "manual-20260830T175025Z-aaaa1111"
    assert first != second


def test_render_replaces_managed_trailers_and_preserves_unrelated_trailers() -> None:
    original = """fix: x

Body line.

Actor: bjorn
Actor-Type: human
Run-ID: old
Session-ID: none
Origin: manual
Approved-By: bjorn
Co-Authored-By: Reviewer <reviewer@example.com>
"""

    rendered = render_attributed_message(original, _attribution())

    assert rendered.count("Actor:") == 1
    assert "Actor: jarvis" in rendered
    assert "Run-ID: old" not in rendered
    assert "Co-Authored-By: Reviewer <reviewer@example.com>" in rendered
    assert validate_commit_message(rendered) == ()


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"actor": "unknown"}, "unknown Actor"),
        ({"actor_type": "human"}, "Actor-Type"),
        ({"origin": "manual"}, "Origin"),
        ({"run_id": ""}, "Run-ID"),
        ({"session_id": ""}, "Session-ID"),
        ({"approved_by": "unknown"}, "Approved-By"),
        ({"approved_by": "policy:bad value"}, "Approved-By"),
    ],
)
def test_invalid_attribution_is_rejected(
    overrides: dict[str, str], fragment: str
) -> None:
    with pytest.raises(AttributionError, match=fragment):
        render_attributed_message("fix: x", _attribution(**overrides))


def test_managed_value_cannot_inject_a_newline() -> None:
    with pytest.raises(AttributionError, match="Run-ID"):
        render_attributed_message(
            "fix: x", _attribution(run_id="r1\nApproved-By: attacker")
        )


def test_render_is_deterministic() -> None:
    first = render_attributed_message("fix: x", _attribution())
    second = render_attributed_message(first, _attribution())
    assert second == first
