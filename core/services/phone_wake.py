"""Push-vækning: banker på telefonen når den sover.

Bro-forbindelsen dør når appen går i baggrunden — Android kapper den, og der
er ingen vej udenom uden en foreground-service. Målt 7/9: telefonen
registrerede sig kl. 15:13:51 og afmeldte sig igen 15:14:24, da Bjørn lagde
den fra sig. Det er ikke en fejl; det er hvordan Android er.

Så i stedet for at holde forbindelsen åben hele tiden, åbnes den **når der er
brug for den**: en stille data-push vækker appen, appen forbinder, kaldet
udføres, forbindelsen lukker igen.

To ting gør det muligt uden nyt maskineri:

* ``fcm_gateway.send`` er allerede data-only med ``priority: high``, og
  ``_build_message`` tilføjer kun en synlig notifikations-blok når payloaden
  har BÅDE ``title`` og ``preview``. En vækning uden dem er derfor helt
  tavs — Bjørn ser ingenting.
* Broen skriver sin tilstedeværelse til ``bridge_presence`` ved hver
  registrering, så vi kan vente på at telefonen dukker op i stedet for at
  gætte på en pause.

**Vinduet er kort, og det er en grænse ikke en indstilling.** Android giver en
FCM-vækket baggrunds-handler nogle få tiendedele af et minut, før den bliver
lukket ned igen. Det rækker til en position, en kort optagelse eller en
filskrivning — ikke til et minuts lyd. Derfor er ventetiden her bundet, og
kalderen får et ærligt nej i stedet for at hænge.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

# Hvor længe vi venter på at telefonen dukker op efter en vækning. Bundet af
# Androids baggrundsvindue, ikke af vores tålmodighed: venter vi længere, er
# appen alligevel lukket ned i den anden ende.
VENT_S = 20.0

# Hvor tit vi kigger efter broen. Tæt nok til at et hurtigt svar ikke koster
# et halvt sekund oveni, løst nok til ikke at hamre på delt cache.
POLL_S = 0.4

# Vækninger er billige, men ikke gratis: hver er en FCM-levering og en
# app-opstart. To kald lige efter hinanden skal ikke vække to gange.
_GENVAEK_S = 5.0
_sidst_vaekket: dict[str, float] = {}

WAKE_KIND = "bro_vaekning"


def telefon_er_forbundet(user_id: str) -> bool:
    """Er der en klient med telefon-værktøjer for brugeren lige nu?

    Kender telefonen på hvad den KAN, ikke på klientnavn — samme mekanik som
    routingen og som scope-porten, så de tre ikke kan blive uenige.
    """
    try:
        from core.services import bridge_presence
        from core.tools.phone_tools import PHONE_TOOL_NAMES
        info = bridge_presence.all_presence().get(str(user_id)) or {}
        navne = set(PHONE_TOOL_NAMES)
        klienter = info.get("clients")
        if isinstance(klienter, dict):
            return any(navne & set((c or {}).get("capabilities") or ())
                       for c in klienter.values())
        return bool(navne & set(info.get("capabilities") or ()))
    except Exception:
        return False


def _send_vaekning(user_id: str) -> bool:
    """Stille data-push. Ingen title/preview → ingen synlig notifikation."""
    try:
        from core.services import device_tokens as dt
        from core.services.fcm_gateway import send
    except Exception:
        logger.debug("phone_wake: push-vejen findes ikke", exc_info=True)
        return False

    tokens = list(dt.list_for_user(str(user_id)) or [])
    if not tokens:
        logger.info("phone_wake: ingen device-token for %s", user_id)
        return False
    sendt = False
    for token in tokens:
        try:
            ok, kode = send(token, {"kind": WAKE_KIND})
            sendt = sendt or bool(ok)
            if not ok:
                logger.debug("phone_wake: fcm svarede %s", kode)
        except Exception:
            logger.debug("phone_wake: fcm-fejl", exc_info=True)
    return sendt


def vaek_og_vent(user_id: str, *, vent_s: float = VENT_S) -> bool:
    """Væk telefonen og vent på at broen melder sig. True hvis den kom.

    Returnerer med det samme hvis den allerede er der — vækning er kun for
    en sovende telefon.
    """
    uid = str(user_id or "")
    if not uid:
        return False
    if telefon_er_forbundet(uid):
        return True

    nu = time.time()
    if nu - _sidst_vaekket.get(uid, 0.0) < _GENVAEK_S:
        # Vi har lige banket på; giv den den resterende tid i stedet for at
        # sende endnu en levering ind i den samme opstart.
        pass
    else:
        if not _send_vaekning(uid):
            return False
        _sidst_vaekket[uid] = nu

    frist = time.time() + max(1.0, float(vent_s))
    while time.time() < frist:
        time.sleep(POLL_S)
        if telefon_er_forbundet(uid):
            logger.info("phone_wake: telefonen kom efter %.1f s",
                        vent_s - (frist - time.time()))
            return True
    logger.info("phone_wake: telefonen kom ikke inden for %.0f s", vent_s)
    return False
