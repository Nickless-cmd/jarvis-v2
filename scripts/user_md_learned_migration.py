#!/usr/bin/env python3
"""Flyt USER.md «## Durable Preferences» ind i «## Lært» (lærings-sløjfe, blok A).

Baggrund målt 4/9-2026: konsolideringen har skrevet 146 præferencer til
`## Durable Preferences`. Sektionen starter på linje 70 af 202, og prompten
læste enten de første 40 linjer eller — efter Kerne-mekanismen samme dag — kun
`## Kerne`. Ingen af de 146 linjer har nogensinde stået i hans prompt.

`## Lært` er relevans-udvalgt pr. tur (se
`core.services.prompt_sections.learned_about_user`), så indholdet kan nå ham
uden at fylde i det stabile præfiks.

Scriptet er dry-run som standard. `--apply` skriver, altid med backup ved siden
af filen. Linjer der allerede står i `## Kerne` flyttes ikke — de er allerede
altid i prompten.

    python scripts/user_md_learned_migration.py            # dry-run
    python scripts/user_md_learned_migration.py --apply
    python scripts/user_md_learned_migration.py --workspace bjorn --apply
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.prompt_sections.learned_about_user import (  # noqa: E402
    CORE_HEADINGS, section_body,
)

_SOURCE_HEADINGS = frozenset({"durable preferences", "varige præferencer"})


def _user_md_path(workspace: str) -> Path:
    home = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
    candidate = home / "workspaces" / workspace / "USER.md"
    if candidate.exists():
        return candidate
    return home / "shared" / "USER.md"


def migrate(*, workspace: str, apply: bool) -> dict[str, object]:
    path = _user_md_path(workspace)
    if not path.exists():
        return {"error": f"USER.md not found at {path}"}
    raw = path.read_text(encoding="utf-8")

    source = section_body(raw, _SOURCE_HEADINGS)
    if not source.strip():
        return {"path": str(path), "moved": 0, "reason": "no Durable Preferences section"}

    core = " ".join(section_body(raw, CORE_HEADINGS).split()).lower()
    existing_learned = " ".join(section_body(raw, frozenset({"lært"})).split()).lower()

    move: list[str] = []
    skipped_core = 0
    skipped_dup = 0
    for line in source.splitlines():
        body = " ".join(line.split()).strip()
        if not body or body.startswith("#"):
            continue
        probe = body.lstrip("-*").strip().lower()[:60]
        if probe and probe in core:
            skipped_core += 1
            continue
        if probe and probe in existing_learned:
            skipped_dup += 1
            continue
        move.append(body if body.startswith("-") else f"- {body}")

    result: dict[str, object] = {
        "path": str(path),
        "apply": apply,
        "would_move": len(move),
        "skipped_already_in_kerne": skipped_core,
        "skipped_already_in_laert": skipped_dup,
        "sample": move[:5],
    }
    if not apply or not move:
        return result

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(f".md.bak-{stamp}")
    shutil.copy2(path, backup)
    result["backup"] = str(backup)

    # Fjern kildesektionen (overskrift + brødtekst) og læg linjerne i «## Lært».
    out: list[str] = []
    inside = False
    level = 0
    for raw_line in raw.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip().lower()
            if inside and hashes <= level:
                inside = False
            elif title in _SOURCE_HEADINGS:
                inside, level = True, hashes
                continue
        if not inside:
            out.append(raw_line)
    trimmed = "\n".join(out).rstrip() + "\n"
    path.write_text(trimmed, encoding="utf-8")

    from core.memory.memory_md_writer import upsert_section
    upsert_section(path, "Lært", "\n".join(move), mode="append")
    result["moved"] = len(move)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default="bjorn")
    parser.add_argument("--apply", action="store_true", help="skriv (default: dry-run)")
    args = parser.parse_args()
    print(json.dumps(migrate(workspace=args.workspace, apply=args.apply),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
