"""Dæknings-kontrakten skal læses på agentens FULDE tekst (27/10-2026).

MAALT 27/10-2026 på `asg-8c08c689239f4ff8` (researcher, run-18c079a314b24e14):

Agenten gjorde præcis hvad kontrakten kræver — den skrev til sidst:

    DÆKNING: 3

Den havde svaret på spørgsmål 3 og ærligt sagt at 1 og 2 ikke kunne verificeres.
Det sande antal ubesvarede er derfor 2.

Men `agent_runtime_spawn.py` klipper fejlbeskeden til 350 tegn:

    raise RuntimeError("Agent afsluttede uden et brugbart resultat: " + ...[:350])

`failure`-beskeden blev derfor 394 tegn af en tekst på 1575 — og DÆKNING-linjen,
som står ALLERsidst, blev skåret væk. `latest_agent_reply` foretrak `failure`
fordi den bærer markeringen, så kontrakten blev læst på en tekst hvor dens egen
nøgle var fjernet. Målt:

    fuld tekst   -> dækning {3}  -> 2 ubesvarede   (det sande tal)
    final.txt    -> dækning None -> 3 ubesvarede   (over-rapportering)

Rækkefølgen er nu: den FULDE `result`-besked vinder. `failure` bruges kun når
`result` ikke findes. En forkortet kopi må aldrig slå den fulde tekst.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime.db_agent_contract import latest_agent_reply


FULD = (
    "**Summary** — Jeg kunne verificere svar 3, men ikke 1 og 2.\n\n"
    "**Findings**\n"
    "- Spørgsmål 3: funktionen er defineret i agent_loop_core.py, linje 215.\n"
    "- Spørgsmål 1: kunne ikke verificere.\n"
    "- Spørgsmål 2: kunne ikke verificere.\n\n"
    "DÆKNING: 3"
)

#: Præcis den form spawn skriver: markeringen forrest, teksten klippet til 350 tegn.
TRUNKERET = (
    "Agent afsluttede uden et brugbart resultat: UFULDSTÆNDIG (2 spørgsmål uden "
    "nummereret svar) — agentens tekst:\n**Summary** — Jeg kunne verificere svar 3 "
    "med stor sikkerhed, men ikke 1 og 2 inden for de tildelte værktøjs-runder.\n\n"
    "**Findings**\n- Spørgsmål 3: Funktionen `_unanswered_questions` er defineret i "
    "`/media/projects/jarvis-v2/core/services/agent_loop_core.py`, linje 215 (`def "
    "_unanswere"
)


def _conn(rows: list[tuple[str, str]]) -> sqlite3.Connection:
    """En rigtig sqlite-motor med agent_messages — ikke en mock.

    En fake-forbindelse der returnerer de samme rækker uanset SQL kan ikke se
    om WHERE- og ORDER BY-grenene faktisk virker.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE agent_messages (agent_id TEXT, direction TEXT, kind TEXT, "
        "content TEXT, created_at TEXT)"
    )
    # Tidsstemplerne skal stige i indsaettelsesraekkefoelgen: den SIDSTE raekke er
    # den nyeste. Ellers vender opslaget listen og tester sin egen fejl.
    for i, (kind, content) in enumerate(rows):
        conn.execute(
            "INSERT INTO agent_messages VALUES (?,?,?,?,?)",
            ("agent-x", "agent->jarvis", kind, content,
             f"2026-10-27T05:45:{29 + i:02d}.000000Z"),
        )
    conn.commit()
    return conn


def test_den_fulde_tekst_vinder_over_den_trunkerede():
    """Kernen: en forkortet `failure`-kopi må ikke slå den fulde `result`."""
    conn = _conn([("result", FULD), ("failure", TRUNKERET)])
    svar = latest_agent_reply(conn, "agent-x")
    # 27/10-2026: svaret er nu BEGGE halvdele — markeringen fra `failure` foran
    # den fulde tekst fra `result`. Kravet er derfor ikke eksakt lighed med FULD,
    # men at ingen af de to halvdele er tabt: den trunkerede kopi maa ikke vinde,
    # og markeringen maa ikke forsvinde.
    assert FULD in svar, (
        "den fulde tekst er ikke med — den trunkerede failure-kopi vandt. "
        f"Fik {len(svar)} tegn, forventede mindst {len(FULD)}"
    )
    assert "UFULDSTÆNDIG" in svar, "markeringen fra failure skal stadig vaere med"
    assert "DÆKNING: 3" in svar, "dæknings-linjen skal være med i det der læses"
    assert "_unanswere" not in svar, "den afklippede kopi maa ikke vaere med"


def test_daekningen_kan_laeses_paa_det_der_returneres():
    """Kontrakten skal kunne PARSES på resultatet — ikke bare findes i en anden række."""
    from core.services.agent_loop_core import _declared_coverage

    conn = _conn([("result", FULD), ("failure", TRUNKERET)])
    assert _declared_coverage(latest_agent_reply(conn, "agent-x")) == {3}


def test_failure_bruges_naar_result_mangler():
    """En ægte fejl uden en `result`-besked skal stadig kunne læses."""
    conn = _conn([("failure", TRUNKERET)])
    svar = latest_agent_reply(conn, "agent-x")
    assert svar == TRUNKERET, "uden en result-besked er failure den eneste kilde"


def test_tom_result_efterlader_failure_som_kilde():
    """En tom `result` er ikke en leverance — så skal failure stadig bruges."""
    conn = _conn([("result", "   "), ("failure", TRUNKERET)])
    assert latest_agent_reply(conn, "agent-x") == TRUNKERET


def test_ingen_beskeder_giver_tom_streng():
    """Ingen rækker er ikke en fejl — det er en agent der ikke har skrevet endnu."""
    assert latest_agent_reply(_conn([]), "agent-x") == ""


def test_nyeste_result_vinder_over_aeldre():
    """Flere forsøg: det seneste resultat er agentens faktiske leverance."""
    aeldre = "gammelt svar\nDÆKNING: 1"
    nyere = "nyt svar\nDÆKNING: 1,2,3"
    conn = _conn([("result", aeldre), ("result", nyere)])
    assert latest_agent_reply(conn, "agent-x") == nyere
