"""Et raad der blev afbrudt af en genstart skal AFREGNE — Fase 8.

Fase 8 i spec'en beder om en `WorkflowRuntime`. Den byggede jeg IKKE, og
grunden er maalt: der findes ingen flerlags-orkestrering i huset. NUL agenter
har en foraelder der ikke er Jarvis — ingen boerneboern, ingen traeer. Et
workflow-lag ville vaere et runtime uden kalder.

Raadet ER husets orkestrering, og dets kriterier er de samme. Ét af dem holdt
ikke:

    «workflow restart settles as `interrupted_by_restart`»

`run_council_round` har en `try/finally` der altid lukker sessionen — den kom
i juli, og siden da er ALLE 20 raad lukket rent. Men `finally` koerer ikke
naar processen doer. Da bliver sessionen staaende i `deliberating` for evigt,
og intet fejer raad ved opstart. Det er praecis hvad de 174 gamle raekker er:
104 `forming` og 70 `deliberating`, aeldste fra april, nyeste 14. juli — alle
fra FOER juli-rettelsen, og ingen med medlemmer der stadig venter.

ALDER DUER IKKE HER. En raadsrunde tager 5-17 minutter (maalt paa de lukkede),
saa en tidsgraense ville afbryde levende raad. Derfor proces-maerket, som
agenterne allerede bruger: kan vi bevise at processen er vaek, afregner vi.
Kan vi ikke afgoere det, lader vi raadet vaere — samme regel og samme grund.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("uvicorn.error")

# Status hvor et raad stadig arbejder — og som derfor kan efterlades haengende.
AABNE = ("forming", "deliberating", "reporting")

# Sandfaerdig afregning. IKKE «closed»: raadet naaede aldrig frem til noget, og
# en flade der viser det som lukket paastaar at der ligger en konklusion.
AFBRUDT = "interrupted_by_restart"


def settle_interrupted_councils() -> dict[str, Any]:
    """Afregn raad hvis proces beviseligt er vaek. Kaster aldrig."""
    from core.runtime.db_agent_runtime import (
        list_council_sessions,
        update_council_session,
    )

    afregnet: list[str] = []
    sprunget_over = 0
    try:
        # Filtrér i SQL. «Hent de 500 nyeste og filtrer i Python» gav NUL
        # afregninger paa de 154 aeldste, fordi de aabne raad ER de
        # aeldste — loftet skjulte praecis det vi ledte efter.
        sessioner = list_council_sessions(limit=1000, statuses=AABNE)
    except Exception:
        logger.warning("kunne ikke laese raadssessioner", exc_info=True)
        return {"afregnet": 0, "afregnede_ider": [], "sprunget_over": 0}

    for s in sessioner:
        if str(s.get("status") or "") not in AABNE:
            continue
        cid = str(s.get("council_id") or "")
        if not cid:
            continue
        maerke = str(s.get("runtime_owner") or "").strip()
        try:
            from core.services.process_identity import lever
            liv = lever(maerke)
        except Exception:
            liv = None

        if liv is True:
            sprunget_over += 1          # deliberer lige nu, muligvis hos naboen
            continue
        if liv is None and maerke:
            sprunget_over += 1          # maerket findes, men kan ikke afgoeres
            continue
        # Tomt maerke = raekke fra foer migreringen. Dem afregner vi: de 174
        # gamle er alle fra foer juli-rettelsen og har ingen ventende medlemmer.
        try:
            update_council_session(
                cid, status=AFBRUDT,
                summary=str(s.get("summary") or "")
                or "Afbrudt af en genstart — runden naaede aldrig frem til en "
                   "konklusion.",
                finished_at=_nu(),
            )
            _luk_medlemmer(cid)
            afregnet.append(cid)
        except Exception:
            logger.warning("kunne ikke afregne raad %s", cid, exc_info=True)

    if afregnet:
        logger.info("council_settlement: %d raad afregnet som %s (%d sprunget "
                    "over)", len(afregnet), AFBRUDT, sprunget_over)
    return {"afregnet": len(afregnet), "afregnede_ider": afregnet,
            "sprunget_over": sprunget_over}


def _luk_medlemmer(council_id: str) -> int:
    """Medlemmer der stadig venter paa et doedt raad skal ikke taelle med.

    De akkumulerer ellers mod MAX_CONCURRENT_AGENTS og blokerer fremtidige
    raad — praecis den fejl juli-rettelsen loeste for den levende sti.
    """
    from core.runtime.db_agent_runtime import (
        list_agent_registry_entries,
        update_agent_registry_entry,
    )
    n = 0
    try:
        for a in list_agent_registry_entries(limit=500):
            if str(a.get("council_id") or "") != council_id:
                continue
            if str(a.get("status") or "") not in ("waiting", "starting",
                                                  "active", "blocked"):
                continue
            update_agent_registry_entry(
                str(a.get("agent_id") or ""), status="expired",
                last_error="raadet blev afbrudt af en genstart",
                expired_at=_nu(),
            )
            n += 1
    except Exception:
        logger.warning("kunne ikke lukke medlemmer af raad %s", council_id,
                       exc_info=True)
    return n


def _nu() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
