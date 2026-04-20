"""Agent Outcomes Log — persists solo-agent task completions to AGENT_OUTCOMES.md.

Parallel to council_memory_service.py / COUNCIL_LOG.md but for individual agents.
Each entry records agent name, goal, outcome text, and execution mode.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

_LOG_FILE = Path(JARVIS_HOME) / "workspaces" / "default" / "AGENT_OUTCOMES.md"
_OUTCOME_TRIM = 600


def append_agent_outcome(
    *,
    agent_id: str,
    name: str,
    goal: str,
    outcome: str,
    execution_mode: str = "solo-task",
) -> None:
    """Append a completed agent outcome to AGENT_OUTCOMES.md."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    label = name or agent_id
    trimmed = outcome[:_OUTCOME_TRIM].strip()

    entry = f"\n## {timestamp} — {label}\n\n"
    entry += f"**Mode:** {execution_mode} | **Goal:** {goal.strip()}\n\n"
    entry += "### Outcome\n\n"
    entry += trimmed + "\n"

    existing = _LOG_FILE.read_text(encoding="utf-8") if _LOG_FILE.exists() else ""
    _LOG_FILE.write_text(existing + entry, encoding="utf-8")


def get_recent_agent_outcomes(limit: int = 5) -> list[dict[str, Any]]:
    """Return the most recent agent outcomes (newest-first)."""
    if not _LOG_FILE.exists():
        return []
    content = _LOG_FILE.read_text(encoding="utf-8")
    entries = _parse_entries(content)
    return list(reversed(entries))[:limit]


def build_agent_outcomes_prompt_lines(limit: int = 3) -> list[str]:
    """Return compact prompt lines for recent agent outcomes."""
    outcomes = get_recent_agent_outcomes(limit=limit)
    lines = []
    for o in outcomes:
        ts = o.get("timestamp", "")[:16]
        label = o.get("name", "?")
        mode = o.get("execution_mode", "")
        snippet = (o.get("outcome") or "")[:120].replace("\n", " ")
        lines.append(f"[{ts}] {label} ({mode}): {snippet}")
    return lines


def build_agent_outcomes_surface(limit: int = 10) -> dict[str, Any]:
    """Build structured surface dict for runtime_self_model and MC."""
    outcomes = get_recent_agent_outcomes(limit=limit)
    return {
        "recent_outcomes": outcomes,
        "outcome_count": len(outcomes),
        "last_outcome_at": outcomes[0].get("timestamp") if outcomes else None,
        "authority": "agent-outcomes-log",
        "visibility": "internal-only",
        "kind": "agent-completion-memory",
    }


def _parse_entries(content: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    blocks = re.split(r"\n(?=## \d{4}-\d{2}-\d{2}T)", content)
    for block in blocks:
        block = block.strip()
        if not block.startswith("## "):
            continue
        entry = _parse_single_entry(block)
        if entry:
            entries.append(entry)
    return entries


def _parse_single_entry(block: str) -> dict[str, Any] | None:
    lines = block.splitlines()
    if not lines:
        return None

    header = lines[0].lstrip("# ").strip()
    parts = header.split(" — ", 1)
    if len(parts) < 2:
        return None
    timestamp, name = parts[0].strip(), parts[1].strip()

    execution_mode = ""
    goal = ""
    for line in lines[1:5]:
        if "**Mode:**" in line:
            m = re.search(r"\*\*Mode:\*\* ([^|]+)", line)
            if m:
                execution_mode = m.group(1).strip()
            m2 = re.search(r"\*\*Goal:\*\* (.+)", line)
            if m2:
                goal = m2.group(1).strip()
            break

    outcome = _extract_section(block, "### Outcome")
    return {
        "timestamp": timestamp,
        "name": name,
        "goal": goal,
        "outcome": outcome,
        "execution_mode": execution_mode,
    }


def _extract_section(block: str, heading: str) -> str:
    pattern = re.escape(heading) + r"\n\n(.*?)(?=\n### |\Z)"
    m = re.search(pattern, block, re.DOTALL)
    return m.group(1).strip() if m else ""
