"""Udfaldet af en godkendelse skal nå SAMTALEN — ikke kun databasen.

MÅLT 1/11-2026 (Bjørn): «og hvis godkendelsen ikk gik igennem? det ved kun du
= så skal det osse fikses».

Beviset lå i basen hele tiden: `approval-c48e924bff23` blev godkendt 28/10 kl.
14:38:07 og erklæret `outcome_unknown` kl. 16:43:15 — «forældreløs: ingen
afslutning efter afsendelsen». I to timer stod der **«Godkendt»** i samtalen
mens sandheden var at ingen vidste om kommandoen havde kørt.

`approval_claims` HAR udfaldet. `chat_messages` fik det aldrig: `approved` blev
skrevet i det øjeblik der blev trykket, og derefter tav alt. To flader med hver
sin sandhed — og den ene var en løgn uden at nogen havde skrevet den med vilje.

## Hvad testene vogter

* `failed` og `outcome_unknown` skal skrive en NY række (append-only, samme
  form som `pending` → `approved`).
* `completed` skal **ikke** skrive noget. En hændelse der fyrer på den gode
  vej ville gøre tavshed meningsløs: så betød «ingen række» både «gik godt» og
  «blev aldrig skrevet».
* Uden `session_id` må den hverken skrive eller kaste. En baggrunds-godkendelse
  har ingen samtale at skrive i, og det er ikke en fejl.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from core.runtime import db_approval_bridge as B

ARGS = {"command": "rm -rf /tmp/x"}


@pytest.fixture
def aid():
    return "appr-" + datetime.now(UTC).strftime("%H%M%S%f")


def _opret_session(session_id: str) -> None:
    """En godkendelse opstaar ALTID i en koerende samtale — saa sessionen
    findes i produktion. Testen skal derfor oprette den, ikke gaaette.

    Maalt 1/11-2026: uden den kaster `append_chat_message` «chat session not
    found», og fejlen blev slugt som en debug-linje — praecis den tavshed
    denne test findes for at afdaekke.
    """
    from datetime import UTC, datetime

    from core.runtime.db import connect

    nu = datetime.now(UTC).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO chat_sessions "
            "(session_id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (session_id, "udfaldstest", nu, nu),
        )
        conn.commit()


def _bed(aid, **kw):
    sid = str(kw.get("session_id") or "")
    if sid:
        _opret_session(sid)
    return B.request(aid, tool_name="bash", arguments=ARGS, **kw)


def _raekker(aid):
    """Godkendelses-rækkerne for ÉT approval_id, ældste først."""
    from core.runtime import db as runtime_db

    conn = sqlite3.connect(str(runtime_db.DB_PATH))
    try:
        return conn.execute(
            "SELECT content_json FROM chat_messages "
            "WHERE role = 'approval_request' AND content_json LIKE ? "
            "ORDER BY id",
            (f"%{aid}%",),
        ).fetchall()
    finally:
        conn.close()


def _statusser(aid):
    import json

    ud = []
    for (raw,) in _raekker(aid):
        blokke = json.loads(raw or "[]")
        if blokke:
            ud.append(str(blokke[0].get("status") or ""))
    return ud


# ── Det dårlige udfald SKAL siges ──────────────────────────────────────────

def test_settle_som_fejler_skriver_udfaldet_til_samtalen(isolated_runtime, aid):
    _bed(aid, session_id="chat-udfald-1", run_id="run-1")
    B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS)

    assert B.settle(aid, ok=False, detail="exit 1") is True

    statusser = _statusser(aid)
    assert "failed" in statusser, (
        "kommandoen fejlede efter godkendelsen, men samtalen fik det aldrig "
        f"at vide — den står stadig som: {statusser}"
    )


def test_abandon_efter_afsendelse_skriver_outcome_unknown(isolated_runtime, aid):
    _bed(aid, session_id="chat-udfald-2", run_id="run-2")
    B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS)

    ny = B.abandon(aid, detail="runnet døde")
    assert ny == B.OUTCOME_UNKNOWN

    statusser = _statusser(aid)
    assert "outcome_unknown" in statusser, (
        "vi afsendte og så aldrig udfaldet — det er præcis den tilstand "
        f"Bjørn ikke kunne se. Rækkerne siger: {statusser}"
    )


# ── Den gode vej må ikke støje ─────────────────────────────────────────────

def test_completed_skriver_INGEN_ny_raekke(isolated_runtime, aid):
    _bed(aid, session_id="chat-udfald-3", run_id="run-3")
    B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS)

    foer = len(_raekker(aid))
    assert B.settle(aid, ok=True) is True

    assert len(_raekker(aid)) == foer, (
        "en hændelse på den gode vej gør tavshed meningsløs: så kan «ingen "
        "række» ikke længere betyde «gik godt»"
    )


# ── Uden en samtale må den hverken skrive eller kaste ─────────────────────

def test_uden_session_skrives_intet_og_intet_kastes(isolated_runtime, aid):
    _bed(aid)  # bevidst uden session_id
    B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS)

    assert B.settle(aid, ok=False) is True  # må ikke kaste
    assert _statusser(aid) == []
