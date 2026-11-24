"""CI-status — set, ikke gættet.

Hullet, målt 3/10-2026: `ci` var rødt på `main` i to døgn — over 30 kørsler i
træk — uden at nogen så det. Vagten (`tests/test_publish_scan.py`) fangede
fejlen med det samme; det var *fladen* der manglede. Beskyttelsen var en vane,
skrevet i MEMORY tre gange: «husk at tjekke CI efter push». Den fejlede.

Der fandtes ingen alarm. Intet i `core/`, `scripts/` eller `apps/` kaldte
GitHub Actions-API'et. Her lukkes hullet: hjerteslaget spørger selv, husker
hvilke kørsler det har set, og lægger kun det NYE røde i køen.

**Grundlinjen — hvorfor første kørsel tier.** Her er der historik, i modsætning
til baggrunds-shellene. Et rødt run fra i går er ikke nyt, og en vagtpost der
råber op om 30 gamle fejl ved første kørsel bliver slukket igen. Derfor huskes
tidsstemplet for hvornår vagtposten vågnede (`foerste_ved`), og kun kørsler
oprettet EFTER det kan give en besked. Konsekvensen er ærlig og skal siges
højt: vagtposten kan ikke melde hvad der skete før den fandtes — den fanger
det næste. Det er den kontrakt, ikke en tilfældighed.

**Hvorfor i de ubetingede daemoner.** Samme grund som `background_job_watch`:
`act_phase` dispatcher kun videre til `run_heartbeat_tick` når der ER
prioriteter. En alarm der kun kan komme når der i forvejen er travlt, er ikke
en alarm.

**Uden token, med vilje.** Repoet er offentligt og API'et svarer
uautentificeret. Loftet er 60 kald i timen; vi bruger 15. Et token ville
tilføje et nyt fejlled (udløb, manglende brugerkontekst i et bart hjerteslag)
for en grænse vi ikke er i nærheden af. Bliver det et problem, er det her
stedet at ændre.

**Rate-limit og 404 er blindhed, ikke sundhed.** Svarer API'et 403 med
`X-RateLimit-Remaining: 0`, eller 404, eller tier netværket — så VED vi ikke
om CI er rødt. Det må ikke blive «alt fint». Se `ApiUkendt`.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_REPO = "Nickless-cmd/jarvis-v2"
_API = f"https://api.github.com/repos/{_REPO}/actions/runs"
#: Desk-releasen kører på et TAG (`jarvis-desktop-v…`), og et tag er ikke en
#: branch — så `?branch=main` ser den aldrig. Se `_hent_runs`.
_RUNS_DESK = f"https://api.github.com/repos/{_REPO}/actions/workflows/desk-release.yml/runs"

_STATE = "ci_watch_set"
_SIDSTE_TJEK = "ci_watch_sidste_tjek"
# Grundlinjen har sin EGEN fil. Foerste udgave delte `_SIDSTE_TJEK` med
# throttlen, og `_grundlinje()` satte dermed `ved` — saa foerste maaling blev
# sprunget over som «for tidligt». To begreber i én fil kan forstyrre
# hinanden; her er de skilt ad. (Fanget af testene, 3/10-2026.)
_GRUNDLINJE = "ci_watch_grundlinje"

# 60 kald i timen uautentificeret. 240 s = 15 i timen — rigeligt luft, og fint
# nok til at fange et rødt run et par minutter efter det er afsluttet.
_MIN_MELLEMRUM_S = 240.0

# Hvor længe et set run-id huskes. Vinduet er 10 runs; 30 dage er rigeligt til
# at et run ikke kan nå at falde ud af vinduet og dukke op igen som «nyt».
_HUSK_DAGE = 30

# Hvor mange kørsler vi kigger på pr. gang.
_VINDUE = 10

# Konklusioner der tæller som rødt. `cancelled` er med vilje IKKE med: et
# afbrudt run kan være et bevidst valg, og en alarm der råber op om det bliver
# ignoreret. `skipped`/`neutral` er heller ikke fejl.
_ROEDE = frozenset({"failure", "timed_out", "startup_failure", "action_required"})

# ── Abonnement: «sig til når DENNE kørsel er afgjort» ───────────────────────
#
# HVORFOR (maalt 24/11-2026). Vagten kunne kun melde det der gik GALT
# (`conclusion not in _ROEDE: continue`). Men det jeg venter paa efter et push
# er naesten altid en GROEN koersel — og den var usynlig for vagten. Prisen var
# maalt: jeg pollede `gh run list` i haanden to gange samme dag, 7-14 forsoeg
# pr. gang, for at se noget systemet allerede kunne se. Det er den samme
# fejlklasse som vagten selv blev bygget for at fjerne — beskyttelsen var en
# vane, ikke en mekanisme.
#
# ABONNEMENTET ER EN FORVENTNING, IKKE EN ALARM. Derfor sin egen kildetype
# (`ci_svar`) og sin egen state-fil: en groen koersel maa ikke overskrive den
# roede alarms husk, og et abonnement paa en SHA er ikke det samme som «jeg har
# set dette run».
_ABONNEMENTER = "ci_abonnementer"
_SIDSTE_ABONNEMENT_TJEK = "ci_abonnement_sidste_tjek"

#: Mens nogen venter, spoerger vi oftere — men med ET kald pr. abonnement
#: (`?head_sha=`), ikke de to brede kald.
#:
#: REGNESTYKKET, for det er let at sprænge loftet uden at se det: uautentificeret
#: loft er 60 i timen. Det brede scan koster 2 kald pr. runde ved 240 s = 30 i
#: timen. Et abonnement koster 1 kald pr. runde, saa intervallet SKAL skaleres
#: med antallet: `_MIN_MELLEMRUM_ABONNEMENT_S * antal`. Ved 150 s giver ét
#: abonnement 24 i timen, og totalen er 54 — under loftet med luft. Foerste
#: udgave brugte 90 s, hvilket gav 40 + 30 = 70 i timen: over loftet, og fejlen
#: ville foerst vise sig som blindhed i drift.
_MIN_MELLEMRUM_ABONNEMENT_S = 150.0

#: Et abonnement der aldrig faar en koersel (workflow triggede ikke, SHA'en
#: findes ikke, eller Actions er nede) maa ikke henge for evigt — det ville
#: baade holde det brede scan nede og love et svar der aldrig kommer.
_ABONNEMENT_UDLOEB_MIN = 30.0


def _nu() -> datetime:
    return datetime.now(UTC)


class ApiUkendt(RuntimeError):
    """Vi kunne ikke se CI.

    Det er ikke det samme som at CI er grøn — og forskellen er hele grunden til
    at klassen findes. En vagtpost der melder «alt fint» når den i
    virkeligheden er blind, er den fejlklasse `test_publish_scan` blev skrevet
    for at fange.
    """


def _rapporterede() -> dict[str, str]:
    """{run_id: iso-tidsstempel} for det vi allerede har set.

    Poster ældre end `_HUSK_DAGE` falder væk under læsningen — filen rydder
    sig selv uden et separat oprydningsjob.
    """
    from core.runtime import state_store

    raa = state_store.load_json(_STATE, {})
    if not isinstance(raa, dict):
        return {}
    graense = _nu() - timedelta(days=_HUSK_DAGE)
    ud: dict[str, str] = {}
    for noegle, vaerdi in raa.items():
        try:
            stempel = datetime.fromisoformat(str(vaerdi))
        except (ValueError, TypeError):  # ulaeseligt tidsstempel — posten kan ikke dateres
            continue
        if stempel >= graense:
            ud[str(noegle)] = str(vaerdi)
    return ud


def _husk(ids: list[str]) -> None:
    """Skriv id'erne som sete — atomisk, så api og runtime ikke overskriver
    hinandens lister."""
    if not ids:
        return
    from core.runtime import state_store

    stempel = _nu().isoformat()
    with state_store.med_laas(_STATE):
        post = _rapporterede()
        for i in ids:
            if i:
                post[i] = stempel
        state_store.save_json(_STATE, post)


def _grundlinje() -> str:
    """Tidsstemplet for hvornår vagtposten vågnede. Sættes én gang.

    Alt hvad der er oprettet før det, er historik vi ikke kan udtale os om —
    og som vi derfor husker uden at melde. Se modulets docstring.
    """
    from core.runtime import state_store

    post = state_store.load_json(_GRUNDLINJE, None)
    if isinstance(post, dict) and post.get("foerste_ved"):
        return str(post["foerste_ved"])
    stempel = _nu().isoformat()
    state_store.save_json(_GRUNDLINJE, {"foerste_ved": stempel})
    return stempel


def _hent_url(url: str) -> list[dict[str, Any]]:
    """Kørslerne bag én Actions-URL. Rejser `ApiUkendt` når vi ikke kunne se dem."""
    req = urllib.request.Request(
        url,
        headers={
            # GitHub afviser et kald uden User-Agent.
            "User-Agent": "jarvis-ci-status-watch",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raa = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 403/429 = rate-limit, 404 = repoet findes ikke (eller er blevet
        # privat). Begge betyder «vi kan ikke se», ikke «alt er fint».
        raise ApiUkendt(f"http_{exc.code}") from exc
    except Exception as exc:  # netvaerk/utilgaengeligt — samme blindhed
        raise ApiUkendt(f"kaldet_fejlede: {str(exc)[:80]}") from exc
    if not isinstance(raa, dict):
        raise ApiUkendt("uventet_svarform")
    return [r for r in (raa.get("workflow_runs") or []) if isinstance(r, dict)]


def _hent_runs() -> list[dict[str, Any]]:
    """Kørslerne vi holder øje med — på `main` OG desk-release (tag-styret).

    Målt 15/10-2026: vagten spurgte KUN `?branch=main`. Desk-releasen kører på
    et TAG, og et tag er ikke en branch — så 0.6.237's fejlede build
    (`jarvis-desktop-v0.6.237`, TS2741 i electron/preload.ts) var usynligt for
    vagten. Bjørn sad i en åben session og fik intet signal; han opdagede det
    selv. Det er præcis den blindhed vagten findes for at fjerne, så begge
    kilder hentes nu. Dedup paa id, saa et run der optraeder i begge lister
    kun taelles én gang.
    """
    alle = _hent_url(f"{_API}?branch=main&per_page={_VINDUE}") + _hent_url(
        f"{_RUNS_DESK}?per_page={_VINDUE}"
    )
    unikke: dict[str, dict[str, Any]] = {}
    for run in alle:
        rid = str(run.get("id") or "")
        if rid and rid not in unikke:
            unikke[rid] = run
    return list(unikke.values())


def scan_roede() -> list[dict[str, Any]]:
    """Nye røde kørsler på `main` siden sidst — efter grundlinjen.

    Rejser `ApiUkendt` når vi ikke kunne se CI.
    """
    grundlinje = _grundlinje()
    try:
        graense = datetime.fromisoformat(grundlinje)
    except (ValueError, TypeError):  # ulaeselig grundlinje — behandl alt som historik
        graense = _nu()

    kendte = _rapporterede()
    nye: list[dict[str, Any]] = []
    sete: list[str] = []
    for run in _hent_runs():
        rid = str(run.get("id") or "")
        if not rid:
            continue
        sete.append(rid)
        if rid in kendte:
            continue
        if str(run.get("status")) != "completed":
            continue  # kører endnu — ikke rødt, bare ikke færdigt
        if str(run.get("conclusion") or "") not in _ROEDE:
            continue
        try:
            oprettet = datetime.fromisoformat(str(run.get("created_at")).replace("Z", "+00:00"))
        except (ValueError, TypeError):  # ulaeseligt tidsstempel — kan ikke placeres mod grundlinjen
            continue
        if oprettet <= graense:
            continue  # historik fra før vagtposten fandtes — huskes, meldes ikke
        nye.append(run)

    # Alt i vinduet huskes — ogsaa de groenne. Ellers ville et run vi allerede
    # har vurderet blive vurderet igen hver gang, og et gammelt roedt run der
    # laa i vinduet ved grundlinjen kunne dukke op som «nyt» naar dets
    # tidsstempel faldt ud af sammenligningen.
    _husk(sete)
    return nye


# ── Abonnement paa en bestemt kørsel ────────────────────────────────────────


def _abonnementer() -> dict[str, dict[str, Any]]:
    """{sha: {oprettet, note, workflow, set_ved}} for de ventende abonnementer."""
    from core.runtime import state_store

    raa = state_store.load_json(_ABONNEMENTER, {})
    if not isinstance(raa, dict):
        return {}
    return {str(k): v for k, v in raa.items() if isinstance(v, dict)}


def _gem_abonnementer(post: dict[str, dict[str, Any]]) -> None:
    from core.runtime import state_store

    with state_store.med_laas(_ABONNEMENTER):
        state_store.save_json(_ABONNEMENTER, post)


def abonner(sha: str, *, note: str = "", workflow: str = "") -> dict[str, Any]:
    """Vent paa at kørslen for `sha` bliver afgjort — grøn ELLER rød.

    Rejser `ValueError` ved en tom eller ulæselig SHA: et abonnement der aldrig
    kan indfries er værre end intet abonnement, fordi det ser ud som om nogen
    holder øje.
    """
    ren = str(sha or "").strip().lower()
    if len(ren) < 7 or any(c not in "0123456789abcdef" for c in ren):
        raise ValueError(f"ugyldig sha: {sha!r}")

    post = _abonnementer()
    # Samme SHA to gange er ikke to løfter — det er ét. Noten opdateres, saa en
    # senere note ikke overskriver en tidligere med samme indhold.
    post[ren] = {
        "oprettet": _nu().isoformat(),
        "note": str(note or "").strip()[:200],
        "workflow": str(workflow or "").strip()[:80],
    }
    _gem_abonnementer(post)
    return {"status": "ok", "sha": ren, "venter": len(post)}


def _hent_sha_runs(sha: str) -> list[dict[str, Any]]:
    """Alle kørsler for én SHA. ET kald — derfor kan abonnementet køre oftere
    end det brede scan uden at brænde rate-limit-budgettet.

    MÅLT 24/11-2026: GitHubs `head_sha`-filter matcher KUN den fulde
    40-tegns SHA. En forkortet SHA gav 0 kørsler — og 0 blev læst som
    «intet_run», altså et falsk svar der fjernede abonnementet som om det var
    afgjort. `abonner` accepterer fra 7 tegn, så vejen var åben: den der
    abonnerede med en kort SHA fik et svar der lød som et udfald.
    Korte SHA'er slås derfor op i den brede liste og matches på præfiks.
    Grænse: ligger SHA'en længere tilbage end de hentede kørsler, findes den
    ikke her — men et abonnement udløber efter 30 min, så i praksis er den ny.
    """
    ren = str(sha or "").strip().lower()
    if len(ren) >= 40:
        return _hent_url(f"{_API}?head_sha={ren}&per_page=20")
    brede = _hent_url(f"{_API}?per_page=40")
    return [
        r for r in brede
        if str(r.get("head_sha") or "").lower().startswith(ren)
    ]


def _afgoer(runs: list[dict[str, Any]], workflow: str) -> tuple[str, list[dict[str, Any]]]:
    """('venter'|'groen'|'roed'|'afbrudt'|'intet_run', de afgørende kørsler).

    `workflow` filtrerer paa navn eller sti, saa et abonnement kan gælde
    `ci` og ikke desk-releasen. Tom betyder «alle».
    """
    valgte = runs
    if workflow:
        noegle = workflow.strip().lower()
        valgte = [
            r for r in runs
            if noegle in str(r.get("name") or "").lower()
            or noegle in str(r.get("path") or "").lower()
        ]
    if not valgte:
        return "intet_run", []
    if any(str(r.get("status")) != "completed" for r in valgte):
        return "venter", valgte
    konklusioner = {str(r.get("conclusion") or "") for r in valgte}
    if konklusioner & _ROEDE:
        return "roed", valgte
    if konklusioner and konklusioner <= {"cancelled"}:
        return "afbrudt", valgte
    return "groen", valgte


def scan_abonnementer() -> list[dict[str, Any]]:
    """De abonnementer der er afgjort NU — og fjern dem fra listen.

    Rejser `ApiUkendt` naar vi ikke kunne se CI: et abonnement maa ikke indfries
    paa en blindhed, praecis som `scan_roede` ikke maa melde «alt fint».
    """
    post = _abonnementer()
    if not post:
        return []

    afgjorte: list[dict[str, Any]] = []
    tilbage: dict[str, dict[str, Any]] = {}
    aendret = False
    for sha, meta in post.items():
        try:
            oprettet = datetime.fromisoformat(str(meta.get("oprettet")))
        except (ValueError, TypeError):  # ulaeseligt stempel — kan ikke udloebe, behold
            tilbage[sha] = meta
            continue
        alder_min = (_nu() - oprettet).total_seconds() / 60.0

        # Udloeb foer API-kaldet: et abonnement der har ventet for lenge skal
        # ikke koste et kald mere at afslutte.
        if alder_min > _ABONNEMENT_UDLOEB_MIN:
            afgjorte.append({
                "sha": sha,
                "note": str(meta.get("note") or ""),
                "workflow": str(meta.get("workflow") or ""),
                "udfald": "intet_run",
                "runs": [],
                "alder_min": round(alder_min, 1),
            })
            aendret = True
            continue

        try:
            runs = _hent_sha_runs(sha)
        except ApiUkendt:
            # Behold abonnementet: vi ved ikke om det er afgjort. Naeste tik
            # proever igen, og udloebsgraensen fanger det hvis det aldrig sker.
            tilbage[sha] = meta
            continue

        udfald, valgte = _afgoer(runs, str(meta.get("workflow") or ""))
        if udfald == "venter":
            tilbage[sha] = meta
            continue
        afgjorte.append({
            "sha": sha,
            "note": str(meta.get("note") or ""),
            "workflow": str(meta.get("workflow") or ""),
            "udfald": udfald,
            "runs": valgte,
            "alder_min": round(alder_min, 1),
        })
        aendret = True

    if aendret:
        _gem_abonnementer(tilbage)
    return afgjorte


def _beskriv_svar(a: dict[str, Any]) -> str:
    """Én linje pr. abonnement — udfaldet FØRST, for det er hele ærindet."""
    udfald = str(a.get("udfald") or "?")
    sha = str(a.get("sha") or "")[:9]
    note = str(a.get("note") or "").strip()
    hale = f" — {note}" if note else ""
    if udfald == "intet_run":
        return (
            f"- `{sha}`: **ingen kørsel set** inden for "
            f"{_ABONNEMENT_UDLOEB_MIN:.0f} min{hale}\n"
            "  Workflowet blev ikke trigget, eller Actions svarede ikke. "
            "Abonnementet er lukket — kørselen kommer ikke af sig selv."
        )
    linjer = [f"- `{sha}`: **{udfald}**{hale}"]
    for r in (a.get("runs") or [])[:5]:
        linjer.append("  " + _beskriv(r).lstrip("- "))
    return "\n".join(linjer)


def _lever_abonnementer(afgjorte: list[dict[str, Any]]) -> dict[str, Any]:
    """Skriv de afgjorte abonnementer i indbakken. Kaster ikke."""
    from core.services.inbox_state import laese_bruger, registrer_kilde

    bruger = laese_bruger()
    if not bruger:
        return {"status": "fejl", "grund": "ingen-bruger", "antal": len(afgjorte)}

    leveret = 0
    fejl: list[str] = []
    for a in afgjorte:
        tekst = "CI-abonnement indfriet:\n" + _beskriv_svar(a)
        try:
            svar = registrer_kilde(
                bruger_id=bruger,
                # `ci_svar`, ikke `ci_alarm`: en grøn kørsel er ikke en fejl.
                # Men den SKAL kunne vække — det er hele pointen med at vente
                # paa den i stedet for at polle i hånden.
                kildetype="ci_svar",
                kilde_id=f"ci-abonnement-{str(a.get('sha') or '')[:12]}",
                beskrivelse=tekst[:1000],
            )
        except Exception as exc:
            logger.warning("ci_status_watch: kunne ikke levere abonnements-svar: %s", exc)
            fejl.append(str(exc)[:80])
            continue
        if str(svar.get("status") or "") != "ok":
            fejl.append(f"levering-{svar.get('status') or 'error'}")
            continue
        leveret += 1
    return {"status": "ok" if not fejl else "delvist", "antal": leveret, "fejl": fejl}


def _beskriv(run: dict[str, Any]) -> str:
    navn = str(run.get("display_title") or run.get("name") or "(kørsel)").strip()
    navn = " ".join(navn.split())[:90]
    sha = str(run.get("head_sha") or "")[:9]
    konkl = str(run.get("conclusion") or "?")
    url = str(run.get("html_url") or "")
    linje = f"- `{sha}` — {konkl}: {navn}"
    return f"{linje}\n  {url}" if url else linje


def _sekunder_siden(sidste: Any) -> float | None:
    """Sekunder siden forrige tjek — eller None når stemplet mangler eller er
    ulæseligt. None betyder «mål», ikke «spring over»: en ulaeselig state må
    ikke kunne slukke vagtposten for evigt."""
    if not isinstance(sidste, dict) or not sidste.get("ved"):
        return None
    try:
        return (_nu() - datetime.fromisoformat(str(sidste["ved"]))).total_seconds()
    except (ValueError, TypeError):  # ulaeseligt tidsstempel — maal i stedet for at springe over
        return None


def tik() -> dict[str, Any]:
    """Tjek CI og indfri afgjorte abonnementer.

    To ærinder med hver sit tidsstempel: det BREDE scan leder efter nye røde
    kørsler (240 s), og ABONNEMENTERNE svarer på «er den kørsel jeg venter på
    afgjort» (150 s × antal). Ét fælles tidsstempel ville tvinge det ene til den
    andens kadence.

    Kaster aldrig. Kaldes fra de ubetingede daemoner, så den må ikke kunne
    standse et hjerteslag: hver fejl returneres som en status.
    """
    from core.runtime import state_store

    # ── Abonnementerne foerst ──────────────────────────────────────────────
    # De ligger FOER throttlen, fordi de har deres egen. En fejl her maa ikke
    # kunne standse det brede scan nedenfor — de to veje er uafhaengige.
    abonnement: dict[str, Any] = {"antal": 0}
    try:
        aktive = _abonnementer()
        if aktive:
            sidste_ab = state_store.load_json(_SIDSTE_ABONNEMENT_TJEK, None)
            forloeb_ab = _sekunder_siden(sidste_ab)
            # Intervallet SKAL skalere med antallet, ellers sprænger N
            # abonnementer rate-limit-loftet. Se regnestykket ved konstanten.
            krav = _MIN_MELLEMRUM_ABONNEMENT_S * max(1, len(aktive))
            if forloeb_ab is None or forloeb_ab >= krav:
                afgjorte = scan_abonnementer()
                state_store.save_json(
                    _SIDSTE_ABONNEMENT_TJEK, {"ved": _nu().isoformat()}
                )
                if afgjorte:
                    abonnement = _lever_abonnementer(afgjorte)
                    abonnement.setdefault("antal", len(afgjorte))
    except Exception as exc:  # et abonnement maa ikke kunne standse vagtposten
        logger.warning("ci_status_watch: abonnements-tjek fejlede: %s", exc)
        abonnement = {"status": "fejl", "grund": str(exc)[:120], "antal": 0}

    # Throttle for det brede scan. Tidsstemplet ligger i state_store, så
    # målingen holder hen over genstart.
    try:
        sidste = state_store.load_json(_SIDSTE_TJEK, None)
    except Exception as exc:  # ulaeselig state — vi maa hellere maale end springe over
        logger.debug("ci_status_watch: kunne ikke laese sidste tjek: %s", exc)
        sidste = None
    forloebet = _sekunder_siden(sidste)
    if forloebet is not None and forloebet < _MIN_MELLEMRUM_S:
        return {"status": "skip", "grund": "for-tidligt", "abonnement": abonnement}

    try:
        nye = scan_roede()
    except Exception as exc:
        # Vi VED ikke om CI er rødt. Saa siger vi ingenting frem for at sige
        # «alt fint» — og vi roerer ikke tidsstemplet, saa vi proever igen.
        logger.debug("ci_status_watch: kunne ikke se CI: %s", exc)
        return {"status": "ukendt", "grund": str(exc)[:120], "abonnement": abonnement}

    try:
        state_store.save_json(_SIDSTE_TJEK, {"ved": _nu().isoformat()})
    except Exception as exc:  # tidsstemplet er en optimering — et tabt skriv giver kun et tjek for meget
        logger.debug("ci_status_watch: kunne ikke gemme sidste tjek: %s", exc)

    if not nye:
        return {"status": "ok", "nye": 0, "abonnement": abonnement}

    tekst = "CI gik rødt på main:\n" + "\n".join(_beskriv(r) for r in nye)
    # 3/10-2026: udgangen flyttet fra heartbeat-trigger-koeen til
    # notification_bridge — samme grund som i `background_job_watch`.
    #
    # Koeen toemmes aldrig: `consume_trigger` kaldes kun bag
    # `ping_channel != "webchat"` og kun fra head. En CI-alarm der ikke kan
    # naa frem er ikke en alarm — og det var hele grunden til at vagtposten
    # blev bygget (ci var roedt i to doegn uden at nogen saa det).
    #
    # 11/10-2026: leveringsvejen flyttet fra `send_session_notification` til
    # Jarvis' EGEN indbakke. Foer skrev alarmen i den SYN LIGE samtale, saa
    # Bjoern fik CI-stoej midt i chatten for en fejl der kun vedkommer Jarvis.
    # Indbakken er den flade Jarvis selv laeser (`inbox_prompt_section`), og en
    # CI-alarm er en HUSETS begivenhed — kildetype `daemon` kan derfor ikke
    # naegte en mutation. `kilde_id` er konstant, saa posten opdateres i stedet
    # for at hobe sig op; `daemon` staar i IKKE_GATENDE_KILDETYPER, saa en
    # kvitteret post genaabnes naar der kommer et nyt roedt run.
    try:
        from core.services.inbox_state import laese_bruger, registrer_kilde

        bruger = laese_bruger()
        if not bruger:
            return {
                "status": "fejl",
                "nye": len(nye),
                "grund": "ingen-bruger",
                "abonnement": abonnement,
            }
        levering = registrer_kilde(
            bruger_id=bruger,
            # `ci_alarm` og ikke `daemon` (15/10-2026). En CI-fejl er ikke en
            # informerende husets begivenhed — den KRÆVER at Jarvis handler.
            # Med `daemon` kunne posten aldrig vække (`daemon` staar i
            # IKKE_GATENDE_KILDETYPER og er ikke dispatchbar), saa alarmen stod
            # stille til næste heartbeat eller Bjørns næste besked. Det var
            # præcis hvad der skete 15/10.
            kildetype="ci_alarm",
            kilde_id="ci-status-watch",
            beskrivelse=tekst[:1000],
        )
    except Exception as exc:
        logger.warning("ci_status_watch: kunne ikke levere besked: %s", exc)
        return {
            "status": "fejl",
            "nye": len(nye),
            "grund": str(exc)[:120],
            "abonnement": abonnement,
        }
    if str(levering.get("status") or "") != "ok":
        # Uden det her tjek ville vi melde «leveret» om en alarm der aldrig
        # blev skrevet — og runnene er allerede markeret sete, saa de ville
        # ikke komme igen.
        return {
            "status": "fejl",
            "nye": len(nye),
            "grund": f"levering-{levering.get('status') or 'error'}",
            "abonnement": abonnement,
        }
    return {"status": "ok", "nye": len(nye), "tekst": tekst, "abonnement": abonnement}
