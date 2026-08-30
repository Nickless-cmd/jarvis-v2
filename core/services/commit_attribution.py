"""Canonical, audit-only attribution metadata for Git commit messages."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Sequence
from uuid import uuid4


MANAGED_TRAILERS = (
    "Actor",
    "Actor-Type",
    "Run-ID",
    "Session-ID",
    "Origin",
    "Approved-By",
)

_TRAILER_LINE = re.compile(r"^([A-Za-z0-9-]+):[ \t]*(.*)$")
_POLICY_ID = re.compile(r"^policy:[a-z0-9][a-z0-9._-]*$")
_MANUAL_SUFFIX = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class ActorRule:
    """Stable actor type and the origins that actor may claim."""

    actor_type: Literal["human", "agent"]
    origins: frozenset[str]


@dataclass(frozen=True)
class CommitAttribution:
    """The six required audit fields stored in a commit trailer block."""

    actor: str
    actor_type: str
    run_id: str
    session_id: str
    origin: str
    approved_by: str

    def as_trailers(self) -> tuple[tuple[str, str], ...]:
        return (
            ("Actor", self.actor),
            ("Actor-Type", self.actor_type),
            ("Run-ID", self.run_id),
            ("Session-ID", self.session_id),
            ("Origin", self.origin),
            ("Approved-By", self.approved_by),
        )


class AttributionError(ValueError):
    """Raised when attribution cannot satisfy the commit contract."""


ACTOR_REGISTRY: dict[str, ActorRule] = {
    "bjorn": ActorRule("human", frozenset({"manual", "interactive"})),
    "jarvis": ActorRule("agent", frozenset({"autonomous", "interactive"})),
    "codex": ActorRule("agent", frozenset({"interactive", "delegated"})),
    "opus": ActorRule("agent", frozenset({"interactive", "delegated"})),
}


def new_manual_run_id(
    now: datetime | None = None,
    suffix: str | None = None,
) -> str:
    """Return a sortable id for a commit without an existing runtime run."""

    instant = now or datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    instant = instant.astimezone(UTC)
    tail = suffix or uuid4().hex[:8]
    if not _MANUAL_SUFFIX.fullmatch(tail):
        raise AttributionError("manual run suffix contains invalid characters")
    return f"manual-{instant:%Y%m%dT%H%M%SZ}-{tail}"


def parse_git_trailers(message: str) -> tuple[tuple[str, str], ...]:
    """Parse the final trailer block with Git's own trailer semantics."""

    result = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        input=message,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "git trailer parse failed").strip()
        raise AttributionError(detail[:300])
    parsed: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        match = _TRAILER_LINE.match(line)
        if match:
            parsed.append((match.group(1), match.group(2).strip()))
    return tuple(parsed)


def validate_trailers(
    trailers: Sequence[tuple[str, str]],
) -> tuple[str, ...]:
    """Validate parsed trailers without reading process or repository state."""

    errors: list[str] = []
    values: dict[str, list[str]] = {key: [] for key in MANAGED_TRAILERS}
    for key, value in trailers:
        if key in values:
            values[key].append(value)

    for key in MANAGED_TRAILERS:
        count = len(values[key])
        if count != 1:
            errors.append(f"{key} must appear exactly once (found {count})")
        elif not values[key][0].strip() or "\n" in values[key][0] or "\r" in values[key][0]:
            errors.append(f"{key} must be a non-empty single-line value")

    actor = values["Actor"][0] if len(values["Actor"]) == 1 else ""
    actor_type = (
        values["Actor-Type"][0] if len(values["Actor-Type"]) == 1 else ""
    )
    origin = values["Origin"][0] if len(values["Origin"]) == 1 else ""
    approved_by = (
        values["Approved-By"][0]
        if len(values["Approved-By"]) == 1
        else ""
    )

    rule = ACTOR_REGISTRY.get(actor)
    if len(values["Actor"]) > 1:
        errors.append(
            "Actor-Type and Origin cannot be validated while Actor is duplicated"
        )
    if actor and rule is None:
        errors.append(f"unknown Actor: {actor}")
    if rule is not None:
        if actor_type and actor_type != rule.actor_type:
            errors.append(
                f"Actor-Type {actor_type!r} does not match Actor {actor!r}"
            )
        if origin and origin not in rule.origins:
            errors.append(f"Origin {origin!r} is not allowed for Actor {actor!r}")

    if approved_by and not (
        approved_by in ACTOR_REGISTRY or _POLICY_ID.fullmatch(approved_by)
    ):
        errors.append(
            "Approved-By must be a registered actor or policy:<stable-id>"
        )
    return tuple(errors)


def validate_commit_message(message: str) -> tuple[str, ...]:
    """Return every attribution error in a complete commit message."""

    return validate_trailers(parse_git_trailers(message))


def _split_final_trailer_block(message: str) -> tuple[list[str], list[str]]:
    lines = message.rstrip().splitlines()
    index = len(lines)
    while index > 0 and _TRAILER_LINE.match(lines[index - 1]):
        index -= 1
    if index == len(lines) or index == 0:
        return lines, []
    if index > 0 and lines[index - 1].strip():
        return lines, []
    body = lines[:index]
    while body and not body[-1].strip():
        body.pop()
    return body, lines[index:]


def render_attributed_message(
    message: str,
    attribution: CommitAttribution,
) -> str:
    """Replace managed trailers and return a deterministic commit message."""

    direct_errors = validate_trailers(attribution.as_trailers())
    if direct_errors:
        raise AttributionError("; ".join(direct_errors))
    body, existing = _split_final_trailer_block(message)
    unrelated: list[str] = []
    for line in existing:
        match = _TRAILER_LINE.match(line)
        if match is None or match.group(1) not in MANAGED_TRAILERS:
            unrelated.append(line)
    rendered = [*body, ""]
    rendered.extend(unrelated)
    rendered.extend(f"{key}: {value}" for key, value in attribution.as_trailers())
    result = "\n".join(rendered).strip() + "\n"
    final_errors = validate_commit_message(result)
    if final_errors:
        raise AttributionError("; ".join(final_errors))
    return result
