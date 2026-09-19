"""Krydsproces-relæ: events fra den ANDEN proces når de lokale abonnenter.

## Hvorfor (målt 19/9-2026)

`event_bus.subscribe()` er en kø i PROCESSEN. jarvis-api og jarvis-runtime
kører samme app, men lytterne starter kun i runtime-processen (app.py,
`runtime_services_enabled`), mens desk'ens chat serveres af API-processen
(Caddy → 127.0.0.1:8080; `POST /chat/stream/v` 59 gange samme dag, 0 i
runtime). Alt API-processen publicerer — Jarvis' svar til Bjørn
(channel.chat_message_appended), afsluttede synlige ture, godkendelser fra
desk — blev skrevet i events-tabellen og hørt af INGEN lokal lytter.

Døve lyttere, blandt andre: experience_correction (lektier af Bjørns
rettelser — «0 lektier nogensinde»), decision_enforcement (brud på
beslutninger), approval_feedback_subscriber (godkendelser fra desk).
living_executive blev ramt af samme fælde 14/9 og læser selv fra DB'en.

## Hvordan

Ét relæ i runtime-processen poller events-tabellen og leverer rækker som
ANDRE processer har skrevet, til de lokale abonnenter — samme form som
bussens egen fordeling. Rækker denne proces selv skrev, springes over
(`EventBus.er_egen`), så ingen abonnent får et event to gange. Ingen lytter
skal ændres.

Første poll starter ved nyeste række: relæet genafspiller aldrig historik.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

POLL_SEKUNDER = 1.0
BATCH = 500

_koerer = False
_sidste_id = 0


def relae_en_gang(bus: Any, sidste_id: int, *, limit: int = BATCH) -> tuple[int, int]:
    """Én poll. Returnerer (ny sidste_id, antal leveret)."""
    leveret = 0
    for raekke in bus.recent_since_id(sidste_id, limit=limit):
        eid = int(raekke["id"])
        sidste_id = max(sidste_id, eid)
        if bus.er_egen(eid):
            continue
        bus._notify_subscribers(raekke)
        leveret += 1
    return sidste_id, leveret


def _nyeste_id(bus: Any) -> int:
    nyeste = bus.recent(limit=1)
    return int(nyeste[0]["id"]) if nyeste else 0


def _loop(bus: Any) -> None:
    global _sidste_id
    _sidste_id = _nyeste_id(bus)
    while _koerer:
        try:
            _sidste_id, _ = relae_en_gang(bus, _sidste_id)
        except Exception as exc:
            logger.warning("krydsproces-relæ: poll fejlede: %s", exc)
        time.sleep(POLL_SEKUNDER)


def start_relae(bus: Any | None = None) -> None:
    """Idempotent. Startes i den proces hvor lytterne bor (runtime)."""
    global _koerer
    if _koerer:
        return
    if bus is None:
        from core.eventbus.bus import event_bus as bus
    _koerer = True
    threading.Thread(target=_loop, args=(bus,), daemon=True, name="eventbus-krydsproces").start()
    logger.info("krydsproces-relæ startet")
