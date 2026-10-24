from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

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


def test_render_tolerates_non_trailer_line_in_existing_block() -> None:
    with patch(
        "core.services.commit_attribution._split_final_trailer_block",
        return_value=(["fix: x"], ["not-a-trailer"]),
    ):
        with pytest.raises(AttributionError, match="Actor must appear"):
            render_attributed_message("fix: x", _attribution())


def _besked_med_run_id(run_id: str) -> str:
    return f"""fix: x

Actor: jarvis
Actor-Type: agent
Run-ID: {run_id}
Session-ID: none
Origin: interactive
Approved-By: bjorn
"""


@pytest.mark.parametrize(
    "placeholder",
    [
        "RUNIDPLACEHOLDER",
        "manual-RUNIDPLACEHOLDER",
        "manual-20261024T135845Z-PLACEHOLDER",  # pragma: allowlist secret
        "RUN_IDPLACEHOLDER",
        "__RID__",
        "__RUNID__",  # den faktisk observerede historiske værdi
        "__RUN_ID__",  # variant der også findes i historikken
        "manual-20261019T154210Z-COMMITHEX",
    ],
)
def test_skabelon_markør_som_run_id_afvises(placeholder: str) -> None:
    """En skabelon-markør er ikke en kørsel og må ikke passere som provenance.

    Målt 24/10-2026 på Run-ID-traileren over de sidste 300 commits: 14 havde
    en markør i stedet for et rigtigt id — `RUNIDPLACEHOLDER` (6), `__RID__`
    (4), `RUN_IDPLACEHOLDER` (1), `manual-...-PLACEHOLDER` (1), `__RUNID__`
    (1), `manual-RUNIDPLACEHOLDER` (1). Hele historikken rummer 17. Hertil
    `manual-<ts>-COMMITHEX` (1), som `COMMITHEX`-alternativet dækker. De gik
    igennem fordi `validate_trailers` kun krævede at feltet var til stede og
    ikke-tomt, ikke at det navngav en faktisk kørsel.

    Ret 24/10-2026: den første udgave af denne test hævdede 21 og brugte
    `__RUN_ID__` som den observerede værdi. Begge var forkerte — 21 var en
    sum af markører PLUS fem legitime id'er uden `manual-`-præfiks, og den
    faktiske historiske værdi er `__RUNID__`.
    """
    errors = validate_commit_message(_besked_med_run_id(placeholder))

    assert any("Run-ID" in error for error in errors), (
        f"skabelon-markøren {placeholder!r} blev accepteret som Run-ID: {errors}"
    )


@pytest.mark.parametrize(
    "legitimt",
    [
        "manual-20261024T135845Z-dff5f576",
        "manual-20261024T135845Z-mobile",
        "manual-20261024T135845Z-merge",
        "visible-f795573ccd15412298eb8d7d1a2b3c",
        "tool-discovery-nudge-abc12345",
        "01a0b937-3129-75a2-9c21-6a6d3f8e2b1c",
        "autonomous-abc123",
    ],
)
def test_legitime_run_id_formater_afvises_ikke(legitimt: str) -> None:
    """Vagten må ikke ramme de tusindvis af legitime varianter i historikken.

    Målt i hele historikken: 3361× `manual-<ts>-<hex8>` plus varianter som
    `-mobile`, `-merge`, `visible-*`, `tool-discovery-nudge-*` og UUID-formede
    id'er. En streng format-validering ville afvise dem; vagten skal kun ramme
    skabelon-markørerne.
    """
    errors = validate_commit_message(_besked_med_run_id(legitimt))

    assert not any("Run-ID" in error for error in errors), (
        f"legitimt Run-ID {legitimt!r} blev afvist: {errors}"
    )
