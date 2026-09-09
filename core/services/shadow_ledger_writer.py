"""Skygge-skrivning — den første kobling mellem drift og ledgeren.

Spec: Fase 1, «Keep legacy sessions authoritative in `chat_messages`;
shadow-write only selected test sessions.»

## Den ene regel der betyder alt

**Skyggen må aldrig kunne vælte den ægte skrivning.**

Sessionen er stadig `legacy` i praksis: `chat_messages` er sandheden, og hvis
brugeren mister sin besked fordi et eksperiment fejlede, er eksperimentet
værre end det problem det skulle løse. Derfor kaldes denne funktion EFTER at
rækken er skrevet og committet, og den kaster aldrig.

## Men den tier heller ikke

En stille skygge ville være det værste af begge dele: man tror man måler, og
man måler ingenting. Hver fejl logges, og hver fejl tælles i
`skygge_fejl`-tælleren — så drift-sammenligningen ikke er det eneste sted man
kan opdage at skyggen ikke har virket.

Det gør IKKE noget at en skygge-skrivning fejler, så længe man VED det: drift-
detektionen vil finde uenigheden, og porten til et skifte vil holde den lukket.
Det farlige er en skygge der fejler og ser ud som om den lykkedes.

## Én transaktion, ikke tre

Den ejede skrivevej tager en lease, skriver og giver leasen fra sig — tre
skrive-transaktioner pr. besked. Skygge-skrivning sker på den varmeste sti der
findes, i en database hvor to processer skriver samtidig, så den pris er
forkert. `append_unowned` gør det i én, og afviser selv en session der er
kanonisk i ledgeren.

## Hvorfor `message_id` følger med

Ved skiftet bygger projektoren rækkerne af hændelserne. Bar hændelsen ikke det
id rækken allerede fik af `uuid4()`, ville projektoren udlede et nyt — og lægge
den samme samtale ind én gang til ved siden af sig selv.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Tællere pr. proces. Ikke sandhed — et sted at kigge når noget ser skævt ud.
_taellere: dict[str, int] = {"skrevet": 0, "sprunget_over": 0, "fejl": 0}


def taellere() -> dict[str, int]:
    return dict(_taellere)


def _nulstil_for_tests() -> None:
    for k in _taellere:
        _taellere[k] = 0


def shadow_append(session_id: str, *, message_id: str, role: str, content: str,
                  created_at: str, user_id: str = "", workspace_name: str = "",
                  reasoning_content: str = "", git_sha: str = "",
                  content_json: Any = None) -> bool:
    """Skriv beskeden i ledgeren HVIS sessionen er i skygge-tilstand.

    Returnerer om der blev skrevet. Kaster aldrig — kalderen har allerede
    skrevet den ægte række, og den må ikke rulles tilbage af et eksperiment.
    """
    try:
        from core.runtime.db_session_ledger import append_unowned, storage_mode

        if storage_mode(session_id) != "shadow":
            _taellere["sprunget_over"] += 1
            return False

        # `message_id` er både hændelsens identitet OG den værdi projektoren
        # skal genbruge. At bruge den som event_id gør skrivningen idempotent:
        # samme besked to gange bliver til én hændelse.
        haendelse = {
            "event_id": str(message_id),
            "kind": "message",
            "payload": {
                "message_id": str(message_id),
                "role": str(role),
                "content": str(content),
                "user_id": str(user_id or ""),
                "workspace_name": str(workspace_name or ""),
                "reasoning_content": str(reasoning_content or ""),
                "git_sha": str(git_sha or ""),
                "content_json": content_json,
                "created_at": str(created_at or ""),
            },
        }

        # ÉN transaktion, ingen lease. Den ejede vej koster tre skrivninger
        # pr. besked (tag lease, skriv, giv fri) — forkert pris på den varmeste
        # sti der findes. `append_unowned` afviser selv en session der er
        # kanonisk i ledgeren, så afkaldet på fencing er bundet af kode.
        append_unowned(session_id, events=[haendelse])
        _taellere["skrevet"] += 1
        return True
    except Exception:
        # En skygge der vælter den ægte skrivning er værre end ingen skygge.
        _taellere["fejl"] += 1
        logger.warning("shadow_ledger_writer: skygge-skrivning fejlede for %s",
                       session_id, exc_info=True)
        return False
