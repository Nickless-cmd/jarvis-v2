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
#: Et løfte der ikke er indfriet inden da, er uinteressant. Målt 17/9-2026 på
#: ægte runder: 0,45–3,0 s, og de LANGE runder ramte loftet og gav tom etiket.
#: Ingen venter på den — tråden er daemon og etiketten bærer sine
#: `tool_use_ids`, så den finder sine kald uanset hvornår den lander. Et loft
#: der kaster halvdelen af arbejdet væk for at spare to sekunder ingen mærker,
#: er en dårlig handel.
TIMEOUT_S: Final[float] = 6.0

#: Hvor mange kald der kommer MED i billedet. En runde på 50 kald gav en
#: prompt på 15.000 tegn og dermed timeout. De første kald siger hvad runden
#: handlede om; resten tælles med som et antal.
MAKS_KALD: Final[int] = 8

_PROMPT = (
    "Skriv en kort etiket der beskriver hvad de her værktøjskald UDRETTEDE.\n"
    "Den vises som én linje i en app og klippes omkring 30 tegn — tænk "
    "commit-emne, ikke sætning. Behold det mest sigende navneord. "
    # Målt 17/9-2026 på ægte runder: «Sed 645 700p chatview tsx», «cd
    # /media/projects/jarvis-v2 && grep -n», «Grep -rn instrument_fix core».
    # Etiketten blev kommandolinjen selv — præcis det den mekaniske linje
    # allerede viser, og ubrugelig som overskrift.
    "Skriv ALDRIG kommandoen eller værktøjsnavnet af: «grep» bliver til "
    "«Søgte», «sed»/«cat»/«head» til «Læste», «cd» nævnes slet ikke, "
    "«git log» til «Hentede historikken». Ingen flag, stier med skråstreger "
    "eller && i etiketten. "
    # Samme måling: «Grepede», «Sættede», «Editerede», «CD'et til projects».
    # Modellen boejer engelske kommandonavne som danske verber.
    "Brug rigtige danske verber — ikke fordanskede kommandonavne som "
    "«grepede», «editerede» eller «cd'et». "
    # Og: «Hentede loggen» stod som etiket paa runder der hverken hentede
    # eller loggede noget. Det er modellens standardgaet naar den ikke ved
    # hvad runden handlede om.
    "Sig hvad runden handlede OM — den fil, det navn, det tal der blev rørt. "
    "Ved du det ikke, så skriv en kortere, sand etiket frem for at gætte; "
    "«Hentede loggen» er forkert når der ikke blev hentet en log. "
    "Præcis ÉN linje — ikke en liste. "
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
    alle = list(vaerktoejer or [])
    resten = len(alle) - MAKS_KALD
    for v in alle[:MAKS_KALD]:
        raa_navn, raa_input = _navn_og_input(v)
        navn = _klip(raa_navn, 60)
        if not navn:
            continue
        dele.append(
            f"Værktøj: {navn}\n"
            f"Input: {_klip(raa_input, MAKS_PR_VAERKTOEJ)}\n"
            f"Output: {_klip(v.get('result') or v.get('output'), MAKS_PR_VAERKTOEJ)}"
        )
    if resten > 0:
        dele.append(f"(og {resten} kald mere i samme runde)")
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


#: Modellen skriver af og til sin egen instruktion med. Målt i produktion
#: 14/9: «Skriv etiketten: Kørte beacon scriptet». Kun KENDTE instruktions-ord
#: foran kolonet udløser det — ellers ville «Kørte ls: fandt 3 filer» blive
#: klippet, og det er en rigtig etiket.
_INSTRUKTION = re.compile(
    r"^\s*(?:skriv\s+)?(?:etiket(?:ten)?|label|svar|resultat)\s*[:：—–-]\s*",
    re.IGNORECASE,
)

#: Bindeord der starter et NYT led. Blev teksten klippet, ryger leddet efter
#: dem — se `_klip_haengende`.
_LED_SKEL = (" og ", " eller ", " samt ", " men ")

#: Ord en etiket ikke må slutte på når den er blevet klippet.
_HAENGENDE = {
    "og", "eller", "i", "til", "fra", "med", "af", "for", "som", "der",
    "at", "paa", "på", "om", "ved", "over", "under", "efter", "men",
}

_AFSLUT = re.compile(r"[.\s]+$")


def _klip_haengende(s: str, blev_klippet: bool) -> str:
    """Få en klippet etiket til at slutte hvor et led slutter.

    Det ægte fund 14/9: «Restartede crash-beacon og hentede». Den ender ikke på
    et bindeord — den ender på et VERBUM hvis objekt blev klippet væk, og det
    er derfor en liste over bindeord aldrig kunne fange den. To mutationer
    overlevede den test, og det var testen der var tom.

    Er teksten klippet, ryger det sidste led med, så etiketten slutter hvor
    noget faktisk slutter. Var den IKKE klippet, er «og» forfatterens egen
    sætning og skal blive stående.
    """
    if blev_klippet:
        for skel in _LED_SKEL:
            i = s.lower().rfind(skel)
            if i > 0:
                s = s[:i]
                break
    ord_ = s.split()
    while ord_ and ord_[-1].lower().strip(",;:") in _HAENGENDE:
        ord_.pop()
    return " ".join(ord_)


def _ryd(s: str) -> str:
    """Én linje, uden instruktion, uden anførselstegn, uden punktum, klippet
    ved et ordskel — og uden et hængende bindeord til sidst."""
    s = (s or "").split("\n")[0].strip()
    s = _INSTRUKTION.sub("", s).strip()
    for a, b in (('"', '"'), ("'", "'"), ("«", "»"), ("“", "”")):
        if len(s) >= 2 and s.startswith(a) and s.endswith(b):
            s = s[1:-1].strip()
    s = _AFSLUT.sub("", s)
    blev_klippet = len(s) > MAKS_ETIKET
    if blev_klippet:
        klip = s[:MAKS_ETIKET]
        mellemrum = klip.rfind(" ")
        s = (klip[:mellemrum] if mellemrum > 0 else klip).rstrip()
        s = _AFSLUT.sub("", s)
    return _klip_haengende(s, blev_klippet)


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


#: Kommandonavne en etiket aldrig må begynde med. Prompten siger det, men en
#: prompt er et håb — og målt 17/9-2026 skrev modellen alligevel «Sed 645 700p
#: chatview tsx» og «cd /media/projects/jarvis-v2 && grep -n». Samme greb som
#: fabrikations-værnet: en kedelig etiket er harmløs, en der bare gentager
#: kommandolinjen er støj oven på den mekaniske linje der viser den i forvejen.
_KOMMANDOER: Final[frozenset[str]] = frozenset({
    "grep", "rg", "sed", "awk", "cat", "head", "tail", "ls", "cd", "cp", "mv",
    "rm", "mkdir", "chmod", "curl", "wget", "git", "npm", "npx", "node",
    "python", "python3", "pytest", "echo", "find", "wc", "sqlite3", "ssh",
    "scp", "sudo", "systemctl", "journalctl", "diff", "tar", "df", "du", "ps",
})

#: Danske endelser modellen hæfter på et kommandonavn («grepede», «cd'et»).
_ENDELSER: Final[tuple[str, ...]] = ("'ede", "'et", "ede", "et", "te", "de", "'ed")

#: Skal-syntaks der aldrig hører til i en overskrift.
_SKAL_SYNTAKS = re.compile(r"(?:&&|\|\||\s-{1,2}[A-Za-z]|\s\|\s)")


def _er_kommandolinje(s: str) -> bool:
    """Er etiketten bare kommandoen igen?"""
    if _SKAL_SYNTAKS.search(s or ""):
        return True
    foerste = (s or "").strip().split()
    if not foerste:
        return False
    ord0 = foerste[0].lower().strip(".,;:!?«»\"'")
    if ord0 in _KOMMANDOER:
        return True
    for e in _ENDELSER:
        if ord0.endswith(e) and ord0[: -len(e)] in _KOMMANDOER:
            return True
    return False


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
    # Et nøgent verbum er ikke en overskrift. Målt 17/9-2026: modellen svarede
    # «Søgte agent-21cc158c0a274d98ae2e4c0fb56bb57», og klipningen ved 40 tegn
    # åd hele objektet, så der stod «Søgte». Bedre ingen linje end en der ikke
    # siger mere end den mekaniske gør i forvejen.
    if len(ud.split()) < 2:
        return ""
    if _er_kommandolinje(ud):
        logger.info("runde-etiket kasseret — den gentager bare kommandoen: %r", ud)
        return ""
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
