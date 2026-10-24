"""Modsigelses-detektion — «den nyere vinder».

## Hvorfor (målt 24/10-2026)

`jarvis_brain.supersede()` har kunnet markere en gammel post som erstattet af en
ny siden brain blev bygget, og `brain_index` har både `status` og `superseded_by`.
Men da jeg greppede efter ikke-runtime-kaldere, var der **nul**: ingen producent
kaldte den. Mekanikken fandtes, triggeren gjorde ikke.

Konsekvensen er den klassiske: «jeg træner til maraton» og «jeg har forstuvet
anklen» bliver to lige sande poster, og begge bliver hentet som kontekst længe
efter at den ene er forældet. Det er ikke en søgefejl — det er en manglende
skrivetids-beslutning.

## Hvad dette modul gør — og ikke gør

Det **detekterer** kandidater og **foreslår** en supersession. Det afgør ikke
selv hvad der er sandt: en høj cosinus betyder «samme emne», ikke «modsiger».
Derfor er standarden `dry_run=True`, og en ægte supersession kræver at kalderen
eksplicit beder om den.

To signaler skal begge være opfyldt før noget overhovedet foreslås:

1. **Samme emne** — cosinus over `min_cosine` (embedding).
2. **Nyere og mere specifik** — den nye post skal være nyere, og den gamle må
   ikke være bekræftet af flere sessioner (en post der er genbekræftet mange
   gange skal ikke væltes af en enkelt ny sætning).

Grænsen er sat konservativt med vilje. En falsk supersession er værre end en
manglende: den skjuler viden der stadig var sand.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

#: Hvor ens to poster skal være før de overhovedet er kandidater.
#: Målt på nomic-embed-text: samme emne i dansk ligger typisk 0,75-0,90;
#: beslægtede men forskellige emner 0,55-0,70. 0,78 skærer «samme emne» fra
#: «samme domæne».
MIN_COSINE = 0.78

#: En post der er hentet mange gange er stærkere end én ny sætning.
#: `BrainEntry` har ikke `confirmed_sessions` (verificeret 24/10-2026 — feltet
#: findes ikke), men den har `recall_count`, som tæller hvor ofte posten er
#: hentet som kontekst. Det er det nærmeste ægte signal.
MAX_RECALL_COUNT = 5


def find_supersession_candidates(
    *,
    new_entry_id: str,
    new_text: str,
    limit: int = 5,
    min_cosine: float = MIN_COSINE,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Find ældre poster der sandsynligvis er erstattet af `new_entry_id`.

    Returnerer kandidater med deres cosinus og alder — men ændrer INTET.
    Kalderen afgør selv om der skal supersederes.
    """
    now = now or datetime.now(timezone.utc)
    if not str(new_text or "").strip():
        return []

    try:
        from core.services.jarvis_brain import read_entry, search_brain_scored
    except Exception as exc:  # brain utilgængelig — detektion er valgfri
        logger.debug("supersession: brain ikke tilgængelig: %s", exc)
        return []

    try:
        scored = search_brain_scored(
            query_text=new_text,
            limit=max(limit * 3, 10),
            include_archived=False,
            min_cosine=min_cosine,
        )
    except Exception as exc:  # søgning fejlede — hellere intet forslag end et gæt
        logger.debug("supersession: søgning fejlede: %s", exc)
        return []

    kandidater: list[dict[str, Any]] = []
    for score, entry_id in scored:
        if entry_id == new_entry_id:
            continue
        try:
            gammel = read_entry(entry_id)
        except Exception as exc:  # posten kan være slettet mellem søgning og læsning
            logger.debug("supersession: kunne ikke læse %s: %s", entry_id, exc)
            continue
        if gammel.status != "active":
            continue
        # Den nye skal være NYERE. Ellers ville en gammel post vælte en ny.
        if gammel.created_at and gammel.created_at >= now:
            continue
        # En ofte-hentet post er stærkere end én ny sætning.
        hentet = int(getattr(gammel, "recall_count", 0) or 0)
        if hentet > MAX_RECALL_COUNT:
            continue
        alder_dage = 0.0
        if gammel.created_at:
            alder_dage = max(0.0, (now - gammel.created_at).total_seconds() / 86400.0)
        kandidater.append({
            "entry_id": entry_id,
            "title": gammel.title,
            "kind": gammel.kind,
            "score": round(float(score), 4),
            "alder_dage": round(alder_dage, 1),
            "recall_count": hentet,
        })

    kandidater.sort(key=lambda k: -k["score"])
    return kandidater[:limit]


def supersede_if_confident(
    *,
    new_entry_id: str,
    new_text: str,
    dry_run: bool = True,
    min_cosine: float = MIN_COSINE,
) -> dict[str, Any]:
    """Foreslå — eller udfør — supersession af ældre modstridende poster.

    `dry_run=True` (standard) returnerer kun kandidaterne. Med `dry_run=False`
    kaldes `jarvis_brain.supersede()` for hver kandidat, og resultatet bærer
    præcis hvilke id'er der blev markeret.
    """
    kandidater = find_supersession_candidates(
        new_entry_id=new_entry_id,
        new_text=new_text,
        min_cosine=min_cosine,
    )
    if not kandidater:
        return {"status": "ok", "superseded": [], "candidates": [], "dry_run": dry_run}

    if dry_run:
        return {
            "status": "ok",
            "superseded": [],
            "candidates": kandidater,
            "dry_run": True,
            "note": "Intet ændret — kør med dry_run=False for at markere dem.",
        }

    from core.services.jarvis_brain import supersede

    ids = [k["entry_id"] for k in kandidater]
    try:
        supersede(old_ids=ids, new_id=new_entry_id)
    except Exception as exc:  # supersession fejlede — rapportér, skjul ikke
        logger.warning("supersession fejlede for %s: %s", new_entry_id, exc)
        return {
            "status": "error",
            "error": f"supersede fejlede: {exc}",
            "superseded": [],
            "candidates": kandidater,
            "dry_run": False,
        }
    return {
        "status": "ok",
        "superseded": ids,
        "candidates": kandidater,
        "dry_run": False,
    }
