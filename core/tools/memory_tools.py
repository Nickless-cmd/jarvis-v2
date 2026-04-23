"""Memory duplicate-check and safe-write tools for MEMORY.md."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

MEMORY_MD = Path(JARVIS_HOME) / "workspaces" / "default" / "MEMORY.md"


def _read_memory() -> str:
    try:
        return MEMORY_MD.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _parse_headings(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^#{1,4}\s+(.+)$", text, re.MULTILINE)]


def _normalize(heading: str) -> str:
    return re.sub(r"\s+", " ", heading.strip().lower())


def _exec_memory_check_duplicate(args: dict[str, Any]) -> dict[str, Any]:
    heading = str(args.get("heading") or "").strip()
    if not heading:
        return {"status": "error", "error": "heading is required"}

    text = _read_memory()
    existing = _parse_headings(text)
    norm_target = _normalize(heading)

    exact_matches = [h for h in existing if _normalize(h) == norm_target]
    # Fuzzy: heading is contained in existing or vice versa (> 60% overlap)
    fuzzy_matches = [
        h for h in existing
        if h not in exact_matches
        and (norm_target in _normalize(h) or _normalize(h) in norm_target)
        and len(norm_target) > 5
    ]

    return {
        "status": "ok",
        "heading": heading,
        "is_duplicate": bool(exact_matches),
        "exact_matches": exact_matches,
        "fuzzy_matches": fuzzy_matches,
        "all_headings": existing,
        "text": (
            f"DUPLICATE: '{heading}' already exists in MEMORY.md."
            if exact_matches
            else (
                f"POSSIBLE DUPLICATE: Similar headings found: {fuzzy_matches}"
                if fuzzy_matches
                else f"OK: '{heading}' is new — safe to add."
            )
        ),
    }


def _exec_memory_upsert_section(args: dict[str, Any]) -> dict[str, Any]:
    """Write or update a section in MEMORY.md. Replaces existing section if heading matches."""
    heading = str(args.get("heading") or "").strip()
    content = str(args.get("content") or "").strip()
    level = int(args.get("level") or 2)

    if not heading:
        return {"status": "error", "error": "heading is required"}
    if not content:
        return {"status": "error", "error": "content is required"}
    if not 1 <= level <= 4:
        return {"status": "error", "error": "level must be 1-4"}

    text = _read_memory()
    hashes = "#" * level
    full_heading = f"{hashes} {heading}"
    norm_target = _normalize(heading)

    # Find if an existing section matches
    existing_headings = _parse_headings(text)
    match = next((h for h in existing_headings if _normalize(h) == norm_target), None)

    if match:
        # Replace existing section: find start + end of the section
        pattern = rf"(^#{{{level}}}\s+{re.escape(match)}\s*\n)(.*?)(?=^#|\Z)"
        replacement = f"{hashes} {heading}\n{content}\n\n"
        new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)
        if count == 0:
            # Fallback: just append
            new_text = text.rstrip() + f"\n\n{full_heading}\n{content}\n"
        action = "updated"
    else:
        # Append new section
        new_text = text.rstrip() + f"\n\n{full_heading}\n{content}\n"
        action = "added"

    MEMORY_MD.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_MD.write_text(new_text, encoding="utf-8")

    return {
        "status": "ok",
        "action": action,
        "heading": heading,
        "text": f"MEMORY.md section '{heading}' {action} successfully.",
    }


def _exec_memory_list_headings(args: dict[str, Any]) -> dict[str, Any]:
    text = _read_memory()
    headings = _parse_headings(text)
    return {
        "status": "ok",
        "headings": headings,
        "count": len(headings),
    }


MEMORY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "memory_check_duplicate",
            "description": (
                "Check whether a heading already exists in MEMORY.md before writing, "
                "to avoid duplicate sections. Returns exact and fuzzy matches."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string", "description": "The section heading to check for."},
                },
                "required": ["heading"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_upsert_section",
            "description": (
                "Safely write or update a section in MEMORY.md. "
                "If the heading already exists, replaces it. Otherwise appends. "
                "Use this instead of write_file for MEMORY.md updates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string", "description": "Section heading (without # prefix)."},
                    "content": {"type": "string", "description": "Full content of the section."},
                    "level": {"type": "integer", "description": "Heading level 1-4 (default 2, i.e. ##)."},
                },
                "required": ["heading", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_list_headings",
            "description": "List all section headings currently in MEMORY.md.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
