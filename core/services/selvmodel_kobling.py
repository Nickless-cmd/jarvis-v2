"""Selvmodellens første lodrette skive: fra hans svar til hans prompt.

Spec §8 (Jarvis' ændring 5): ét art (`holdning`), én kilde (nominering fra hans
egne svar), hele vejen til prompt-sektionen — før flere kilder bygges.

  hans svar i en ejer-samtale  →  channel.chat_message_appended (role=assistant)
    →  en billig model NOMINERER holdninger (den skriver ikke)
    →  selvmodel.udtryk(kilde="nominering", samtale_id=…)  — korroboreres på
       tværs af samtaler før noget bliver et træk
    →  prompt-sektionen «Hvem jeg er lige nu», med dato og kilde pr. træk

Alt står bag `selvmodel_enabled` (settings, slukket som standard): selvmodellen
tændes først når fase 7's nulpunkt er indsamlet. Fail-open hele vejen: en fejl
her må aldrig koste et svar eller en tur.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

SKIVE_ARTER = ("holdning",)
MAX_PR_TIME = 30          # nomineringskald i alt pr. time
MIN_TEKST = 200           # korte svar bærer sjældent en holdning
MAX_TEKST = 6000

NOMINER_PROMPT = """Du læser ét svar fra Jarvis, en AI, til sin ejer Bjørn.

Find de steder hvor JARVIS SELV giver udtryk for en holdning: en mening eller
vurdering han står inde for («jeg synes …», «jeg mener …», «det er forkert at …»).
IKKE: fakta, planer, opsummeringer af hvad andre mener, høflighed, eller
beskrivelser af kode og drift.

Svar KUN med JSON: en liste med højst 2 elementer,
[{"emne": "2-4 ord", "udsagn": "holdningen i første person, én sætning"}]
eller [] hvis der ingen holdning er.

SVAR:
"""

_laas = threading.Lock()
_kald: list[float] = []
_lytter_koerer = False


def er_taendt() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().selvmodel_enabled)
    except Exception:
        return False


def selvmodel_sektion() -> str | None:
    """Prompt-sektionen — kun når flaget er tændt og kun i ejerens samtaler."""
    if not er_taendt():
        return None
    try:
        from core.identity.workspace_context import current_role
        if str(current_role() or "") != "owner":
            return None
    except Exception:
        return None
    from core.services.selvmodel import prompt_sektion
    return prompt_sektion() or None


def _ejer_id() -> str:
    from core.identity.users import get_owner
    owner = get_owner()
    return str(getattr(owner, "discord_id", "") or "").strip() if owner else ""


def samtalens_kilde(session_id: str) -> str | None:
    """«nominering» for ejerens samtaler, «anden_bruger» for andres, None for autonome."""
    if not session_id or session_id.startswith("auto-"):
        return None
    from core.runtime.db_core import connect
    with connect() as conn:
        row = conn.execute(
            "SELECT user_id FROM chat_messages WHERE session_id=? AND role='user' "
            "ORDER BY id DESC LIMIT 1", (session_id,)).fetchone()
    if not row:
        return None
    ejer = _ejer_id()
    return "nominering" if ejer and str(row[0] or "") == ejer else "anden_bruger"


def parse_nomineringer(tekst: str) -> list[dict[str, str]]:
    m = re.search(r"\[.*\]", tekst or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    ud = []
    for d in data[:2] if isinstance(data, list) else []:
        if isinstance(d, dict) and str(d.get("emne") or "").strip() and str(d.get("udsagn") or "").strip():
            ud.append({"emne": str(d["emne"]).strip()[:60], "udsagn": str(d["udsagn"]).strip()[:300]})
    return ud


def _maa_kalde(nu: float) -> bool:
    with _laas:
        while _kald and nu - _kald[0] > 3600:
            _kald.pop(0)
        if len(_kald) >= MAX_PR_TIME:
            return False
        _kald.append(nu)
        return True


def _kald_billig_model(prompt: str) -> str:
    from core.services.cheap_lane_balancer import call_balanced
    return str((call_balanced(prompt=prompt, daemon_name="selvmodel_nominering") or {}).get("text") or "")


def behandl_svar(session_id: str, besked: dict[str, Any]) -> list[dict]:
    """Nominér holdninger fra ét af hans svar. Returnerer selvmodellens udfald."""
    if not er_taendt():
        return []
    tekst = str(besked.get("content") or "")
    if len(tekst) < MIN_TEKST:
        return []
    kilde = samtalens_kilde(session_id)
    if kilde is None or not _maa_kalde(time.time()):
        return []
    from core.services import selvmodel
    udfald = []
    for n in parse_nomineringer(_kald_billig_model(NOMINER_PROMPT + tekst[:MAX_TEKST])):
        for art in SKIVE_ARTER:
            udfald.append(selvmodel.udtryk(
                art, n["emne"], n["udsagn"], kilde=kilde, samtale_id=session_id,
                bevis=f"{session_id}:{besked.get('id') or ''}"))
    return udfald


_SIDSTE_ID_NOEGLE = "selvmodel_nominering_sidste_event_id"
POLL_SEKUNDER = 5.0


def _sidste_id() -> int:
    from core.runtime.db_core import get_runtime_state_value
    try:
        return int(get_runtime_state_value(_SIDSTE_ID_NOEGLE, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _gem_sidste_id(event_id: int) -> None:
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(_SIDSTE_ID_NOEGLE, int(event_id))


def poll_en_gang(*, limit: int = 200) -> int:
    """Behandl nye assistant-svar fra eventbussens tabel. Returnerer antal svar set.

    DB'en, ikke subscribe(): subscribe() er en kø i PROCESSEN, og chatten
    serveres af API-processen, mens lytterne starter i runtime-processen
    (app.py, runtime_services_enabled). En in-process lytter ville aldrig høre
    et eneste af hans svar — samme fælde som living_executive 14/9-2026.
    """
    from core.eventbus.bus import event_bus
    sidste = _sidste_id()
    if sidste == 0:
        # Første start: ingen genbehandling af historikken, kun det der kommer.
        nyeste = event_bus.recent(limit=1)
        _gem_sidste_id(int(nyeste[0]["id"]) if nyeste else 0)
        return 0
    set_ = 0
    for item in event_bus.recent_since_id(sidste, limit=limit):
        sidste = max(sidste, int(item["id"]))
        if str(item.get("kind") or "") != "channel.chat_message_appended":
            continue
        payload = item.get("payload") or {}
        besked = payload.get("message") or {}
        if str(besked.get("role") or "").lower() != "assistant":
            continue
        set_ += 1
        try:
            behandl_svar(str(payload.get("session_id") or ""), besked)
        except Exception as exc:
            logger.warning("selvmodel: nominering fejlede (fail-open): %s", exc)
    _gem_sidste_id(sidste)
    return set_


def _loop() -> None:
    while _lytter_koerer:
        try:
            if er_taendt():
                poll_en_gang()
            elif _sidste_id():
                # Slukket: glem pegepinden, så en ny tænding starter fra nu og
                # ikke gennemgår alt der skete mens den var slukket.
                _gem_sidste_id(0)
        except Exception as exc:
            logger.debug("selvmodel: poll-fejl: %s", exc)
        time.sleep(POLL_SEKUNDER)


def start_lytter() -> None:
    """Idempotent. Startes KUN i runtime-processen (én poller, ingen dobbelt-behandling)."""
    global _lytter_koerer
    if _lytter_koerer:
        return
    _lytter_koerer = True
    threading.Thread(target=_loop, daemon=True, name="selvmodel-poller").start()
    logger.info("selvmodel: poller startet")
