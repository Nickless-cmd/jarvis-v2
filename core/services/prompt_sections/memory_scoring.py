"""core/services/prompt_sections/memory_scoring.py

Rene memory-relevans helpers — udskilt fra prompt_contract.py (Boy Scout, task_d6100d6e).

Disse funktioner er PURE (kun str/list-operationer, ingen prompt_contract-lokale typer/globals) →
sikker udskillelse uden circular-import. Re-eksporteres fra prompt_contract for bagudkompatibilitet.
Scorer + ordner workspace-memory-entries efter relevans for brugerbeskeden. Ingen sideeffekter.
"""
from __future__ import annotations


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _memory_line_relevance_score(entry: str, user_message: str) -> int:
    line = str(entry or "").lower()
    query = str(user_message or "").lower()
    score = 0

    if _contains_any(
        query, ("mit navn", "hvad hedder jeg", "name", "navn")
    ) and _contains_any(
        line,
        ("name", "navn"),
    ):
        score += 8
    if _contains_any(
        query,
        ("bygger vi", "build", "building", "projekt", "project", "arbejder vi på"),
    ) and _contains_any(
        line,
        (
            "project anchor",
            "building jarvis together",
            "jarvis together",
            "shared project",
        ),
    ):
        score += 8
    if _contains_any(
        query,
        (
            "repo",
            "repoet",
            "repository",
            "arbejder vi i",
            "working context",
            "hvilket repo",
        ),
    ) and _contains_any(
        line,
        ("jarvis v2 repo", "working context", "repo context", "repo"),
    ):
        score += 8
    if _contains_any(
        query,
        ("context", "continuity", "stable", "carry", "workspace"),
    ) and _contains_any(
        line,
        ("stable context", "carry forward", "carried", "workspace continuity"),
    ):
        score += 5

    for token in (
        "jarvis",
        "repo",
        "project",
        "context",
        "name",
        "working",
        "build",
        "stable",
        "workspace",
    ):
        if token in query and token in line:
            score += 1
    return score


def _heuristic_relevant_memory_entries(
    entries: list[str],
    *,
    user_message: str,
    max_lines: int,
) -> list[str]:
    scored: list[tuple[int, int, str]] = []
    for index, entry in enumerate(entries):
        score = _memory_line_relevance_score(entry, user_message)
        if score <= 0:
            continue
        scored.append((score, index, entry))

    if scored:
        chosen = sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)[
            : max(max_lines, 1)
        ]
        ordered = [item[2] for item in sorted(chosen, key=lambda item: item[1])]
    else:
        ordered = entries[-max(max_lines, 1) :]
    return ordered


def _merge_ordered_memory_entries(
    primary: list[str],
    secondary: list[str],
    *,
    max_lines: int,
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for entry in [*primary, *secondary]:
        key = " ".join(str(entry or "").lower().split()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(entry)
        if len(merged) >= max(max_lines, 1):
            break
    return merged
