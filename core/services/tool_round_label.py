"""Én kort etiket for en afsluttet værktøjs-runde — «Rettede NPE i UserService».

## Hvad den er, og hvad den ikke er

Der er TO linjer om en runde, og de svarer på hvert sit spørgsmål:

- Den **mekaniske** («Kørte en kommando og redigerede 2 filer +12 −4») siger
  hvad der SKETE. Den bygges af værktøjernes egne resultater og står der med
  det samme. Den bor i klienterne.
- Den her siger hvad runden **udrettede** — i forhold til det der blev bedt om.
  Den kræver sprog, altså en model.

Jeg argumenterede 14/9 for at den slags ikke hørte hjemme på en visningslinje,
fordi et modelkald ville gøre UI'et langsommere. Det var for kategorisk.
Jarvis' research i Claude Codes kilde
(`src/services/toolUseSummary/toolUseSummaryGenerator.ts`) viser at den findes
dér, at den bruger Haiku, og at dens egen prompt siger hvor den skal vises:
*«a single-line row in a mobile app»*. Den er bygget til præcis den flade.

Og indvendingen om ventetid har et svar jeg ikke havde: CC bærer den som
`pendingToolUseSummary: Promise<…>` og leverer den **næste tur**. Den koster
ingen ventetid i den kørende tur.

## Hvorfor vi leverer den i SAMME runde

CC venter til næste tur fordi deres loop er bygget sådan. Vores stream kan bære
et top-level runde-event med det samme (`round_restart_discard_partial` findes
allerede), og klienterne grupperer i forvejen værktøjer pr. runde. Så etiketten
kan lande i den runde den handler om — uden at blokere noget. Kaldet er
fire-and-forget; runden venter aldrig.

## Hvorfor en lokal model og ikke primær-lanen

CC bruger Haiku, den lille hjælpe-model, netop fordi det er nyttearbejde.
Huset siger det samme i CLAUDE.md: billige modeller må STØTTE ham, ikke
definere ham. En etiket er ikke hans samtale, den er en overskrift over den.
Samme lokale model som komponist-forslagene — målt 0,27 s, gratis.

## Budgetterne kommer fra kilden

300 tegn pr. værktøj (navn, input, output), 200 tegn af det brugeren bad om,
og højst ~30 tegn ud. Formen er commit-emne, ikke sætning: datid, det mest
sigende navneord, artikler og bindeord ryger først.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Any, Final

logger = logging.getLogger(__name__)

#: Modellen sættes i runtime.json, ikke i kode.
MODEL_NOEGLE: Final[str] = "tool_round_label_model"
_STANDARD_MODEL: Final[str] = "qwen3:4b-instruct-2507-q4_K_M"

#: Pr. værktøj: navn, input og output klippes hver især her. Tallet er CC's.
MAKS_PR_VAERKTOEJ: Final[int] = 300
#: Hvad brugeren bad om, som kontekst. Etiketten skal beskrive hvad runden
#: udrettede I FORHOLD TIL det — ikke bare hvad værktøjet gjorde.
MAKS_HENSIGT: Final[int] = 200
#: Ud. «Omkring 30» i CC's prompt; vi klipper hårdt ved 40 så en model der
#: skriver en sætning alligevel ikke sprænger linjen.
MAKS_ETIKET: Final[int] = 40
#: Et løfte der ikke er indfriet inden da, er uinteressant.
TIMEOUT_S: Final[float] = 3.0

_PROMPT = (
    "Skriv en kort etiket der beskriver hvad de her værktøjskald UDRETTEDE.\n"
    "Den vises som én linje i en app og klippes omkring 30 tegn — tænk "
    "commit-emne, ikke sætning. Behold det mest sigende navneord. "
    # Målt: modellen gentog brugerens egen formulering — «Hent logfilerne» om
    # en runde der HAVDE hentet dem, «Finder ucommittede filer» om en der
    # fandt dem. «Datid» alene var ikke nok; den skal se forvandlingen.
    "Skriv i DATID om noget der ER sket — ikke i bydeform og ikke i nutid. "
    "«hent loggen» bliver til «Hentede loggen», ikke «Hent loggen». "
    "Drop artikler, bindeord og lange stinavne først. Svar KUN med etiketten, "
    "uden anførselstegn og uden punktum.\n"
    # Målt i produktion 14/9: modellen skrev «Søgte i bash/» om et ssh-kald —
    # den efterabede eksemplet «Søgte i auth/» og opfandt et bibliotek. Derfor
    # står forbuddet nu FØR eksemplerne, og eksemplerne siger selv at deres
    # navne er opdigtede.
    "VIGTIGT: brug kun navne, stier og kommandoer der FAKTISK står i kaldene "
    "nedenfor. Opfind aldrig et filnavn eller en mappe. Er der intet sigende "
    "navn, så skriv etiketten uden et.\n\n"
    "Eksempler paa FORMEN (navnene i dem er opdigtede — brug dem ikke): "
    "«Rettede NPE i brugerlaget» · «Byggede endpointet» · "
    "«Læste konfigurationen» · «Kørte de fejlende tests»\n\n"
)


def _model() -> str:
    try:
        from core.runtime.secrets import read_runtime_key
        m = str(read_runtime_key(MODEL_NOEGLE) or "").strip()
        if m:
            return m
    except Exception:
        pass
    return _STANDARD_MODEL


def _base_url() -> str:
    try:
        from core.runtime.secrets import read_runtime_key
        u = str(read_runtime_key("composer_suggest_base_url") or "").strip()
        if u:
            return u.rstrip("/")
    except Exception:
        pass
    return "http://127.0.0.1:11434"


def _klip(v: Any, maks: int) -> str:
    """Kort, én linje, og aldrig `None` som teksten «None»."""
    if v is None:
        return ""
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    s = " ".join(s.split())
    return s[:maks]


def _navn_og_input(v: dict[str, Any]) -> tuple[str, Any]:
    """Navn og argumenter, uanset hvilken form kaldet har.

    Runde-løkken i `visible_runs` holder kaldene i OpenAI-form —
    `{id, type, function: {name, arguments}}` — mens klienterne og
    værktøjs-laget bruger `{name, input}`. En etiket der kun forstod den ene
    ville tie om den halvdel af huset der bruger den anden.
    """
    fn = v.get("function")
    if isinstance(fn, dict):
        return str(fn.get("name") or ""), fn.get("arguments")
    return str(v.get("name") or v.get("navn") or ""), v.get("input")


def byg_prompt(vaerktoejer: list[dict[str, Any]], hensigt: str = "") -> str:
    """Det kompakte billede af runden som modellen får.

    Hvert kald bliver til tre linjer — navn, input, output — hver klippet for
    sig. At klippe hele blokken under ét ville lade ét stort `bash`-output
    skubbe de øvrige kald ud af billedet, og etiketten ville så beskrive én
    tilfældig del af runden som om den var det hele.
    """
    dele: list[str] = []
    if hensigt.strip():
        dele.append(f"Brugeren bad om: {_klip(hensigt, MAKS_HENSIGT)}\n")
    for v in vaerktoejer or []:
        raa_navn, raa_input = _navn_og_input(v)
        navn = _klip(raa_navn, 60)
        if not navn:
            continue
        dele.append(
            f"Værktøj: {navn}\n"
            f"Input: {_klip(raa_input, MAKS_PR_VAERKTOEJ)}\n"
            f"Output: {_klip(v.get('result') or v.get('output'), MAKS_PR_VAERKTOEJ)}"
        )
    return _PROMPT + "\n\n".join(dele)


def _kald_model(prompt: str) -> str:
    krop = json.dumps({
        "model": _model(), "stream": False, "temperature": 0.2, "max_tokens": 32,
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


_AFSLUT = re.compile(r"[.\s]+$")


def _ryd(s: str) -> str:
    """Én linje, uden anførselstegn, uden punktum, klippet ved et ordskel."""
    s = (s or "").split("\n")[0].strip()
    for a, b in (('"', '"'), ("'", "'"), ("«", "»"), ("“", "”")):
        if len(s) >= 2 and s.startswith(a) and s.endswith(b):
            s = s[1:-1].strip()
    s = _AFSLUT.sub("", s)
    if len(s) > MAKS_ETIKET:
        klip = s[:MAKS_ETIKET]
        mellemrum = klip.rfind(" ")
        s = (klip[:mellemrum] if mellemrum > 0 else klip).rstrip()
        s = _AFSLUT.sub("", s)
    return s


#: Ser ud som en sti eller et navn — det modellen kan finde på at opdigte.
#: Almindelige ord efterprøves IKKE: krævede vi at hvert ord stod i kaldet,
#: ville enhver omskrivning blive kasseret, og en etiket der kun må gentage
#: sit input er ikke en etiket.
_NAVNAGTIGT = re.compile(r"[A-Za-zÆØÅæøå][\wÆØÅæøå.\-/]*[./_\-][\wÆØÅæøå.\-/]*")


def _opdigtet(tekst: str, billede: str) -> str:
    """Hvilket navn i etiketten står IKKE i kaldene? `""` når alt er dækket.

    Målt i produktion 14/9: første ægte etiketter var «Kørte ssh og hentede
    logfiler» (god) og «Søgte i bash/» — hvor modellen efterabede promptens
    eget eksempel «Søgte i auth/» og opfandt et bibliotek der ikke findes.

    En strammere prompt er et håb. Huset har et bedre greb: `explore_claim_check`
    slår påstande op i kilden. Samme princip her. En kedelig etiket er harmløs;
    en der lyver om hvad der skete, er ikke.

    Kassen ses der bort fra — modellen retter gerne begyndelsesbogstavet, og et
    match der krævede samme kasse ville kassere en RIGTIG etiket.
    """
    lav = billede.lower()
    for m in _NAVNAGTIGT.finditer(tekst or ""):
        navn = m.group().strip(".,;:")
        if len(navn) < 3:
            continue
        if navn.lower() not in lav:
            return navn
    return ""


def etiket(vaerktoejer: list[dict[str, Any]], hensigt: str = "") -> str:
    """Én kort etiket for runden, eller `""`.

    Kaster aldrig. En etiket er en overskrift; en tur må aldrig vælte fordi
    overskriften ikke kunne skrives.
    """
    kald = [v for v in (vaerktoejer or []) if _navn_og_input(v)[0]]
    if not kald:
        return ""
    billede = byg_prompt(kald, hensigt)
    try:
        raa = _kald_model(billede)
    except Exception:
        logger.debug("tool_round_label: kald fejlede", exc_info=True)
        return ""
    ud = _ryd(raa)
    fundet = _opdigtet(ud, billede)
    if fundet:
        logger.info("runde-etiket kasseret — %r staar ikke i kaldene: %r", fundet, ud)
        return ""
    return ud


def tool_use_ids(vaerktoejer: list[dict[str, Any]]) -> list[str]:
    """Hvilke kald etiketten dækker.

    CC bærer det samme som `preceding_tool_use_ids`, og det er ikke pynt: uden
    det hæfter etiketten sig på en PLADS i strømmen i stedet for på sit batch.
    Kommer den sent, eller genopbygger klienten tråden i en anden rækkefølge,
    ville den ellers sætte sig over de forkerte kald.
    """
    ud: list[str] = []
    for v in vaerktoejer or []:
        i = str(v.get("id") or v.get("tool_use_id") or "").strip()
        if i:
            ud.append(i)
    return ud
