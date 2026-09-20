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
from uuid import uuid4
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

#: Hvor mange rækker der HENTES. Kun den sidste bruges i prompten (se
#: `_kontekst`); de øvrige afgør om turen er i gang.
MAKS_HISTORIK: Final[int] = 6

#: Budgettet for den ENE besked der bærer konteksten. Afløste
#: `MAKS_BESKED_TEGN = 400` 20/9-2026: dengang skulle seks beskeder deles om
#: prompten, nu er der kun én — men den skal stadig kunne holdes i hovedet af
#: en 4b-model.
MAKS_KONTEKST_TEGN: Final[int] = 900

#: Under det er assistentens sidste besked en stump — «4.», «Generation
#: cancelled.», «OK» — og der er intet at bygge et næste skridt på. Målt
#: 17/9-2026: netop dér svarede modellen «Fire. Det er nemt.» og «Jeg forstår
#: ikke, hvad du mener», altså replikker i samtalen frem for forslag.
MIN_SVAR_TEGN: Final[int] = 40

_PROMPT_NAESTE = (
    "Du hjælper en bruger med at skrive sin næste besked til sin assistent.\n"
    "Herunder står assistentens SENESTE besked. Foreslå ÉN besked brugeren "
    "kunne sende nu — det næste skridt der følger af netop den besked.\n\n"
    "Krav:\n"
    # Målt 17/9-2026: modellen svarede assistenten i stedet for at bede om
    # noget — «Fire. Det er nemt.», «Ja, det kan vi lave i morgen!». Et svar
    # kan brugeren skrive selv; et forslag skal spare ham for at formulere en
    # ordre.
    "- Det skal være en ORDRE eller et SPØRGSMÅL til assistenten — noget "
    "brugeren beder om. Aldrig et svar, en kommentar eller en høflighed.\n"
    # Målt samme dag: «Så kan vi gå videre til næste trin» — sandt om enhver
    # samtale, og derfor ubrugeligt i denne.
    "- Det skal nævne noget KONKRET fra beskeden: en fil, et navn, et tal, en "
    "opgave. Et forslag der passer på enhver samtale, er ikke et forslag.\n"
    # Bjørn 20/9-2026: «hvis du feks. har skrevet 3 veje hvor du anbefaler en
    # bør den gå med den». Peger beskeden selv på en vej, er valget truffet —
    # et forslag der spørger om noget der allerede er anbefalet, er spild.
    "- Peger beskeden på en anbefalet vej blandt flere, skal forslaget følge "
    "DEN vej — ikke de fravalgte.\n"
    "- Dansk. Højst ti ord. Ingen indledning som «Så nu» eller «Okay».\n"
    "- Svar KUN med beskeden: ingen anførselstegn, intet rollenavn, ingen "
    "forklaring.\n\n"
    "Eksempler på FORMEN (indholdet skal komme fra samtalen nedenfor): "
    "«Deploy det og hold øje med journalen» · «Vis mig de to der står i "
    "karantæne» · «Hvorfor fejler den kun på ct105?» · «Ret det og kør "
    "testene igen»\n\n"
    "Assistentens sidste besked:\n"
)

#: Åbninger der afslører en REPLIK frem for en ordre. Kun begyndelser, og kun
#: entydige: «Ja, det kan vi…» er et svar, mens «Jeg vil have dig til at…» er
#: en ordre og skal slippe igennem.
_REPLIK_START: Final[tuple[str, ...]] = (
    "ja,", "ja.", "ja ", "nej,", "nej.", "nej ", "tak", "okay", "ok,", "ok.",
    # Begge stavemaader: modellen skriver af og til uden danske bogstaver
    # (målt: den svarede endda «Takk for det» på norsk).
    "jeg forstår", "jeg forstaar", "det lyder", "det er godt", "godt,",
    "super", "fedt", "takk",
    "enig", "nemlig", "præcis",
)

#: Modellen svarer gerne med rollen foran, fordi den står i prompten.
_ROLLE_PRAEFIKS = ("bruger:", "brugeren:", "user:", "assistent:", "assistant:")


def _er_paastand(s: str) -> bool:
    """Er forslaget en konstatering frem for noget man beder om?

    Målt 17/9-2026: «Fyrede kl. 20:18, ventetid var 60 sekunder» — modellen
    refererede hvad der var sket i stedet for at bede om noget. En ordre
    begynder aldrig med et datids-verbum («Vis», «Ret», «Kør», «Verificer»),
    og et spørgsmål bærer sit spørgsmålstegn. Derfor kan de to skelnes uden at
    forstå sætningen.
    """
    t = (s or "").strip()
    if not t or "?" in t:
        return False
    ord0 = t.split()[0].lower().strip(".,;:!«»\"'")
    return len(ord0) > 4 and (ord0.endswith("ede") or ord0.endswith("te"))


#: Vendinger hvor beskeden selv peger på en vej. Målt på Jarvis' egne svar
#: 20/9-2026: anbefalingen står næsten altid til SIDST, efter mulighederne —
#: «Tre veje: (a) … (b) … (c) … Jeg ville tage (b) først».
_ANBEFALING: Final[tuple[str, ...]] = (
    "jeg ville", "jeg anbefaler", "min anbefaling", "jeg foreslår",
    "jeg foreslaar", "mit forslag", "jeg vil anbefale", "bedst at",
    "det rigtige er", "start med", "tag den", "vælg", "vaelg",
)


def _anbefaling(tekst: str) -> str:
    """Den sætning hvor beskeden peger på ÉN vej — eller `""`.

    Hvorfor den skal løftes ud og ikke bare stå i teksten: en 4b-model læser
    en lang besked som en liste af muligheder og griber den første. Bjørn
    20/9-2026: «hvis du feks. har skrevet 3 veje hvor du anbefaler en bør den
    gå med den». Står anbefalingen ALENE i prompten under sin egen overskrift,
    er der ikke noget at vælge imellem.

    Den SIDSTE der matcher vinder: står der «jeg ville tage (b)» efter
    «jeg foreslår tre veje», er det (b) der er dommen.
    """
    t = " ".join((tekst or "").split())
    if not t:
        return ""
    fundet = ""
    for saetning in re.split(r"(?<=[.!?])\s+", t):
        lav = saetning.lower()
        if any(v in lav for v in _ANBEFALING):
            fundet = saetning.strip()
    return fundet


def _klip_kontekst(tekst: str, maks: int = MAKS_KONTEKST_TEGN) -> str:
    """Klip en lang besked, men behold BEGGE ender.

    En ren `[:maks]` ville tage begyndelsen — og netop dér står anbefalingen
    ikke. Den står til sidst, efter mulighederne. En ren hale ville omvendt
    tabe hvad beskeden handler om. Derfor en tredjedel fra starten og resten
    fra slutningen, med et synligt spring imellem, så modellen ikke læser det
    som én sammenhængende sætning.
    """
    t = " ".join((tekst or "").split())
    if len(t) <= maks:
        return t
    hoved = maks // 3
    hale = maks - hoved
    return t[:hoved].rstrip() + " […] " + t[-hale:].lstrip()


def _kontekst(besked: str) -> str:
    """Prompt-konteksten: assistentens sidste besked, og dens anbefaling.

    Før 20/9-2026 stod her de seks seneste beskeder fra BEGGE sider. Bjørn:
    «hvis den ska virke rigtigt, skal den kun udlede kontekst fra din sidste
    besked, og hvad næste step kan være». Hans egne tidligere formuleringer er
    støj for en lille model — næste skridt ligger i svaret, ikke i spørgsmålet
    der førte til det.
    """
    krop = _klip_kontekst(besked)
    anb = _anbefaling(krop)
    if anb and anb != krop:
        return f"{krop}\n\nAssistenten anbefaler: {anb}"
    return krop


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
    # peger nogen steder hen. Målt: dér begyndte modellen at føre samtalen.
    if len(" ".join(str(beskeder[-1].get("content") or "").split())) < MIN_SVAR_TEGN:
        return _tomt()

    # Mønstret fra hans tidligere valg (fase 3, 20/9-2026). Står SIDST, som
    # en erfaring modellen vægter — ikke som et krav den adlyder. Et forslag
    # der altid beder om det samme, er en vane og ikke et tilbud.
    try:
        from core.services.composer_moenster import prompt_linje
        erfaring = prompt_linje()
    except Exception:
        logger.debug("composer_suggest: mønsteret kunne ikke læses", exc_info=True)
        erfaring = ""

    prompt = _PROMPT_NAESTE + _kontekst(str(beskeder[-1].get("content") or ""))
    if erfaring:
        prompt = f"{prompt}\n\n{erfaring}"
    try:
        raa = _kald_model(prompt)
    except Exception:
        logger.debug("composer_suggest: næste-kald fejlede", exc_info=True)
        return _tomt()

    ud = _ryd(raa)
    for praefiks in _ROLLE_PRAEFIKS:
        if ud.lower().startswith(praefiks):
            ud = ud[len(praefiks):].strip()
            break
    ud = ud.strip()
    # Et svar er ikke et forslag. Prompten siger det, men en 4b-model glider
    # tilbage i replik-rollen, og et forkert forslag koster mere end intet:
    # det står og fylder pladsholderens plads.
    if ud.lower().startswith(_REPLIK_START):
        logger.debug("composer_suggest: kasseret som replik: %r", ud)
        return _tomt()
    if _er_paastand(ud):
        logger.debug("composer_suggest: kasseret som påstand: %r", ud)
        return _tomt()
    # Ingen hæftning med mellemrum her: det er en hel besked, ikke en
    # fortsættelse af noget.
    return {
        "forslag": ud,
        "forslag_id": f"cs-{uuid4().hex[:16]}",
        "kilde_besked_id": str(beskeder[-1].get("message_id") or ""),
    }
