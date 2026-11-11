"""Én indgang til at vække — kilderne SIGNALERER, indbakken VURDERER og vækker.

Bjørn 11/11-2026: «der skal kun være en vækker (inbox) og de andre der kan
vække sender signalet til inbox'en, den vurderer signalet og vækker».

## Kontrakten

`anmod_om_vaekning(...)` er den ENESTE funktion en vækningskilde skal kalde.
Den

  * skriver (eller genkender) en post af kildetype `vaekning` i indbakken,
  * starter ALDRIG selv et run — det gør kun `inbox_idle_waker`,
  * svarer med en kvittering: `queued` / `deduped` / `rejected` + grund,
  * er self-safe: en fejl her vælter ikke kalderen, men logges som WARNING
    og bliver en `rejected`-kvittering (aldrig en tavs `None`).

## Dedup

Nøglen er SAGEN, ikke kilden: to kilder der vækker om samme sag deler
`kilde_id` (`vaek-{sag}`), og `opret_eller_hent` er idempotent. Den anden får
`deduped` — ikke et ekstra run. En `drop`/`udloebet` post genåbnes (samme
mekanik som `genaabn_af_kilde`); en `done` post er afgjort, og samme sag kan
kun vække igen med en NY sag-nøgle (fx med forekomstens tidsstempel).

## Hvad den IKKE gør

Kanal-svar (Discord/Telegram/desk) er ikke vækninger og går ikke herigennem.
Se docs/findings/vaekningsflade-2026-11-11.md for grænsen.

Vurderingen (kræver handling? verificeret ejer? kører noget?) ligger i
`inbox_idle_waker` — gatewayen dublerer den ikke. Posten skrives med
`verificeret_ejer=jarvis` og `kraever_handling=False`: den må vække, men aldrig
nægte en mutation i et kørende run.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

KILDETYPE = "vaekning"

QUEUED = "queued"
DEDUPED = "deduped"
REJECTED = "rejected"

_SAG_RE = re.compile(r"[^0-9A-Za-z_.:-]+")
_MAKS_SAG = 120


def _kvittering(status: str, grund: str, **ekstra: Any) -> dict[str, Any]:
    return {"status": status, "grund": grund, **ekstra}


def vaekning_kilde_id(sag: str) -> str:
    """Stabil post-nøgle for en sag. Tom streng hvis sagen er tom."""
    ren = _SAG_RE.sub("-", str(sag or "").strip()).strip("-")[:_MAKS_SAG]
    return f"vaek-{ren}" if ren else ""


def _bruger() -> str:
    from core.identity.workspace_context import current_workspace_name
    from core.services.inbox_state import bruger_for_workspace

    return str(bruger_for_workspace(current_workspace_name() or "bjorn") or "")


def anmod_om_vaekning(
    *,
    kilde: str,
    sag: str,
    tekst: str,
    bruger_id: str = "",
    session_id: str = "",
    importance: str = "normal",
    task_id: str = "",
    permission_session: str = "",
    origin: str = "",
    max_tool_calls: int = 0,
    max_seconds: float = 0.0,
    tool_scope: str = "",
) -> dict[str, Any]:
    """Bed indbakken om at vække. Starter ikke noget selv.

    `kilde`  hvem beder (til fejlfinding: «hvem vækkede mig?»)
    `sag`    hvad vækningen handler om — dedup-nøglen
    `tekst`  instruktionen runnet skal have
    `session_id` den samtale vækningen hører til (tom = waker vælger/venter)
    `task_id` den forpligtelse vækningen fortsætter (tom = et nyt run)
    `permission_session` samtalen adgangsniveauet skal læses fra, når den
        afviger fra `session_id` — ellers arver et run i en `auto-*`-silo
        tilladelsen fra den silo i stedet for fra den samtale der bookede det
    `origin` hvilken slags run vækningen må starte (dream, heartbeat,
        scheduled, recurring …). Uden den skrev wakeren ALTID "inbox", og et
        drømme-run blev umuligt at skelne fra en påmindelse i telemetrien.
        Falder tilbage til `kilde`, så feltet aldrig er tomt for en kilde
        der navngav sig.
    """
    try:
        kilde = str(kilde or "").strip()
        tekst = str(tekst or "").strip()
        kilde_id = vaekning_kilde_id(sag)
        if not kilde:
            return _kvittering(REJECTED, "mangler_kilde")
        if not kilde_id:
            return _kvittering(REJECTED, "mangler_sag", kilde=kilde)
        if not tekst:
            return _kvittering(REJECTED, "mangler_tekst", kilde=kilde,
                               kilde_id=kilde_id)
        bruger = str(bruger_id or "").strip() or _bruger()
        if not bruger:
            # En post i den forkerte indbakke er værre end ingen post.
            return _kvittering(REJECTED, "ingen_bruger", kilde=kilde,
                               kilde_id=kilde_id)

        from core.runtime import db_inbox

        eksisterende = db_inbox.hent(bruger_id=bruger, kilde_id=kilde_id)
        if eksisterende is not None:
            status = str(eksisterende.get("status") or "")
            if status in db_inbox.GENAABNING_STATUSSER:
                r = db_inbox.genaabn_af_kilde(bruger_id=bruger, kilde_id=kilde_id)
                if r.get("status") != "ok":
                    return _kvittering(REJECTED, f"genaabning_fejlede:{r.get('status')}",
                                       kilde=kilde, kilde_id=kilde_id)
                logger.info("wake_gateway: %s genaabnede %s", kilde, kilde_id)
                return _kvittering(QUEUED, "genaabnet", kilde=kilde,
                                   kilde_id=kilde_id)
            if status == db_inbox.STATUS_AABEN:
                logger.info("wake_gateway: %s dedupet paa %s", kilde, kilde_id)
                return _kvittering(DEDUPED, "aaben_post_findes", kilde=kilde,
                                   kilde_id=kilde_id)
            return _kvittering(DEDUPED, f"sagen_er_{status or 'afgjort'}",
                               kilde=kilde, kilde_id=kilde_id)

        r = db_inbox.opret_eller_hent(
            bruger_id=bruger,
            kildetype=KILDETYPE,
            kilde_id=kilde_id,
            verificeret_ejer=db_inbox.EJER_JARVIS,
            kraever_handling=False,
            beskrivelse=tekst,
            session_id=str(session_id or ""),
            importance=importance,
            task_id=str(task_id or ""),
            permission_session=str(permission_session or ""),
            # HERKOMSTEN (11/11-2026): falder tilbage til kildenavnet, så en
            # vækning altid kan svare på hvem der kaldte — også når kalderen
            # ikke selv kender sin run-origin.
            origin=str(origin or "").strip() or kilde,
            # BUDGETTET (11/11-2026). Uden disse tre felter kører et migreret
            # rutine-run uden loft: det starter, ser rigtigt ud og bruger
            # ubegrænset tid og værktøjskald. `0` betyder «intet loft».
            max_tool_calls=int(max_tool_calls or 0),
            max_seconds=float(max_seconds or 0.0),
            tool_scope=str(tool_scope or ""),
        )
        if r.get("status") != "ok":
            logger.warning("wake_gateway: %s kunne ikke skrive %s: %s",
                           kilde, kilde_id, r.get("error"))
            return _kvittering(REJECTED, f"skrivefejl:{r.get('error')}",
                               kilde=kilde, kilde_id=kilde_id)
        logger.info("wake_gateway: %s koe-lagde %s", kilde, kilde_id)
        return _kvittering(QUEUED, "ny_post", kilde=kilde, kilde_id=kilde_id)
    except Exception as exc:  # noqa: BLE001 — self-safe, men SYNLIG
        logger.warning("wake_gateway: anmodning fra %r fejlede: %s", kilde, exc,
                       exc_info=True)
        return _kvittering(REJECTED, f"gateway_fejl:{type(exc).__name__}",
                           kilde=str(kilde or ""))
