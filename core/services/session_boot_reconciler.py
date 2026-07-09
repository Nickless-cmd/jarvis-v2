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
from typing import Any

from core.services import in_flight_runs

logger = logging.getLogger(__name__)

# Konservativ tærskel: > _MIN_AGE_TO_SURFACE_SECONDS (=90s) OG > længste realistiske
# run. Under den er en 'running'-record sandsynligvis bare stadig-streamende på en
# anden worker, ikke en ægte crash-zombie.
STALE_AFTER_SECONDS = 600.0

_INTERRUPTION_REASON = "afbrudt af container-genstart"


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
            except Exception as exc:  # noqa: BLE001 — én fejl må ikke stoppe resten
                logger.warning(
                    "session_boot_reconciler: mark_interrupted(%s) failed: %s",
                    run_id, exc,
                )

    summary: dict[str, Any] = {
        "count": count,
        "enforced": enforced,
        "kinds": kinds,
        "error": False,
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

    return summary
