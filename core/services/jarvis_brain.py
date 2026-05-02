"""Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget.

Kun ren læs/skriv + søg. Ingen daemon-logik (det ligger i jarvis_brain_daemon.py).
Ingen LLM-kald (konsolidering ligger i daemonen).

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import secrets
import time

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
