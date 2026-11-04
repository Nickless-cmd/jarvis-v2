"""Opgave → værktøj-mapping: hvad vil denne opgave sandsynligvis røre?

Baggrund (3/11-2026, Bjørn): `derive_gut_signal` modtog `task_description`, men brugte
den kun til `task_hint` — de første 80 tegn som label. `confidence` var derfor ren global
statistik (`recent_error_count`/`recent_success_count`) og 0,5 som rå default. Gaten kunne
se AT systemet havde fejlet 23 gange, men ikke OM netop denne opgave var risikabel.

Dette modul lukker det hul: det læser opgaveteksten og svarer hvilken *risikoklasse*
opgaven tilhører, så `confidence` kan blive opgavespecifik.

HVAD DER ER MÅLT, OG HVAD DER IKKE ER
-------------------------------------
Målt 3/11-2026, før dette modul blev skrevet:

- `tool_embeddings.top_k_similar()` er hurtig (0,09–0,19 s) men **ubrugelig her**:
  «læs logfilen og find fejlen» pegede på `phone_location`, og simulariteterne lå i et
  snævert 0,60–0,69-bånd — modellen kan ikke skelne. Indekset har desuden 800 poster mod
  514 katalognavne (det bærer `skillcand:`-nøgler). En confidence bygget på det ville være
  teater: den ville give tilfældige værktøjer med et troværdigt udseende.
- `heartbeat_runtime_ticks` bærer `action_type` men **ikke hvilke værktøjer** der blev brugt,
  og `action_summary` er for de fleste bare `productive_idle`. En indlært (empirisk) mapping
  er derfor ikke mulig med de data der findes.
- `AUTONOMOUS_TOOLS` er en **tilladelses**-akse, ikke en risiko-akse: 414 af 514 katalognavne
  står udenfor, inklusive harmløse som `analyze_image`. Den bruges her kun som ét signal.

Mappingen er derfor **deterministisk og kurateret** — ikke indlært. Den er grov, men ærlig:
den kan efterprøves, den kan testes, og den kan ikke narre sig selv ved at se rigtig ud.
Usikkerhed rapporteres som `unknown` med delta 0,0 — ikke som en falsk 0,5.
"""
from __future__ import annotations

import re
from typing import Any

# ── Risiko-tiers ────────────────────────────────────────────────────────────
#
# Tre niveauer, ikke to. Den binære «må et autonomt run bruge det» (AUTONOMOUS_TOOLS)
# kan ikke skelne en læsning fra en fil-sletning, og en skrivning fra en irreversibel
# migration. Det er netop den skelnen gaten har brug for.

TIER_READ = "read"           # læser eller søger — kan fortrydes ved at gøre ingenting
TIER_MUTATE = "mutate"       # skriver, opretter, retter — kan fortrydes, men rører verden
TIER_IRREVERSIBLE = "irreversible"  # sletter, udgiver, sender, migrerer — kan ikke rulles tilbage
TIER_UNKNOWN = "unknown"     # intet signal — og det siges højt

#: Confidence-justering pr. tier.
#:
#: Fortegnet er det vigtige: en farlig opgave skal sænke confidence, så den lettere
#: rammer `caution`-grenen i `derive_gut_signal` og dermed tærsklen i `gut_gate`.
#: Størrelserne er små (±0,05 / −0,15) med vilje: de må ikke selv blive en skjult
#: tærskel, og de er en HEURISTIK — ikke en måling. A5 (den egentlige tærskel) er
#: stadig urørt og skal først justeres når shadow-data findes.
_DELTA: dict[str, float] = {
    TIER_READ: 0.05,
    TIER_MUTATE: -0.05,
    TIER_IRREVERSIBLE: -0.15,
    TIER_UNKNOWN: 0.0,
}

#: Nøgleord pr. tier, dansk og engelsk. Rækkefølgen betyder noget: den FØRSTE tabel
#: der matcher afgør, og de farligste prøves først — så «slet og læs» klassificeres
#: som sletning, ikke som læsning.
_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (TIER_IRREVERSIBLE, (
        # Sletning og destruktion
        "slet", "slette", "fjern permanent", "destroy", "wipe", "purge",
        "drop", "truncate", "reset --hard", "force-push", "force push",
        # Udgivelse og afsendelse — virkning uden for systemet.
        # «send» er et enkeltord med ordgrænse: målt 3/11-2026 matchede frasen
        # «send besked» ikke «send en besked til Bjorn», så en afsendelse blev
        # klassificeret som `unknown` — den mest tillidsfulde tier for den farligste
        # handling. Ordgrænsen forhindrer samtidig at «send» rammer inde i et andet ord.
        "deploy", "deployér", "udgiv", "release", "publish", "offentliggør",
        "send", "sender", "afsend", "notificér",
        "push til", "push to", "merge til main", "merge to main",
        # Strukturelle og uigenkaldelige indgreb
        "migrér", "migrer", "migration", "migrate", "skemaændring", "schema change",
        "genstart", "restart", "reboot", "kill process", "dræb",
        "rotér nøgle", "rotate key", "tilbagefør", "rollback", "revert",
        "produktionsdatabase", "production database",
    )),
    (TIER_MUTATE, (
        "skriv", "write", "opret", "create", "ret", "retf", "fix", "opdatér",
        "opdater", "update", "gem", "save", "tilføj", "add", "indsæt", "insert",
        "flyt", "move", "omdøb", "rename", "ændr", "modify", "redigér", "edit",
        "byg", "build", "installér", "install", "konfigurér", "configure",
        "commit", "stash", "patch", "implementér", "implement", "refaktor",
    )),
    (TIER_READ, (
        "læs", "read", "søg", "search", "find", "vis", "show", "tjek", "check",
        "inspicér", "inspect", "analysér", "analyze", "analyse", "list", "list op",
        "grep", "status", "oversigt", "overview", "rapportér", "report",
        "undersøg", "investigate", "mål", "measure", "se på", "look at",
        "hvor mange", "how many", "hvad er", "what is",
        # 3/11-2026: kontrol-verberne manglede. Uden dem blev «Verificér desk-release
        # 0.6.290: tjek at GitHub-releasen har 11 assets» klassificeret som en
        # UDGIVELSE, fordi ordet «release» stod i teksten — opgaven er en kontrol AF en
        # udgivelse. Målt: 22 af 40 faktiske wakeup-tekster blev irreversible af den grund.
        "verificér", "verify", "kontrollér", "confirm", "bekræft", "gennemgå",
        "review", "evaluer", "evaluate",
    )),
)

#: Første ord i opgaven — verbet. `[\w]` dækker æ/ø/å via re.UNICODE.
_LEADING_WORD_RE = re.compile(r"^\s*([\wæøåéü]+)", re.UNICODE)

#: Præfikser der gør et værktøjsnavn læsende, uanset hvad resten af navnet indeholder.
#: Målt 3/11-2026: 93 katalognavne bærer et mutations-ord, og mange er falske positiver —
#: `list_skill_mutations`, `get_agent_skills`, `analyze_skill_usage`. Uden denne vagt
#: ville de blive klassificeret som farlige.
_READ_PREFIXES: tuple[str, ...] = (
    "list_", "get_", "read_", "search_", "find_", "analyze_", "recall_", "show_",
    "check_", "status_", "verify_", "count_", "describe_",
)

#: Værktøjer der er irreversible PER KONSTRUKTION, uanset hvad navnet ellers antyder.
#: Målt 3/11-2026: `bash` blev klassificeret som `read` fordi navnet ikke bærer et
#: mutations-ord — men et shell kan udføre hvad som helst, inklusive `rm -rf`. Et navn
#: kan ikke bære den slags viden; den skal stå her, eksplicit og gennemskuelig.
_ALWAYS_IRREVERSIBLE: frozenset[str] = frozenset({
    "bash", "operator_bash", "bash_session_run", "operator_bash_session_run",
    "operator_session_run", "operator_run_in_background",
    "execute_code", "run_code", "python_exec", "eval",
    "commit_attributed", "commit_staged_edits",
    "integrate_agent_work", "restart_self",
})

#: Navne-mønster for mutation. Bruges KUN som supplement når opgave-nøgleord intet gav.
_MUTATE_NAME_RE = re.compile(
    r"(send|delete|remove|deploy|create|write|update|push|drop|reset|restart|"
    r"kill|approve|commit|publish|install|merge|run|execute|edit|patch|move)"
)

_IRREVERSIBLE_NAME_RE = re.compile(r"(delete|remove|drop|deploy|publish|send|kill|reset|restart|migrate)")

#: Cache for katalognavne. `get_tool_definitions()` koster 378 ms første gang og 1 ms
#: derefter (målt 3/11-2026); gaten kaldes ved hvert preflight, så vi slår kun op én gang
#: pr. proces og tåler at kataloget ikke kan læses.
_CATALOG: set[str] | None = None


def _catalog() -> set[str]:
    """Katalognavne, eller et tomt sæt hvis kataloget ikke kan læses.

    Et tomt sæt betyder at eksplicit-navn-vejen ikke fyrer — mappingen falder så tilbage
    til nøgleord. Det er den sikre side: en manglende katalog må ikke gøre en opgave
    mere risikabel, end den er.
    """
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG
    try:
        from core.tools.simple_tools import get_tool_definitions
        defs = get_tool_definitions() or []
        navne = set()
        for d in defs:
            fn = d.get("function") or d
            n = fn.get("name")
            if n:
                navne.add(str(n))
        _CATALOG = navne
    except Exception:
        _CATALOG = set()
    return _CATALOG


def _tier_for_tool_name(name: str) -> str:
    """Klassificér et konkret værktøj ud fra dets navn."""
    n = name.lower()
    # Navnet kan ikke bære alt: et shell er farligt uanset hvad det hedder.
    if n in _ALWAYS_IRREVERSIBLE:
        return TIER_IRREVERSIBLE
    if n.startswith(_READ_PREFIXES):
        return TIER_READ
    if _IRREVERSIBLE_NAME_RE.search(n):
        return TIER_IRREVERSIBLE
    if _MUTATE_NAME_RE.search(n):
        return TIER_MUTATE
    # Kendt navn uden mutations-ord: læsende eller neutral.
    return TIER_READ


def _matcher(noegleord: str, tekst: str) -> bool:
    """Match et nøgleord mod teksten — enkeltord med ordgrænse, fraser som substring.

    Målt 3/11-2026: ren substring gjorde at «ret» ramte inde i «opret» og «direkte»,
    så en oprettelse blev talt som en rettelse (samme tier, men af den forkerte grund),
    og kortere ord som «byg» kunne ramme midt i et andet ord. Ordgrænsen koster intet
    og fjerner hele klassen af falske positiver for enkeltord.
    """
    if " " in noegleord or "-" in noegleord:
        return noegleord in tekst
    return re.search(rf"\b{re.escape(noegleord)}", tekst) is not None


def _leading_tier(lav: str) -> tuple[str | None, str | None]:
    """Tier for opgavens FØRSTE ord — verbet — og ordet selv.

    Returnerer `(None, None)` når første ord ikke er et handlingsord; så afgør
    nøgleordsscanningen i resten af teksten.

    HVORFOR (3/11-2026, målt): `_KEYWORDS` blev gennemløbet tabel for tabel med den
    farligste først, så et hvilket som helst farligt ord i teksten afgjorde sagen. Målt
    på 40 faktiske wakeup-tekster: **22 blev `irreversible`** — bl.a. «Verificér
    desk-release 0.6.290: tjek at GitHub-releasen har 11 assets», hvor «release» er
    objektet for en kontrol, ikke en handling. Med `mode=on` ville gaten have afvist
    55 % af alle autonome runs, inklusive ren læsning.

    Reglen er derfor: det FØRSTE ord er handlingen, resten er objektet. En opgave der
    begynder med et kontrol-verbum er en kontrol — også når den nævner noget farligt.
    """
    m = _LEADING_WORD_RE.match(lav)
    if not m:
        return None, None
    ord_ = m.group(1)
    for tier, ordliste in _KEYWORDS:
        for o in ordliste:
            if " " in o or "-" in o:
                continue
            # Præfiks-match, ikke lighed: dansk bøjer («slet» → «sletning», «verificér»
            # → «verificering»), og de bøjede former står ikke i tabellen.
            if ord_.startswith(o):
                return tier, o
    return None, None


#: Sætningsdele. En opgave kan bære FLERE handlinger: «læs listen og slet de gamle
#: rækker» er en sletning, ikke en læsning. Derfor afgøres hver del for sig, og den
#: farligste vinder — men kun verbet i hver del, så objektet ikke bliver en handling.
_CLAUSE_SPLIT_RE = re.compile(r"[.,;:&]|\bog\b|\bsamt\b|\bderefter\b", re.UNICODE)


def _clause_tiers(lav: str) -> list[tuple[str, str]]:
    """(tier, ord) for hver sætningsdels ledende verbum. Tom liste = intet handlingsord."""
    ud: list[tuple[str, str]] = []
    for del_ in _CLAUSE_SPLIT_RE.split(lav):
        tier, ord_ = _leading_tier(del_ or "")
        if tier:
            ud.append((tier, ord_))
    return ud


def map_task_to_tools(task_description: str) -> dict[str, Any]:
    """Svar på hvad denne opgave sandsynligvis vil røre, og hvor risikabel den er.

    Returnerer::

        {
          "tools":   [navne der faktisk findes i kataloget],   # kan være tom
          "tier":    "read" | "mutate" | "irreversible" | "unknown",
          "signals": [de nøgleord/navne der udløste klassifikationen],
          "method":  "explicit" | "keyword" | "name" | "none",
          "confidence_delta": float,
        }

    `method="none"` er et ÆRLIGT svar: opgaven bar intet signal, og delta er 0,0 —
    ikke en gættet neutral værdi der ser ud som en måling.

    Kaster aldrig. En fejl her må ikke kunne stoppe et run; gaten er rådgivende.
    """
    tekst = str(task_description or "")
    lav = tekst.lower()
    tomt = {
        "tools": [], "tier": TIER_UNKNOWN, "signals": [],
        "method": "none", "confidence_delta": 0.0,
    }
    if not lav.strip():
        return tomt

    katalog = _catalog()
    fundne_navne = [n for n in katalog if n and n.lower() in lav]
    fundne_navne.sort(key=lambda n: -len(n))  # længste navn først = mest specifikt

    # 1) EKSPLICIT: opgaven nævner et værktøj ved navn. Stærkeste signal — slå tier op.
    if fundne_navne:
        tiers = [_tier_for_tool_name(n) for n in fundne_navne]
        tier = _vaerste(tiers)
        return {
            "tools": fundne_navne,
            "tier": tier,
            "signals": fundne_navne,
            "method": "explicit",
            "confidence_delta": _DELTA[tier],
        }

    # 2) NØGLEORD: opgavens handlingstalende — pr. SÆTNINGSDEL.
    #
    # 3/11-2026: rækkefølgen var «farligste tabel først», så ET farligt ord hvor som helst
    # i teksten afgjorde sagen. Det gjorde 22 af 40 faktiske wakeup-tekster irreversible —
    # inklusive rene kontroller som «Verificér desk-release 0.6.290», hvor «release» er
    # OBJEKTET for en kontrol. Nu afgør verbet i hver sætningsdel handlingen, og den
    # farligste del vinder — så «læs listen og slet de gamle rækker» stadig er en sletning.
    dele = _clause_tiers(lav)
    if dele:
        tier = _vaerste([t for t, _ in dele])
        return {
            "tools": [],
            "tier": tier,
            "signals": [o for _, o in dele][:3],
            "method": "keyword",
            "confidence_delta": _DELTA[tier],
        }

    # 3) INTET LEDENDE HANDLINGSORD («kritisk migration af produktionsdatabase») →
    # farligste tabel først, som før. Rækkefølgen i `_KEYWORDS` bærer den regel.
    for tier, ord in _KEYWORDS:
        ramte = [o for o in ord if _matcher(o, lav)]
        if ramte:
            return {
                "tools": [],
                "tier": tier,
                "signals": ramte,
                "method": "keyword",
                "confidence_delta": _DELTA[tier],
            }

    # 3) INTET SIGNAL — og det siges som det er.
    return tomt


def _vaerste(tiers: list[str]) -> str:
    """Den mest risikable tier vinder. En opgave er så farlig som sit farligste led."""
    rang = {TIER_IRREVERSIBLE: 3, TIER_MUTATE: 2, TIER_READ: 1, TIER_UNKNOWN: 0}
    if not tiers:
        return TIER_UNKNOWN
    return max(tiers, key=lambda t: rang.get(t, 0))
