"""Forslag i komponisten — hvad der kunne skrives videre, mens man skriver.

## Hvem der foreslår (ændret 28/9-2026)

Forslaget til den NÆSTE besked kommer nu udelukkende fra Jarvis selv, gennem
vaerktoejet `suggest_next_message`. Den lokale model (qwen3:4b) skrev tidligere
et bud naar han ikke selv lagde et ned; det blev droppet efter Bjoerns maaling
og dom: «drop den anden models forslag og kun bruge dine... den anden model
viser lorte forslag». Af 428 viste forslag kom 411 fra modellen, og de blev
valgt 2,9 % af gangene mod 23,5 % for hans egne.

Det er et bevidst tab af daekning: uden et eget forslag staar pladsholderen
TOM. Et tomt felt er aerligere end et daarligt forslag.

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


def _kald_model(prompt: str) -> str:
    """Ét kald til den lokale model. Kaster ved fejl; kalderen fanger."""
    krop = json.dumps({
        "model": _model(),
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 40,
        "messages": [{"role": "user", "content": prompt}],
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
        raa = _kald_model(_PROMPT + u)
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


# ───────────────────────────────────────────── forslag til den NÆSTE besked
#
# Desk viser forslaget dér hvor pladsholderen står — i det TOMME felt, ikke
# som grå tekst der dukker op midt i en sætning man er i gang med at skrive.
# Bjørn 17/9-2026: «det kommer dumpende mens jeg skriver, det er virkelig
# træls». Et forslag der konkurrerer med hans egne ord er en afbrydelse; et
# forslag der står og venter i det tomme felt er et tilbud.
#
# Det ændrer hvad forslaget ER: ikke resten af en sætning, men et helt bud på
# hvad han kunne sige nu. Derfor er kilden samtalen og ikke udkastet — der er
# jo ikke noget udkast.

#: Hvor mange rækker der HENTES. Kun den sidste bruges — den bærer
#: kilde-beskeden; de øvrige afgør om turen er i gang.
MAKS_HISTORIK: Final[int] = 6

#: Under det er assistentens sidste besked en stump — «4.», «Generation
#: cancelled.», «OK» — og der er intet at bygge et næste skridt på. Målt
#: 17/9-2026: netop dér svarede modellen «Fire. Det er nemt.» og «Jeg forstår
#: ikke, hvad du mener», altså replikker i samtalen frem for forslag.
MIN_SVAR_TEGN: Final[int] = 40

def _samtale(session_id: str) -> list[dict[str, str]]:
    """De seneste beskeder. Egen funktion, så testene kan sætte dem."""
    from core.services.chat_sessions import recent_chat_session_messages
    return recent_chat_session_messages(session_id, limit=MAKS_HISTORIK)


def _tomt() -> dict[str, str]:
    """Intet forslag — og dermed intet at melde tilbage om."""
    return {"forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def foreslaa_naeste(session_id: str) -> str:
    """Et bud på brugerens næste besked, eller `""`.

    Kaster aldrig — samme regel som `foreslaa`: komponisten skal virke uanset
    hvad der sker med modellen.
    """
    return foreslaa_naeste_detaljer(session_id)["forslag"]


def foreslaa_naeste_detaljer(session_id: str) -> dict[str, str]:
    """Forslaget OG det klienten skal bruge for at kunne melde valget tilbage.

    Tre felter: `forslag`, `forslag_id` og `kilde_besked_id`. Id'et fødes her
    og gemmes IKKE — serveren husker ingenting om et forslag der måske aldrig
    kommer på skærmen (se `db_composer_choice`). Klienten sender de to id'er
    tilbage når forslaget vises og når det bliver valgt eller vraget.

    Tomt forslag → tomme id'er. Der er ikke noget at melde tilbage om.
    """
    sid = (session_id or "").strip()
    if not sid:
        return _tomt()
    try:
        raekker = _samtale(sid)
    except Exception:
        logger.debug("composer_suggest: kunne ikke læse samtalen", exc_info=True)
        return _tomt()
    beskeder = [
        b for b in raekker
        if str(b.get("role") or "") in ("user", "assistant")
        and str(b.get("content") or "").strip()
    ]
    if not beskeder:
        return _tomt()
    # Står der en ubesvaret besked fra ham, er turen i gang. At foreslå en ny
    # besked dér er at tale i munden på et svar der er på vej.
    if str(beskeder[-1].get("role") or "") != "assistant":
        return _tomt()
    # En stump til sidst («4.», «Generation cancelled.») er ikke et svar der
    # peger nogen steder hen — og et forslag på den ville være et bud uden
    # noget at bygge på.
    if len(" ".join(str(beskeder[-1].get("content") or "").split())) < MIN_SVAR_TEGN:
        return _tomt()

    # Jarvis' EGET forslag (24/9-2026). Bjørn: «det burde endelig osse være
    # dig der kommer med forslag i composer». Skriver han selv linjen, er den
    # bedre end en 4b-model der kun læser én besked — han ved hvad han lige
    # har lavet, og hvad næste skridt er. Forslaget forbruges ved læsning:
    # det hører til ÉN tur, og et forældet bud er værre end ingen. Findes det
    # ikke, står pladsholderen tom — den lokale model blev droppet 28/9-2026.
    try:
        from core.runtime.db_composer_jarvis import tag_forslag
        eget = tag_forslag(session_id=sid)
    except Exception:
        logger.debug("composer_suggest: kunne ikke læse Jarvis' forslag", exc_info=True)
        eget = None
    if eget and str(eget.get("forslag") or "").strip():
        return {
            "forslag": str(eget["forslag"]).strip(),
            "forslag_id": str(eget.get("forslag_id") or ""),
            "kilde_besked_id": str(beskeder[-1].get("message_id") or ""),
        }

    # Her stod den lokale models forslag (qwen3:4b) indtil 28/9-2026.
    # Bjørn: «drop den anden models forslag og kun bruge dine... den anden
    # model viser lorte forslag». Målt i `composer_choices`: af 428 viste
    # forslag kom 411 fra modellen og 17 fra Jarvis selv — og hans egne blev
    # valgt 23,5 % af gangene mod modellens 2,9 %, altså otte gange så ofte.
    # Modellen læste ÉN besked og gættede i blinde; Jarvis ved hvad han lige
    # har lavet. Uden et eget forslag står pladsholderen tom — et tomt felt
    # er bedre end et dårligt forslag.
    return _tomt()
