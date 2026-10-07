"""core/services/prompt_dump.py

Gated fuld-payload-dump for visible-lanen: skriver PRÆCIS den request vi
sender til udbyderen — messages, tools og alle sampling-params — til
``/tmp/jarvis-prompt-dumps/latest.json`` og roterer den forrige til
``prev.json`` (så to ture kan diff'es).

Hvorfor et selvstændigt modul: de to kaldesteder byggede hver sin inline
dump-blok (first-pass i ``visible_model_adapters``, de agentiske runder i
``visible_followup_adapters``), og INGEN af dem tog værktøjslisten med — som
er langt den største del af payloaden (~82k af ~111k tegn). Én funktion, ét
format, begge stier.

INERT medmindre sentinel-filen findes::

    touch /tmp/jarvis-prompt-dump

Self-safe: kaster aldrig, koster ~0 når slukket.
"""
from __future__ import annotations

import json
import os

_SENTINEL = "/tmp/jarvis-prompt-dump"
_DUMP_DIR = "/tmp/jarvis-prompt-dumps"


def is_armed() -> bool:
    """Er dumpet arméret? (sentinel-filen findes)"""
    try:
        return os.path.exists(_SENTINEL)
    except Exception:  # self-safe: et sentinel-tjek maa ikke kaste ind i stream-stien
        return False


def dump_payload(
    *,
    provider: str,
    model: str,
    messages: list | None,
    tools: list | None = None,
    params: dict | None = None,
    lane: str = "",
    round_index: int | None = None,
) -> None:
    """Skriv HELE requesten til latest.json; forrige dump → prev.json.

    Inert uden sentinel. Self-safe — en fejlende dump maa aldrig ramme streamen.
    """
    if not is_armed():
        return
    try:
        os.makedirs(_DUMP_DIR, exist_ok=True)
        latest = os.path.join(_DUMP_DIR, "latest.json")
        if os.path.exists(latest):
            try:
                os.replace(latest, os.path.join(_DUMP_DIR, "prev.json"))
            except Exception:  # self-safe: rotation er bekvemmelighed, ikke kritisk
                pass
        payload = {
            "provider": provider,
            "model": model,
            "lane": lane,
            "round_index": round_index,
            "messages": messages or [],
            "tools": tools or [],
            "params": params or {},
        }
        with open(latest, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
    except Exception:  # self-safe: en dump maa aldrig kaste ind i stream-stien
        pass
