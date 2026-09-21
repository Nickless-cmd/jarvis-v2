"""Det notifikations-feeden skal have gjort ved hver opstart (spec 2026-09-21).

Begge dele er idempotente og maa ALDRIG kunne vaelte opstarten: en feed der
ikke kan rydde op er stadig bedre end en API der ikke starter.
"""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def koer_ved_opstart() -> None:
    from core.services.notifikations_valg import migrer_kolonner
    from core.services.notifikationer import ryd_gamle
    try:
        flyttet = migrer_kolonner()
    except Exception:
        _log.warning("notifikations-valg kunne ikke migreres", exc_info=True)
    else:
        if flyttet:
            _log.info("notifikations-valg: %d valg migreret fra kolonner", flyttet)
    try:
        fjernet = ryd_gamle()
    except Exception:
        _log.warning("notifikationer kunne ikke ryddes", exc_info=True)
    else:
        if fjernet:
            _log.info("notifikationer: %d klarede raekker ryddet", fjernet)
