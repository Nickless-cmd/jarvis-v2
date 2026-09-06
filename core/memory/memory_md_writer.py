"""One writer for MEMORY.md-style section files (memory repair 2026-09-04, R7).

Five code paths appended to MEMORY.md with five different dedupe rules, which
is how the owner's file ended up with "## Decisions" twice and "## LivingNeuron
— Centralen er mig" twice. This module is the single place that knows how to
find, replace, append to and add a `#`-heading section:

- headings are matched on a normalized key (case, whitespace, punctuation,
  trailing dates/parentheticals removed) — so "## Decisions" and "## decisions"
  and "## Decisions (2026-07-12)" are the same section;
- writes are atomic (temp file + rename);
- ``mode="replace"`` swaps the section body, ``mode="append"`` adds lines to
  the end of the existing body (skipping lines already present).
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_PAREN_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_DATE_RE = re.compile(r"\b\d{1,2}\.?\s*(?:jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)[a-z]*\.?\s*\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^0-9a-zæøå ]+")


def normalize_heading(heading: str) -> str:
    """Key used to decide that two headings name the same section:
    lowercase, no dates, no parentheticals, no punctuation, collapsed spaces."""
    h = str(heading or "").strip().lstrip("#").strip().lower()
    h = _PAREN_RE.sub(" ", h)
    h = _DATE_RE.sub(" ", h)
    h = _PUNCT_RE.sub(" ", h)
    return " ".join(h.split())


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def parse_sections(text: str) -> list[dict[str, Any]]:
    """Split markdown into [{level, heading, body_lines, start, end}] by heading line.
    Text before the first heading is returned as a pseudo-section with heading ""."""
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    cur: dict[str, Any] = {"level": 0, "heading": "", "body": [], "start": 0}
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            cur["end"] = i
            sections.append(cur)
            cur = {"level": len(m.group(1)), "heading": m.group(2), "body": [], "start": i}
        else:
            cur["body"].append(line)
    cur["end"] = len(lines)
    sections.append(cur)
    return sections


def find_section(text: str, heading: str, *, level: int | None = None) -> dict[str, Any] | None:
    key = normalize_heading(heading)
    if not key:
        return None
    for sec in parse_sections(text):
        if not sec["heading"]:
            continue
        if level is not None and sec["level"] != level:
            continue
        if normalize_heading(sec["heading"]) == key:
            return sec
    return None


def _render(sections: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for sec in sections:
        if sec["heading"]:
            out.append("#" * int(sec["level"]) + " " + sec["heading"])
        out.extend(sec["body"])
    text = "\n".join(out)
    return text.rstrip() + "\n" if text.strip() else ""


def upsert_section(
    path: Path,
    heading: str,
    body: str,
    *,
    level: int = 2,
    mode: str = "replace",
) -> dict[str, Any]:
    """Write ``body`` under ``heading`` in ``path``.

    Returns {"action": "added"|"updated"|"appended"|"unchanged", "heading", "path"}.
    ``mode="replace"``: existing body is replaced. ``mode="append"``: new lines are
    added after the existing body (lines already present are skipped).
    """
    heading = " ".join(str(heading or "").split()).strip()
    body_lines = [ln.rstrip() for ln in str(body or "").strip().splitlines()]
    if not heading:
        raise ValueError("heading is required")
    level = max(1, min(6, int(level)))
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    sections = parse_sections(text)
    key = normalize_heading(heading)
    target = next((s for s in sections if s["heading"] and normalize_heading(s["heading"]) == key), None)

    if target is None:
        sections.append({"level": level, "heading": heading, "body": [""] + body_lines + [""], "start": -1, "end": -1})
        action = "added"
    elif mode == "append":
        existing = {" ".join(ln.split()).strip() for ln in target["body"] if ln.strip()}
        new_lines = [ln for ln in body_lines if " ".join(ln.split()).strip() not in existing and ln.strip()]
        if not new_lines:
            return {"action": "unchanged", "heading": target["heading"], "path": str(path)}
        while target["body"] and not target["body"][-1].strip():
            target["body"].pop()
        target["body"].extend(new_lines + [""])
        action = "appended"
    else:
        target["body"] = [""] + body_lines + [""]
        target["heading"] = heading
        target["level"] = level
        action = "updated"

    # blank line before every heading except the first
    for i, sec in enumerate(sections):
        if i > 0 and sec["heading"]:
            prev = sections[i - 1]
            if prev["body"] and prev["body"][-1].strip():
                prev["body"].append("")
    _atomic_write(path, _render(sections))
    return {"action": action, "heading": heading, "path": str(path)}


def merge_duplicate_headings(text: str) -> tuple[str, int]:
    """Merge sections whose normalized heading repeats: first keeps its place,
    later bodies are appended under it. Returns (new_text, merged_count)."""
    sections = parse_sections(text)
    out: list[dict[str, Any]] = []
    index: dict[str, int] = {}
    merged = 0
    for sec in sections:
        if not sec["heading"]:
            out.append(sec)
            continue
        key = normalize_heading(sec["heading"])
        if key in index:
            merged += 1
            target = out[index[key]]
            while target["body"] and not target["body"][-1].strip():
                target["body"].pop()
            body = list(sec["body"])
            while body and not body[0].strip():
                body.pop(0)
            if body:
                target["body"].append("")
                target["body"].extend(body)
            continue
        index[key] = len(out)
        out.append(sec)
    return _render(out), merged
