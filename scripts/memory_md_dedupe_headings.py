"""Merge duplicate `## ` headings in a MEMORY.md (memory repair 2026-09-04, R7).

Five write paths appended to MEMORY.md with different dedupe rules, so the
owner's file had "## Decisions" twice, "## LivingNeuron — Centralen er mig"
twice, and so on. Section-based selection (memory_md_selection) keys on the
heading, so duplicates split the evidence for one topic across two chunks.

Rule: the FIRST occurrence keeps its place; the bodies of later duplicates are
appended under it (separated by a blank line), in file order. Nothing is
deleted. Headings are compared case-insensitively with whitespace collapsed.

Usage:
    python scripts/memory_md_dedupe_headings.py <path/to/MEMORY.md>            # dry-run
    python scripts/memory_md_dedupe_headings.py <path/to/MEMORY.md> --apply    # writes + .bak-<ts>
"""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _norm(heading: str) -> str:
    return " ".join(heading.strip().lstrip("#").split()).strip().lower()


def dedupe_headings(text: str) -> tuple[str, int]:
    """Return (new_text, merged_count). Only `## ` headings are merged."""
    lines = text.splitlines()
    sections: list[tuple[str | None, list[str]]] = []  # (heading line or None, body lines)
    current_heading: str | None = None
    current_body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            sections.append((current_heading, current_body))
            current_heading, current_body = line, []
        else:
            current_body.append(line)
    sections.append((current_heading, current_body))

    merged = 0
    index_by_key: dict[str, int] = {}
    out: list[tuple[str | None, list[str]]] = []
    for heading, body in sections:
        if heading is None:
            out.append((heading, body))
            continue
        key = _norm(heading)
        if key in index_by_key:
            merged += 1
            target = out[index_by_key[key]]
            target_body = target[1]
            # trim trailing blanks on the existing body, then add a blank + new body
            while target_body and not target_body[-1].strip():
                target_body.pop()
            new_body = list(body)
            while new_body and not new_body[0].strip():
                new_body.pop(0)
            if new_body:
                target_body.append("")
                target_body.extend(new_body)
            continue
        index_by_key[key] = len(out)
        out.append((heading, list(body)))

    rendered: list[str] = []
    for heading, body in out:
        if heading is not None:
            rendered.append(heading)
        rendered.extend(body)
    new_text = "\n".join(rendered)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return new_text, merged


def dedupe_file(path: Path, *, apply: bool) -> int:
    text = path.read_text(encoding="utf-8")
    new_text, merged = dedupe_headings(text)
    if merged and apply:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(path.name + f".bak-{stamp}")
        shutil.copy2(path, backup)
        path.write_text(new_text, encoding="utf-8")
        print(f"merged {merged} duplicate heading(s); backup: {backup}")
    else:
        print(f"{'would merge' if merged else 'no duplicates'}: {merged}")
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dedupe_file(args.path, apply=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
