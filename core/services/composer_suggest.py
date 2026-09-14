"""Forslag i komponisten — hvad der kunne skrives videre, mens man skriver.

## Hvorfor lokalt, og kun lokalt

Et forslag er baggrundsarbejde, ikke Bjørns tur. Reglen han har gentaget mange
gange — og som blev håndhævet i koden 14/9 — er at den betalte DeepSeek-API kun
må bruges i hans egne kørsler. Et forslag fyrer mens han *skriver*, altså før
der overhovedet er en tur.

Der er en grund mere, og den vejer tungere: **udkastet forlader aldrig
maskinen.** Halvskrevne sætninger er det mest private i en samtale — de
indeholder det man fortryder, omformulerer eller sletter igen. Den slags sendes
ikke til en betalt API for at spare et halvt sekunds tastearbejde.

## Hvorfor et kort loft på ventetiden

`semantic_memory._ollama_base_url` bærer husets erfaring: recall-embeds
konkurrerede med det synlige svar om GPU-ollamaen og køede **28–91 sekunder**.
Et forslag der kommer efter et sekund er allerede uinteressant — brugeren har
skrevet videre. Derfor et hårdt loft, og tomt frem for sent.

## Hvad der ikke spørges om

Tre tilfælde giver aldrig et kald: et udkast der er for kort (intet at gætte
på), et der slutter på tegnsætning (han er færdig — at foreslå videre dér er at
tale i munden på ham), og et der er meget langt (skriver han et helt afsnit,
ved han hvad han vil). Hvert af dem sparer et kald OG en dårlig oplevelse.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Final

logger = logging.getLogger(__name__)

#: Modellen sættes i runtime.json, ikke i kode. Bjørn har qwen på sin GPU i
#: dag; i morgen er det en anden.
MODEL_NOEGLE: Final[str] = "composer_suggest_model"
_STANDARD_MODEL: Final[str] = "qwen3:4b-instruct-2507-q4_K_M"

#: Målt 14/9 på runtime: 0,51–0,69 s for et forslag. Loftet er sat over det,
#: men langt under hvad der ville nå at blive irrelevant.
TIMEOUT_S: Final[float] = 1.8

#: Under det er der intet signal — og et forslag der flimrer ved hvert
#: tastetryk er værre end ingen.
MIN_TEGN: Final[int] = 8
#: Over det ved han hvad han vil, og prompten skal ikke vokse ubegrænset.
MAKS_UDKAST: Final[int] = 600
#: Et langt forslag er ikke et forslag, det er et svar.
MAKS_TEGN: Final[int] = 80

#: Slutter udkastet her, er sætningen færdig.
_FAERDIG = re.compile(r"[.!?:;]\s*$")


def _base_url() -> str:
    """GPU-ollamaen. Aldrig en betalt vært — se modulets docstring."""
    try:
        from core.runtime.secrets import read_runtime_key
        u = str(read_runtime_key("composer_suggest_base_url") or "").strip()
        if u:
            return u.rstrip("/")
    except Exception:
        pass
    return "http://127.0.0.1:11434"


def _model() -> str:
    try:
        from core.runtime.secrets import read_runtime_key
        m = str(read_runtime_key(MODEL_NOEGLE) or "").strip()
        if m:
            return m
    except Exception:
        pass
    return _STANDARD_MODEL


_PROMPT = (
    "Du fuldfører en sætning som en bruger er i gang med at skrive til sin "
    "assistent. Svar KUN med fortsættelsen — gentag ikke det der allerede står, "
    "og skriv ikke selve svaret på spørgsmålet. Højst ti ord. Ingen "
    "anførselstegn.\n\nSkrevet indtil nu:\n"
)


def _kald_model(udkast: str) -> str:
    """Ét kald til den lokale model. Kaster ved fejl; `foreslaa` fanger."""
    krop = json.dumps({
        "model": _model(),
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 40,
        "messages": [{"role": "user", "content": _PROMPT + udkast}],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{_base_url()}/v1/chat/completions", data=krop,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as svar:
        d = json.loads(svar.read().decode("utf-8"))
    besked = ((d.get("choices") or [{}])[0]).get("message") or {}
    return str(besked.get("content") or "")


def _afkort(udkast: str, svar: str) -> str:
    """Fjern den del af svaret der gentager udkastet.

    Modellen gentager gerne hele sætningen — målt 14/9 svarede qwen
    `"kan du lige tjekke om der er fejl i denne sætning?"` på et udkast der
    allerede indeholdt de første seks ord. Uden det her ville komponisten vise
    «kan du tjekke kan du tjekke om…».

    Sammenligningen ser bort fra kasse: modellen retter gerne
    begyndelsesbogstavet, og et match der krævede samme kasse ville lade
    gentagelsen slippe igennem.
    """
    s = (svar or "").strip()
    u = (udkast or "")
    if s.lower().startswith(u.strip().lower()):
        return s[len(u.strip()):]
    return s


def _ryd(s: str) -> str:
    """Én linje, uden omsluttende anførselstegn, afkortet ved et ordskel."""
    s = (s or "").split("\n")[0].strip()
    # Anførselstegn om HELE svaret — ikke inde i det; et citat midt i en
    # sætning er brugerens eget og skal blive stående.
    for a, b in (('"', '"'), ("'", "'"), ("«", "»"), ("“", "”")):
        if len(s) >= 2 and s.startswith(a) and s.endswith(b):
            s = s[1:-1].strip()
    if len(s) > MAKS_TEGN:
        # Klip ved et ordskel. Et halvt ord ligner en fejl, ikke et forslag.
        klip = s[:MAKS_TEGN]
        mellemrum = klip.rfind(" ")
        s = (klip[:mellemrum] if mellemrum > 0 else klip).rstrip()
    return s


def foreslaa(udkast: str) -> str:
    """Fortsættelsen af `udkast`, eller `""`.

    Kaster aldrig. Komponisten skal kunne skrives i uanset hvad der sker med
    modellen — et forslag er en bekvemmelighed, ikke en funktion man kan miste.
    """
    u = (udkast or "").strip()
    if len(u) < MIN_TEGN or len(u) > MAKS_UDKAST:
        return ""
    if _FAERDIG.search(u):
        return ""
    try:
        raa = _kald_model(u)
    except Exception:
        logger.debug("composer_suggest: kald fejlede", exc_info=True)
        return ""
    if not raa.strip():
        return ""
    ud = _ryd(_afkort(u, _ryd(raa)))
    # Et forslag der kun gentager det man allerede har skrevet, er støj.
    if not ud.strip():
        return ""
    # Fortsættelsen hænger på det sidste ord med et mellemrum, med mindre den
    # selv begynder med tegnsætning («…tjekke» + «, tak»).
    if not ud[0].isspace() and not ud[0] in ",.!?:;":
        ud = " " + ud
    return ud
