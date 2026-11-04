"""Arkivering uden for glemselsreglerne: undtagelser og genoprettelse.

Brain-poster glemmes automatisk (observation: halveringstid 14 dage, arkiveres under
saliens 0,05 ≈ 29 dage; `jarvis_brain_daemon`: 90 dage). Det er rigtigt for en
enkeltstående observation og forkert for en dagbog, hvis hele formål er at kunne slå en
dag op måneder efter. Målt 4/11-2026: 58 af 147 backfillede dagbøger blev arkiveret
inden for minutter. Et tag (`daily-journal`) undtager dem — som `reference` allerede er.

`archive_entry` havde intet modstykke; `restore_entry` er det.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.services import jarvis_brain

logger = logging.getLogger(__name__)

UNDTAGNE_TAGS = frozenset({"daily-journal"})


def er_undtaget(entry: Any) -> bool:
    """Skal posten springes over af de automatiske arkiverere? Dict eller BrainEntry."""
    tags = entry.get("tags") if isinstance(entry, dict) else getattr(entry, "tags", None)
    return bool(UNDTAGNE_TAGS & set(tags or []))


def sql_ikke_undtaget() -> str:
    """WHERE-led der holder undtagne poster UDE af en kandidatpulje. Uden det fylder de
    puljen (ældste, uanvendte, lavest saliens) og fortrænger det der faktisk skal glemmes."""
    return "".join(f" AND tags NOT LIKE '%\"{t}\"%'" for t in sorted(UNDTAGNE_TAGS))


def restore_entry(entry_id: str, *, now: datetime | None = None) -> str:
    """Hent en arkiveret post tilbage: «restored» | «not-archived» | «unknown».

    Filen flyttes tilbage til `<kind>/`, status bliver `active`, og indeks-rækken
    beholder id og embedding — kun sti, hash og stat skifter, så et reindex-pas bagefter
    ikke ser en ændring.
    """
    now = now or datetime.now(UTC)
    conn = jarvis_brain.connect_index()
    try:
        row = conn.execute("SELECT status FROM brain_index WHERE id = ?", (entry_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return "unknown"
    if row[0] != "archived":
        return "not-archived"

    entry = jarvis_brain.read_entry(entry_id)
    entry.status = "active"
    entry.updated_at = now
    old_path = jarvis_brain._workspace_root() / jarvis_brain._index_path_for(entry_id)
    new_path = jarvis_brain.brain_dir() / entry.kind / old_path.name
    md = jarvis_brain.render_entry_markdown(entry)
    jarvis_brain._atomic_write(new_path, md)
    if old_path.exists() and old_path != new_path:
        old_path.unlink()

    stat = new_path.stat()
    conn = jarvis_brain.connect_index()
    try:
        conn.execute(
            "UPDATE brain_index SET status='active', path=?, file_hash=?, file_mtime_ns=?, "
            "file_size=?, updated_at=?, indexed_at=? WHERE id=?",
            (str(new_path.relative_to(jarvis_brain._workspace_root())), jarvis_brain._file_hash(md),
             stat.st_mtime_ns, stat.st_size, jarvis_brain._iso(now), jarvis_brain._iso(now), entry_id),
        )
        conn.commit()
    finally:
        conn.close()
    return "restored"


def restore_exempt_archived() -> dict[str, int]:
    """Hent ALLE arkiverede poster med et undtaget tag tilbage. Idempotent."""
    like = " OR ".join("tags LIKE ?" for _ in UNDTAGNE_TAGS)
    conn = jarvis_brain.connect_index()
    try:
        ids = [r[0] for r in conn.execute(
            f"SELECT id FROM brain_index WHERE status = 'archived' AND ({like})",
            [f'%"{t}"%' for t in sorted(UNDTAGNE_TAGS)],
        )]
    finally:
        conn.close()
    talt = {"restored": 0, "failed": 0}
    for entry_id in ids:
        try:
            talt["restored" if restore_entry(entry_id) == "restored" else "failed"] += 1
        except Exception as exc:  # noqa: BLE001 — én brudt post må ikke stoppe de øvrige
            logger.warning("brain_archive: %s kunne ikke gendannes: %s", entry_id, exc)
            talt["failed"] += 1
    return talt
