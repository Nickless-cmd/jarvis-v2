"""Den periodiske sweep der manglede: en ``running``-række uden ejer bliver aldrig lukket.

## Hullet (målt 14/11-2026)

``stamp_visible_run_interrupted`` fandtes, var smal og idempotent — men blev
kaldt fra præcis to steder, og begge kræver en hændelse udefra:

* ``session_boot_reconciler`` — kun ved **opstart**
* nedluknings-sweepen i ``app.py`` — kun når processen **lukker**

Der fandtes ingen periodisk runde i drift. Et run der døde midt i en tur — en
afbrudt stream, en fanget exception, en proces der blev dræbt — blev derfor
stående ``running`` indtil næste genstart. Konsekvensen er ikke kosmetisk:

``ChatView`` poller ``/chat/active-runs`` og sætter ``bgActive`` så længe
sessionen har et aktivt run. En efterladt række holder den låst, follow-effekten
genstarter ``followRun`` mod et run der aldrig sender flere events, og klienten
genåbner forbindelsen i det uendelige. Målt i journalen: attach/detach flere
gange i sekundet på et **konstant** ``from_idx``. For Bjørn så det ud som om
streamen «resetter hele tiden», og næste besked blev afvist med et
genoptagelses-varsel.

Rækken blokerer sin session indtil nogen genstarter processen. Det er derfor
denne vagt findes.

## Hvorfor tærsklen ligger over husets egen

Et run midt i et langt værktøjskald har også en gammel ``last_progress_at`` —
det er ikke det samme som dødt. ``visible_runs``' egen runde-watchdog giver op
efter ``round_silence_timeout_s`` (180 s som standard, se
``visible_runs.py:3216``). Stempler vi før det, dræber vi en tur der stadig
kører og ville have afsluttet sig selv.

``STILSTAND_S`` er derfor 420 s: 180 s + rigelig margin. Et run der har været
tavst i syv minutter er ikke «måske i gang» — det er dødt, og dets egen vagt
ville have opgivet det for fire minutter siden.

## Værnet der gør den sikker at lade køre

Vagten stempler KUN når to uafhængige kilder er enige om at runnet ikke lever:

1. **``levende_koersler``** — den delte sandhed (``state/in_flight_runs.json``
   under flock, ejer verificeret mod ``/proc``). Er runnet i det sæt, springes
   det over. Dette er cross-proces, så et run der kører i ``jarvis-runtime``
   bliver ikke stemplet af ``jarvis-api``.
2. **``run_er_terminal``** — står rækken allerede terminal, røres den ikke.

Er svaret ``None`` (kunne ikke afgøres) springes rækken over. Vi stempler ikke
på et gæt: en forkert «afbrudt» er værre end en række der venter én runde mere.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

#: Tavshed før en ``running``-række regnes efterladt. Se modul-docstringen:
#: skal ligge over husets egen 180 s tavshedsgrænse.
STILSTAND_S = 420.0

#: Hvor ofte runden kører. Et minut er nok — blokeringen mærkes i minutter.
KADENCE_S = 60.0

#: Loft pr. runde, så en ophobet bagage ikke giver én meget lang transaktion.
MAX_PR_RUNDE = 25

_vagt_startet = False
_vagt_lock = threading.Lock()
_stop = threading.Event()


def _running_raekker(stilstand_s: float) -> list[tuple[str, str]]:
    """``(run_id, started_at)`` for ``running``-rækker ældre end tærsklen.

    Kun et groft forfilter — alderen alene afgør intet. Den ægte afgørelse
    træffes i :func:`sweep_efterladte_runs` mod den delte sandhed.
    """
    from core.runtime.db import connect

    graense = (datetime.now(UTC) - timedelta(seconds=float(stilstand_s))).isoformat()
    with connect() as conn:
        rows = conn.execute(
            "SELECT run_id, started_at FROM visible_runs "
            "WHERE status = 'running' AND started_at < ? "
            "ORDER BY id ASC LIMIT ?",
            (graense, MAX_PR_RUNDE),
        ).fetchall()
    return [(str(r[0]), str(r[1] or "")) for r in rows if r and r[0]]


def sweep_efterladte_runs(*, stilstand_s: float = STILSTAND_S) -> dict[str, list[str]]:
    """Stempl ``running``-rækker der hverken lever eller er terminale.

    Returnerer ``{"stemplet": [...], "sprunget_over": [...]}`` så en måling
    bagefter kan se hvad runden gjorde — og hvad den med vilje lod være.

    Self-safe: kaster aldrig. En fejl i sweepen må ikke vælte et heartbeat.
    """
    ud: dict[str, list[str]] = {"stemplet": [], "sprunget_over": []}
    try:
        kandidater = _running_raekker(stilstand_s)
        if not kandidater:
            return ud

        from core.services.in_flight_runs import levende_koersler, mark_interrupted
        from core.services.visible_runs_outcomes import (
            run_er_terminal,
            stamp_visible_run_interrupted,
        )

        levende = {
            str(rec.get("run_id") or "")
            for rec in levende_koersler(max_alder_s=float(stilstand_s))
        }

        for rid, _started in kandidater:
            if not rid:
                continue
            if rid in levende:
                # Den delte sandhed siger den lever. Ikke vores at røre.
                ud["sprunget_over"].append(rid)
                continue
            terminal = run_er_terminal(rid)
            if terminal is not False:
                # True = allerede slut · None = vi kan ikke afgøre det.
                # Ingen af dem er grund til at stemple.
                ud["sprunget_over"].append(rid)
                continue

            # Stempl DB-rækken FØRST: det er den der blokerer klienten.
            if not stamp_visible_run_interrupted(rid, reason="efterladt uden fremgang"):
                # Rækken blev ikke rørt — den var ikke `running` længere.
                ud["sprunget_over"].append(rid)
                continue
            ud["stemplet"].append(rid)
            try:
                mark_interrupted(
                    rid,
                    reason="efterladt uden fremgang",
                    summary="rækken stod `running` uden at være levende",
                )
            except Exception:
                logger.debug("kunne ikke lukke in-flight-post for %s", rid, exc_info=True)
    except Exception:
        logger.debug("sweep af efterladte runs fejlede", exc_info=True)
    return ud


def _loop() -> None:
    """Kadence-loop. Venter ``KADENCE_S`` mellem runder, ikke på et fast ur."""
    while not _stop.is_set():
        try:
            ud = sweep_efterladte_runs()
            if ud["stemplet"]:
                logger.warning(
                    "efterladt-run-vagt: stemplede %d række(r) afbrudt: %s",
                    len(ud["stemplet"]),
                    ", ".join(ud["stemplet"][:5]),
                )
        except Exception:
            logger.debug("efterladt-run-vagt runde fejlede", exc_info=True)
        _stop.wait(KADENCE_S)


def start_efterladt_run_vagt() -> bool:
    """Start vagten én gang pr. proces. Idempotent. Returnerer True hvis startet.

    Skal kaldes fra **api-processen** — det er der chat-latensen bor, og det er
    der klienten bliver blokeret. Cross-proces-læsningen gør at den også ser
    ``jarvis-runtime``s runs uden at røre dem der lever.
    """
    global _vagt_startet
    try:
        with _vagt_lock:
            if _vagt_startet:
                return False
            _vagt_startet = True
        _stop.clear()
        threading.Thread(
            target=_loop, name="efterladt-run-vagt", daemon=True
        ).start()
        logger.info(
            "efterladt-run-vagt startet (stilstand=%.0fs, kadence=%.0fs)",
            STILSTAND_S,
            KADENCE_S,
        )
        return True
    except Exception:
        logger.debug("kunne ikke starte efterladt-run-vagt", exc_info=True)
        return False


def stop_efterladt_run_vagt() -> None:
    """Stop loopet. Idempotent; no-op hvis det aldrig startede."""
    global _vagt_startet
    try:
        _stop.set()
        with _vagt_lock:
            _vagt_startet = False
    except Exception:
        logger.debug("kunne ikke stoppe efterladt-run-vagt", exc_info=True)
