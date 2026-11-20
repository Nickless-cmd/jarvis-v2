"""Fast kadence for curriculum-materialisering — uden om action-vaelgeren.

20/11-2026: `generate_curriculum` er kun en *foreslaaet* action (fase deep_work,
kl. 10-13) og blev aldrig valgt. Materialiseringen er ren DB-logik uden LLM,
saa den kan koere paa en fast kadence i stedet.

Kadencen er TIDSBASERET, ikke tik-baseret. Maalt 20/11-2026: et tik tager
~8,2 minutter (60 tik over 483 min), ikke de ~30 s som foerste udgave antog —
saa 120 tik ville vaere 16,4 timer. Samtidig er `_HEARTBEAT_TICK_COUNTER`
process-lokal og nulstilles ved hver genstart (4-5 om dagen), saa en
tik-taeller naar aldrig sin graense. Det er praecis den fejl der allerede blev
rettet for `interlanguage_practice` (heartbeat_runtime.py:1534). Nu maales der
paa tid siden sidste materialisering i stedet — immun over for baade genstart
og tik-frekvens.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Materialisér højst hver time. Uden LLM — ren DB-læsning plus op til `limit`
# indsættelser, saa et ekstra kald i timen er billigt.
CURRICULUM_INTERVAL_SECONDS = 3600

# De to origins der kan have skrevet curriculum-tasks. Begge tælles med, saa
# kadencen ikke fyrer igen lige efter action-vælgeren selv har materialiseret.
_CURRICULUM_ORIGINS = ("heartbeat:curriculum-cadence", "heartbeat:curriculum")


def _sidste_materialisering(conn: sqlite3.Connection) -> datetime | None:
    """Nyeste curriculum-task uanset origin, eller None hvis der ingen er."""
    pladsholdere = ",".join("?" for _ in _CURRICULUM_ORIGINS)
    row = conn.execute(
        f"SELECT MAX(created_at) FROM runtime_tasks WHERE origin IN ({pladsholdere})",
        _CURRICULUM_ORIGINS,
    ).fetchone()
    if not row or not row[0]:
        return None
    try:
        return datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
    except ValueError:
        # Kan tidsstemplet ikke læses, behandles det som «ingen tidligere
        # kørsel» — kadencen må ikke lammes af ét skævt felt.
        logger.warning("curriculum cadence: ulaeseligt created_at %r", row[0])
        return None


def tick_curriculum_cadence(
    *, now: datetime | None = None, db_path: str | None = None
) -> dict[str, object] | None:
    """Materialisér hvis der er gået mere end `CURRICULUM_INTERVAL_SECONDS`.

    Returnerer materialiserings-resultatet naar den fyrer, ellers None.
    Kaster aldrig — et fejlet kald maa ikke vaelte et hjerteeslag.
    """
    nu = now or datetime.now(UTC)
    sti = db_path or str(Path.home() / ".jarvis-v2" / "state" / "jarvis.db")
    try:
        with sqlite3.connect(f"file:{sti}?mode=ro", uri=True) as conn:
            sidste = _sidste_materialisering(conn)
    except Exception:
        logger.warning("curriculum cadence: kunne ikke laese sidste koersel", exc_info=True)
        return None

    if sidste is not None:
        if sidste.tzinfo is None:
            sidste = sidste.replace(tzinfo=UTC)
        alder = (nu - sidste).total_seconds()
        if alder < CURRICULUM_INTERVAL_SECONDS:
            return None

    try:
        from core.services.self_experiments import (
            materialize_learning_curriculum_tasks,
        )

        return materialize_learning_curriculum_tasks(
            limit=3,
            origin="heartbeat:curriculum-cadence",
            owner="heartbeat-runtime",
            run_id=f"heartbeat-cadence:{nu.isoformat(timespec='seconds')}",
        )
    except Exception:
        logger.warning("curriculum cadence failed", exc_info=True)
        return None
