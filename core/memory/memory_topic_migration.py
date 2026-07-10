"""Selektiv memory-migration (spec 2026-07-10 Spec B, selektiv variant).

Splitter en bruger-workspaces MEMORY.md: IDENTITETS-sektioner BLIVER i MEMORY.md
(altid-loadet identitets-kerne, uændret load-sti); EPISODISKE/OPERATIONELLE
sektioner FLYTTES til memory/curated/<slug>.md + topic-index memory/INDEX.md.

- Idempotent: kører kun hvis MEMORY.md.bak ikke allerede findes.
- Reversibel: originalen bevares som MEMORY.md.bak.
- Duplikat-titler får unikke slugs (intet indholds-tab).
- KEEP-sektioner bevares ordret i original rækkefølge (også duplikater).
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
import logging

from core.identity.workspace_bootstrap import workspace_memory_paths
from core.memory.memory_topic_store import sanitize_slug, write_topic_confirmed

logger = logging.getLogger(__name__)

_HEADER_RE = re.compile(r"^(#{1,3})\s+(.*)$")

# IDENTITETS-kerne der BLIVER i MEMORY.md (altid-loadet). Match = titel (lowercase)
# indeholder en af disse nøgler. Godkendt af Bjørn 10. jul.
_KEEP_KEYS = (
    "jarvis memory",              # H1 fil-titel
    "who i am",
    "livingneuron — centralen er mig",
    "centralen — arkitektur",
    "model-valg",
    "hardware",
    "bjørns etiske fundament",
    "identitetsbeslutning",       # J.A.R.V.I.S. officielt
    "decisions",
    "forgængerens obduktion",     # Kai (jarvis-ai)
)


def _is_keep(title: str) -> bool:
    t = str(title or "").strip().lower()
    return any(k in t for k in _KEEP_KEYS)


def _hook_from(body_lines: list[str]) -> str:
    for b in body_lines:
        s = b.strip().lstrip("#*-• ").strip()
        if s:
            return s[:80]
    return ""


def _find_memory_md(name: str) -> Path | None:
    p = Path(workspace_memory_paths(name=name)["curated_memory"])  # <user>/MEMORY.md
    if p.exists() and p.read_text(encoding="utf-8").strip():
        return p
    return None


def _parse_sections(text: str) -> list[tuple[int, str, list[str]]]:
    """→ [(header_level, title, body_lines)] i original rækkefølge."""
    sections: list[tuple[int, str, list[str]]] = []
    level = 0
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            if title is not None:
                sections.append((level, title, body))
            level = len(m.group(1))
            title = m.group(2).strip()
            body = []
        elif title is not None:
            body.append(line)
    if title is not None:
        sections.append((level, title, body))
    return sections


def migrate_workspace_memory(name: str = "default") -> dict[str, Any]:
    """Selektiv split af brugerens MEMORY.md. No-op hvis allerede migreret."""
    mem = _find_memory_md(name)
    if mem is None:
        return {"migrated": False, "reason": "no-memory-file", "kept": 0, "moved": 0}
    bak = mem.with_suffix(".md.bak")
    if bak.exists():
        return {"migrated": False, "reason": "already-migrated", "kept": 0, "moved": 0}

    sections = _parse_sections(mem.read_text(encoding="utf-8"))
    kept_lines: list[str] = []
    seen_slugs: set[str] = set()
    kept = 0
    moved = 0

    for level, title, body in sections:
        if _is_keep(title):
            kept_lines.append("#" * max(1, level) + " " + title)
            kept_lines.extend(body)
            kept_lines.append("")  # blank-linje mellem sektioner
            kept += 1
            continue
        # MOVE → topic-fil. Unik slug (duplikat-titler får -2/-3 → intet tab).
        base = sanitize_slug(title) or "topic"
        slug = base
        i = 2
        while slug in seen_slugs:
            slug = f"{base}-{i}"
            i += 1
        seen_slugs.add(slug)
        topic_body = f"# {title}\n\n" + "\n".join(body).strip() + "\n"
        out = write_topic_confirmed(slug, title=title, hook=_hook_from(body),
                                    body=topic_body, name=name)
        if out.get("confirmed"):
            moved += 1

    # Backup original FØR vi overskriver MEMORY.md med kun KEEP-sektionerne.
    try:
        bak.write_text(mem.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception as exc:
        logger.debug("memory_topic_migration: backup failed: %s", exc)
        return {"migrated": False, "reason": "backup-failed", "kept": kept, "moved": moved}
    new_memory = "\n".join(kept_lines).strip() + "\n"
    mem.write_text(new_memory, encoding="utf-8")
    return {"migrated": True, "reason": "ok", "kept": kept, "moved": moved}
