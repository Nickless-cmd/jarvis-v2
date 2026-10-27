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
    """Den anden vej: en rigtig fejl skal ikke pakkes ind som 'delivery'."""
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
