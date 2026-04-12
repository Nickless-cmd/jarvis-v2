"""Council Memory Service — persists council conclusions to COUNCIL_LOG.md.

Each entry is a structured markdown block with timestamp, topic, score, members,
signals, full transcript, conclusion, and optional initiative proposal.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

_LOG_FILE = Path(JARVIS_HOME) / "workspaces" / "default" / "COUNCIL_LOG.md"


def append_council_conclusion(
    *,
    topic: str,
    score: float,
    members: list[str],
    signals: list[str],
    transcript: str,
    conclusion: str,
    initiative: str | None,
) -> None:
    """Append a council conclusion entry to COUNCIL_LOG.md."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    members_str = ", ".join(members)
    signals_str = ", ".join(signals)

    entry = f"\n## {timestamp} — {topic}\n\n"
    entry += f"**Score:** {score:.2f} | **Members:** {members_str} | **Signals:** {signals_str}\n\n"
    entry += "### Transcript\n\n"
    entry += transcript.strip() + "\n\n"
    entry += "### Konklusion\n\n"
    entry += conclusion.strip() + "\n"
    if initiative:
        entry += "\n### Initiative-forslag\n\n"
        entry += initiative.strip() + "\n"

    existing = _LOG_FILE.read_text(encoding="utf-8") if _LOG_FILE.exists() else ""
    _LOG_FILE.write_text(existing + entry, encoding="utf-8")


def read_all_entries() -> list[dict[str, Any]]:
    """Parse COUNCIL_LOG.md and return list of entry dicts.

    Each dict has: timestamp, topic, score, members, signals, transcript, conclusion, initiative.
    Returns [] if file does not exist or has no valid entries.
    """
    if not _LOG_FILE.exists():
        return []
    content = _LOG_FILE.read_text(encoding="utf-8")
    return _parse_entries(content)


def _parse_entries(content: str) -> list[dict[str, Any]]:
    """Parse markdown content into list of entry dicts."""
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
    """Parse a single markdown entry block."""
    lines = block.splitlines()
    if not lines:
        return None

    header = lines[0].lstrip("# ").strip()
    ts_topic = header.split(" — ", 1)
    if len(ts_topic) < 2:
        return None
    timestamp, topic = ts_topic[0].strip(), ts_topic[1].strip()

    score = 0.0
    members: list[str] = []
    signals: list[str] = []
    for line in lines[1:5]:
        if "**Score:**" in line:
            m = re.search(r"\*\*Score:\*\* ([\d.]+)", line)
            if m:
                score = float(m.group(1))
            m2 = re.search(r"\*\*Members:\*\* ([^|]+)", line)
            if m2:
                members = [x.strip() for x in m2.group(1).split(",")]
            m3 = re.search(r"\*\*Signals:\*\* (.+)", line)
            if m3:
                signals = [x.strip() for x in m3.group(1).split(",")]
            break

    transcript = _extract_section(block, "### Transcript")
    conclusion = _extract_section(block, "### Konklusion")
    initiative = _extract_section(block, "### Initiative-forslag") or None

    return {
        "timestamp": timestamp,
        "topic": topic,
        "score": score,
        "members": members,
        "signals": signals,
        "transcript": transcript,
        "conclusion": conclusion,
        "initiative": initiative,
    }


def _extract_section(block: str, heading: str) -> str:
    """Extract text content between a heading and the next heading."""
    pattern = re.escape(heading) + r"\n\n(.*?)(?=\n### |\Z)"
    m = re.search(pattern, block, re.DOTALL)
    return m.group(1).strip() if m else ""
