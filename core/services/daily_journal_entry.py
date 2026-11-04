"""Dagbøger som rigtige brain-poster.

`daily_journal` skrev `YYYY-MM-DD-daily.md` ind i `jarvis_brain/observation/` uden
frontmatter. Hjerne-indekset gennemsøger mappen, men kræver frontmatter — så ingen af
de 147 dagbøger nåede nogensinde ind i indekset, og det de blev bygget til (at kunne
huske en hel dag) kunne ikke genfindes. Målt 4/11-2026.

Filnavnet bevares (idempotensen i `daily_journal` hviler på det); kun frontmatter
tilføjes, gennem hjernens egen renderer. `intimate`: dagbogen opsummerer en hel dags
samtaler, og `memory_recall_engine` slår op med loftet `personal` uden at kende
brugeren — medlemmer får `public_safe`, og kun ejerens værktøjer løfter til `intimate`.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime
from pathlib import Path

from core.services import jarvis_brain

logger = logging.getLogger(__name__)

_NAVN = re.compile(r"^(\d{4}-\d{2}-\d{2})-daily\.md$")
_STEMPEL = re.compile(r"_Synthesized (\S+) ")


def _dag(path: Path) -> date | None:
    m = _NAVN.match(path.name)
    if m is None:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:  # 2026-02-31 matcher mønstret men er ingen dato → ikke en dagbog
        return None


def _oprettet(tekst: str, path: Path) -> datetime:
    """Dagbogens egen stempel; ellers filens ændringstid. Aldrig «nu» — en gammel
    dagbog skal ældes som den gamle dag den er, ikke som dagen den blev rettet."""
    m = _STEMPEL.search(tekst[:600])
    if m:
        try:
            ts = datetime.fromisoformat(m.group(1))
            return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
        except ValueError:
            logger.debug("daily_journal_entry: ulæseligt stempel %r i %s", m.group(1), path.name)
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def _markdown(dag: date, tekst: str, oprettet: datetime, entry_id: str) -> str:
    vigtighed = jarvis_brain._IMPORTANCE_BY_KIND["observation"]
    entry = jarvis_brain.BrainEntry(
        id=entry_id, kind="observation", visibility="intimate", domain="self",
        title=f"Daily journal — {dag.isoformat()}", content=tekst,
        created_at=oprettet, updated_at=oprettet, last_used_at=None,
        salience_base=vigtighed, salience_bumps=0, importance=vigtighed,
        related=[], tags=["daily-journal"], trigger="daily_journal",
        status="active", superseded_by=None, source_chronicle=None, source_url=None,
    )
    return jarvis_brain.render_entry_markdown(entry)


def ensure_frontmatter(path: Path) -> str:
    """Giv én dagbog frontmatter. «added» | «present» | «skipped:<grund>». Idempotent."""
    dag = _dag(path)
    if dag is None:
        return "skipped:not-a-daily-journal"
    try:
        tekst = path.read_text(encoding="utf-8")
        if tekst.startswith("---\n"):
            return "present"
        jarvis_brain._atomic_write(
            path, _markdown(dag, tekst, _oprettet(tekst, path), jarvis_brain.new_brain_id()),
        )
    except OSError as exc:
        logger.warning("daily_journal_entry: %s kunne ikke læses/skrives: %s", path.name, exc)
        return "skipped:unreadable"
    return "added"


def write_journal(path: Path, dag: date, tekst: str, *, nu: datetime | None = None) -> None:
    """Skriv en dagbog som brain-post. Overskriver (force) beholder det gamle id, så
    indekset ikke får to poster for samme fil."""
    entry_id = jarvis_brain.new_brain_id()
    if path.exists():
        try:
            entry_id = str(jarvis_brain.parse_frontmatter(path)[0].get("id") or entry_id)
        except (OSError, ValueError):  # gammel fil uden frontmatter: ingen id at bevare
            logger.debug("daily_journal_entry: intet id at bevare i %s", path.name)
    jarvis_brain._atomic_write(path, _markdown(dag, tekst, nu or datetime.now(UTC), entry_id))


def backfill(directory: Path | None = None) -> dict[str, int]:
    """Giv alle dagbøger uden frontmatter en. Idempotent; reindex-løkken indekserer dem."""
    mappe = directory or jarvis_brain.brain_dir() / "observation"
    talt = {"added": 0, "present": 0, "skipped": 0, "total": 0}
    for path in sorted(mappe.glob("*-daily.md")):
        udfald = ensure_frontmatter(path).split(":", 1)[0]
        talt[udfald] += 1
        talt["total"] += 1
    return talt
