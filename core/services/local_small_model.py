"""Ét-ords-spoergsmaal til den lille lokale model paa Jarvis' eget kort.

Udskilt 7/9-2026 da kalder nummer to kom til (``local_intent_gate`` og
``smith_noise_veto``). Begge stiller samme slags spoergsmaal: en kort tekst
ind, ét ord ud, og et svar der aldrig maa vaere vaerd at vente paa.

Modellen ligger residens i CT105's VRAM (qwen3:4b, 5,37 af 8 GB, keep_alive
uendeligt) paa et kort med 0 % udnyttelse. Maalt: 0,17-0,19 s pr. kald.

## Hvorfor lokalt frem for cheap lane

Ikke kvalitet — **fejlretning**. Begge kaldere sidder taet paa Jarvis' prompt
og hans staaende direktiver. En udbyder der er nede har to gange leveret sin
kvotefejl videre som INDHOLD (``provider_error_in_self_anchor``; explore-fundet
der viste sig at vaere en fejlbesked). En lokal model der er nede leverer
``None``, og kalderen bestemmer selv hvad tavshed betyder.

## Hvorfor deadlinen er saa stram

Ollama-kald KOEER 28-91 s naar ollama er optaget — dokumenteret som selve
cut-off-roden i ``prompt_contract._timed_result``. Standarden her giver otte
gange luft over det maalte kald og fejler til ``None``.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

MODEL = "qwen3:4b-instruct-2507-q4_K_M"
STANDARD_TIMEOUT_S = 1.5

# (14/11-2026) KOLD START ER EN ANDEN SAG END ET VARMt KALD.
# Maalt: varm model svarer paa 0,10-0,20 s, men naar modellen ikke ligger i
# VRAM tager det 3,20 s at indlaese de 5,37 GB. Med den stramme graense paa
# 1,5 s kunne det FOERSTE kald efter en kold model derfor ALDRIG lykkes — det
# timede ud, returnerede None, og dommeren talte det som «ikke undersoegt».
# Maalt i journalen: 170 runtime-genstarter siden 7/11, og hver af dem er en
# kold model. Det var ikke en hang — det var en graense sat efter den varme
# tilstand, anvendt paa den kolde.
#
# Fristen haeves KUN for det foerste kald efter en kold model. Den stramme
# standard bevares for alle varme kald, saa prompt-samlingens samlede budget
# (som `test_deadlinen_er_stram_nok` vaerner) ikke aendres.
KOLD_START_TIMEOUT_S = 8.0

#: Er modellen set svare siden denne proces startede? Foerste kald betaler
#: indlaesningen; derefter er den varm indtil ollama selv genstarter.
_model_varm = False


def base_url() -> str:
    """CHAT-ollamaens adresse — ikke embeddings'.

    Maalt 2/10-2026: her stod ``semantic_memory._ollama_base_url()``, og den
    peger med vilje paa den DEDIKEREDE EMBED-vaert (``embed_ollama_base_url``,
    127.0.0.1:11435), som KUN har ``nomic-embed-text``. Chat-modellen
    (``qwen3:4b``) ligger paa 11434.

    Foelgen var tavs: hvert kald svarede ``None`` paa 0,00 s, og
    ``local_intent_gate`` fejler LUKKET — saa gaten sagde nej til ALT.
    Gate-events viser det praecist: sidste ``gate=1`` var 24/9-2026, derefter
    nul ja i otte doegn. Ingen opdagede det, fordi kanalen var slukket og
    sektionen returnerede tomt alligevel.

    Det er samme fejl som ``model_pair_resolver`` fik rettet 28/9-2026 — den
    blev blot ikke rettet her, hvor kopien stod. Adressen tages derfor fra
    samme kilde som den der FAKTISK kalder chat-modellen.
    """
    try:
        from core.services.model_pair_resolver import _chat_ollama_base_url
        return (_chat_ollama_base_url() or "").rstrip("/") or "http://127.0.0.1:11434"
    except Exception:
        return "http://127.0.0.1:11434"


def spoerg_et_ord(
    system: str, bruger: str, *, timeout_s: float = STANDARD_TIMEOUT_S,
) -> str | None:
    """Foerste HELE ord af modellens svar, med STORE bogstaver. ``None`` = intet svar.

    ``None`` daekker alt: modellen er nede, den koeer, den svarer uforstaaeligt.
    Kalderen afgoer hvad det betyder — de to nuvaerende kaldere laeser det
    modsat, og det er med vilje (se deres respektive moduler).

    Foerste ORD, ikke praefiks: «JAVEL» er ikke et ja, og begge kaldere fejler
    i en retning hvor et fejllaest ord koster noget.
    """
    system = (system or "").strip()
    bruger = (bruger or "").strip()
    if not system or not bruger:
        return None

    # Kold model betaler indlaesningen (maalt 3,20 s for 5,37 GB). Kun det
    # foerste kald efter en kold model faar den lange frist; en kalder der selv
    # har sat en strammere graense beholder sin egen.
    global _model_varm
    effektiv_timeout = timeout_s
    if not _model_varm and timeout_s >= STANDARD_TIMEOUT_S:
        effektiv_timeout = max(timeout_s, KOLD_START_TIMEOUT_S)

    krop = json.dumps({
        "model": MODEL,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 4},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": bruger[:1200]},
        ],
    }).encode()

    try:
        anmodning = urllib.request.Request(  # noqa: S310 - fast lokal URL
            f"{base_url()}/api/chat", krop, {"Content-Type": "application/json"})
        with urllib.request.urlopen(anmodning, timeout=effektiv_timeout) as svar:  # noqa: S310
            data = json.loads(svar.read())
        tekst = str((data.get("message") or {}).get("content") or "").strip().upper()
        _model_varm = True
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # INFO, ikke DEBUG: root-loggeren staar paa INFO, saa en debug-linje her
        # var usynlig — og saa forsvandt de kolde timeouts uden spor. Det var
        # derfor fejlen kunne leve i ni dage uden at nogen saa den.
        logger.info("local_small_model: naaede ikke modellen (%s)", exc)
        return None
    except Exception as exc:
        logger.info("local_small_model: uventet svar: %s", exc)
        return None

    foerste = re.match(r"[A-ZÆØÅ]+", tekst)
    return foerste.group(0) if foerste else None
