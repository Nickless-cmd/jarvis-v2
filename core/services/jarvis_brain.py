"""Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget.

Kun ren læs/skriv + søg. Ingen daemon-logik (det ligger i jarvis_brain_daemon.py).
Ingen LLM-kald (konsolidering ligger i daemonen).

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import secrets
import time

import yaml

# Prøv python-ulid først, fallback til lokal Crockford b32 generator.
try:
    import ulid as _ulid_mod  # type: ignore

    def new_brain_id() -> str:
        return f"brn_{_ulid_mod.new().str}"
except ImportError:
    _CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # pragma: allowlist secret

    def new_brain_id() -> str:
        ms = int(time.time() * 1000)
        time_part = ""
        for _ in range(10):
            time_part = _CROCKFORD[ms & 0x1F] + time_part
            ms >>= 5
        rand_part = "".join(secrets.choice(_CROCKFORD) for _ in range(16))
        return f"brn_{time_part}{rand_part}"


_VALID_KINDS = {"fakta", "indsigt", "observation", "reference"}
_VALID_VISIBILITY = {"public_safe", "personal", "intimate"}
_VALID_STATUS = {"active", "superseded", "archived"}
_VALID_TRIGGER = {
    "spontaneous",
    "post_web_search",
    "reflection_slot",
    "adopted_proposal",
}


@dataclass
class BrainEntry:
    id: str
    kind: str
    visibility: str
    domain: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    salience_base: float
    salience_bumps: int
    related: list[str]
    trigger: str
    status: str
    superseded_by: Optional[str]
    source_chronicle: Optional[str]
    source_url: Optional[str]

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"invalid kind: {self.kind!r}")
        if self.visibility not in _VALID_VISIBILITY:
            raise ValueError(f"invalid visibility: {self.visibility!r}")
        if self.status not in _VALID_STATUS:
            raise ValueError(f"invalid status: {self.status!r}")
        if self.trigger not in _VALID_TRIGGER:
            raise ValueError(f"invalid trigger: {self.trigger!r}")


# ---------------------------------------------------------------------------
# File I/O helpers — frontmatter + atomic write
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str) -> None:
    """Atomic file write via tmp + rename. Creates parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter + body from a markdown file.

    Returns (frontmatter_dict, body_string). Raises ValueError if frontmatter
    is missing or unterminated.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing frontmatter in {path}")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"unterminated frontmatter in {path}")
    yaml_text = parts[0][len("---\n"):]
    body = parts[1]
    fm = yaml.safe_load(yaml_text) or {}
    if not isinstance(fm, dict):
        raise ValueError(f"frontmatter is not a mapping in {path}")
    return fm, body


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    return datetime.fromisoformat(s)


def render_entry_markdown(entry: BrainEntry) -> str:
    """Render a BrainEntry as markdown with YAML frontmatter."""
    fm = {
        "id": entry.id,
        "kind": entry.kind,
        "visibility": entry.visibility,
        "domain": entry.domain,
        "title": entry.title,
        "created_at": _iso(entry.created_at),
        "updated_at": _iso(entry.updated_at),
        "last_used_at": _iso(entry.last_used_at),
        "created_by": "visible_jarvis",
        "trigger": entry.trigger,
        "salience_base": entry.salience_base,
        "salience_bumps": entry.salience_bumps,
        "related": entry.related,
        "status": entry.status,
        "superseded_by": entry.superseded_by,
        "source_chronicle": entry.source_chronicle,
        "source_url": entry.source_url,
    }
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_text}---\n\n{entry.content.rstrip()}\n"


def entry_from_frontmatter(fm: dict, body: str) -> BrainEntry:
    """Build a BrainEntry from parsed frontmatter dict + body string."""
    return BrainEntry(
        id=fm["id"],
        kind=fm["kind"],
        visibility=fm["visibility"],
        domain=fm["domain"],
        title=fm["title"],
        content=body.strip(),
        created_at=_parse_iso(fm["created_at"]),
        updated_at=_parse_iso(fm.get("updated_at") or fm["created_at"]),
        last_used_at=_parse_iso(fm.get("last_used_at")),
        salience_base=float(fm.get("salience_base", 1.0)),
        salience_bumps=int(fm.get("salience_bumps", 0)),
        related=list(fm.get("related") or []),
        trigger=fm.get("trigger", "spontaneous"),
        status=fm.get("status", "active"),
        superseded_by=fm.get("superseded_by"),
        source_chronicle=fm.get("source_chronicle"),
        source_url=fm.get("source_url"),
    )
