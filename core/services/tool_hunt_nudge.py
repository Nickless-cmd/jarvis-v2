"""Han leder efter et værktøj med bash — og værktøjet findes allerede.

## Den halvdel der manglede

Bjørn bad 6/9-2026 om «en lille mekanisme … som læser kontekstsen og nudgeder
dig **i runet** til at load_more og finde det relevante tool uden for den
toolboks du for severet».

Det der blev bygget, læste hans BESKED i prompt-assembly — altså før turen gik
i gang. Den halvdel virker og har fyret 252 gange siden. Men «i runet» blev
aldrig bygget: en prompt-sektion er skrevet færdig før første værktøjskald, og
den kan derfor ikke se hvad han griber til.

Og det er dér problemet bor. Bjørn 20/9-2026: «han først leder efter toolet med
bash eller jeg skal sidder og fortælle ham hvilke tools han har og han skal
huske og load_more_tools». To kald hvor ét havde været nok — og et menneske i
rollen som værktøjs-katalog.

## Hvor den hænger

`_finalize_call` i `simple_tool_executor`: ét kald pr. værktøjskald, efter
udførelsen, i den serialiserede fase. Forbilledet står i samme funktion —
soft-warn hæfter `⚠ {note}` foran resultatet. Noten lander i hans kontekst som
var den en del af svaret, og det er hele mekanikken.

Efter udførelsen, ikke før: noten er et faktum om noget der ER sket («du ledte
efter X»), ikke en gate der forhindrer noget. Den standser aldrig et kald.

## Hvad målingen slog ihjel (20/9-2026)

Første udgave gættede på hvad han ledte efter, ud fra hans søgekommandoer.
Målt over 14 døgn på 12.328 af hans EGNE kald (de 27.057 øvrige
`tool.invoked` er desk'ens pollere uden `_runtime_turn_id` — tages de med,
bliver enhver frekvens tre gange for lav):

* Det leksikalske opslag fyrede 7 gange. **Alle 7 var falske** — han greppede
  efter strengene `tool_result`, `home_assistant`, `council_status` i
  KILDEKODEN, og værktøjet hed tilfældigvis det samme.
* Og den så kun 2 % af hans søgninger overhovedet: hans stil er
  `cd X && echo "=== A ===" && grep …`, og funktionen kiggede kun på første
  led. At åbne den for hele kæden ville give FLERE falske, ikke færre.

Derfor er gætteriet væk. Tilbage står kun regler hvor signalet er entydigt:
et navn der ikke findes, en søgning uden træf, en tabel der ikke eksisterer,
en fil der er skrevet et sted han plejer at udgive fra.

## Hvorfor den er tavs næsten altid

Han bruger `grep` og `find` hele dagen til rigtigt arbejde. En note på hver af
dem ville forgifte kanalen indenfor en time — og en kanal man lærer at
overse, er værre end ingen kanal.

Derfor er porten smal: kaldet skal både VÆRE en søgning, og søgeteksten skal
pege på et værktøj der findes og er USYNLIGT for ham i dag. Peger den på noget
han allerede kan se i kataloget, er der intet at fortælle.

Opslaget er det samme leksikalske som prompt-sektionen bruger — ingen model,
rene strengoperationer, så noten ikke koster et kald midt i hans tur.

## Den anden regel: spørg frem for at grave

Leder han tre gange i samme tur uden at finde noget, er svaret sjældent en
fjerde søgning. Bjørn: «eller den skal nudged ham til at bruge pause and ask».
Den regel tæller på turens egen stak og siger det én gang.

## Den tredje regel: park det, i stedet for at glemme det

Bjørn 20/9-2026: «den burde osse kunne minde ham om at flagge ting til side
opgaver». `flag_side_task` findes — og står IKKE i kataloget, så han kan ikke
se den. Det er samme fejl som de andre 300: værktøjet er der, og manden ved
siden af må huske ham på det.

Signalet er det han lige har LÆST: dukker der TODO/FIXME op i et resultat, har
han set arbejde han ikke er i gang med. Det er øjeblikket hvor det enten bliver
parkeret eller glemt. Har han allerede flagget noget i turen, siges der intet.

## Den fjerde regel: en fil på containeren er ikke en fil Bjørn har

Bjørn 20/9-2026: «eller publicere filer på containeren». `publish_file` giver
en fil en URL han kan hente den på. Uden den ligger rapporten på en maskine i
et rack, og Jarvis tror han har afleveret den.

Også dét værktøj er usynligt i kataloget. Faktisk står kun ét af de fire
værktøjer i denne fil — `load_more_tools` — i klartekst; `pause_and_ask`,
`flag_side_task` og `publish_file` er alle skjulte for ham.

Porten er snæver med vilje: kun filer der ligner noget FOR Bjørn (en rapport,
en side, et billede), og kun uden for kode-træet. En `.md` i `docs/` er hans
arbejde, ikke en aflevering.
"""
from __future__ import annotations

import json
import logging
import re
import shlex
from typing import Any, Final

logger = logging.getLogger(__name__)

#: Værktøjer hvor et kald KAN være en søgning efter en evne.
_SOEGE_VAERKTOEJER: Final[frozenset[str]] = frozenset({
    "bash", "operator_bash", "bash_session", "operator_bash_session",
    "search", "grep", "operator_grep", "find_files", "operator_glob", "glob",
    "list_dir", "operator_list_dir",
})

#: Kommandoer der leder. `cat`, `python` og `git` står ikke her: de gør noget.
_SOEGE_KOMMANDOER: Final[frozenset[str]] = frozenset({
    "grep", "rg", "ag", "ack", "find", "fd", "locate", "which", "whereis",
    "type", "apropos", "man", "ls",
})

#: Han læser KODE, ikke efter en evne. Målt 20/9-2026 i et tørløb over 3
#: døgns rigtige kald: 13 af 13 værktøjs-noter kom fra søgninger som
#: «def approve_proposal» og «def list_scheduled_tasks» — han ledte efter
#: funktionen i kodebasen, og værktøjet hed tilfældigvis det samme. En note
#: dér er ikke bare unyttig, den er forkert.
_KODESOEGNING: Final[re.Pattern[str]] = re.compile(
    r"\b(?:def|class|import|from|async|function|const|export|interface)\b|=>|::")

#: Flag der tager en VÆRDI. «rg x --type py» leder efter «x», ikke efter
#: «py» — og uden det her ville filtypen tælle som et ord han søgte efter.
_FLAG_MED_VAERDI: Final[frozenset[str]] = frozenset({
    "--type", "-t", "--glob", "-g", "--include", "--exclude", "-e", "--regexp",
    "--iglob", "--name", "-name", "-iname", "-path", "--max-depth", "-maxdepth",
})

#: Hvor mange gange han skal lede i samme tur, før forslaget er at spørge.
GRAVE_GRAENSE: Final[int] = 3
#: Højst ét nudge af hver slags pr. tur. To noter i samme tur er ikke en
#: påmindelse, det er en afbrydelse.
MAKS_PR_TUR: Final[int] = 1

# ── R10: han kalder det samme igen og igen ─────────────────────────────────
#
# Taget fra DeepSeek-harness' `dsh-repeat-tool-reminder` (læst 20/9-2026).
# Deres form er værd at kopiere præcist, fordi hver detalje er et valg:
#
#   * Tærskler ved 3, 5 og 8 — en STIGE, ikke ét råb. Kort påmindelse ved 3;
#     ved 5 og 8 nævnes værktøjet og argumenterne, så han kan se HVAD han
#     gentager. Bjørn spurgte i formiddags om et forslag skulle kunne
#     eskalere. Det her er deres svar: eskaleringen er mere DETALJE, ikke
#     mere tvang.
#   * Rådgivende. Den blokerer aldrig et lovligt gentaget kald.
#   * Kun NØJAGTIGE gentagelser (samme værktøj, samme argumenter uanset
#     nøglerækkefølge). Næsten-ens varianter fanges ikke — det er en bevidst
#     grænse, ikke en mangel.
#   * Stimen brydes af et andet kald. To ens kald med arbejde imellem er
#     ikke en løkke.
GENTAGELSE_TAERSKLER: Final[tuple[int, ...]] = (3, 5, 8)
#: Hvor meget af argumenterne den detaljerede påmindelse viser.
GENTAGELSE_ARG_TEGN: Final[int] = 500
#: Værktøjer hvor en nøjagtig gentagelse er normal og ikke skal kommenteres.
#: `bash_session` og `operator_bash_session` er Bjørns vej uden om systemet
#: («de 2 er den eneste måde jeg kan få ham til at gøre noget uden om
#: systemet») — de får ingen påmindelser hæftet på deres svar.
GENTAGELSE_UNDTAGET: Final[frozenset[str]] = frozenset({
    "bash_session", "operator_bash_session", "todo_write", "update_todos",
})

_NOTE_GENTAGELSE_KORT = (
    "Du har nu kaldt det samme værktøj med de samme argumenter {antal} gange "
    "i træk. Læs det forrige resultat igennem før du kalder igen — enten "
    "siger det allerede hvad du mangler, eller også skal du prøve en anden vej."
)
_NOTE_GENTAGELSE_LANG = (
    "{antal}. gang i træk med samme kald: `{vaerktoej}` med argumenterne "
    "{argumenter}. Resultatet har ikke ændret sig og gør det formentlig "
    "heller ikke næste gang. Vælg én: skift fremgangsmåde, hent nyt at gå "
    "efter, eller afslut med det du har — og sig hvad der mangler."
)

_NOTE_SPOERG = (
    "⚠ Det er {antal}. søgning uden træf i denne tur. Kan du ikke finde det, "
    "så spørg frem for at grave: `pause_and_ask`."
)
_NOTE_UKENDT = (
    "⚠ `{gaettet}` findes ikke. {naermeste}Kan du stadig ikke finde den, så "
    "spørg frem for at gætte videre: `pause_and_ask`."
)
_NOTE_VAAGN = (
    "⚠ `{hvad}` kører videre efter turen — og intet bringer dig tilbage til "
    "det. Sæt en `schedule_self_wakeup`, eller sig til Bjørn hvornår han skal "
    "kigge."
)
#: Værktøjer der sætter noget i gang som lever videre efter turen.
_BAGGRUND: Final[frozenset[str]] = frozenset({
    "run_in_background", "operator_bash_background", "dispatch_code_mode_task",
    "schedule_task", "dispatch_agent",
})
VAAGN_VAERKTOEJ: Final[str] = "schedule_self_wakeup"

_NOTE_SKEMA = (
    "⚠ Det er {antal}. tabel eller kolonne du gætter forkert i denne tur. "
    "Slå skemaet op ÉN gang i stedet: "
    "`db_query(\"SELECT name FROM sqlite_master WHERE type='table'\")`."
)

#: Værktøjets eget svar siger «tools not found» — men ikke hvad der så FINDES.
_UKENDT_SVAR: Final[re.Pattern[str]] = re.compile(
    r"(?i)\b(?:tools? not found|ukendt v(?:æ|ae)rkt(?:ø|oe)j|no such tool)\b")
#: En søgning uden træf. IKKE forankret i starten: et rigtigt resultat
#: begynder med «[tool_result:…] [bash]: », så et `^` ville aldrig matche
#: (målt 20/9-2026: nul træf på 16.459 rigtige resultater). Kun de første
#: 200 tegn, så en «no matches» midt i et langt output ikke tæller.
_TOMT_SVAR: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:\[no matches\]|ingen tr(?:æ|ae)f|no matches found|0 matches)")
_TOMT_VINDUE: Final[int] = 200
#: Han gætter på et skema han ikke har slået op.
_SKEMA_FEJL: Final[re.Pattern[str]] = re.compile(
    r"(?i)no such (?:table|column)")
#: Hvor mange tomme søgninger / skema-gæt der skal til i samme tur.
TOMME_GRAENSE: Final[int] = 2
#: Fire, ikke tre. Målt 20/9-2026: ved tre fyrede skema-reglen 53 gange på 14
#: døgn og var dermed den højeste stemme i kanalen. Ved fire rammer den de
#: ture hvor han virkelig gætter videre — 11 af 67 — og tier i resten.
SKEMA_GRAENSE: Final[int] = 4
_NOTE_SIDEOPGAVE = (
    "⚠ Der står {antal} TODO/FIXME i det du lige læste. Skal noget af det "
    "laves — men ikke nu — så park det i stedet for at glemme det: "
    "`flag_side_task` (hent den med `load_more_tools`)."
)

#: Mærker der betyder «her ligger arbejde nogen har udskudt».
_ARBEJDSMAERKER: Final[re.Pattern[str]] = re.compile(
    r"\b(?:TODO|FIXME|HACK|XXX)\b")
#: Ét mærke er en tilfældighed i en kodebase med 15.000 tests. To er et sted
#: hvor nogen har efterladt arbejde.
MIN_MAERKER: Final[int] = 2
#: Værktøjet der parkerer noget til senere.
SIDEOPGAVE_VAERKTOEJ: Final[str] = "flag_side_task"

_NOTE_UDGIV = (
    "⚠ `{fil}` ligger nu på containeren — ikke hos Bjørn. Skal han kunne "
    "åbne den, så giv den en adresse: `publish_file` (hent den med "
    "`load_more_tools`)."
)
#: Værktøjet der giver en fil en adresse.
UDGIV_VAERKTOEJ: Final[str] = "publish_file"
#: Værktøjer der skriver en fil.
_SKRIVENDE: Final[frozenset[str]] = frozenset({
    "write_file", "operator_write_file", "edit_file", "operator_edit_file",
    "multi_edit", "operator_multi_edit", "fuzzy_edit", "apply_patch",
})
#: Endelser der ligner en aflevering frem for kode.
_LEVERBARE: Final[frozenset[str]] = frozenset({
    ".md", ".html", ".htm", ".csv", ".pdf", ".png", ".jpg", ".jpeg", ".svg",
    ".xlsx", ".docx", ".pptx", ".zip",
})
#: `.txt` er skåret væk med vilje: af 45 træf i den første udgave var 12
#: `commit_msg_*.txt` — netop den arbejdsgang CLAUDE.md påbyder — og 6 var
#: testfixtures. HVER ENESTE .txt var støj (målt 20/9-2026 over 14 døgn).
_IKKE_AFLEVERING: Final[tuple[str, ...]] = (
    "commit_msg", "merge_msg", "msg-", "test", "fixture", "rediger-mig",
)
#: Kode-træet. En fil her er hans arbejde, ikke en aflevering til Bjørn.
_KODESTIER: Final[tuple[str, ...]] = (
    # Uden skråstreg til sidst: «/media/projects/jarvis-v2» (uden efterfølgende
    # skråstreg) slap forbi og gav tre falske positiver i tørløbet 20/9-2026.
    "jarvis-v2", "/core/", "/apps/", "/tests/", "/docs/", "/scripts/",
    "/shared/", "node_modules", ".git/",
)
def _i_kodetraeet(sti: str) -> bool:
    """Ligger stien i kodetræet? Både «docs/x.md» og «/media/.../docs/x.md».

    Begge former optræder i hans kald: et relativt `path` fra repo-roden, og
    en absolut sti midt i en bash-kommando.
    """
    lav = (sti or "").lower()
    return any(lav.startswith(k.strip("/") + "/") or k in lav for k in _KODESTIER)


#: `/tmp` står IKKE her. Det var mit første gæt, men målingen modsagde det:
#: `/tmp/xlsxwork/ugedage.xlsx` blev faktisk udgivet til Bjørn. Støjen kom fra
#: filnavnene, ikke fra mappen — se `_IKKE_AFLEVERING`.
_SKRABBE: Final[tuple[str, ...]] = ("scratchpad", "/dev/shm/")


def _leverbar_fil(navn: str, argumenter: dict[str, Any] | None) -> str:
    """Filen han lige skrev, hvis den ligner noget Bjørn skal kunne åbne."""
    if navn not in _SKRIVENDE:
        return ""
    arg = argumenter or {}
    sti = str(arg.get("path") or arg.get("file_path") or arg.get("sti") or "").strip()
    if not sti:
        return ""
    lav = sti.lower()
    if not any(lav.endswith(e) for e in _LEVERBARE):
        return ""
    if _i_kodetraeet(sti) or any(k in lav for k in _SKRABBE):
        return ""
    fil = lav.rsplit("/", 1)[-1]
    if any(k in fil for k in _IKKE_AFLEVERING):
        return ""
    return sti

#: Tælleren pr. tur. Nulstilles af runtimen når turen slutter; en tur der
#: aldrig ryddes op efter, koster et par heltal.
_GRAVNINGER: dict[str, dict[str, int]] = {}
_SAGT: dict[str, set[str]] = {}
#: run_id -> {"aftryk": str, "antal": int, "sagt": set[int]}. Én stime ad
#: gangen: et andet kald erstatter aftrykket og nulstiller tælleren.
_GENTAGELSER: dict[str, dict[str, Any]] = {}


def _aftryk(navn: str, argumenter: dict[str, Any] | None) -> str:
    """Identiteten af ét kald: værktøj + argumenter, uanset nøglerækkefølge.

    `sort_keys` er hele pointen — to kald der kun adskiller sig ved i hvilken
    orden modellen skrev nøglerne, ER det samme kald.
    """
    try:
        return navn + "\u0000" + json.dumps(argumenter or {}, sort_keys=True,
                                             ensure_ascii=False, default=str)
    except Exception as exc:  # userialiserbare argumenter: tæl dem aldrig som ens
        logger.debug("tool_hunt_nudge: aftryk fejlede for %s: %s", navn, exc)
        return navn + "\u0000<uberegneligt>"


def _noter_gentagelse(noegle: str, navn: str,
                      argumenter: dict[str, Any] | None) -> int:
    """Hvor mange gange i træk er PRÆCIS dette kald nu set? 1 = nyt."""
    if navn in GENTAGELSE_UNDTAGET:
        _GENTAGELSER.pop(noegle, None)  # undtagne kald bryder også stimen
        return 0
    stime = _GENTAGELSER.get(noegle)
    nu = _aftryk(navn, argumenter)
    if stime is None or stime.get("aftryk") != nu:
        _GENTAGELSER[noegle] = {"aftryk": nu, "antal": 1, "sagt": set()}
        return 1
    stime["antal"] = int(stime.get("antal") or 0) + 1
    return int(stime["antal"])


def _gentagelses_note(noegle: str, navn: str, argumenter: dict[str, Any] | None,
                      antal: int) -> str:
    """Påmindelsen for denne stime, eller "". Hver tærskel fyrer én gang."""
    if antal not in GENTAGELSE_TAERSKLER:
        return ""
    stime = _GENTAGELSER.get(noegle) or {}
    sagt = stime.setdefault("sagt", set())
    if antal in sagt:
        return ""
    sagt.add(antal)
    if antal == GENTAGELSE_TAERSKLER[0]:
        return _NOTE_GENTAGELSE_KORT.format(antal=antal)
    try:
        vist = json.dumps(argumenter or {}, sort_keys=True, ensure_ascii=False,
                          default=str)[:GENTAGELSE_ARG_TEGN]
    except Exception as exc:  # vis hellere intet end at vælte påmindelsen
        logger.debug("tool_hunt_nudge: kunne ikke vise argumenter: %s", exc)
        vist = "(kunne ikke vises)"
    return _NOTE_GENTAGELSE_LANG.format(antal=antal, vaerktoej=navn,
                                        argumenter=vist)


def _taeller(noegle: str, hvad: str) -> int:
    """Tæl én forekomst af `hvad` i turen og giv det nye tal."""
    tur = _GRAVNINGER.setdefault(noegle, {})
    tur[hvad] = tur.get(hvad, 0) + 1
    return tur[hvad]

# ── Målingen: tog han imod? ────────────────────────────────────────────────
#
# Uden den her ved vi kun at vi HAR sagt noget. Spec'ens mål nummer fire fra
# 6/9-2026 — «Lærer af sine egne hits» — blev aldrig bygget, og det er præcis
# det tal der afgør om en note fortjener at blive fulgt op.
#
# Målt i samme krog: noten peger på ét værktøj, og krogen ser hvert eneste
# kald i turen bagefter. Kalder han det, er det et JA. Går der `MISS_EFTER`
# kald uden, er det et NEJ. Begge dele er et event, så tallet kan læses uden
# at spørge nogen.
#
# Hvorfor et antal og ikke «når turen slutter»: der findes ingen krog der
# fyrer ved turens afslutning — R2.5 har samme hul. Et loft på kald er det
# der faktisk kan måles her, og det siger sit eget navn i `rapport()`.
MISS_EFTER: Final[int] = 6
#: Hvor mange ture der huskes ad gangen. Et loft, ikke en horisont.
_MAKS_TURE: Final[int] = 200
_UDESTAAENDE: dict[str, dict[str, Any]] = {}


def _taendt() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().tool_hunt_nudge_enabled)
    except Exception:
        return True


def _afgoer_udestaaende(noegle: str, navn: str) -> None:
    """Kaldte han det værktøj noten pegede på? Eller gav han op på at svare?"""
    sag = _UDESTAAENDE.get(noegle)
    if not sag:
        return
    sag["kald"] = int(sag.get("kald", 0)) + 1
    if navn == sag.get("vaerktoej"):
        _log_svar("hit", noegle, sag)
        _UDESTAAENDE.pop(noegle, None)
    elif sag["kald"] >= MISS_EFTER:
        _log_svar("miss", noegle, sag)
        _UDESTAAENDE.pop(noegle, None)


def _husk_udestaaende(noegle: str, vaerktoej: str, slags: str) -> None:
    if len(_UDESTAAENDE) >= _MAKS_TURE:
        _UDESTAAENDE.pop(next(iter(_UDESTAAENDE)), None)
    _UDESTAAENDE[noegle] = {"vaerktoej": vaerktoej, "slags": slags, "kald": 0}


def _log_svar(udfald: str, noegle: str, sag: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"tool_discovery.hunt_{udfald}", {
            "tool": str(sag.get("vaerktoej") or ""),
            "slags": str(sag.get("slags") or ""),
            "run_id": noegle,
            "kald_efter_noten": int(sag.get("kald", 0)),
        })
    except Exception:
        logger.debug("tool_hunt_nudge: svar-event fejlede", exc_info=True)


def rapport(*, limit: int = 500) -> dict[str, Any]:
    """Blev noterne fulgt? Tallet bag «fortjener den her at eskalere».

    Læser de tre events (`hunt_nudge`, `hunt_hit`, `hunt_miss`) og svarer pr.
    slags. Et udestående svar tælles hverken som ja eller nej — han kan stadig
    nå at gøre det.
    """
    ud: dict[str, Any] = {"pr_slags": {}, "noter": 0, "ja": 0, "nej": 0}
    felt = {"tool_discovery.hunt_nudge": "noter",
            "tool_discovery.hunt_hit": "ja",
            "tool_discovery.hunt_miss": "nej"}
    try:
        from core.eventbus.bus import event_bus
        for e in event_bus.recent_by_family("tool_discovery", limit=limit) or []:
            noegle = felt.get(str(e.get("kind") or ""))
            if not noegle:
                continue
            nyttelast = e.get("payload") or {}
            slags = str(nyttelast.get("slags") or nyttelast.get("tool") or "?")
            pr = ud["pr_slags"].setdefault(slags, {"noter": 0, "ja": 0, "nej": 0})
            pr[noegle] += 1
            ud[noegle] += 1
    except Exception:
        logger.debug("tool_hunt_nudge: rapport fejlede", exc_info=True)
    svarede = ud["ja"] + ud["nej"]
    ud["andel_taget_imod"] = round(ud["ja"] / svarede, 3) if svarede else None
    return ud


def _maa_sige(noegle: str, slags: str) -> bool:
    sagt = _SAGT.setdefault(noegle, set())
    if slags in sagt or len(sagt) >= MAKS_PR_TUR:
        return False
    sagt.add(slags)
    return True


def ryd_tur(run_id: str | None) -> None:
    """Turen er slut. Self-safe. Et ubesvaret nudge tælles som et nej."""
    noegle = str(run_id or "")
    sag = _UDESTAAENDE.pop(noegle, None)
    if sag:
        _log_svar("miss", noegle, sag)
    _GRAVNINGER.pop(noegle, None)
    _SAGT.pop(noegle, None)
    _GENTAGELSER.pop(noegle, None)


def note(
    *, navn: str, argumenter: dict[str, Any] | None, run_id: str | None = None,
    resultat_tekst: str = "",
) -> str:
    """Noten der skal hæftes på resultatet, eller `""`.

    Reglerne står i den rækkefølge de er mest entydige. Højst én note pr. tur,
    og kun når signalet ikke kan læses som noget andet.

    Kaster aldrig: en fejl her må aldrig koste et værktøjsresultat.
    """
    try:
        if not _taendt():
            return ""
        noegle = str(run_id or "")
        _afgoer_udestaaende(noegle, navn)
        # Tælles på HVERT kald, også når en anden regel vinder noten nedenfor:
        # en tæller der kun løber når den bliver hørt, måler sig selv.
        gentaget = _noter_gentagelse(noegle, navn, argumenter)
        svar = resultat_tekst or ""

        # Har han selv gjort det, skal han ikke mindes om det.
        if navn == SIDEOPGAVE_VAERKTOEJ:
            _maa_sige(noegle, "sideopgave")
            return ""
        if navn == UDGIV_VAERKTOEJ:
            _maa_sige(noegle, "udgiv")
            return ""
        if navn in (VAAGN_VAERKTOEJ, "schedule_recurring"):
            _maa_sige(noegle, "vaagn")
            return ""

        # ── R5: han bad om et værktøj der ikke findes ────────────────────────
        # Målt: 9 ukendte navne mod 30 kendte på 14 døgn — hver fjerde
        # by-name-forespørgsel rammer ved siden af. I én tur prøvede han
        # `memory_delete_line`, `delete_memory_line`, `memory_remove_line` og
        # `memory_line_delete`: fire stavemåder af et værktøj han fandt på.
        # Værktøjets eget svar siger «tools not found» — men ikke hvad der så
        # FINDES, og det er hele forskellen.
        if navn == "load_more_tools" and _UKENDT_SVAR.search(svar):
            gaettet = _foerste_ukendte(argumenter, svar)
            if gaettet and _maa_sige(noegle, "ukendt"):
                naermeste = _naermeste_navne(gaettet)
                _log("load_more_tools", run_id, 0.0, gaettet)
                _husk_udestaaende(noegle, "pause_and_ask", "ukendt")
                return _NOTE_UKENDT.format(
                    gaettet=gaettet,
                    naermeste=(f"Nærmeste der gør: {naermeste}. " if naermeste else ""))

        # ── R9: han startede noget der kører videre ──────────────────────────
        # Målt 20/9-2026: 20 ture startede baggrundsarbejde, og 15 af dem satte
        # ALDRIG en wakeup — 1,07 pr. døgn. Arbejdet kører, turen slutter, og
        # ingen kommer tilbage til det. Noten kommer i det øjeblik han starter
        # det, ikke når turen er forbi: dér kan han stadig nå at sætte den.
        if navn in _BAGGRUND or str((argumenter or {}).get("background") or "").lower() in ("true", "1"):
            if VAAGN_VAERKTOEJ not in _SAGT.get(noegle, set()) and _maa_sige(noegle, "vaagn"):
                _log(VAAGN_VAERKTOEJ, run_id, 0.0, navn)
                _husk_udestaaende(noegle, VAAGN_VAERKTOEJ, "vaagn")
                return _NOTE_VAAGN.format(hvad=navn)

        # ── R6: tredje tabel eller kolonne han gætter forkert ────────────────
        # Målt: 374 skema-fejl i 67 ture, 340 af dem fra håndskrevet sqlite3 i
        # bash. Det er burst-formet — han gætter videre. En tur havde ti.
        if _SKEMA_FEJL.search(svar):
            antal = _taeller(noegle, "skema")
            if antal >= SKEMA_GRAENSE and _maa_sige(noegle, "skema"):
                _log("db_query", run_id, 0.0, f"{antal} skema-gæt")
                _husk_udestaaende(noegle, "db_query", "skema")
                return _NOTE_SKEMA.format(antal=antal)

        # ── R7: en aflevering, skrevet hvor han plejer at udgive fra ─────────
        fil = _leverbar_fil(navn, argumenter)
        if fil and _maa_sige(noegle, "udgiv"):
            _log(UDGIV_VAERKTOEJ, run_id, 0.0, fil)
            _husk_udestaaende(noegle, UDGIV_VAERKTOEJ, "udgiv")
            return _NOTE_UDGIV.format(fil=fil)

        # ── R3: han har lige læst arbejde nogen har udskudt ──────────────────
        maerker = len(_ARBEJDSMAERKER.findall(svar))
        if maerker >= MIN_MAERKER and _maa_sige(noegle, "sideopgave"):
            _log(SIDEOPGAVE_VAERKTOEJ, run_id, 0.0, f"{maerker} mærker")
            _husk_udestaaende(noegle, SIDEOPGAVE_VAERKTOEJ, "sideopgave")
            return _NOTE_SIDEOPGAVE.format(antal=maerker)

        # ── R8: anden søgning uden træf ──────────────────────────────────────
        # Den ærlige udgave af «han leder forgæves». Første udgave talte HVER
        # søgning — også de vellykkede. Et tomt resultat er selve signalet om
        # at søgningen slog fejl, og det kræver ingen gætteri om hvad han ledte
        # efter.
        if _TOMT_SVAR.search(svar[:_TOMT_VINDUE]):
            antal = _taeller(noegle, "tomme")
            if antal >= TOMME_GRAENSE and _maa_sige(noegle, "spoerg"):
                _log("pause_and_ask", run_id, 0.0, f"{antal} tomme søgninger")
                _husk_udestaaende(noegle, "pause_and_ask", "spoerg")
                return _NOTE_SPOERG.format(antal=antal)

        # ── R10: samme kald igen og igen ─────────────────────────────────────
        # Til SIDST med vilje. De øvrige regler peger på noget konkret han kan
        # gøre; løkke-påmindelsen siger kun «stands op og kig». Har en af dem
        # noget at sige, er den bedre. Tælleren løber uanset hvem der vandt.
        # Egen kvote: stigen SKAL kunne fyre tre gange i samme tur, og
        # MAKS_PR_TUR er skruet til opdagelses-noterne.
        gentagelse = _gentagelses_note(noegle, navn, argumenter, gentaget)
        if gentagelse:
            _log("gentagelse", run_id, 0.0, f"{gentaget}x {navn}")
            return gentagelse
        return ""
    except Exception:
        logger.debug("tool_hunt_nudge: note fejlede", exc_info=True)
        return ""


def _foerste_ukendte(argumenter: dict[str, Any] | None, svar: str) -> str:
    """Det navn han bad om, som ikke findes. Fra argumenterne, ikke fra svaret.

    Svaret formulerer sig forskelligt; argumenterne bærer det han SKREV.
    """
    navne = (argumenter or {}).get("names") or (argumenter or {}).get("navne") or []
    if isinstance(navne, str):
        navne = [navne]
    try:
        from core.services.prompt_sections.tool_discovery_nudge import _registrerede_navne
        findes = _registrerede_navne()
    except Exception:
        return ""
    for n_ in navne:
        if str(n_) and str(n_) not in findes:
            return str(n_)
    return ""


def _naermeste_navne(gaettet: str, antal: int = 2) -> str:
    """De nærmeste rigtige navne — leksikalsk, ingen model."""
    try:
        import difflib

        from core.services.prompt_sections.tool_discovery_nudge import _registrerede_navne
        bud = difflib.get_close_matches(gaettet, list(_registrerede_navne()), n=antal, cutoff=0.5)
        return ", ".join(f"`{b}`" for b in bud)
    except Exception:
        return ""


def _log(vaerktoej: str, run_id: str | None, score: float, tekst: str) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("tool_discovery.hunt_nudge", {
            "tool": vaerktoej, "run_id": str(run_id or ""), "score": round(score, 4),
            # Søgeteksten er HANS egen — den siger hvad nudgen byggede på, og
            # uden den kan ingen efterprøve om buddet var rimeligt.
            "soegte_efter": tekst[:120],
        })
    except Exception:
        logger.debug("tool_hunt_nudge: event fejlede", exc_info=True)
