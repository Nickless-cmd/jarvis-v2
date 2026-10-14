#!/usr/bin/env python3
"""Detektor for ture der ender uden assistent-svar ("tavse cutoffs").

FLYTTET IND I REPOET 14/10-2026
--------------------------------
Scriptet levede fra 30/8 til 14/10 som `/usr/local/sbin/jarvis-cutoff-detector.py`
— uden for git, uden test, usynligt for enhver der laeste koden. Men det skrev
til `central_incidents`, altsaa til Centralen. Maalt 14/10: 307 fund i alt, og
ingen kunne se hvad der skrev dem; jeg ledte selv i repoet fire gange og
konkluderede fejlagtigt "skriveren er ufundet", fordi et instrument uden for
repoet er usynligt for kode-grep.

Det hoerer her. `scripts/` scannes af `api_docs_gen`, importeres direkte i tests,
og baerer i forvejen `silent_chain_verify.py` — samme slags bagud-maaling.

TRE BLINDE PLETTER RETTET SAMME DAG (alle maalt, ikke gaettet)
--------------------------------------------------------------
1. `api_restarted_near` svarede "nej (stroemmen doede)" VED KONSTRUKTION.
   Den ledte efter systemds besked `Started jarvis-api`, som `bs` ikke kunne se.
   Kommentaren paastod at `bs` hverken var i `adm` eller `systemd-journal` —
   det er ikke laengere sandt: gruppen `systemd-journal` (gid 999) blev tilfoejet
   senere, og `bs` ER medlem nu (maalt 14/10: `id` viser `999(systemd-journal)`,
   og journalen giver 9 traef paa baade `Started jarvis-api` og uvicorns
   `Started server process` over 24 timer). Fejlen var altsaa selvhelet —
   men koden kunne ikke SELV se forskel, og ville blive tavst blind igen hvis
   gruppen forsvandt. Den svarer nu `None` ("ved ikke") naar journalen ikke kan
   laeses. Fravaer af svar maa aldrig bekraeftes som svar.
2. "sidste kald '2026-10-09'" var en DATO, ikke et vaerktoejsnavn. Raekkens
   format er `[tool_result:<id>]\\n[<navn>]: …` — med et LINJESKIFT mellem
   klammerne. Parserens `"] ["` fandt ingen i headeren og gled ned i selve
   resultatet, hvor den greb den foerste `] [` den kunne finde. Parseren ligger
   nu i `sidste_vaerktoej()`, er ankret til starten, og har en test.
3. FALSK POSITIV: et run der svarede — bare i en ANDEN session. Detektoren
   maalte assistent-svar i runnets EGEN session. Men `auto-recurring-*` er
   recurring-opgavernes FAELLES auto-session, og baade morgenmedicinen og
   morgenbriefen leverede deres svar gennem `notify_user` til Bjorns samtale.
   Sessionen fik derfor kun `tool`-raekker, og detektoren saa en tavs tur der
   ikke var tavs. Maalt 14/10: begge nats fund (04:20 og 05:05) var falske —
   begge runs staar `completed` i `visible_runs` (44 og 63 s, tom `error`).
   Rettelsen hviler paa den VARIGE kobling run -> session, som er
   `events.kind = 'runtime.autonomous_run_started'` (baerer baade `run_id` og
   `session_id`). `visible_runs` har ingen `session_id`-kolonne, og
   `run_event_log.session_for_run` er in-memory og kan ikke bruges af et
   script. Ligger sessionens sidste besked INDE i et `completed`-run uden fejl
   for NETOP denne session, springes fundet over.

HVORFOR DEN FINDES (30-08-2026)
--------------------------------
Jarvis blev gentagne gange kappet midt i en tur — og INTET sted fangede det:
`visible_runs` fik ingen raekke, runtime-journalen intet spor, `central_incidents`
intet. Koerslen bliver nemlig ikke *fejlet*, den bliver **kasseret**: dens levetid er
bundet til klientens socket, og der findes hverken `is_disconnected` eller
`CancelledError` nogen steder i `apps/api/jarvis_api/`. Forsvinder klienten et
oejeblik, doer turen tavst.

Udelukket ved maaling samme dag: det er IKKE kontekst-bloat (~38k tokens, tool-results
225-699 tegn) og IKKE runde-cap (17 kald brugt, cap er 100, en tidligere tur i samme
session brugte 137). Og det er *tilfaeldigt* — hvilket i sig selv udelukker enhver
deterministisk graense.

DENNE DETEKTOR RETTER INTET. Den goer det usynlige synligt: den observerer kun
resultatet i chat_messages og roerer ikke stream-vejen. Naar den naeste tur bliver
kappet, staar der hvornaar, i hvilken session, hvor mange vaerktoejskald den naaede,
hvad det sidste kald var, og om api'et blev genstartet omkring tidspunktet (som
skelner "processen doede" fra "stroemmen doede").

Brug:
    python scripts/cutoff_detector.py
    JARVIS_CUTOFF_DB=/tmp/kopi.db python scripts/cutoff_detector.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Repo-roden udledes af filens placering frem for at vaere hardcodet: systemd
# saetter PYTHONPATH, men et script der selv ved hvor det bor kan flyttes.
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# JARVIS_CUTOFF_DB lader detektoren testes mod en KOPI af databasen, saa man
# aldrig behoever skrive kunstige raekker ind i den rigtige chat-historik.
DB = os.environ.get("JARVIS_CUTOFF_DB") or os.path.expanduser("~/.jarvis-v2/state/jarvis.db")
STATE = os.environ.get("JARVIS_CUTOFF_STATE") or os.path.expanduser("~/.jarvis-v2/state/cutoff-detector-seen.json")
LOG = os.path.expanduser("~/.jarvis-v2/logs/cutoff-detector.log")

# En tur er "strandet" naar sidste besked er tool/user og der er gaaet saa lang tid
# at et svar burde vaere kommet. 180 s er rundhaandet: enkelte vaerktoejskald tager
# et minut, men tre minutters tavshed efter et tool-resultat er ikke normalt.
STALE_SECONDS = 180
# Kig kun paa aktivitet det seneste doegn — aeldre strandede ture er historik.
LOOKBACK_HOURS = 24

# Journalen kan naegte os indsigt. Det sker som en ADVARSEL paa stderr, mens
# exit-koden stadig er 0 og uddata er tom — altsaa praecis den form hvor et
# "kunne ikke laese" nemt forveksles med et "leste, intet fundet".
_INGEN_JOURNALADGANG = "not seeing messages from other users"


def log(msg: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(f"{datetime.now(UTC).isoformat()} {msg}\n")


def load_seen() -> set[str]:
    try:
        return set(json.load(open(STATE)))
    except Exception:  # state-filen kan mangle eller vaere halvskrevet — tom liste
        return set()


def save_seen(seen: set[str]) -> None:
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        tmp = STATE + ".tmp"
        json.dump(sorted(seen)[-500:], open(tmp, "w"))
        os.replace(tmp, STATE)
    except Exception:  # best-effort: uskrivbar state maa ikke vaelte detektoren
        pass


def sidste_vaerktoej(content: str) -> str:
    """Vaerktoejsnavnet fra en `tool`-raekkes content — eller "-".

    FORMATET ER MAALT (14/10-2026), ikke gaettet. Raekken ser saadan ud:

        [tool_result:tool-result-96aeff7b806641f5a8d9e34277d1330c]
        [send_ntfy]: Beskeden er leveret til din enhed.

    Der er et LINJESKIFT mellem `]` og `[send_ntfy]:` — ikke et mellemrum.
    Den foerste udgave soegte efter `"] ["`, fandt ingen i headeren, og gled
    derfor ned i selve RESULTATET, hvor den greb den foerste `] [` den kunne
    finde. Maalt konsekvens: fundet kl. 05:04:35 skrev "sidste kald
    '2026-10-09'" — en DATO fra et resultat langt inde i indholdet.

    Ankret til starten med `\\s*` mellem klammerne, saa baade linjeskift- og
    mellemrums-varianten rammes, og et `] [` inde i resultatet ikke kan vinde.
    """
    m = re.match(r"\s*\[[^\]]*\]\s*\[([^\]]{1,80})\]\s*:", str(content or ""))
    if not m:
        return "-"
    # Et logformat med én linje pr. fund maa aldrig kunne braekkes af sit eget
    # indhold (maalt 11/9-2026: et navn med linjeskift delte posten i to).
    return " ".join(m.group(1).split())[:40] or "-"


def til_utc(tekst: object) -> datetime | None:
    """ISO-tidsstreg -> tz-aware datetime, eller None hvis den er ulaesbar.

    Udskilt 14/10-2026: moensteret (parse, og saet UTC hvis tidszonen mangler)
    stod tre steder med hver sin `try/except`. `None` er et aerligt svar her —
    "ved ikke" — og kalderen vaelger selv om posten skal springes over eller
    beholdes med den vaerdi den havde. At gaette en tid ville skrive et forkert
    tal ind i Centralen.
    """
    try:
        t = datetime.fromisoformat(str(tekst))
    except (TypeError, ValueError):  # ikke en ISO-tid => "ved ikke", ikke et gaet
        return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t


def api_restarted_near(when: datetime) -> bool | None:
    """Blev jarvis-api genstartet omkring tidspunktet?

    Skelner "processen doede" fra "stroemmen doede" — to helt forskellige fejl
    med samme symptom. Svarer `True`/`False`, eller `None` naar journalen ikke
    kunne laeses: fravaer af svar maa ikke bekraeftes som svar.

    Historikken er vaerd at kende. Kommentaren her stod i den eksterne udgave
    og paastod at skelnen returnerede "nej" VED KONSTRUKTION, fordi `bs` ikke
    var i `adm` eller `systemd-journal`:

        Maalt over 24 timer i den journal vi FAKTISK kan laese:
            "Started jarvis-api"       0
            "Stopped jarvis-api"       0
            "systemd"                  0
            "Started server process"  64   <- uvicorns egen stdout

    Det var sandt den 11/9-2026. Det er ikke sandt nu: `bs` er medlem af
    `systemd-journal` (gid 999), og samme maaling giver 9 traef paa BEGGE
    moenstre over 24 timer (verificeret 14/10). Koden kunne bare ikke selv se
    forskel — og ville blive tavst blind igen hvis gruppen forsvandt. Derfor
    tjekker den nu eksplicit om journalen naegtede adgang.
    """
    try:
        lo = (when - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
        hi = (when + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
        p = subprocess.run(
            ["journalctl", "-u", "jarvis-api", "--since", lo, "--until", hi,
             "--no-pager", "-o", "cat"],
            capture_output=True, text=True, timeout=20)
        if _INGEN_JOURNALADGANG in (p.stderr or ""):
            return None
        if p.returncode != 0:
            return None
        # `Started jarvis-api` er systemds EGEN besked; `Started server process`
        # er uvicorns stdout. Vi tager begge — den ene kan vaere skjult for os
        # mens den anden er der.
        return any(m in (p.stdout or "") for m in (
            "Started server process", "Finished server process",
            "Started jarvis-api", "Stopped jarvis-api"))
    except Exception:  # journalen kunne ikke spoerges => "ved ikke", ikke "nej"
        return None


def doede_runs_uden_svar(con, siden_ts: str) -> list[dict]:
    """Runs der DOEDE uden at naa at skrive noget.

    Detektoren laeser `chat_messages`. En tur der doer FOER sin foerste
    skrivning efterlader ingen besked at se paa - og er derfor usynlig for
    netop det instrument vi byggede til at fange den.

    Maalt 11/9-2026: fem ture doede paa `append_chat_message` ->
    `chat session not found`, 6-17 sekunder inde, alle foer den agentiske
    loekke. `visible_runs` baerer alle fem som `failed` med fejlstrengen.
    Detektoren saa nul. (Jarvis' fund.)
    """
    # SKEMAET, IKKE GAETTET. Foerste udgave spurgte efter `session_id` og
    # `error_message`; tabellen har hverken. Faldbacken slugte det, saa hver
    # post kom ud som "? :: ... fejl: (ingen)" - et fund uden indhold, hvilket
    # er praecis den slags tomme bekraeftelse vi har jaget hele natten.
    #   visible_runs: id run_id lane provider model status started_at
    #                 finished_at text_preview error capability_id user_id
    #                 workspace_name
    try:
        rows = con.execute(
            "SELECT run_id, status, started_at, error, lane, provider, model "
            "FROM visible_runs WHERE started_at > ? AND status IN ('failed','cancelled') "
            "ORDER BY started_at DESC LIMIT 40", (siden_ts,)).fetchall()
    except Exception:  # skema-drift: hellere nul fund end at vaelte hele koerslen
        return []
    ud = []
    for r in rows:
        d = dict(r)
        ud.append({
            "run_id": str(d.get("run_id") or ""),
            "lane": str(d.get("lane") or ""),
            "model": f"{d.get('provider') or '?'}/{d.get('model') or '?'}",
            "status": str(d.get("status") or ""),
            "fejl": " ".join(str(d.get("error") or "").split())[:160],
            "started_at": str(d.get("started_at") or ""),
        })
    return ud


def turen_koerer_stadig(con, sid: str) -> bool | None:
    """Er der et LEVENDE visible-run for denne session lige nu?

    Detektoren kunne ikke skelne "turen koerer stadig" fra "turen blev kappet".
    Den saa kun at sidste `chat_messages`-raekke var `tool`/`user` og aeldre end
    STALE_SECONDS - og en tur midt i et langt vaerktoejskald opfylder praecis
    det. De tre nyeste fund i loggen (7, 12 og 17 vaerktoejskald) var netop
    saadanne ture; de blev aldrig kappet.

    `visible_runs.active_run` friskes ved hvert kald, saa raekkens `updated_at`
    er et paalideligt livstegn - uafhaengigt af hvordan nyttelasten er formet.
    """
    try:
        r = con.execute(
            "SELECT value_json, updated_at FROM runtime_state_kv WHERE key = ?",
            ("visible_runs.active_run",)).fetchone()
        if not r:
            return False
        data = json.loads(r["value_json"] or "{}") or {}
        if not data.get("active"):
            return False
        # Hoejst ét aktivt visible-run ad gangen. Baerer nyttelasten en session,
        # skal den matche; goer den ikke, spaerrer vi kun paa friskhed.
        kendt = str(data.get("session_id") or "")
        if kendt and kendt != sid:
            # Noeglen holder ÉT run. Et samtidigt autonomt run kan have
            # overskrevet den, saa "en anden session er aktiv" udelukker IKKE
            # at DENNE ogsaa er levende. Det er uafgjort, ikke et nej.
            return None
        t = datetime.fromisoformat(str(r["updated_at"]))
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        return (datetime.now(UTC) - t).total_seconds() < STALE_SECONDS
    except Exception:
        # FOER: `return False` — en DB-hikke blev altsaa til et FUND, ikke til
        # "ved ikke". Det er praecis den sammenblanding vi fjernede fra
        # claim-guarden i nat: fravaer af svar maa ikke bekraeftes som svar.
        return None


def _genstart_dom(restarted: bool | None) -> str:
    """Teksten der gaar i fundet. `None` maa ikke lyde som et svar."""
    if restarted is True:
        return "JA (processen doede)"
    if restarted is False:
        return "nej (stroemmen doede)"
    return "KUNNE IKKE AFGOERES (journalen svarede ikke)"


def run_ids_pr_session(con, cutoff_ts: str) -> dict[str, list[str]]:
    """session_id -> [run_id] for autonome runs startet i vinduet.

    Koblingen run -> session findes ikke i `visible_runs` (ingen `session_id`-
    kolonne) og ikke i `run_event_log` (in-memory, doer med processen). Den
    findes i `events`, hvor `runtime.autonomous_run_started` baerer BEGGE id'er
    — og den tabel er varig og laeses paa tvaers af processer.

    Ét opslag for hele koerslen, ikke ét pr. session: indekset
    `idx_events_kind_created` goer det til ~5 ms for 35 raekker i doegnet.
    """
    ud: dict[str, list[str]] = {}
    try:
        rows = con.execute(
            "SELECT payload_json FROM events "
            "WHERE kind = 'runtime.autonomous_run_started' AND created_at > ?",
            (cutoff_ts,)).fetchall()
    except Exception:  # skema-drift: hellere ingen kobling end at vaelte koerslen
        return ud
    for r in rows:
        try:
            p = json.loads(r["payload_json"] or "{}") or {}
        except Exception:  # ulaesbar nyttelast: spring posten over, gaet ikke
            continue
        sid = str(p.get("session_id") or "")
        rid = str(p.get("run_id") or "")
        if sid and rid:
            ud.setdefault(sid, []).append(rid)
    return ud


def svar_leveret_eksternt(con, run_ids: list[str], tavs_ts: datetime) -> str | None:
    """Laa der et PAENT afsluttet run i denne session da den gik tavs?

    Returnerer run_id'et hvis ja — ellers None. "Paent afsluttet" er praecist:
    `status='completed'` OG tom `error`. Et `failed`/`cancelled`/`interrupted`
    run er IKKE et svar og maa ikke kunne daempe et fund.

    Tidskriteriet: sessionens sidste besked skal ligge INDE i runnets vindue
    [started_at, finished_at]. Maalt 14/10 rammer det begge nats falske fund
    praecist, uden tolerance — 04:15:28 i [04:14:28, 04:15:31] og 05:01:08 i
    [05:00:28, 05:01:12].
    """
    if not run_ids:
        return None
    pladsholdere = ",".join("?" * len(run_ids))
    try:
        rows = con.execute(
            f"SELECT run_id, status, error, started_at, finished_at FROM visible_runs "
            f"WHERE run_id IN ({pladsholdere})", run_ids).fetchall()
    except Exception:  # skema-drift: hellere intet svar end et gaettet
        return None
    for r in rows:
        if str(r["status"] or "").lower() != "completed":
            continue
        if str(r["error"] or "").strip():
            continue  # afsluttet MED fejl — ikke et svar
        start = til_utc(r["started_at"])
        slut = til_utc(r["finished_at"])
        if start is None or slut is None:
            continue
        if start <= tavs_ts <= slut:
            return str(r["run_id"])
    return None


def main() -> int:
    if not os.path.exists(DB):
        return 0
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    cutoff_ts = (datetime.now(UTC) - timedelta(hours=LOOKBACK_HOURS)).isoformat()

    sessions = [r[0] for r in con.execute(
        "SELECT DISTINCT session_id FROM chat_messages WHERE created_at > ?",
        (cutoff_ts,)).fetchall()]

    # Koblingen run -> session bygges ÉN gang for hele koerslen. Uden den kan vi
    # ikke se at et svar blev leveret i en anden session (docstring, plet 3).
    runs_pr_session = run_ids_pr_session(con, cutoff_ts)

    seen = load_seen()
    found = 0

    # DEN ANDEN KLASSE: runs der doede foer deres foerste skrivning. De har
    # ingen `chat_messages`-raekke, saa loekken nedenfor kan ikke se dem.
    for _d in doede_runs_uden_svar(con, cutoff_ts):
        _key = f"vr:{_d['run_id']}"
        if _key in seen:
            continue
        seen.add(_key)
        found += 1
        log(f"{_d['run_id'][:28]} :: doedt run uden svar: {_d['status']} "
            f"({_d['lane']} {_d['model']}) start {_d['started_at'][11:19]}, "
            f"fejl: {_d['fejl'] or '(ingen fejlstreng gemt)'}")

    for sid in sessions:
        rows = con.execute(
            "SELECT message_id, role, content, created_at FROM chat_messages "
            "WHERE session_id = ? ORDER BY created_at DESC LIMIT 60", (sid,)).fetchall()
        if not rows:
            continue
        last = rows[0]
        if last["role"] == "assistant":
            continue  # turen sluttede pænt

        last_at = til_utc(last["created_at"])
        if last_at is None:
            continue  # ulaesbar tidsstreg: spring posten over, gaet ikke
        age = (datetime.now(UTC) - last_at).total_seconds()
        if age < STALE_SECONDS:
            continue  # kan stadig vaere i gang

        key = f"{sid}:{last['message_id']}"
        if key in seen:
            continue

        _levende = turen_koerer_stadig(con, sid)
        if _levende is True:
            continue   # den er i gang - ikke kappet

        # Svarede et run i DENNE session — bare et andet sted hen? Saa er den
        # manglende assistent-raekke det RIGTIGE udfald, ikke en kappet tur.
        if svar_leveret_eksternt(con, runs_pr_session.get(sid, []), last_at):
            continue

        # Forensik: hvor langt naaede turen?
        tools = 0
        started = last_at
        last_tool = "-"
        for r in rows:  # nyeste foerst
            if r["role"] == "tool":
                tools += 1
                if last_tool == "-":
                    last_tool = sidste_vaerktoej(r["content"])
            elif r["role"] == "user":
                # Turen startede her. Er tidsstegen ulaesbar, beholdes `last_at`
                # som start — den er sat foer loekken, saa `started` er bundet
                # uanset hvad, og en varighed paa 0s er aerligere end et gaet.
                fundet_start = til_utc(r["created_at"])
                if fundet_start is not None:
                    started = fundet_start
                break
        dur = int((last_at - started).total_seconds())
        restarted = api_restarted_near(last_at)

        msg = (f"tavs cutoff: turen endte uden assistent-svar efter {tools} værktøjskald "
               f"({dur}s), sidste kald '{last_tool}', tavs i {int(age)}s. "
               f"api-genstart omkring tidspunktet: {_genstart_dom(restarted)}"
               + ("" if _levende is not None
                  else ". LEVENDE TUR: KUNNE IKKE AFGØRES — dommen er svagere end den ser ud"))
        msg = " ".join(msg.split())
        log(f"{sid} :: {msg}")

        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="runtime", nerve="silent_cutoff", kind="turn_without_reply",
                severity="error", message=msg, session_id=sid, dedup=True)
        except Exception as e:  # aldrig lade detektoren vaelte noget
            log(f"kunne ikke skrive central incident: {e}")

        seen.add(key)
        found += 1

    save_seen(seen)
    if found:
        print(f"registreret {found} tavse cutoff(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
