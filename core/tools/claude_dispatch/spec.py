from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ALLOWED_TOOLS_WHITELIST = frozenset({
    "Read", "Edit", "Write", "Glob", "Grep", "Bash",
    "TodoWrite", "WebFetch", "WebSearch",
})

ALLOWED_PERMISSION_MODES = frozenset({"default", "acceptEdits", "plan"})

MAX_ALLOWED_TOKENS = 500_000
MAX_ALLOWED_WALL_SECONDS = 3600


class SpecValidationError(ValueError):
    pass


@dataclass(frozen=True)
class TaskSpec:
    goal: str
    scope_files: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    max_tokens: int = 100_000
    max_wall_seconds: int = 1800
    permission_mode: str = "default"
    forbidden_paths: tuple[str, ...] = field(default_factory=tuple)
    success_criteria: str = ""


def parse_spec(raw: dict[str, Any]) -> TaskSpec:
    goal = (raw.get("goal") or "").strip()
    if not goal:
        raise SpecValidationError("goal is required and non-empty")

    scope_raw = raw.get("scope_files") or []
    if not isinstance(scope_raw, list) or not scope_raw:
        raise SpecValidationError("scope_files must be a non-empty list")

    scope: list[str] = []
    for p in scope_raw:
        if not isinstance(p, str) or not p.strip():
            raise SpecValidationError(
                f"scope_files entries must be non-empty strings, got {p!r}"
            )
        if p.startswith("/"):
            raise SpecValidationError(
                f"absolute paths forbidden in scope_files: {p}"
            )
        if ".." in p.split("/"):
            raise SpecValidationError(
                f"parent-directory traversal forbidden in scope_files: {p}"
            )
        scope.append(p)

    tools_raw = raw.get("allowed_tools") or []
    if not isinstance(tools_raw, list) or not tools_raw:
        raise SpecValidationError("allowed_tools must be a non-empty list")
    for t in tools_raw:
        if t not in ALLOWED_TOOLS_WHITELIST:
            raise SpecValidationError(f"unknown tool in allowed_tools: {t}")

    max_tokens = int(raw.get("max_tokens", 100_000))
    if max_tokens <= 0 or max_tokens > MAX_ALLOWED_TOKENS:
        raise SpecValidationError(
            f"max_tokens must be in (0, {MAX_ALLOWED_TOKENS}]"
        )

    max_wall = int(raw.get("max_wall_seconds", 1800))
    if max_wall <= 0 or max_wall > MAX_ALLOWED_WALL_SECONDS:
        raise SpecValidationError(
            f"max_wall_seconds must be in (0, {MAX_ALLOWED_WALL_SECONDS}]"
        )

    permission_mode = str(raw.get("permission_mode", "default"))
    if permission_mode not in ALLOWED_PERMISSION_MODES:
        raise SpecValidationError(
            f"permission_mode must be one of {sorted(ALLOWED_PERMISSION_MODES)}"
        )

    forbidden_raw = raw.get("forbidden_paths") or []
    forbidden = tuple(str(p) for p in forbidden_raw if isinstance(p, str))

    return TaskSpec(
        goal=goal,
        scope_files=tuple(scope),
        allowed_tools=tuple(tools_raw),
        max_tokens=max_tokens,
        max_wall_seconds=max_wall,
        permission_mode=permission_mode,
        forbidden_paths=forbidden,
        success_criteria=str(raw.get("success_criteria", "")),
    )
