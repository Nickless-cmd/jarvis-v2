"""Boot-reconciler: crash-zombie runs → interrupted, så de genoptages.

Ved en hård container-crash kører et run's ``finally`` (mark_interrupted/
mark_completed) ALDRIG → record'en i ``in_flight_runs`` står ``status='running'``
= zombie. ``interrupted_for_session`` returnerer kun ``interrupted``-records, så
zombien surfacer ALDRIG i prompt'en — og næste ``mark_started`` dropper den.
Crash-afbrudt arbejde forsvinder tavst.

Denne reconciler kaldes ved opstart (efter state-store er klar, før trafik). Den
flipper forældede ``running``-records → ``interrupted``, så den EKSISTERENDE
``interruption_prompt_section`` genoptager sessionen næste tur.

Governance (§5.5):
- Kill-switch ``session_persistence`` (default OFF = shadow). OFF → observe-only:
  tæl hvad DER VILLE ske, skriv INTET. ON → udfør ``mark_interrupted``.
- Fail-open: hele kroppen i try/except. En reconciler-fejl må ALDRIG crashe opstart.
- Idempotent: kun ``running → interrupted``; api- og runtime-processen deler samme
  entrypoint, så begge kalder den — anden kørsel finder intet nyt.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.services import in_flight_runs

logger = logging.getLogger(__name__)

# Konservativ tærskel: > _MIN_AGE_TO_SURFACE_SECONDS (=90s) OG > længste realistiske
# run. Under den er en 'running'-record sandsynligvis bare stadig-streamende på en
# anden worker, ikke en ægte crash-zombie.
STALE_AFTER_SECONDS = 600.0

_INTERRUPTION_REASON = "afbrudt af container-genstart"

#: Hvor gammel skal en `visible_runs`-række være, før fraværet i
#: `in_flight_runs` tolkes som drift og ikke som et kapløb ved opstart?
#:
#: Seks timer, ikke ti minutter. Tærsklen ovenfor (600 s) hviler på ET
#: EJERSKAB — pid plus proces-starttid — og kan derfor være stram. Denne her
#: hviler på et FRAVÆR, og et fravær kan skyldes en startvej der (endnu) ikke
#: skriver begge spor. Så længe vi ikke kan afgøre ejerskab, skal alderen bære
#: hele beviset alene, og den længste kørsel målt i huset er minutter.
VISIBLE_DRIFT_AFTER_SECONDS = 6 * 3600.0


def _observe(payload: dict[str, Any]) -> None:
    """Fyr central-nerve ``session_persistence`` (cluster runtime). Best-effort,
    kaster aldrig (Central.observe er selv fail-safe, men vær dobbelt-sikker)."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "runtime",
            "nerve": "session_persistence",
            **payload,
        })
    except Exception:
        pass


def reconcile_on_boot(stale_after_s: float = STALE_AFTER_SECONDS) -> dict[str, Any]:
    """Reconcile crash-zombie runs ved opstart. Fail-open.

    Returnerer en summary-dict: ``{count, enforced, kinds, error}``.
    - ``count``: antal zombier reconcileret (ON) eller som VILLE reconcileres (OFF).
    - ``enforced``: om kill-switchen var ON (ægte skrivning) eller OFF (observe-only).
    - ``kinds``: sorterede unikke run-kinds blandt zombierne.
    """
    try:
        from core.services.session_persistence_flag import session_persistence_enabled
        enforced = bool(session_persistence_enabled())
    except Exception:
        enforced = False

    try:
        orphans = in_flight_runs.list_running_orphans(stale_after_s)
    except Exception as exc:
        logger.warning("session_boot_reconciler: list_running_orphans failed: %s", exc)
        return {"count": 0, "enforced": enforced, "kinds": [], "error": True}

    kinds = sorted({str(o.get("kind") or "visible") for o in orphans})
    count = len(orphans)

    if enforced:
        for rec in orphans:
            run_id = str(rec.get("run_id") or "")
            if not run_id:
                continue
            try:
                in_flight_runs.mark_interrupted(run_id, reason=_INTERRUPTION_REASON)
                # 12/9-2026: spejl stemplet ind i `visible_runs`. Uden dette stod
                # rækken `running` for evigt efter et crash — og et run der aldrig
                # blev afsluttet så ud som et der stadig kørte. Kun `running`
                # rækker rammes, så et rigtigt udfald ikke kan overskrives.
                try:
                    from core.services.visible_runs_outcomes import (
                        stamp_visible_run_interrupted,
                    )
                    stamp_visible_run_interrupted(
                        run_id, reason=_INTERRUPTION_REASON)
                except Exception:
                    pass
            except Exception as exc:  # noqa: BLE001 — én fejl må ikke stoppe resten
                logger.warning(
                    "session_boot_reconciler: mark_interrupted(%s) failed: %s",
                    run_id, exc,
                )

    drift = _ryd_visible_drift(enforced)

    summary: dict[str, Any] = {
        "count": count,
        "enforced": enforced,
        "kinds": kinds,
        "error": False,
        "visible_drift": drift,
    }

    try:
        _observe({"count": count, "enforced": enforced, "kinds": kinds})
    except Exception:
        pass

    if count:
        logger.info(
            "session_boot_reconciler: %d crash-zombie(s) %s (kinds=%s)",
            count,
            "reconciled → interrupted" if enforced else "observed (shadow, no write)",
            ",".join(kinds) or "-",
        )

    if drift:
        logger.warning(
            "session_boot_reconciler: %d visible_runs-raekke(r) stod 'running' "
            "uden en post i in_flight_runs %s",
            drift,
            "— stemplet" if enforced else "— SKYGGE, intet skrevet",
        )

    return summary


def _ryd_visible_drift(enforced: bool) -> int:
    """`visible_runs`-rækker der står `running` og som INTET kender.

    ## Hullet

    `list_running_orphans` itererer over `in_flight_runs`. En række der findes i
    `visible_runs` men aldrig blev skrevet — eller blev ryddet — i det andet
    lager er derfor usynlig for reconcileren **for altid**.

    Målt 13/9-2026: `autonomous-53cc4ddf…` stod `running` uden `finished_at`
    siden 12/9 kl. 20:19, altså ~20 timer, mens reconcileren rapporterede
    `count: 0` ved hver eneste opstart. Begge dele var sande. De så bare på hvert
    sit lager.

    ## Hvorfor fraværet er signalet

    Hver startvej skriver begge spor — `autonomous_stream_run` gør det endda
    synkront i api-processen med en kommentar om præcis den fejl. Er posten væk
    fra `in_flight_runs`, er der ingen proces der streamer den.

    Men fravær er et svagere bevis end ejerskab, og derfor bærer alderen resten:
    seks timer, mod de ti minutter der gælder når vi kan spørge om en pid.
    En kørsel der har været «i gang» i seks timer er død efter enhver målestok
    huset kender — medianen er 77 sekunder.

    Skygge følger samme kontakt som resten af reconcileren. Kaster aldrig.
    """
    try:
        from core.runtime.db import connect
    except Exception:
        return 0
    try:
        graense = (datetime.now(UTC)
                   - timedelta(seconds=VISIBLE_DRIFT_AFTER_SECONDS)).isoformat()
        with connect() as conn:
            raekker = conn.execute(
                "SELECT run_id FROM visible_runs WHERE status = 'running' "
                "AND (finished_at IS NULL OR finished_at = '') "
                "AND started_at < ? LIMIT 200",
                (graense,),
            ).fetchall()
    except Exception as exc:
        logger.warning("session_boot_reconciler: visible-drift-opslag fejlede: %s", exc)
        return 0

    kendte: set[str] = set()
    try:
        kendte = {str(r.get("run_id") or "") for r in in_flight_runs._load().values()}
    except Exception as exc:
        # Kan vi ikke laese det andet lager, kan vi ikke vide at posten er
        # ukendt — og saa stempler vi ikke. Et gaet er ikke et fravaer.
        # MEN: fejlen skal ses. Sker den ved hver opstart, ryddes intet, og
        # uden denne linje ville det aldrig staa nogen steder.
        logger.warning(
            "session_boot_reconciler: kunne ikke laese in_flight_runs — "
            "rydder ingen visible-drift denne gang: %s", exc)
        return 0

    drift = [str(r[0]) for r in raekker if str(r[0]) and str(r[0]) not in kendte]
    if enforced:
        for rid in drift:
            try:
                from core.services.visible_runs_outcomes import (
                    stamp_visible_run_interrupted,
                )
                stamp_visible_run_interrupted(
                    rid, reason="proces doede uden at afslutte koerslen")
            except Exception as exc:
                # Tavs slugning her gjorde netop DENNE fejl usynlig: importen
                # af `visible_runs_outcomes` er cirkulaer og kan fejle hvis
                # `visible_runs` endnu ikke er importeret. Uden loggen ville
                # raekken bare blive staaende `running` — igen.
                logger.warning(
                    "session_boot_reconciler: kunne ikke stemple %s som "
                    "interrupted: %s", rid, exc)
    return len(drift)
