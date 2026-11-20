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

import json
import logging
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Materialisér højst hver time. Uden LLM — ren DB-læsning plus op til `limit`
# indsættelser, saa et ekstra kald i timen er billigt.
CURRICULUM_INTERVAL_SECONDS = 3600

# Desk-maalingen (`npx vitest run` i rigtig Chromium, ~9 s + node) er meget
# dyrere end en DB-laesning, saa den har sit EGET, laengere interval. 6 timer:
# suiten aendrer sig kun naar koden goer, og et par maalinger i doegnet fanger
# en regression uden at holde en browser i gang hele tiden.
DESK_MEASUREMENT_INTERVAL_SECONDS = 6 * 3600

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


def _aktiv_db_sti() -> str:
    from core.runtime import db_core

    return str(db_core.DB_PATH)


def _samme_base(a: str, b: str) -> bool:
    return Path(a).expanduser().resolve() == Path(b).expanduser().resolve()


def tick_curriculum_cadence(
    *, now: datetime | None = None, db_path: str | None = None
) -> dict[str, object] | None:
    """Materialisér hvis der er gået mere end `CURRICULUM_INTERVAL_SECONDS`.

    Returnerer materialiserings-resultatet naar den fyrer, ellers None.
    Kaster aldrig — et fejlet kald maa ikke vaelte et hjerteeslag.

    `db_path` styrer LAESNINGEN, men skrivningen gaar via `runtime_tasks` ->
    `db_core.DB_PATH` og kan ikke peges andetsteds. Maalt 20/11-2026 04:24Z: et
    kald med teststi skrev tre tasks i den levende base. Derfor: default er
    `db_core.DB_PATH`, og et `db_path` der ikke er SAMME base afvises med
    markoeren `refused=db_path_mismatch` — der laeses og skrives aldrig i hver
    sin base. Tests isolerer ved at pege `db_core.DB_PATH` paa deres tmp-base.
    """
    nu = now or datetime.now(UTC)
    aktiv = _aktiv_db_sti()
    sti = db_path or aktiv
    if not _samme_base(sti, aktiv):
        logger.error(
            "curriculum cadence: db_path %s != db_core-base %s — afvist, intet skrevet",
            sti,
            aktiv,
        )
        return {"refused": "db_path_mismatch", "db_path": sti, "db_core_path": aktiv}
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


# --- desk-maaling -----------------------------------------------------------

_desk_lock = threading.Lock()


def _desk_stempel_sti() -> Path:
    # Ved siden af den aktive base: isoleret base => isoleret stempel.
    return Path(_aktiv_db_sti()).parent / "desk_render_measurement_last.json"


def _laes_desk_stempel() -> datetime | None:
    sti = _desk_stempel_sti()
    if not sti.is_file():
        return None
    try:
        t = datetime.fromisoformat(json.loads(sti.read_text())["started_at"])
    except (ValueError, KeyError, TypeError, OSError):
        logger.warning("desk measurement: ulaeseligt stempel %s", sti, exc_info=True)
        return None
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _skriv_desk_stempel(nu: datetime) -> None:
    sti = _desk_stempel_sti()
    sti.parent.mkdir(parents=True, exist_ok=True)
    tmp = sti.with_suffix(".tmp")
    tmp.write_text(json.dumps({"started_at": nu.isoformat()}))
    tmp.replace(sti)


def _maal_desk() -> None:
    try:
        from core.services import desk_render_capability

        result = desk_render_capability.record()
        logger.info(
            "desk measurement: measured=%s ok=%s",
            result.get("measured"),
            result.get("ok"),
        )
    except Exception:
        logger.warning("desk measurement failed", exc_info=True)
    finally:
        _desk_lock.release()


def _spawn(fn) -> None:
    """Baggrundstraad: maalingen tager ~9 s og maa ikke blokere hjerteslaget."""
    threading.Thread(target=fn, name="desk-render-measurement", daemon=True).start()


def tick_desk_measurement_cadence(
    *, now: datetime | None = None
) -> dict[str, object] | None:
    """Kør `desk_render_capability.record()` hvis der er gået
    `DESK_MEASUREMENT_INTERVAL_SECONDS` siden sidste start.

    Tidsbaseret og persisteret (stempelfil), af samme grund som curriculum-
    kadencen: tik-taelleren nulstilles ved genstart. Stemplet skrives FOER
    maalingen, saa en fejlende maaling ikke genprøves hvert tik. Kaster aldrig.
    """
    nu = now or datetime.now(UTC)
    try:
        sidste = _laes_desk_stempel()
        if sidste is not None and (nu - sidste).total_seconds() < DESK_MEASUREMENT_INTERVAL_SECONDS:
            return None
        if not _desk_lock.acquire(blocking=False):
            return None  # en maaling koerer allerede
        try:
            _skriv_desk_stempel(nu)
            _spawn(_maal_desk)  # _maal_desk frigiver laasen
        except Exception:
            _desk_lock.release()
            raise
        return {"started": True, "at": nu.isoformat(timespec="seconds")}
    except Exception:
        logger.warning("desk measurement cadence failed", exc_info=True)
        return None
