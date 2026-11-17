"""`settle_agent_status` skal laese den besked der BAERER markeringen (26/10-2026).

MAALT 26/10-2026 paa `asg-bcbee979ef364037` (run-ccb6c74d81404103):

  * spawn bevarede den delvise leverance som `kind='result'` kl. 22:21:50.931
  * 1 ms senere skrev den `kind='failure'` kl. 22:21:50.932
  * opslaget tog den NYESTE besked inden for `kind IN ('result','')` — ramte
    `failure`-beskeden, som laa uden for filteret, og fik `None`
  * `full` blev tom → `partial_delivery_error` faldt tilbage paa
    `AGENT_FAILED`/`model`, selv om markeringen stod i `failure`-beskeden

Resultatet var to sandheder i samme koersel: `failure_reason` bar den aerlige
markering, mens `error_code`/`error_phase` pegede paa modellen. Den forkerte fase
er ikke kosmetik — den sender den naeste mig efter den gale aarsag.

Vagten laaser TRE ting, fordi en vagt der kun ser den ene vej goer systemet blindt:

  1. markeringen i `failure` naar udfaldet
  2. en `result`-besked UDEN markering bliver ikke til en falsk "delvis"
  3. en aegte fejl uden tekst er stadig `model`
"""

from __future__ import annotations

import sqlite3

import pytest

from core.runtime import db_agent_contract as dac


AGENT = "agent-vagt-settle"


def _opslag(conn: sqlite3.Connection) -> str:
    """Den RIGTIGE funktion — ikke en kopi af dens SQL.

    Foerste udgave kopierede SQL'en ind i testen. Den var groen baade foer og efter
    mutationen, fordi den maalte sin egen kopi. En test der gentager koden den
    vogter, beviser intet om koden.
    """
    return dac.latest_agent_reply(conn, AGENT)


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE agent_messages (message_id TEXT, agent_id TEXT, direction TEXT, "
        "kind TEXT, content TEXT, created_at TEXT)"
    )
    yield c
    c.close()


def _besked(c, kind: str, content: str, ts: str) -> None:
    c.execute(
        "INSERT INTO agent_messages VALUES (?,?,?,?,?,?)",
        (f"m-{kind}-{ts}", AGENT, "agent->jarvis", kind, content, ts),
    )


MARKERET = (
    "Agent afsluttede uden et brugbart resultat: "
    "UFULDSTÆNDIG (3 spørgsmål uden nummereret svar) — agentens tekst:\n"
    "Now line 54 shows the 5 properties: description, prompt, subagent_type, "
    "model, run_in_background."
)
RAA = (
    "Now line 54 shows the 5 properties: description, prompt, subagent_type, "
    "model, run_in_background."
)


def test_markeringen_i_failure_naar_udfaldet(conn):
    """Den maalte koersel: `result` (raa) skrives 1 ms FOER `failure` (markeret)."""
    _besked(conn, "result", RAA, "2026-10-26T22:21:50.931787Z")
    _besked(conn, "failure", MARKERET, "2026-10-26T22:21:50.932120Z")

    full = _opslag(conn)
    assert "UFULDSTÆNDIG" in full, "opslaget ramte den raa besked i stedet for markeringen"
    assert dac.partial_delivery_error(full=full, registry_status="failed") == (
        "AGENT_INCOMPLETE",
        "delivery",
    )


def test_raa_result_uden_markering_er_ikke_falsk_delvis(conn):
    """En `result`-besked alene maa ikke goeres til en delvis leverance."""
    _besked(conn, "result", RAA, "2026-10-26T22:21:50.931787Z")

    full = _opslag(conn)
    assert "UFULDSTÆNDIG" not in full
    assert dac.partial_delivery_error(full=full, registry_status="failed") == (
        "AGENT_FAILED",
        "model",
    )


def test_aegte_fejl_uden_tekst_er_stadig_model(conn):
    """Den anden vej: en rigtig fejl skal ikke pakkes ind som 'delivery'.

    17/11-2026: tabellen er SIDSTE udvej, ikke et udsagn om virkeligheden. Uden
    et run og uden en `last_error` findes intet bevis, og `AGENT_FAILED`/`model`
    er da det bedste gæt der findes. `settle_agent_status` sender begge kilder
    med, saa i drift vinder den observerede aarsag — se `_run_fejlkode`.
    """
    _besked(conn, "failure", "Connection reset by peer", "2026-10-26T22:21:50.932120Z")

    full = _opslag(conn)
    assert dac.partial_delivery_error(full=full, registry_status="failed") == (
        "AGENT_FAILED",
        "model",
    )


def test_ingen_besked_giver_tom_tekst(conn):
    """Uden beskeder er `full` tom — ikke en fejl, men heller ikke en leverance."""
    assert _opslag(conn) == ""
    assert dac.partial_delivery_error(full="", registry_status="failed") == (
        "AGENT_FAILED",
        "model",
    )


# ── 17/11-2026: dommen skal laese RUNNET, ikke kun tabellen ──────────────────
# Maalt paa de 65 fejlede assignments: 26 blev stemplet `AGENT_FAILED`/`model`
# mens runnet under dem bar en helt anden aarsag. Kun 2 af de 26 var aegte
# model-fejl. Vagten her maaler den RIGTIGE funktion mod en DB med de faktiske
# rækkeformer — ikke en kopi af dens SQL.

def _runs_db() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE agent_runs (run_id TEXT, assignment_id TEXT, status TEXT, "
        "error_code TEXT, error_phase TEXT, finished_at TEXT, attempt_no INTEGER)"
    )
    return c


def _run(c, run_id, aid, code, phase, finished, attempt):
    c.execute("INSERT INTO agent_runs VALUES (?,?,?,?,?,?,?)",
              (run_id, aid, "failed", code, phase, finished, attempt))


def test_run_koden_arves_naar_agentens_tekst_er_tom():
    """Den maalte fejl: tom tekst gjorde at tabellen vandt over runnet."""
    c = _runs_db()
    _run(c, "run-a", "asg-1", "LEASE_EXPIRED", "recovery", "2026-11-16T21:00:03Z", 1)
    kode, fase = dac._run_fejlkode(c, "asg-1")
    assert (kode, fase) == ("LEASE_EXPIRED", "recovery")
    assert dac.partial_delivery_error(
        full="", registry_status="failed",
        run_error_code=kode, run_error_phase=fase,
    ) == ("LEASE_EXPIRED", "recovery")


def test_orphan_markeren_skyder_ikke_den_aegte_aarsag_vaek():
    """`RUN_ORPHANED` skrives EFTER det ægte run og beskriver kun lukningen.

    Maalt paa `asg-d96dabe04904478c`: LEASE_EXPIRED kl. 21:00:03,
    orphan-markeren kl. 21:05:38. Uden sorteringen arvede vi meta-koden.
    """
    c = _runs_db()
    _run(c, "run-aegte", "asg-2", "LEASE_EXPIRED", "recovery", "2026-11-16T21:00:03Z", 1)
    _run(c, "agent-run-orphan", "asg-2", "RUN_ORPHANED", "recovery", "2026-11-16T21:05:38Z", 2)
    assert dac._run_fejlkode(c, "asg-2") == ("LEASE_EXPIRED", "recovery")


def test_kun_en_orphan_giver_stadig_orphan_koden():
    """Findes intet andet, er `RUN_ORPHANED` sandt nok — bedre end "model"."""
    c = _runs_db()
    _run(c, "agent-run-orphan", "asg-3", "RUN_ORPHANED", "recovery", "2026-11-16T19:19:56Z", 1)
    assert dac._run_fejlkode(c, "asg-3") == ("RUN_ORPHANED", "recovery")


def test_run_uden_kode_giver_tomme_felter():
    """Et run der ikke selv ved noget maa ikke opfinde en aarsag."""
    c = _runs_db()
    _run(c, "run-tom", "asg-4", "", "", "2026-11-16T19:19:56Z", 1)
    assert dac._run_fejlkode(c, "asg-4") == ("", "")
    assert dac._run_fejlkode(c, "findes-ikke") == ("", "")

FULL_TEXT = (
    "**Summary** — Jeg kunne verificere svar 3 med stor sikkerhed.\n\n"
    "**Findings**\n"
    "- Spørgsmål 3: Funktionen er defineret i agent_loop_core.py, linje 215.\n"
    "- Spørgsmål 1: Kunne ikke verificere.\n"
    "- Spørgsmål 2: Nåede ikke at finde en tabel-definition.\n\n"
    "**Blockers** — Opbrugte tool-runder før spørgsmål 1 og 2 kunne verificeres.\n\n"
    "DÆKNING: 3\n"
)


def test_markeringen_kommer_fra_failure_men_teksten_fra_result(conn):
    """Markeringen er kort, teksten er lang — de bor i hver sin besked (27/10-2026).

    MAALT 27/10-2026 paa `asg-8c08c689239f4ff8`: spawn klipper sin raise-besked
    ved 350 tegn, saa `failure` bar markeringen OG en trunkeret kopi af teksten.
    Da opslaget tog hele `failure`, blev `final.txt` 394 tegn hvor agentens svar
    var 1575 — markeringen rigtig, 3/4 af teksten vaek.

    Vagten er et PAR: markeringen skal med, OG den fulde tekst skal med. En
    rettelse der kun redder den ene halvdel er netop den fejl den skal forhindre.
    """
    _besked(conn, "result", FULL_TEXT, "2026-10-27T05:00:00.001Z")
    _besked(conn, "failure",
            "Agent afsluttede uden et brugbart resultat: UFULDSTÆNDIG (2 spørgsmål "
            "uden nummereret svar) — agentens tekst:\n**Summary** — Jeg kunne verificere",
            "2026-10-27T05:00:00.002Z")
    svar = _opslag(conn)
    assert "UFULDSTÆNDIG (2 spørgsmål uden nummereret svar)" in svar, (
        f"markeringen mangler: {svar[:200]!r}")
    assert FULL_TEXT.strip() in svar, (
        "den fulde tekst mangler — markeringen blev reddet, teksten tabt")
