"""Indbakken som LÆSEFLADE. Seks sektioner, én linje per post, aldrig payload.

Opgave 2 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.

## Denne fil skriver ikke

Det er ikke en stilregel, det er filens eneste ansvar. Tre af husets kilder ser
ud som læsninger og er det ikke:

* `self_wakeup.due_wakeups()` **fyrer og gemmer** forfaldne vækninger.
* `build_tool_intent_approval_surface()` kan oprette og udløbe godkendelser.
* `background_jobs.liste()` starter ikke daemonen, men dens `_shell_sessioner()`
  nulstiller daemonens idle-ur, så en session-løs daemon ikke lukker ned mens
  panelet er åbent.

Ingen af dem kaldes herfra. Jobbene læses gennem `_supervisor_jobs`,
`_scout_jobs` og `_tool_jobs` — de tre rene — og shell-sessionerne er med vilje
helt ude: de er Bjørns aftalte bagdør og hører ikke i en flade der kan gate.
`tests/test_inbox_view.py` har en AST-vagt om præcis den liste, fordi
«en læseflade der kan skrive» er den fælde en hel memory er skrevet om.

## Kilderne er injicérbare

`Kilder` samler de syv læsninger som felter. Testene sender en fake ind, så de
er deterministiske uden at mocke halve moduler — og `nu_ts` injiceres af samme
grund: forfald i dage kan ikke testes mod en klokke der går.

## Ejer-mærket afgør ALT om gating

En post bærer `[dig]`, `[huset]` eller `[ukendt]`. Kun `[dig]` kan gate, og
`[ukendt]` kan det aldrig. Visningen regner det ikke ud — den viser hvad
`inbox_items.verificeret_ejer` blev sat til ved oprettelsen, hvor konteksten
kunne bevise det. En visning der selv udnævnte en ejer ville være et flag
forklædt som et bevis.
"""
from __future__ import annotations

import logging
import os
import os.path
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from core.runtime import db_inbox

logger = logging.getLogger(__name__)

#: Hvor længe et job må stå `kører` med beviseligt død proces, før det flyttes
#: fra «I GANG» til «VENTER PÅ DIG» som `foraeldreloes`. Måles i Opgave 7.
#: Lavt sat med vilje: et dødt job der står «kører» i dagevis er netop fejlen —
#: men under et minut kan en pid-læsning ramme et hul mellem fork og registrering.
_FORAELDRELOES_EFTER_S: Final[float] = 300.0

EJER_MAERKE: Final[dict[str, str]] = {
    db_inbox.EJER_JARVIS: "[dig]",
    db_inbox.EJER_HUSET: "[huset]",
    db_inbox.EJER_UKENDT: "[ukendt]",
}

#: Linjen er ÉN linje. Spec'ens egen test: `len(linje) < 200`. Loftet findes
#: fordi en post med et jobs output på 112 kB ville trække hele filen med ind i
#: promptens hale, hvis beskrivelsen ikke blev afkortet.
_LINJE_LOFT: Final[int] = 200
_BESKRIVELSE_LOFT: Final[int] = 70


def _kort(tekst: str, loft: int) -> str:
    """Afkort på et ordskel. Den GEMTE post afkortes aldrig — kun linjen."""
    t = " ".join(str(tekst or "").split())
    if len(t) <= loft:
        return t
    skaaret = t[:loft].rsplit(" ", 1)[0]
    return (skaaret or t[:loft]) + "…"


def _bytes_tekst(b: int | None) -> str:
    """`None` ⇒ «stoerrelse ukendt», aldrig «0 B».

    De to kan ikke mappes sammen: `0 B` er en ægte tom fil og et gyldigt svar,
    mens `None` er «filen er væk siden posten blev skrevet». Stod der `0 B` for
    en forsvundet fil, ville man åbne en fil der ikke findes — og tro at jobbet
    ikke skrev noget.
    """
    if b is None:
        return "stoerrelse ukendt"
    b = int(b)
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b // 1024} kB"
    return f"{b // (1024 * 1024)} MB"


def _alder_dage(fra_iso: str, nu_ts: float) -> int | None:
    """Hele dage siden `fra_iso`. `None` når tidsstemplet ikke kan læses.

    Fald mod `None`, ikke mod 0: et uparsabelt tidsstempel der blev 0 dage ville
    se ud som «lige nu», og en forfalden post ville forsvinde i støjen. Det er
    samme retning som `fejlretningen_skal_standse` — fald mod det der kan ses.
    """
    s = str(fra_iso or "").strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        # Uparsabelt skal SES. Sker det systematisk, mangler hver post sit
        # forfald, og uden linjen ville det aldrig stå nogen steder.
        logger.warning("inbox_view: kunne ikke laese tidsstempel %r", s[:40])
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return max(0, int((nu_ts - d.timestamp()) // 86400))


# ── Kilderne ────────────────────────────────────────────────────────────────

def _aegte_poster(bruger_id: str) -> list[dict[str, Any]]:
    """Åbne poster PLUS de nyligt afgjorte.

    De afgjorte er ikke pynt: visningen skal kunne SPRINGE en lukket post
    over, også når kilden stadig rapporterer den. Før 4/10 hentede denne kun
    åbne rækker, og så havde visningen ingen måde at vide at en post var
    lukket — `drop` skrev en afgørelse ingen læste.

    `liste_aktiv` er Opgave 11's retention-vindue, og den havde indtil nu
    ingen kalder i koden. Nu er den vejen ind.
    """
    return db_inbox.liste_aktiv(bruger_id=bruger_id)


def _aegte_vaekninger(bruger_id: str) -> list[dict[str, Any]]:
    """`list_wakeups()` er GLOBAL — den har intet brugerfilter.

    Derfor filtreres her, eksplicit, på postens eget `user_id`. En post uden
    ejer udelades og tælles som `ukendt`; den må ikke få Bjørn som stiltiende
    fallback, for så ville en anden brugers vækning dukke op i hans indbakke.
    """
    try:
        from core.services import self_wakeup
        alle = self_wakeup.list_wakeups(limit=200)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_view: kunne ikke laese vaekninger: %s", exc)
        return []
    ud = []
    for r in alle:
        uid = str(r.get("user_id") or "").strip()
        if uid and uid != bruger_id:
            continue
        ud.append(r)
    return ud


def planlagte_vaekning_ids(
    bruger_id: str, kilder: "Kilder | None" = None,
) -> set[str]:
    """Vækninger der er PLANLAGT (`pending`) — de venter ikke på nogen.

    Delt af visningen og indbakke-gaten, så de to ikke kan blive uenige om
    hvad «venter» betyder. Det er læren i dette spor: hver gang to led hver
    for sig afgjorde hvad der «findes» eller «venter», drev de fra hinanden og
    efterlod en post der blev vist men ikke kunne afgøres.

    ## Hvorfor (målt 4/10-2026)

    Den durable række skrives ved BOOKINGEN, og `kraever_handling` sættes
    derfra: `ejer == jarvis and kildetype not in IKKE_GATENDE_KILDETYPER`.
    `wakeup` står ikke på den liste — så hver vækning jeg bookede til mig selv
    fik en post der stod i VENTER PÅ DIG og GATEDE, før den havde fyret. Intet
    opdaterer rækken når vækningen fyrer (`meld_kilde_faerdig` har nul
    kaldere), så flaget er et øjebliksbillede fra bookingen.

    Målt i drift: gaten nægtede et `bash`-kald med min egen netop bookede
    efterkontrol som grund (`wake-155d570154`, `paamindelser=1`, tærskel 2).

    Uden `kilder` læses den ægte vækning-kilde — det er gaten, der ikke har en
    injiceret flade. Med `kilder` bruges SAMME læsning som visningen selv, så
    en test kan bytte kilden ud ét sted uden at kende klassen.
    """
    raekker = (kilder.vaekninger(bruger_id) if kilder is not None
               else _aegte_vaekninger(bruger_id))
    return {
        str(r.get("wakeup_id") or "").strip()
        for r in raekker
        if str(r.get("status") or "") == "pending"
        and str(r.get("wakeup_id") or "").strip()
    }


def _aegte_jobs(bruger_id: str) -> list[dict[str, Any]]:
    """De TRE rene job-læsninger. Aldrig `liste()`, aldrig shell-sessionerne."""
    from core.services import background_jobs
    ud: list[dict[str, Any]] = []
    for navn in ("_supervisor_jobs", "_scout_jobs", "_tool_jobs"):
        fn = getattr(background_jobs, navn, None)
        if fn is None:
            continue
        try:
            ud += list(fn() or [])
        except Exception as exc:  # noqa: BLE001
            # Én kilde der fejler må ikke tømme panelet — men den skal ses,
            # ellers forsvinder en hel jobtype tavst.
            logger.warning("inbox_view: %s fejlede: %s", navn, exc)
    return ud


def _aegte_godkendelser(bruger_id: str) -> list[dict[str, Any]]:
    """`recent_tool_intent_approval_requests` med EKSPLICIT bruger.

    `include_unassigned=False`: en godkendelse uden tildelt bruger hører ikke i
    nogens indbakke. Og `build_tool_intent_approval_surface()` bruges IKKE —
    den kan oprette og udløbe.
    """
    try:
        from core.runtime.db_governance import recent_tool_intent_approval_requests
        return list(recent_tool_intent_approval_requests(
            limit=50, user_id=bruger_id, include_unassigned=False) or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_view: kunne ikke laese godkendelser: %s", exc)
        return []


def _aegte_backlog_tal() -> int:
    """Hvor mange står i backloggen — ÉT tal, med en adresse.

    Spec'ens egen afgørelse: kandidat-backloggen er **ude** af indbakken, kun
    tællingen er med, fordi «1.896 poster ville drukne den dag ét». Men tallet
    skal så faktisk VÆRE der.

    Målt 4/10-2026: `Kilder.backlog_tal` stod som `lambda: 0`, altså den
    standard jeg skrev da jeg byggede klassen. Linjen «Backlog: N → …» har
    derfor aldrig stået i en visning. Det er den samme fejl som de tre andre i
    dette spor — en korrekt mekanisme uden en kilde — og den er min.

    Instrument-fundene er den store: 2.259 åbne, den ældste set 23/6-2026.
    De hører IKKE som poster (samme argument som kandidaterne), men et tal
    uden en adresse er ingen oplysning, og et tal der altid er nul er værre:
    det siger at der ikke er noget.
    """
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            r = conn.execute(
                "SELECT count(*) FROM central_instrument_findings "
                "WHERE status = 'open'").fetchone()
        return int(r[0] or 0) if r else 0
    except Exception as exc:  # noqa: BLE001
        # Et tal vi ikke kan laese er ikke nul. Fald til 0 betyder «ingen
        # backlog-linje», hvilket er aerligt — men fejlen skal ses, ellers
        # ser en tabel der mangler ud som en tom backlog.
        logger.warning("inbox_view: kunne ikke taelle backloggen: %s", exc)
        return 0


def _aegte_proces_lever(pid: int | None) -> bool | None:
    """Lever processen? `None` = kan ikke afgøres HER.

    Forældreløs kræver pålideligt procesbevis fra den SAMME host. Et job på en
    utilgængelig operator-maskine er `status_ukendt`, ikke bevist dødt — og det
    er forskellen mellem «ryd op» og «du må kigge selv».
    """
    if not pid:
        return None
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:  # processen findes IKKE — bevist doed
        return False
    except PermissionError:  # findes, men en anden brugers — den LEVER
        return True
    except Exception as exc:  # noqa: BLE001
        # Alt andet er «kan ikke afgoeres»: en ugyldig pid, en kerne der
        # naegter, en host vi ikke naar. Det er sin EGEN klasse, og den maa
        # ikke blive «doed» — forskellen er «ryd op» mod «du maa kigge selv».
        logger.debug("inbox_view: proces-bevis for pid %r kunne ikke afgoeres: %s",
                     pid, exc)
        return None
    return True


@dataclass(slots=True)
class Kilder:
    """Rene, bruger-afgrænsede læsninger. Ingen af dem muterer.

    Standardværdierne er SENT bundne — `lambda b: _aegte_jobs(b)`, ikke
    `_aegte_jobs`. Forskellen er ikke kosmetisk: en dataclass-default er en
    KOPI af funktionsobjektet, fanget da klassen blev defineret, så en patch af
    `inbox_view._aegte_jobs` følger IKKE med. Mine egne værktøjstests nåede
    derfor de ægte vækninger og jobs fra udviklingsmaskinen — fire poster hvor
    testen forventede nul — og `slots=True` gjorde at klasse-attributten heller
    ikke kunne patches.

    Med den sene binding er modulet den ene kilde, og en test (eller en
    fremtidig anden adapter) kan bytte ÉN læsning uden at kende klassen.
    """
    poster: Callable[[str], list[dict[str, Any]]] = field(
        default=lambda b: _aegte_poster(b))
    vaekninger: Callable[[str], list[dict[str, Any]]] = field(
        default=lambda b: _aegte_vaekninger(b))
    jobs: Callable[[str], list[dict[str, Any]]] = field(
        default=lambda b: _aegte_jobs(b))
    godkendelser: Callable[[str], list[dict[str, Any]]] = field(
        default=lambda b: _aegte_godkendelser(b))
    proces_lever: Callable[[int | None], bool | None] = field(
        default=lambda p: _aegte_proces_lever(p))
    #: Vækningen der startede DENNE tur. Skal komme fra dispatcherens
    #: registrerede årsag — ikke gættes fra den seneste fyrede vækning, for så
    #: ville en tur han selv startede arve en tilfældig vækning som sin grund.
    turens_wakeup_id: Callable[[], str] = lambda: ""
    backlog_tal: Callable[[], int] = field(
        default=lambda: _aegte_backlog_tal())
    planlagte: Callable[[str], list[dict[str, Any]]] = field(
        default=lambda _b: [])
    gentagende: Callable[[str], list[dict[str, Any]]] = field(
        default=lambda _b: [])


# ── Postens seks felter ─────────────────────────────────────────────────────

def _post(
    *,
    post_id: str,
    status: str,
    beskrivelse: str,
    ejer: str,
    nu_ts: float,
    kildetype: str = "",
    udfald: str = "",
    output_sti: str = "",
    output_bytes: int | None = None,
    har_artefakt: bool = False,
    forfalden_dage: int | None = None,
    alder_dage: int | None = None,
    tid_tekst: str = "",
) -> dict[str, Any]:
    """Byg én post med de seks felter — og ÉN linje, uden payload.

    Felt 5 er «henvisning og størrelse, NÅR der findes et artefakt». Uden fil
    bruges det typede kilde-id, og der opdigtes ingen sti: skemaet må ikke kræve
    en outputfil der ikke findes.
    """
    maerke = EJER_MAERKE.get(ejer, EJER_MAERKE[db_inbox.EJER_UKENDT])
    dele = [post_id, status]
    if tid_tekst:
        dele.append(tid_tekst)
    if forfalden_dage is not None and forfalden_dage > 0:
        dele.append(f"{forfalden_dage}d forfalden")
    if udfald:
        dele.append(udfald)
    dele.append(f"«{_kort(beskrivelse, _BESKRIVELSE_LOFT)}»")
    if har_artefakt:
        dele.append(f"→ {output_sti} ({_bytes_tekst(output_bytes)})")
    dele.append(maerke)
    linje = _kort("  ".join(d for d in dele if d), _LINJE_LOFT)
    return {
        "id": post_id,
        "kildetype": kildetype,
        "status": status,
        "beskrivelse": str(beskrivelse or ""),   # den GEMTE afkortes ikke
        "udfald": udfald,
        "output_sti": output_sti if har_artefakt else "",
        "output_bytes": output_bytes if har_artefakt else None,
        "ejer": ejer,
        "ejer_maerke": maerke,
        "forfalden_dage": forfalden_dage,
        "alder_dage": alder_dage,
        "kraever_handling": ejer == db_inbox.EJER_JARVIS,
        "dubletter": 1,
        "kilde_ider": [post_id],
        "linje": linje,
    }


def _indenfor_workspace(sti: str, bruger_id: str) -> bool:
    """Må stien vises? Uden for brugerens autoriserede workspace: nej.

    Global Constraint: «En sti må ikke læses uden for brugerens autoriserede
    workspace.» Posten vises stadig — stien gør ikke. En absolut sti uden for
    workspacet er netop den vej en anden brugers krypterede mappe kunne blive
    navngivet i Bjørns indbakke.
    """
    s = str(sti or "").strip()
    if not s:
        return False
    if ".." in s.split("/"):
        return False
    if not s.startswith("/"):
        return True            # relativ sti = inde i arbejdsområdet
    try:
        from core.identity.workspace_context import current_workspace_name
        navn = str(current_workspace_name() or "").strip()
    except Exception:  # noqa: BLE001 — kan vi ikke afgøre det, viser vi ikke stien
        return False
    if not navn:
        return False
    return os.path.normpath(s).startswith(f"/home/bs/.jarvis-v2/workspaces/{navn}")


def _min_post(r: dict[str, Any], bruger_id: str) -> bool:
    """Er denne rå kilde-post min?

    En post UDEN ejer slipper igennem — men den får `[ukendt]` og kan aldrig
    gate. En post med en ANDEN ejer slippes aldrig. Den asymmetri er valgt:
    `list_wakeups()` er global og har ejerløse poster, og skjulte vi dem,
    forsvandt reel tilstand fra fladen; men en fremmed ejer er et databrud.
    """
    uid = str(r.get("user_id") or r.get("bruger_id") or "").strip()
    return not uid or uid == bruger_id


def _dubletter_sammen(poster: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Grupper PRÆSENTATIONEN på (kildetype, beskrivelse) — bevar alle id'er.

    Dublet-tællingen må ikke erstatte identiteten: tre reelle vækninger har hver
    sit id og kan fyre eller annulleres selvstændigt. Lighed på (type,
    beskrivelse) er et FORSLAG om dublet, ikke et bevis — derfor bæres alle tre
    `kilde_ider` med, og afgørelser rammer stadig den enkelte.
    """
    ud: list[dict[str, Any]] = []
    indeks: dict[tuple[str, str], int] = {}
    for p in poster:
        # Grupper paa den AFKORTEDE beskrivelse. Maalt 3/10: 174 fyrede
        # «Resume interrupted visible run <id>»-vaekninger blev IKKE grupperet,
        # fordi hvert id er unikt i den GEMTE tekst — men de er den samme sag,
        # og i linjen ser de ens ud. En gruppering der ikke samler dem lader
        # husets stoej fylde hele sektionen.
        n = (str(p.get("kildetype") or ""),
             _kort(str(p.get("beskrivelse") or ""), _BESKRIVELSE_LOFT))
        if not n[1]:
            ud.append(p)        # uden beskrivelse er der intet at gruppere på
            continue
        i = indeks.get(n)
        if i is None:
            indeks[n] = len(ud)
            ud.append(p)
            continue
        g = ud[i]
        g["dubletter"] += 1
        g["kilde_ider"].append(p["id"])
        # BYG linjen om fra grundformen. Foerste udgave TILFOEJEDE til den
        # forrige, og med rigtige data stod der
        # «… booket 2 gange booket 3 gange booket 4 gange» — én gang per
        # dublet. 38 groenne tests saa det ikke, fordi de alle havde praecis
        # TRE dubletter og testede antallet, ikke teksten.
        grund = g.get("_grundlinje")
        if grund is None:
            grund = g["linje"].replace(g["ejer_maerke"], "").rstrip()
            g["_grundlinje"] = grund
        g["linje"] = _kort(
            f"{grund}  booket {g['dubletter']} gange  {g['ejer_maerke']}",
            _LINJE_LOFT)
    return ud


# ── Opgave 10: loft og rangorden ────────────────────────────────────────────
#
# BESLUTNINGEN (trin 1): **8 linjer per sektion, ældste først**, og den
# blokerende sektion har INTET loft.
#
# Hvorfor et loft overhovedet: argumentet der udelukkede kandidat-backloggen
# («1.896 poster ville drukne den dag ét») gælder også INDE i sektionerne. Seks
# sektioner uden loft er den samme kurve, bare senere.
#
# Hvorfor ældste først: forfald er postens vigtigste egenskab, og en post der
# har ventet tre dage er mere presserende end en der kom i morges. Sortering på
# «mest handlingskrævende» ville kræve en rangering vi ikke har målt endnu.
#
# Hvorfor «VENTER PÅ DIG» er undtaget: en SKJULT blokerende post er en usynlig
# blokering. Et gate-loft blev afvist af samme grund — «rammes et loft af støj,
# er den vigtige post den der falder udenfor». Et visnings-loft er kun
# forsvarligt fordi det SIGER hvor mange der er skjult; dér hvor det ikke kan
# sige det meningsfuldt, gælder det ikke.
_SEKTION_LOFT: Final[int] = 8

#: Sektioner uden loft. Præcis én, og den er den eneste der kan gate.
_UDEN_LOFT: Final[frozenset[str]] = frozenset({"venter_paa_dig"})


def _ordn(poster: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ældste først, med id som sekundær nøgle.

    Den sekundære nøgle er ikke pynt: poster med SAMME alder ville ellers
    flakke mellem ture, og en visning der flakker buster prompt-cachen fra sit
    eget sted og alt efter den. `None` i alder sorterer sidst — et uparsabelt
    tidsstempel skal ikke kunne snige sig øverst.
    """
    return sorted(
        poster,
        key=lambda p: (-(p.get("alder_dage") if p.get("alder_dage") is not None else -1),
                       str(p.get("id") or "")))


def _med_loft(navn: str, poster: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """(viste, skjulte). Et loft der ikke siger hvad det skjuler er selv en tavshed."""
    ordnet = _ordn(poster)
    if navn in _UDEN_LOFT or len(ordnet) <= _SEKTION_LOFT:
        return ordnet, 0
    return ordnet[:_SEKTION_LOFT], len(ordnet) - _SEKTION_LOFT


# ── Visningen ───────────────────────────────────────────────────────────────

def byg_indbakke(
    bruger_id: str,
    *,
    nu_ts: float | None = None,
    kilder: Kilder | None = None,
) -> dict[str, Any]:
    """Seks sektioner for ÉN bruger. Uden bruger-id: en typet fejl.

    Aldrig en liste over alle brugere. Husstanden har flere brugere, og de
    andres workspaces er krypterede — en indbakke der blander dem er et
    databrud, ikke en fejl i visningen.
    """
    bruger_id = str(bruger_id or "").strip()
    if not bruger_id:
        return {"status": "fejl", "error": "bruger_id kraeves"}
    k = kilder or Kilder()
    nu = float(nu_ts if nu_ts is not None else time.time())
    # ÉN laesning. Kilden kan vaere dyr, og to laesninger kunne give to
    # forskellige svar midt i en afgoerelse.
    alle_poster = list(k.poster(bruger_id))
    # Vækningernes EGEN tilstand, slået op ÉN gang. En `pending` vækning er
    # PLANLAGT, ikke ventende — se `planlagte_vaekning_ids`.
    planlagte_vaek_ids = planlagte_vaekning_ids(bruger_id, k)

    vakte: list[dict[str, Any]] = []
    venter_paa_dig: list[dict[str, Any]] = []
    i_gang: list[dict[str, Any]] = []
    paa_vej: list[dict[str, Any]] = []
    planlagte: list[dict[str, Any]] = []
    venter_paa_bjorn: list[dict[str, Any]] = []

    turens_wake = str(k.turens_wakeup_id() or "").strip()

    # ── Afgjorte poster, ÉT sted ──────────────────────────────────────────
    #
    # Jarvis' review 4/10-2026. Han lukkede tre poster; vækningen forsvandt,
    # men de to jobs stod der stadig som `fejlet`. Vækningen forsvandt kun
    # fordi `mark_wakeup_consumed` ændrer vækningens EGEN status i kilden —
    # job-grenen læste jobbets status og konsulterede aldrig `inbox_items`.
    # `drop` skrev altså en afgørelse visningen ikke læste.
    #
    # Det er samme form som de tre foregående fejl i dette spor, bare
    # spejlvendt: dér manglede en skriver og en læser, her læses der et andet
    # sted end der skrives.
    #
    # Derfor ÉT sæt, brugt af hver kilde-gren. En ny kilde der tilføjes senere
    # skal bruge `_er_afgjort` — og `tests/test_inbox_view.py` måler det for
    # hver gren, så et hul i den næste ikke kan være tavst.
    afgjorte: set[str] = {
        str(p.get("id") or "") for p in alle_poster
        if str(p.get("status") or "") != db_inbox.STATUS_AABEN
    }

    def _er_afgjort(kilde_id: str) -> bool:
        """Har nogen truffet en afgørelse om denne post?

        Alle terminale tilstande tæller — `done`, `drop`, `udloebet` og
        `afsluttet_af_kilde`. Dækkede den kun `done`/`drop`, ville en udløbet
        post stå for evigt, og Opgave 8's hele formål var at den ikke skulle.
        """
        return kilde_id in afgjorte

    # 1. De durable poster. DE er sandheden om hvad der kræver handling —
    #    kilderne nedenfor bidrager med tilstand, ikke med gating.
    for p in alle_poster:
        if p.get("status") != db_inbox.STATUS_AABEN:
            continue
        sti = str(p.get("output_sti") or "")
        vis_sti = _indenfor_workspace(sti, bruger_id)
        post = _post(
            post_id=str(p["id"]), status=str(p.get("status") or ""),
            beskrivelse=str(p.get("beskrivelse") or ""),
            ejer=str(p.get("verificeret_ejer") or db_inbox.EJER_UKENDT),
            kildetype=str(p.get("kildetype") or ""),
            output_sti=sti if vis_sti else "",
            output_bytes=p.get("output_bytes"),
            har_artefakt=bool(sti) and vis_sti,
            alder_dage=_alder_dage(str(p.get("created_at") or ""), nu),
            forfalden_dage=_alder_dage(str(p.get("created_at") or ""), nu),
            nu_ts=nu,
        )
        if post["id"] == turens_wake:
            vakte.append(post)
        # En vækning der stadig er PLANLAGT venter ikke på nogen. Dens række
        # findes allerede ved bookingen, så uden denne gren stod hver vækning
        # jeg booker til mig selv i VENTER PÅ DIG — og gatede — før den havde
        # fyret. Sektion 2's egen regel siger det samme; den sprang bare over,
        # fordi rækken kom først.
        if (str(p.get("kildetype") or "") == "wakeup"
                and str(p.get("kilde_id") or "") in planlagte_vaek_ids):
            paa_vej.append(post)
        else:
            venter_paa_dig.append(post)

    # 2. Vækninger. `pending` → PÅ VEJ; `fired` uden kvittering → VENTER PÅ DIG.
    for r in k.vaekninger(bruger_id):
        # DOBBELT bruger-filter, med vilje. Den ægte adapter filtrerer også —
        # men filteret lå ALENE der, og min egen test afslørede hvad det betød:
        # en kilde der glemmer filteret lækker en anden brugers vækning direkte
        # ind i visningen. Det er et databrud, ikke en visningsfejl, og det er
        # for dyrt at lade hænge på én vagt i et lag der kan udskiftes.
        if not _min_post(r, bruger_id):
            continue
        wid = str(r.get("wakeup_id") or "").strip()
        if not wid or _er_afgjort(wid):
            continue                      # afgjort — uanset hvad kilden siger
        if any(wid in p["kilde_ider"] for p in venter_paa_dig + paa_vej):
            continue                      # den durable post bærer den allerede
        st = str(r.get("status") or "")
        if st not in ("pending", "fired"):
            continue
        ejer = (db_inbox.EJER_JARVIS if str(r.get("user_id") or "") == bruger_id
                else db_inbox.EJER_UKENDT)
        forfald = _alder_dage(str(r.get("fired_at") or ""), nu) if st == "fired" else None
        post = _post(
            post_id=wid, status=st, kildetype="wakeup",
            beskrivelse=str(r.get("prompt") or r.get("reason") or ""),
            ejer=ejer, forfalden_dage=forfald,
            alder_dage=_alder_dage(str(r.get("scheduled_at") or ""), nu),
            tid_tekst=("fyrede " + str(r.get("fired_at") or "")[11:16]) if st == "fired" else "",
            nu_ts=nu)
        (venter_paa_dig if st == "fired" else paa_vej).append(post)
        if wid == turens_wake:
            vakte.append(post)

    # 3. Jobs. Et dødt job må IKKE stå som «kører» — men «kan ikke afgøres» er
    #    sin egen klasse, ikke et bevis på død.
    for j in k.jobs(bruger_id):
        if not _min_post(j, bruger_id):
            continue
        jid = str(j.get("id") or "").strip()
        if not jid or _er_afgjort(jid):
            # DEN fejl Jarvis fandt. Uden denne linje stod et droppet job som
            # `fejlet` for evigt, fordi grenen kun saa jobbets egen status.
            continue
        if any(jid in p["kilde_ider"] for p in venter_paa_dig):
            continue
        st = str(j.get("status") or "")
        sek = int(j.get("sekunder") or 0)
        lever = k.proces_lever(j.get("pid"))
        exit_kode = j.get("exit_code")
        udfald = "" if exit_kode in (None, "") else f"exit {exit_kode}"
        sti = str(j.get("output_sti") or j.get("output") or "")
        vis_sti = _indenfor_workspace(sti, bruger_id)
        faelles = {
            "post_id": jid, "kildetype": "job",
            "beskrivelse": str(j.get("navn") or j.get("beskrivelse") or ""),
            "ejer": db_inbox.EJER_UKENDT, "udfald": udfald,
            "output_sti": sti if vis_sti else "",
            "output_bytes": j.get("output_bytes"),
            "har_artefakt": bool(sti) and vis_sti, "nu_ts": nu,
        }
        # Et job UDEN pid er et KALD, ikke en proces — og `_tool_jobs`' egen
        # kontrakt er «Uparret = kører stadig». `lever is None` betyder derfor
        # to ting, og det er `pid` der skiller dem:
        #
        #   * MED pid, som ikke kan ses herfra (supervisor/operator på en host
        #     vi ikke kan nå) → «kan ikke afgøres» er det RIGTIGE svar.
        #   * UDEN pid → der er intet at spørge om. Grenen er en tautologi, og
        #     hvert kørende kald lander i «VENTER PÅ DIG» med et epoch i id'et,
        #     hvor `drop` aldrig kan ramme det.
        #
        # Kilden på listen, ikke navnet: `tool`, `tool_operator`, `agent`,
        # `shell` og `shell_operator` bærer alle `pid: None` og rammes derfor
        # af samme fejl. Målt 4/10-2026: `venter_paa_dig:
        # [('bash#1791092371','status_ukendt')]`, `i_gang: []` — og `== "tool"`
        # slap `tool_operator` forbi, som er netop den vej desk-broen bruger.
        er_kald = not j.get("pid")
        if st in ("kører", "running") and er_kald:
            i_gang.append(_post(status="koerer", **faelles))
        elif st in ("kører", "running") and lever is False and sek >= _FORAELDRELOES_EFTER_S:
            venter_paa_dig.append(_post(status="foraeldreloes", **faelles))
        elif st in ("kører", "running") and lever is None:
            venter_paa_dig.append(_post(status="status_ukendt", **faelles))
        elif st in ("kører", "running"):
            i_gang.append(_post(status="koerer",
                                tid_tekst=f"{sek // 60}m" if sek else "", **faelles))
        elif udfald and str(exit_kode) not in ("0",):
            venter_paa_dig.append(_post(status="fejlet", **faelles))

    # 4. Planlagte engangsopgaver → PÅ VEJ. Gentagende → PLANLAGTE.
    #    De er adskilt fordi `scheduled_tasks` fyrer ÉN gang mens
    #    `recurring_tasks` har interval og næste affyring. Blandedes de, ville
    #    indbakken overdrive hvor meget der venter — og så bliver den noget man
    #    lukker i stedet for at læse.
    for t in k.planlagte(bruger_id):
        if _er_afgjort(str(t.get("id") or "")):
            continue
        paa_vej.append(_post(
            post_id=str(t.get("id") or ""), status="planlagt", kildetype="scheduled",
            beskrivelse=str(t.get("beskrivelse") or t.get("prompt") or ""),
            ejer=db_inbox.EJER_UKENDT, nu_ts=nu))
    for t in k.gentagende(bruger_id):
        if _er_afgjort(str(t.get("id") or "")):
            continue
        planlagte.append(_post(
            post_id=str(t.get("id") or ""), status="gentagende", kildetype="recurring",
            beskrivelse=str(t.get("beskrivelse") or t.get("prompt") or ""),
            ejer=db_inbox.EJER_HUSET, nu_ts=nu,
            tid_tekst=f"hver {t.get('interval_minutes')}m" if t.get("interval_minutes") else ""))

    # 5. Godkendelser: synlige, gater ALDRIG. Hans svartid må ikke blive
    #    Jarvis' blokering.
    for a in k.godkendelser(bruger_id):
        if _er_afgjort(str(a.get("request_id") or a.get("id") or "")):
            continue
        venter_paa_bjorn.append(_post(
            post_id=str(a.get("request_id") or a.get("id") or ""),
            status=str(a.get("effective_approval_state") or a.get("approval_state") or ""),
            kildetype="approval", beskrivelse=str(a.get("summary") or a.get("tool") or ""),
            ejer=db_inbox.EJER_HUSET, nu_ts=nu,
            alder_dage=_alder_dage(str(a.get("created_at") or ""), nu)))

    ud: dict[str, Any] = {
        "status": "ok",
        "bruger_id": bruger_id,
        # «VAKTE» har pr. definition nul eller én linje og behoever intet loft.
        "vakte": vakte,
        "backlog_tal": int(k.backlog_tal() or 0),
    }
    for navn, poster in (("venter_paa_dig", venter_paa_dig), ("i_gang", i_gang),
                         ("paa_vej", paa_vej), ("planlagte", planlagte),
                         ("venter_paa_bjorn", venter_paa_bjorn)):
        # Dubletter FOERST, saa loftet taeller grupper og ikke raa poster —
        # ellers kunne tre bookinger af samme vaekning spise tre af de otte
        # pladser og skubbe noget andet ud.
        vist, skjult = _med_loft(navn, _dubletter_sammen(poster))
        ud[navn] = vist
        # Kun naar der ER noget skjult. «+0 mere» er en loegn i formen af et tal.
        if skjult:
            ud[f"{navn}_skjult"] = skjult
    return ud


__all__ = ["Kilder", "byg_indbakke"]
