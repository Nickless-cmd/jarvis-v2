"""Memory maintenance daemon — periodic dedup and health of MEMORY.md.

Runs every 12 hours. Two tiers:
  Tier A (auto): exact + fuzzy heading duplicates → auto-merge.
  Tier B (flag): overlapping content across headings → publish event for review.

This is the daemon companion to the writer-level fuzzy dedup in
candidate_workflow._fuzzy_line_match (Lag 1). Lag 1 prevents
near-duplicate *lines* from being appended. This daemon prevents
near-duplicate *sections* from accumulating over time.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.config import JARVIS_HOME

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 12
_TIER_A_HEADING_SIMILARITY = 0.85  # Jaccard threshold for auto-merge
_TIER_B_CONTENT_SIMILARITY = 0.50  # Jaccard threshold for flagging
_MIN_SECTION_LINES = 2  # skip sections with fewer lines

MEMORY_MD = Path(JARVIS_HOME) / "workspaces" / "default" / "MEMORY.md"

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_last_result: dict = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_memory_maintenance_daemon(now: datetime | None = None) -> dict:
    """Run 12h maintenance cycle on MEMORY.md.

    Returns dict with tier_a (auto-merged) and tier_b (flagged) counts.
    """
    global _last_tick_at, _last_result

    now = now or datetime.now(UTC)

    # Cadence gate
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"maintained": False, "reason": "cadence"}

    text = _read_memory()
    if not text.strip():
        return {"maintained": False, "reason": "empty"}

    sections = _parse_sections(text)
    if len(sections) < 2:
        return {"maintained": False, "reason": "too_few_sections"}

    # Tier A: auto-merge exact + fuzzy heading duplicates
    tier_a_merged = _tier_a_auto_merge(sections, text)

    # Re-read after potential merges
    text = _read_memory()
    sections = _parse_sections(text)

    # Tier B: flag overlapping content across different headings
    tier_b_flagged = _tier_b_flag_overlaps(sections)

    _last_tick_at = now
    _last_result = {
        "tier_a_merged": tier_a_merged,
        "tier_b_flagged": tier_b_flagged,
        "sections_before": len(sections) + tier_a_merged,  # before merges
        "sections_after": len(_parse_sections(_read_memory())),
    }

    # Publish event
    try:
        event_bus.publish(
            "memory.maintenance",
            {
                "tier_a_merged": tier_a_merged,
                "tier_b_flagged": tier_b_flagged,
                "timestamp": now.isoformat(),
            },
        )
    except Exception:
        pass

    return _last_result


def build_memory_maintenance_surface() -> dict:
    return {
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
        "last_result": _last_result,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_memory() -> str:
    try:
        return MEMORY_MD.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _parse_sections(text: str) -> list[dict]:
    """Parse MEMORY.md into sections: [{heading, level, content, start_line, end_line}]."""
    sections: list[dict] = []
    current_heading = None
    current_level = 0
    current_lines: list[str] = []
    start_line = 0

    for i, line in enumerate(text.splitlines()):
        m = re.match(r"^(#{1,4})\s+(.+)$", line)
        if m:
            if current_heading is not None:
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "content": "\n".join(current_lines).strip(),
                    "start_line": start_line,
                    "end_line": i - 1,
                })
            current_level = len(m.group(1))
            current_heading = m.group(2).strip()
            current_lines = []
            start_line = i
        else:
            current_lines.append(line)

    if current_heading is not None:
        sections.append({
            "heading": current_heading,
            "level": current_level,
            "content": "\n".join(current_lines).strip(),
            "start_line": start_line,
            "end_line": len(text.splitlines()) - 1,
        })

    return sections


def _jaccard(a: str, b: str) -> float:
    """Word-level Jaccard similarity between two strings."""
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _containment(a: str, b: str) -> float:
    """What fraction of tokens in `a` appear in `b`? (subset check)"""
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa:
        return 0.0
    return len(wa & wb) / len(wa)


def _tier_a_auto_merge(sections: list[dict], text: str) -> int:
    """Auto-merge sections with exact or fuzzy-matching headings.

    Criteria for auto-merge (safe — no information loss):
      - Exact heading match (case-insensitive)
      - One heading is a subset/containment of the other (≥0.9)

    Merges by keeping the longer section's content + appending unique lines
    from the shorter section.
    """
    merged_count = 0
    to_remove: list[str] = []  # headings to remove after merge
    merge_targets: dict[str, str] = {}  # target_heading → source_heading

    for i, s1 in enumerate(sections):
        for j, s2 in enumerate(sections):
            if j <= i:
                continue
            if s1["level"] != s2["level"]:
                continue
            if s1["heading"] in to_remove or s2["heading"] in to_remove:
                continue

            h1, h2 = s1["heading"], s2["heading"]
            heading_sim = _jaccard(h1, h2)
            containment_1in2 = _containment(h1, h2)
            containment_2in1 = _containment(h2, h1)

            # Auto-merge criteria: exact match, high Jaccard, or strong containment
            is_exact = h1.lower().strip() == h2.lower().strip()
            is_fuzzy_high = heading_sim >= _TIER_A_HEADING_SIMILARITY
            is_subset = containment_1in2 >= 0.9 or containment_2in1 >= 0.9

            if not (is_exact or is_fuzzy_high or is_subset):
                continue

            # Merge: keep the longer section, append unique lines from shorter
            longer = s1 if len(s1["content"]) >= len(s2["content"]) else s2
            shorter = s2 if longer is s1 else s1

            longer_lines = set(longer["content"].splitlines())
            unique_lines = [
                line for line in shorter["content"].splitlines()
                if line.strip() and line.strip() not in longer_lines
            ]

            if unique_lines:
                # Append unique lines to the longer section
                new_content = longer["content"].rstrip() + "\n" + "\n".join(unique_lines)
                _replace_section_content(longer["heading"], longer["level"], new_content)

            to_remove.append(shorter["heading"])
            merge_targets[longer["heading"]] = shorter["heading"]
            merged_count += 1

    # Remove merged-away sections
    for heading in to_remove:
        _remove_section(heading)

    return merged_count


def _tier_b_flag_overlaps(sections: list[dict]) -> list[dict]:
    """Flag sections with different headings but overlapping content.

    Does NOT auto-merge — just publishes events for review.
    """
    flagged: list[dict] = []

    for i, s1 in enumerate(sections):
        for j, s2 in enumerate(sections):
            if j <= i:
                continue
            if s1["level"] != s2["level"]:
                continue
            # Skip sections with very little content
            if len(s1["content"].splitlines()) < _MIN_SECTION_LINES:
                continue
            if len(s2["content"].splitlines()) < _MIN_SECTION_LINES:
                continue

            content_sim = _jaccard(
                s1["content"][:500],
                s2["content"][:500],
            )
            if content_sim >= _TIER_B_CONTENT_SIMILARITY:
                flag = {
                    "section_a": s1["heading"],
                    "section_b": s2["heading"],
                    "similarity": round(content_sim, 3),
                }
                flagged.append(flag)
                try:
                    event_bus.publish(
                        "memory.overlap_detected",
                        {
                            **flag,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
                except Exception:
                    pass

    return flagged


def _replace_section_content(heading: str, level: int, new_content: str) -> None:
    """Replace a section's content in MEMORY.md."""
    text = _read_memory()
    hashes = "#" * level
    pattern = rf"(^{re.escape(hashes)}\s+{re.escape(heading)}\s*\n)(.*?)(?=^#|\Z)"
    replacement = f"{hashes} {heading}\n{new_content}\n\n"
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if count > 0:
        MEMORY_MD.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_MD.write_text(new_text, encoding="utf-8")


def _remove_section(heading: str) -> None:
    """Remove a section entirely from MEMORY.md."""
    text = _read_memory()
    # Match heading line + content until next heading or EOF
    pattern = rf"^#{1,4}\s+{re.escape(heading)}\s*\n.*?(?=^#|\Z)"
    new_text = re.sub(pattern, "", text, count=1, flags=re.MULTILINE | re.DOTALL)
    # Clean up excessive blank lines
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    MEMORY_MD.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_MD.write_text(new_text, encoding="utf-8")