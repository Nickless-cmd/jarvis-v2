"""Klientlog ved renderbeslutningen — fire målepunkter, ingen guard.

## Hvorfor den findes (25/10-2026)

`MarkdownRenderer.tsx` falder lydløst tilbage til `ChatCodeBlock` når en
`jarvis-ui`-blok ikke kan blive en flade. Intet blev logget, og derfor kunne
fire diagnoser i træk pege forkert: fejlen var usynlig præcis dér hvor
beslutningen blev truffet.

Ruten bærer et ØJEBLIKSBILLEDE. Den retter intet, blokerer intet og afviser
intet — den skriver hvad browseren så, så spørgsmålet kan besvares med data i
stedet for gæt.

## Hvorfor ikke `POST /internal-errors/report`

Målt 25/10-2026: den rute er `loopback-only` og afviser enhver request med
`x-forwarded-for` eller `forwarded` (403). Desk'en taler med `api.srvlab.dk`
gennem Caddy, så den kan pr. konstruktion ikke bruge den. At lempe dens
loopback-krav ville svække en sikkerhedsgrænse for at løse et
observabilitets-behov; derfor en smal rute med samme auth som resten.

## Fire målepunkter

`foer` og `efter` er teksten før og efter `stabilizeStreamingMarkdown`.
`blok` er den konkrete markdown-blok ReactMarkdown modtog. `className`, `lang`
og `kode` er hvad `pre`-grenen så. `udfald` er én af:

  - `native`       — blokken blev en flade
  - `parse-null`   — `lang` var rigtig, men `parseNativeRichSpec` gav null
  - `wrong-lang`   — teksten nævner jarvis-ui, men `lang` blev ikke `jarvis-ui`
  - `no-pre-node`  — blokken blev aldrig et `<pre>`, så `pre`-grenen så den aldrig

`no-pre-node` er den vigtigste: en log inde i `pre`-grenen ser ikke en fejl der
betyder at grenen aldrig blev kørt.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.runtime.config import STATE_DIR

logger = logging.getLogger(__name__)

router = APIRouter()

#: Filen er append-only JSONL. Den ligger i `state/` og er registreret i
#: `docs/persistens/register.json` — husets regel: et varigt format skal stå
#: i registret, ellers ved den næste ikke hvad filen er.
_LOG_PATH = STATE_DIR / "flade_log.jsonl"

#: Et loft pr. dag, ikke pr. request. Streaming kan kalde loggen mange gange i
#: sekundet, og en log der vokser uden grænse bliver selv et problem.
_MAKS_PR_DAG = 2000


class FladeSnapshot(BaseModel):
    """Ét øjebliksbillede af en renderbeslutning."""

    udfald: Literal["native", "parse-null", "wrong-lang", "no-pre-node"]
    besked_id: str = Field(default="", max_length=200)
    blok: str = Field(default="", max_length=8000)
    foer: str = Field(default="", max_length=2000)
    efter: str = Field(default="", max_length=2000)
    className: str = Field(default="", max_length=300)
    lang: str = Field(default="", max_length=100)
    kode: str = Field(default="", max_length=4000)
    build: str = Field(default="", max_length=100)


def _antal_i_dag() -> int:
    """Antal linjer skrevet i dag. Læses kun når filen findes."""
    try:
        if not _LOG_PATH.exists():
            return 0
        i_dag = datetime.now(UTC).date().isoformat()
        with _LOG_PATH.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for linje in fh if i_dag in linje[:40])
    except Exception:
        # fail-open: et loft der ikke kan måles må ikke blokere en log-linje
        return 0


@router.post("/flade-log")
async def flade_log(snapshot: FladeSnapshot) -> JSONResponse:
    """Modtag ét snapshot og skriv det. Svarer altid 202.

    Fail-open med vilje: en observabilitets-rute der kan fejle for brugeren
    ville gøre den til et nyt problem i stedet for et svar på det gamle.
    """
    if _antal_i_dag() >= _MAKS_PR_DAG:
        return JSONResponse({"status": "accepted", "skrevet": False,
                             "grund": "dagligt loft nået"}, status_code=202)

    post: dict[str, Any] = {
        "tid": datetime.now(UTC).isoformat(),
        **snapshot.model_dump(),
    }
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(post, ensure_ascii=False) + "\n")
    except Exception:
        # fail-open: en manglende log-linje må aldrig koste klienten noget
        logger.debug("flade-log: kunne ikke skrive", exc_info=True)
        return JSONResponse({"status": "accepted", "skrevet": False}, status_code=202)

    return JSONResponse({"status": "accepted", "skrevet": True}, status_code=202)
