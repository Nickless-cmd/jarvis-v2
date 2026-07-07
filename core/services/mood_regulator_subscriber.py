"""Mood regulator subscriber — router truth-gate detektioner til humøret.

PROBLEM (opdaget 2026-07-07 af Bjørn):
``central_mood_regulator.regulate_auto`` har en korrekt mapping fra
eventbus-hændelser (fx ``diagnosis.unverified`` → ``confabulation``), men
INTET abonnerede på eventbussen og kaldte den. Resultat: når Jarvis blev
fanget i at konfabulere, blev humøret aldrig jordet — det friløb på sinus-
oscillatoren og viste "Meget Euforisk (1.00)" selv lige efter en løgn.

LØSNING:
En lille daemon-tråd (samme mønster som ``inner_voice_notifier`` og
``approval_feedback_subscriber``) der abonnerer på eventbussen og for hver
hændelse, hvis ``kind`` findes i ``AUTO_EVENT_MAPPING``, kalder
``regulate_auto`` synkront. Self-safe: fanger alle fejl, kaster aldrig —
humøret må ALDRIG bringe runtime ned.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any

from core.eventbus.bus import event_bus
from core.services.central_mood_regulator import AUTO_EVENT_MAPPING, regulate_auto

logger = logging.getLogger(__name__)

_SUBSCRIBER_THREAD: threading.Thread | None = None
_SUBSCRIBER_STOP = threading.Event()
_SUBSCRIBER_QUEUE: queue.Queue[dict[str, Any] | None] | None = None


def start_mood_regulator_subscriber() -> None:
    """Start daemon-tråden der router detektions-events til mood-regulering.

    Idempotent: starter ikke to gange.
    """
    global _SUBSCRIBER_THREAD, _SUBSCRIBER_QUEUE
    if _SUBSCRIBER_THREAD and _SUBSCRIBER_THREAD.is_alive():
        return
    _SUBSCRIBER_STOP.clear()
    subscriber = event_bus.subscribe()
    _SUBSCRIBER_QUEUE = subscriber
    thread = threading.Thread(
        target=_subscriber_loop,
        kwargs={"subscriber": subscriber},
        name="jarvis-mood-regulator-subscriber",
        daemon=True,
    )
    thread.start()
    _SUBSCRIBER_THREAD = thread
    logger.info("mood_regulator_subscriber: started")


def stop_mood_regulator_subscriber() -> None:
    global _SUBSCRIBER_THREAD, _SUBSCRIBER_QUEUE
    _SUBSCRIBER_STOP.set()
    subscriber = _SUBSCRIBER_QUEUE
    if subscriber is not None:
        try:
            event_bus.unsubscribe(subscriber)
        except Exception:
            pass
    thread = _SUBSCRIBER_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=1.0)
    _SUBSCRIBER_THREAD = None
    _SUBSCRIBER_QUEUE = None
    logger.info("mood_regulator_subscriber: stopped")


def _subscriber_loop(*, subscriber: queue.Queue[dict[str, Any] | None]) -> None:
    while not _SUBSCRIBER_STOP.is_set():
        try:
            item = subscriber.get(timeout=0.5)
        except queue.Empty:
            continue
        if item is None:
            break
        if not isinstance(item, dict):
            continue
        try:
            _route_event(item)
        except Exception as exc:  # self-safe: må ALDRIG bringe tråden/runtime ned
            logger.warning("mood_regulator_subscriber: routing failed: %s", exc)


def _route_event(item: dict[str, Any]) -> bool:
    """Route en enkelt eventbus-hændelse til ``regulate_auto``.

    Returnerer True hvis en regulering blev anvendt (kind matchede mapping),
    ellers False. Self-safe: sluger fejl fra regulate_auto.

    Udskilt fra loopet så den kan testes direkte med et syntetisk event-dict
    uden at race daemon-tråden.
    """
    kind = str(item.get("kind") or "")
    if kind not in AUTO_EVENT_MAPPING:
        return False
    payload = item.get("payload")
    payload_dict = dict(payload) if isinstance(payload, dict) else {}
    try:
        return bool(regulate_auto(event_kind=kind, payload=payload_dict))
    except Exception as exc:
        logger.warning("mood_regulator_subscriber: regulate_auto raised: %s", exc)
        return False
