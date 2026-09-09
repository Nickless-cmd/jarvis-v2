"""Hvad der sker naar et run doer midt-flugt.

Udskilt fra `visible_runs.py` (7.291 linjer) efter Boy Scout-reglen, foer K6
lagde godkendelses-broens opgivelse ind samme sted.

De fire ting her hoerer sammen: de svarer alle paa «runnet naaede aldrig sin
beslutning — hvad skal saa vaere sandt bagefter?»

  * Central-nerven, saa abort-raten kan ses stige.
  * En rigtig incident, fordi observe() alene gaar i en flygtig ring-buffer
    per proces og var vaek ved genstart — panelet saa derfor ALDRIG cut-offs.
  * En rolig besked til brugeren, saa han ikke moeder tavshed ved reload.
  * Og nu: godkendelses-broens poster for runnet.

## Den sidste er K6

«disconnect tests distinguish `aborted_before_dispatch` from
`outcome_unknown`.» Broen KUNNE skelne fra dag ét — `abandon()` svarer
forskelligt alt efter tilstand. Men INGEN kaldte den. Skelnen der aldrig
foretages, er ikke en skelnen; posten blev bare liggende som `dispatching`
for evigt, og saa betyder «udfald ukendt» ingenting.

Forskellen er ikke akademisk:

    prepared/approved → `aborted_before_dispatch` — handlingen skete ALDRIG.
                        Sikkert at proeve igen.
    dispatching       → `outcome_unknown` — vi naaede at afsende og saa aldrig
                        udfaldet. K7 forbyder et automatisk genforsoeg her,
                        fordi et gentaget ikke-idempotent kald kan goere
                        skaden to gange.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _loop_lag() -> float:
    """Hvor sultent var event-loopet lige nu?

    Korrelationen Bjoern bad om 4. juli: klynger cut-offs sig ved lag-spikes
    (kontention) eller ej (uforklaret)?
    """
    try:
        from core.services.central_loop_lag import recent_peak_ms
        return round(recent_peak_ms(10.0), 1)
    except Exception:
        return -1.0


def report_abandoned_run(run: Any, *, abort_kind: str, run_stage: Any,
                         visible_len: int) -> None:
    """Rapportér et run der aldrig naaede sin beslutning. Kaster aldrig."""
    lag = _loop_lag()

    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "loop", "nerve": "run_abandoned_midflight",
            "run_id": str(run.run_id or ""), "provider": str(run.provider or ""),
            "model": str(run.model or ""), "abort": str(abort_kind),
            "stage": str(run_stage), "vis_len": int(visible_len),
            "loop_lag_peak_ms": lag,
        })
    except Exception:
        pass

    # observe() alene gik i en flygtig ring-buffer per proces og var vaek ved
    # genstart → central_incidents fik 0 raekker → panelet saa ALDRIG cut-offs.
    # dedup: gentagne cut-offs bumper en tael-op i stedet for at oversvoemme.
    try:
        from core.runtime.db_central_incidents import record_central_incident
        record_central_incident(
            cluster="loop", nerve="run_abandoned_midflight",
            kind="cutoff", severity="error",
            message=(f"run afbrudt midt-flugt: abort={abort_kind} "
                     f"provider={run.provider or '?'} model={run.model or '?'} "
                     f"stage={run_stage} vis_len={visible_len} "
                     f"loop_lag_peak_ms={lag}"),
            run_id=str(run.run_id or ""),
            session_id=str(run.session_id or ""),
            dedup=True,
        )
    except Exception:
        pass

    abandon_bridge_records(run)


def abandon_bridge_records(run: Any) -> dict[str, int]:
    """K6: giv runnets uafklarede godkendelses-poster deres AERLIGE udfald.

    Returnerer antal pr. udfald. Kaster aldrig — et run der doer, maa ikke
    doe én gang til paa vej ud.
    """
    try:
        from core.runtime.db_approval_bridge import abandon_run
        ud = abandon_run(str(run.run_id or ""),
                         detail=f"run doede: {run.run_id}")
        if ud.get("outcome_unknown"):
            # Dét er den alvorlige: vi afsendte og saa aldrig udfaldet.
            logger.warning(
                "K6: run=%s efterlod %d handling(er) med UKENDT udfald "
                "(afsendt, aldrig set afsluttet) og %d der aldrig skete",
                run.run_id, ud.get("outcome_unknown", 0),
                ud.get("aborted_before_dispatch", 0))
        return ud
    except Exception:
        logger.warning("K6: kunne ikke opgive broens poster for run=%s",
                       getattr(run, "run_id", "?"), exc_info=True)
        return {}
