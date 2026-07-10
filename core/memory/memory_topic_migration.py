"""Engangs-migration (spec 2026-07-10 Spec B): split monolitisk MEMORY.*.md i
index + curated/<slug>.md. Idempotent + reversibel (.bak). Pr. bruger-workspace."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
import logging

from core.identity.workspace_bootstrap import workspace_memory_paths
from core.memory.memory_topic_store import sanitize_slug, write_topic_confirmed

logger = logging.getLogger(__name__)

_HEADER_RE = re.compile(r"^#{1,3}\s+(.*)$")


_MONOLITH_NAMES = ("MEMORY.da.md", "MEMORY.en.md")


def _find_monolith(name: str) -> Path | None:
    ws = Path(workspace_memory_paths(name=name)["workspace_dir"])
    for cand in _MONOLITH_NAMES:
        p = ws / cand
        if p.exists() and p.read_text(encoding="utf-8").strip():
            return p
    return None


def _already_migrated(name: str) -> bool:
    ws = Path(workspace_memory_paths(name=name)["workspace_dir"])
    for cand in _MONOLITH_NAMES:
        if (ws / cand).with_suffix(".md.bak").exists():
            return True
    return False


def migrate_workspace_memory(name: str = "default") -> dict[str, Any]:
    """Split brugerens monolit i index+topics. No-op hvis allerede migreret."""
    # Allerede migreret? (.bak fra en tidligere koersel) → no-op, uanset om den
    # aktive monolit stadig findes. Tjekkes FOER _find_monolith, saa anden
    # koersel korrekt rapporterer 'already-migrated' i stedet for 'no-monolith'.
    if _already_migrated(name):
        return {"migrated": False, "reason": "already-migrated", "topics": 0}
    mono = _find_monolith(name)
    if mono is None:
        return {"migrated": False, "reason": "no-monolith", "topics": 0}

    text = mono.read_text(encoding="utf-8")
    sections: list[tuple[str, list[str]]] = []
    cur_title: str | None = None
    cur_body: list[str] = []
    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            if cur_title is not None:
                sections.append((cur_title, cur_body))
            cur_title = m.group(1).strip()
            cur_body = []
        elif cur_title is not None:
            cur_body.append(line)
    if cur_title is not None:
        sections.append((cur_title, cur_body))

    count = 0
    for title, body_lines in sections:
        slug = sanitize_slug(title)
        if not slug:
            continue
        body = f"# {title}\n\n" + "\n".join(body_lines).strip() + "\n"
        hook = (next((b.strip() for b in body_lines if b.strip()), ""))[:80]
        out = write_topic_confirmed(slug, title=title, hook=hook, body=body, name=name)
        if out.get("confirmed"):
            count += 1

    # Reversibel: bevar originalen som .bak, fjern monolitten som aktiv kilde.
    try:
        mono.rename(mono.with_suffix(".md.bak"))
    except Exception as exc:
        logger.debug("memory_topic_migration: backup rename failed: %s", exc)
        return {"migrated": False, "reason": "backup-failed", "topics": count}
    return {"migrated": True, "reason": "ok", "topics": count}
