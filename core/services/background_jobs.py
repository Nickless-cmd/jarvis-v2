"""Alle kørende baggrundsopgaver — uanset hvor de kører.

Bjørn 12/9-2026: «et sted hvor brugeren kan se de aktive opgaver der kører,
uanset om det er bash commander eller andre ting».

Kilderne er forskellige, og det er ikke en designfejl — de slags arbejde er
virkelig forskellige:

``supervisor``
    Langtidsservicer på serveren (`process_supervisor`): trading-bot, workers,
    pollere. Målt 12/9 kørte fire. De har navne, logfiler og skal kunne stoppes
    og startes uafhængigt af en samtale.

``operator``
    Ad hoc-shells på Bjørns EGEN maskine (`operator_background`), gemt som
    filer i ``/tmp/jarvis-bg/<id>.{log,pid,rc}``. De opstår midt i en opgave og
    dør igen. Målt 12/9 lå der poster fra samme dag.

``agent``
    Scout-agenter (`scout_agent`, før `explore`) — læsende research-agenter i
    agent-registret. Tilføjet 17/9-2026: Jarvis gjorde dem til baggrundsjob fra
    start til slut, og Bjørn: «scout agenter [skal] vises i baggrundsjob panel
    i desk». Før var de usynlige her, selv mens de arbejdede i minutter.

``shell``
    Åbne shell-sessioner: `bash_session` (serverens egen daemon) og
    `operator_bash_session` (Bjørns maskine). Tilføjet 26/9-2026 — Bjørn:
    «hans bash og operator_bash [skal] ramme baggrundsjobs panelet... simple
    vising med en stop knap».

    De to værktøjsfiler er IKKE rørt. Begge havde `list` og `close` i forvejen,
    og panelet bruger netop dem: stop-knappen er den samme lukning Jarvis selv
    kan kalde. Intet nyt gates.

    Tallet er IKKE levetid: hverken daemonen eller operator-dict'en gemmer et
    fødselstidspunkt, kun «sidst brugt». Hvad det så er, står i `_shell_kort`
    — og det er ikke det samme for de to kilder.

    Fra 26/9-2026 svarer `bash_session.list` også `busy` og `command`, så et
    kort kan sige hvad der kører og hvor længe. Operator-siden kan det ikke:
    dens `run` er ét bro-hop uden noget der holder tilstanden imens.

``tool``
    Værktøjskald fra et model-run, læst ud af de `tool.invoked`/`tool.completed`
    events runtime allerede udgiver. Tilføjet 3/10-2026 — Bjørn: «alle hans
    opgaver/bash commandoer bliver vist i baggrunds panelet... det sker ikk på
    vores?». De øvrige kilder er BEHOLDERE; et bash-kald er en kommando inde i
    en shell, og den blev aldrig til en række. Se `_tool_jobs` for hvorfor kun
    kald med et `run_id` kommer med.

Et panel der kun viste den ene ville være sandt om sin form og tavst om sit
indhold — man ville tro der ikke kørte noget, mens der gjorde.

## Hvorfor operator-siden læses med ÉN kommando

Hver fil kunne læses for sig, men det er en netværkstur over broen pr. fil.
Én compound-kommando giver hele billedet i én tur — samme afvejning som
``hostname`` der hænger på git-status' kommando.

``ps -o stat=`` giver ``T`` for en standset proces, så pause-tilstanden kommer
med i samme svar frem for at skulle gættes.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_ROD = "/tmp/jarvis-bg"

# Én kommando, ét svar. `stat -c %Y` er filens mtime i sekunder — .pid skrives
# når shellen starter, så den ER starttidspunktet.
_LISTE_CMD = (
    f'for f in {_ROD}/*.pid; do '
    '[ -e "$f" ] || continue; '
    'id=$(basename "$f" .pid); pid=$(cat "$f" 2>/dev/null); '
    f'rc=""; [ -f "{_ROD}/$id.rc" ] && rc=$(cat "{_ROD}/$id.rc" 2>/dev/null); '
    'st="dead"; if kill -0 "$pid" 2>/dev/null; then st=$(ps -o stat= -p "$pid" 2>/dev/null | cut -c1); fi; '
    'start=$(stat -c %Y "$f" 2>/dev/null); '
    # `$id`, IKKE `"$f"`. `$f` ER pid-filen, saa `"$f".cmd` pegede paa
    # `<id>.pid.cmd` — en fil der ikke findes. `operator_background` skriver
    # `<id>.cmd` og `<id>.title`. Maalt 6/10-2026 paa ni aegte jobs: begge
    # felter var TOMME, saa hvert operator-job stod som «(baggrunds-shell)» —
    # ogsaa efter at titlen blev bygget 3/10 praecis for at raade bod paa at
    # «Jarvis' kommandoer var usynlige». Stien var det sidste led.
    #
    # Titlen staar nu FOER kommandoen og faar sine egne `|` fjernet, og
    # kommandoen samles igen fra resten: en pipe i kommandoen delte foer linjen
    # midt over, saa titel-feltet fik halen af kommandoen i stedet for titlen.
    f'titel=$(tr "\\n|" "  " < "{_ROD}/$id.title" 2>/dev/null | cut -c1-120); '
    f'cmd=$(tr "\\n" " " < "{_ROD}/$id.cmd" 2>/dev/null | cut -c1-200); '
    'echo "$id|$pid|$st|$rc|$start|$titel|$cmd"; '
    'done'
)


def _nu() -> float:
    return datetime.now(UTC).timestamp()


def _operator_jobs(uid: str, exec_fn) -> list[dict[str, Any]]:
    """Baggrunds-shells på operatørens maskine. Tom liste hvis broen tier.

    Fail-soft med vilje: en død bro betyder at vi ikke VED om der kører noget
    derovre, og panelet siger det med et eget felt — ikke ved at lade som om
    listen var tom.
    """
    res = exec_fn("operator_bash", {"command": _LISTE_CMD, "_user_id": uid})
    if res.get("status") != "ok":
        raise BroTier(str(res.get("error") or res.get("reason") or "broen svarede ikke"))
    ud = str((res.get("result") or {}).get("stdout") or "")
    jobs: list[dict[str, Any]] = []
    nu = _nu()
    for linje in ud.splitlines():
        dele = linje.strip().split("|")
        if len(dele) < 5 or not dele[0]:
            continue
        jid, pid, st, rc, start = dele[0], dele[1], dele[2], dele[3], dele[4]
        titel = dele[5].strip() if len(dele) > 5 else ""
        kommando = "|".join(dele[6:]).strip() if len(dele) > 6 else ""
        levende = st not in ("dead", "", "Z")
        jobs.append({
            "id": jid,
            "kilde": "operator",
            # B (Bjørn 29/9-2026): linje 1 er hvad opgaven LAVER, ikke hvad
            # den hedder. Titlen skrives ved start (`<id>.title`); mangler
            # den — fx et job startet foer 29/9 — er kommandoens foerste
            # linje den aerlige faldback. Id'et baeres separat og staar kun
            # i tooltip + aria-label.
            "navn": titel or kommando or "(baggrunds-shell)",
            "kommando": kommando,
            # Titlen baeres ogsaa raa videre: `navn` falder tilbage paa
            # kommandoen, og en forbruger skal kunne se forskel paa «Jarvis
            # gav den et navn» og «vi viser kommandoen i mangel af bedre».
            "titel": titel,
            # T = standset af et signal. Den kommer GRATIS med i `ps -o stat=`
            # og skulle ellers gaettes.
            "status": "paused" if st == "T" else ("running" if levende else "exited"),
            "pid": _tal(pid),
            "sekunder": max(0, int(nu - _tal(start))) if _tal(start) else None,
            "exit_code": _tal(rc) if rc.strip() else None,
            "can_pause": levende,
        })
    return jobs


class BroTier(RuntimeError):
    """Broen svarede ikke — vi VED ikke hvad der kører på operatørens maskine."""


def _tal(v: Any) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return 0


def _sekunder(v: Any) -> int:
    """Sekunder der kan komme som float.

    `_tal` er til heltalsfelter og svarer 0 på «12.4», fordi `int("12.4")`
    rejser. Operator-sessionernes `idle_s` er netop `round(..., 1)`, så en
    session der havde ligget 12,4 sekunder ville stå som 0 — et tavst nul der
    lignede en helt frisk session.
    """
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):  # ikke et tal — 0 betyder «ukendt», ikke fejl
        return 0


def _supervisor_jobs() -> list[dict[str, Any]]:
    from core.services.process_supervisor import list_processes
    ud = list_processes(include_stopped=True)
    jobs = []
    for p in ud.get("processes") or []:
        sek = p.get("uptime_seconds")
        jobs.append({
            "id": str(p.get("name") or ""),
            "kilde": "supervisor",
            "navn": str(p.get("name") or ""),
            "kommando": str(p.get("command") or ""),
            "status": str(p.get("status") or ""),
            "pid": p.get("pid"),
            "sekunder": int(sek) if isinstance(sek, (int, float)) else None,
            "exit_code": p.get("exit_code"),
            # 3/10-2026: `stopped_at` med, fordi registret er et ARKIV uden
            # oprydning — processer fra maj ligger side om side med dem der
            # døde i dag. Uden et tidspunkt kan en læser ikke skelne dem, og
            # en vagtpost ville melde en proces der døde for fire måneder
            # siden som om den lige var færdig.
            "stopped_at": p.get("stopped_at"),
            "can_pause": bool(p.get("can_pause")),
        })
    return jobs


#: Scout-agentens tool-policies (`simple_tools_explore._explore_spawn`).
_SCOUT_POLICIES = frozenset({"read-only-runtime", "read-only-workstation"})
_AGENT_AKTIV = frozenset({"planned", "queued", "starting", "running", "active", "waiting"})
#: Hvor længe en FÆRDIG scout står under «Færdige». Den kan ikke ryddes
#: herfra (der er intet at slette — den er en række i registret), så den
#: skal ældes ud af sig selv i stedet for at hobe sig op.
_SCOUT_FAERDIG_VINDUE_S = 3600


def _iso_ts(v: Any) -> float | None:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _scout_jobs() -> list[dict[str, Any]]:
    """Scout-agenter der kører — og dem der blev færdige den seneste time."""
    from core.runtime.db_agent_runtime import list_agent_registry_entries
    nu = _nu()
    jobs: list[dict[str, Any]] = []
    for a in list_agent_registry_entries(include_completed=True, limit=200):
        if str(a.get("role") or "") != "researcher":
            continue
        if str(a.get("tool_policy") or "") not in _SCOUT_POLICIES:
            continue
        status = str(a.get("status") or "")
        start = _iso_ts(a.get("created_at"))
        aktiv = status in _AGENT_AKTIV
        slut = None if aktiv else (_iso_ts(a.get("completed_at")) or _iso_ts(a.get("updated_at")))
        if not aktiv and (slut is None or nu - slut > _SCOUT_FAERDIG_VINDUE_S):
            continue
        maal = str(a.get("goal") or "").strip().splitlines()
        emne = maal[0] if maal else ""
        # B (Bjørn 29/9-2026): spoergsmaalet ER titlen — «Scout-agent» siger
        # hvad den ER, ikke hvad den laver. Rollen flytter i tooltip.
        rolle = "Scout-agent" + (
            " · din maskine" if a.get("tool_policy") == "read-only-workstation" else "")
        jobs.append({
            "id": str(a.get("agent_id") or ""),
            "kilde": "agent",
            "navn": emne[:120] or "(scout)",
            "kommando": rolle,
            "status": "running" if aktiv else "exited",
            "pid": None,
            "sekunder": int(((nu if aktiv else slut) or nu) - start) if start else None,
            # «failed» er en fejl og skal blive stående under «Kører»-filteret
            # (_skal_vises); en annulleret eller udløbet scout er ikke gået galt.
            "exit_code": None if aktiv else (1 if status == "failed" else 0),
            "can_pause": False,
        })
    return jobs


#: Hvor mange events kilden læser bagud. Målt 3/10-2026: 2.000 rækker koster
#: ~7 ms inkl. JSON-parse, og panelet henter hvert 5. sekund — så det er
#: gratis. Vinduet skal kunne rumme et LANGT kald: kører der en bygning eller
#: en fuld testsuite i femten minutter mens hundredevis af andre kald passerer,
#: skal dens `tool.invoked` stadig være inden for rækkevidden.
_TOOL_VINDUE = 2000

#: Hvor længe et kald uden parret `tool.completed` må stå som «kører».
#: Et kald der aldrig fik sit svar — fx fordi processen blev genstartet midt i
#: det — ville ellers stå som kørende for evigt. Det er en TIDSGRÆNSE, ikke en
#: påstand om at kaldet lever.
_TOOL_SPOEGER_VINDUE_S = 1800


def _tool_jobs() -> list[dict[str, Any]]:
    """Værktøjskald fra et model-run — dem der kører lige nu.

    Panelet kendte indtil 3/10-2026 kun BEHOLDERE: supervisor-processer, åbne
    shells og scout-agenter. Et `bash`-kald er en kommando INDE i en shell —
    den kører, svarer og forsvinder, og der blev aldrig skrevet en række.
    Claude Desktop viser hvert kald med titel og ur; her var de usynlige.
    (Bjørn 3/10-2026: «alle hans opgaver/bash commandoer bliver vist i
    baggrunds panelet... det sker ikk på vores?»)

    Kilden læser de to events runtime ALLEREDE udgiver ved hvert kald og
    parrer dem på `tool_use_id`. Uparret = kører stadig. Der er intet nyt at
    føre bog over: begge events har ligget i `events` hele tiden.

    ## Hvorfor kun kald med et `run_id`

    Et kald fra et model-run bærer `run_id` (sat af `simple_tool_executor`).
    UI'ets EGNE bro-kald gør ikke: panelets eget poll af `/api/jobs` kalder
    `operator_bash` gennem `execute_tool` uden om executoren, og hverken run
    eller session følger med. Målt 3/10-2026: **151 af 152** `operator_bash`-
    kald i et kvarters events var netop dét poll — ét hvert femte sekund.

    Uden reglen ville panelet vise sig selv. Med den viser det Jarvis' arbejde
    og ikke sin egen puls. Det er også derfor kilden ikke kræver at nogen
    markerer deres kald: skellet findes allerede i data.

    ## Hvad den ikke viser

    Et kald der er FÆRDIGT forsvinder — også når det gik galt. Det er med
    vilje: fejlen står i samtalen, hvor man kan læse hvad der skete, og et
    panel der samlede fejl op ville vokse uden grænse. Det panel viser er
    «hvad kører NU», og det er dét man åbner det for.
    """
    from core.runtime.db import connect
    from core.tools.tool_call_telemetry import UKENDT

    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, payload_json, created_at
                FROM events
                WHERE kind IN ('tool.invoked', 'tool.completed')
                ORDER BY id DESC
                LIMIT ?
                """,
                (_TOOL_VINDUE,),
            ).fetchall()
    except Exception:
        logger.warning("background_jobs: kunne ikke laese tool-events", exc_info=True)
        return []

    # Nyeste foerst fra SQL; parringen skal gaa kronologisk.
    rows.reverse()

    aabne: dict[str, dict[str, Any]] = {}
    for event_id, kind, payload, created in rows:
        try:
            d = json.loads(payload)
        except Exception:
            continue  # en enkelt ulaesbar raekke maa ikke tage hele listen
        if kind == "tool.invoked":
            run_id = str(d.get("run_id") or "")
            if not run_id or run_id == UKENDT:
                continue  # UI-plumbing, ikke et model-run
            args = d.get("arguments") or {}
            noegle = str(args.get("_runtime_tool_use_id") or "")
            if not noegle:
                # Uden kald-id kan to kald ikke skelnes. Raekkefoelgen er den
                # eneste rest — den bruges, og raekkens eget id goer noeglen unik.
                noegle = f"{d.get('tool')}#{event_id}"
            aabne[noegle] = {
                "tool": str(d.get("tool") or ""),
                "args": args,
                "start": _iso_ts(created),
            }
            continue
        # tool.completed — luk det kald den hoerer til.
        kald_id = str(d.get("tool_use_id") or "")
        if kald_id and kald_id in aabne:
            aabne.pop(kald_id, None)
            continue
        # Ældre completed-events (foer 3/10-2026) bar intet id. De parres paa
        # værktøjsnavn i rækkefølge — upræcist naar to kald af samme værktøj
        # kører samtidig, men bedre end at lade dem stå som kørende for evigt.
        for k, v in list(aabne.items()):
            if v["tool"] == d.get("tool"):
                aabne.pop(k, None)
                break

    nu = _nu()
    jobs: list[dict[str, Any]] = []
    for v in aabne.values():
        start = v["start"]
        if start is None or nu - start > _TOOL_SPOEGER_VINDUE_S:
            continue
        tool = v["tool"]
        args = v["args"]
        # Titel er hvad kaldet LAVER — den beskrivelse Jarvis selv skriver til
        # det. Uden den er kommandoen den aerlige faldback, og værktøjets navn
        # den sidste.
        titel = str(args.get("description") or args.get("titel") or "").strip()
        kommando = str(args.get("command") or "").strip()
        jobs.append({
            "id": f"{tool}#{int(start)}",
            "kilde": "tool_operator" if tool.startswith("operator_") else "tool",
            "navn": titel or kommando[:120] or tool,
            # Samme form som shell-kortet: værktøj og kommando i tooltip.
            "kommando": f"{tool} · {kommando[:200]}" if kommando else tool,
            "status": "running",
            "pid": None,
            "sekunder": max(0, int(nu - start)),
            "exit_code": None,
            # Et kald inde i et run kan hverken pauses eller stoppes udefra —
            # det ville rive turen i stykker. Panelet skal ikke tilbyde en knap
            # der ikke kan holde hvad den lover.
            "can_pause": False,
            "can_stop": False,
        })
    return jobs


def _default_bash_sid() -> str:
    """Id'et på den DELTE shell som det almindelige `bash`-værktøj bruger.

    Målt 26/9-2026: `simple_tools_web._default_bash_session()` åbner én
    vedvarende session og genbruger den til hvert `bash`-kald. Den står derfor
    i daemonens liste side om side med de sessioner der er åbnet MED VILJE via
    `bash_session_open` — og de to skal ikke se ens ud i panelet: et stop på
    arbejds-shellen smider Jarvis' `cd`, env og venv væk midt i en opgave
    (den genåbnes ved næste kald, men tilstanden er tabt).

    Samme proces-forbehold som operator-sessionerne: globalen lever i den
    proces der kører værktøjet. Kan den ikke læses, falder kortet tilbage til
    den neutrale tekst frem for at gætte.
    """
    try:
        from core.tools import simple_tools_web
        return str(simple_tools_web._DEFAULT_BASH_SESSION_ID or "")
    except Exception:
        logger.debug("background_jobs: default-bash-sessionen kunne ikke laeses",
                     exc_info=True)
        return ""


def _shell_kort(sid: str, *, egen_maskine: bool, idle: int, cwd: str = "",
                arbejds_shell: bool = False, koerer: str = "",
                titel: str = "") -> dict[str, Any]:
    """Ét kort for en åben shell — samme form som de øvrige kilder.

    Teksten siger hvad tallet ER, og de to kilder er ikke ens:

    ``bash_session``
        `_Session.run` sætter `last_used` ved kommandoens START, så tallet er
        tiden siden sidste kommando blev startet. Kører der en lige nu, ER
        tallet dens hidtidige køretid — samme betydning som i panelets øvrige
        rækker.

    ``operator_bash_session``
        `last` sættes EFTER kaldet er vendt tilbage, så tallet er tiden siden
        sidste kommando sluttede. Kører der en, står tallet stille og tæller
        stadig fra den forrige.

    Det stod «intet kører · tiden er tomgang» i første udgave. Begge halvdele
    var påstande jeg ikke havde målt: daemonen er tråd-per-forbindelse, så
    `list` besvares MENS en kommando kører, og `list` fortæller ikke om
    sessionen er optaget.
    """
    hvor = f" i {cwd}" if cwd and cwd != "~" else ""
    siden = "sidste kommando sluttede" if egen_maskine else "sidste kommando startede"
    hvad = "Jarvis' arbejds-shell" if arbejds_shell else "åben shell"
    # Kører der noget, ER tallet kommandoens køretid (`last_used` sættes ved
    # dens start), og så siger linjen hvad der kører — som i panelets øvrige
    # rækker. Det kunne den ikke før 26/9-2026: `list` svarede det samme
    # uanset, så kortet påstod «intet kører» uden at kunne vide det.
    linje = f"kører: {koerer}" if koerer else f"{hvad}{hvor} · tiden er siden {siden}"
    # B (Bjørn 29/9-2026): linje 1 er TITLEN — hvad shellen laver lige nu,
    # eller hvad den ER naar den venter. Id'et er ude af raekken og staar kun
    # i tooltip + aria-label. Den fulde linje (hvor + hvad tallet betyder)
    # ligger i `kommando`, som panelet viser i `title`.
    # Titlen skrives naar sessionen AABNES (`bash_session_open`), ligesom
    # baggrunds-jobbenes. Mangler den, er «kører: …» den aerlige faldback —
    # og «aaben shell» naar der ikke koerer noget.
    navn = titel or (f"kører: {koerer}" if koerer else hvad)
    return {
        "id": sid,
        "navn": navn,
        # To kilder, ikke én med maskinen gemt i navnet: i den eksisterende
        # kontrakt svarer `kilde` netop på HVILKEN maskine, og det er dét
        # panelets linje 2 viser. Én fælles kilde ville gøre den linje stum.
        "kilde": "shell_operator" if egen_maskine else "shell",
        "kommando": linje,
        "status": "running",
        "pid": None,
        "sekunder": max(0, int(idle)),
        "exit_code": None,
        # `close` dræber shellen. Der findes ingen pause.
        "can_pause": False,
    }


def _lokale_shell_sessioner() -> list[dict[str, Any]]:
    """Åbne `bash_session`-shells — KUN hvis daemonen allerede kører.

    `_exec_bash_session_list` går gennem `_ensure_daemon_running()`, som
    STARTER daemonen når den er væk. Et panel der poller hvert femte sekund
    ville dermed skabe den proces det påstod at observere. Derfor spørges der
    først når pid-filen peger på en ægte daemon; ellers er svaret den tomme
    liste, hvilket er sandt: ingen daemon, ingen sessioner.

    Tilbage står én bivirkning, og den skal stå skrevet frem for at blive
    opdaget: daemonens selv-nedlukning kræver `last_activity` ældre end en
    time OG nul sessioner, og ENHVER forespørgsel — også `list` — nulstiller
    uret. Så længe panelet er åbent, lukker en session-løs daemon altså ikke
    ned af sig selv. Panelet henter kun mens det er åbent, så virkningen
    holder op når man lukker det.
    """
    from core.tools.bash_session import (
        _exec_bash_session_list,
        _pid_is_our_daemon,
        _read_daemon_pid,
    )
    pid = _read_daemon_pid()
    if pid is None or not _pid_is_our_daemon(pid):
        return []
    svar = _exec_bash_session_list({})
    if str(svar.get("status") or "") != "ok":
        raise RuntimeError(str(svar.get("error") or "daemonen svarede ikke"))
    ud = []
    arbejds = _default_bash_sid()
    for s in svar.get("sessions") or []:
        # En doed session udelades. Daemonen beholder den i sin dict til den
        # reapes, men en lukket shell er ikke et baggrundsjob: der er intet
        # at stoppe, og panelet viser ikke stop-knappen paa noget faerdigt.
        # Den ville staa under «Faerdige» og hverken kunne ryddes eller
        # handles paa.
        if not s.get("alive"):
            continue
        sid = str(s.get("session_id") or "")
        if not sid:
            continue
        # Jarvis' arbejds-shell vises IKKE. Daemonen maerker den ved
        # fødselen (`arbejde=True`), saa det gaelder ogsaa de shells
        # tidligere procesgenerationer efterlod — foer blev de sammenlignet
        # med en PROCES-GLOBAL, og hver genstart slap en ny raekke «aaben
        # shell» igennem (maalt 29/9-2026: fire). Sammenligningen med
        # globalen staar tilbage som faldback for en daemon der er aeldre
        # end maerkningen.
        if s.get("arbejde") or sid == arbejds:
            continue
        ud.append(_shell_kort(
            sid, egen_maskine=False,
            idle=_sekunder(s.get("idle_seconds")),
            arbejds_shell=False,
            titel=str(s.get("titel") or ""),
            # Mangler feltet, er daemonen ældre end 26/9-2026 og kan ikke
            # svare på spørgsmålet. Så siger kortet det ikke.
            koerer=str(s.get("command") or "") if s.get("busy") else "",
        ))
    return ud


def _operator_shell_sessioner() -> list[dict[str, Any]]:
    """Åbne `operator_bash_session`-shells på Bjørns maskine.

    `_SESSIONS` er en dict i PROCESSENS hukommelse, ikke en daemon. Målt
    26/9-2026 på CT105: en frisk proces så en tom liste i samme øjeblik som
    `bash_session`-daemonen havde `bsh-115cd823bf` åben. Listen her dækker
    derfor kun sessioner åbnet i SAMME proces som den der svarer — API-
    processen, der betjener den synlige samtale. Åbner han en session under
    en autonom kørsel (jarvis-runtime, en anden proces), er den usynlig her.

    Det er en halv sandhed, men en afgrænset og målt en. Alternativet — at
    flytte sessionerne ud af processen — er en ændring af selve værktøjet, og
    de to filer skal stå urørt.
    """
    from core.tools.operator_bash_session import _exec_operator_bash_session_list
    svar = _exec_operator_bash_session_list({})
    if str(svar.get("status") or "") != "ok":
        raise RuntimeError(str(svar.get("error") or "operator-sessionerne svarede ikke"))
    ud = []
    for s in svar.get("sessions") or []:
        sid = str(s.get("session_id") or "")
        if not sid:
            continue
        ud.append(_shell_kort(
            sid, egen_maskine=True, idle=_sekunder(s.get("idle_s")),
            cwd=str(s.get("cwd") or ""),
            titel=str(s.get("titel") or ""),
        ))
    return ud


def _shell_sessioner() -> list[dict[str, Any]]:
    """Begge slags åbne shells. Den ene kilde må ikke kunne tie den anden."""
    jobs: list[dict[str, Any]] = []
    for navn, fn in (("lokale", _lokale_shell_sessioner),
                     ("operator", _operator_shell_sessioner)):
        try:
            jobs += fn()
        except Exception:
            logger.warning("background_jobs: %s shell-sessioner kunne ikke laeses",
                           navn, exc_info=True)
    return jobs


def liste(*, uid: str = "", exec_fn=None, kun_aktive: bool = True) -> dict[str, Any]:
    """Alle jobs fra alle kilder.

    `kun_aktive` fjerner det der er FÆRDIGT — Bjørn: «de skal automatisk
    forsvinde når opgave er fuldført». Et job der fejlede bliver derimod
    stående: det er ikke fuldført, det er gået galt, og det er netop dem man
    skal se. Et panel der altid er tomt bliver et panel man holder op med at
    åbne.
    """
    jobs = _supervisor_jobs()
    jobs += _shell_sessioner()
    try:
        jobs += _scout_jobs()
    except Exception:
        # Registret er en tilføjelse til panelet, ikke dets fundament: fejler det,
        # skal supervisor- og operator-jobbene stadig vises.
        logger.warning("background_jobs: kunne ikke læse scout-agenter", exc_info=True)
    try:
        jobs += _tool_jobs()
    except Exception:
        # Samme afvejning som scout-registret: de øvrige kilder skal stå, selv
        # om værktøjssporet ikke kan læses.
        logger.warning("background_jobs: kunne ikke laese tool-kald", exc_info=True)
    bro_ok = True
    if exec_fn is not None:
        try:
            jobs += _operator_jobs(uid, exec_fn)
        except Exception as exc:
            bro_ok = False
            logger.debug("background_jobs: operator-siden svarede ikke: %s", exc)
    if kun_aktive:
        jobs = [j for j in jobs if _skal_vises(j)]
    # Koerende foerst, derefter laengst koerende oeverst. Det man skal gribe
    # ind i staar oeverst; det der bare koerer og koerer staar under.
    jobs.sort(key=lambda j: (j["status"] == "exited", -(j.get("sekunder") or 0)))
    return {"jobs": jobs, "bridge_ok": bro_ok}


def _skal_vises(job: dict[str, Any]) -> bool:
    """Kører den, eller gik den galt?

    En afsluttet opgave forsvinder — men KUN hvis den lykkedes. `exit_code`
    forskellig fra 0 er ikke «fuldført», og at skjule den ville betyde at en
    fejl bare stille forsvandt.
    """
    if job.get("status") in ("running", "paused"):
        return True
    kode = job.get("exit_code")
    return kode is not None and int(kode) != 0
