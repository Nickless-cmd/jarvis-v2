"""Efterfyldning og skygge-start på en RIGTIG session.

Rækkefølgen er ikke en detalje: slog man bare skyggen til, ville ledgeren have
3 beskeder og tabellen 300 — drift ville melde uenighed for altid, og porten
ville aldrig kunne åbne. Skyggen ville måle ingenting.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import ledger_canary as K
from core.services import projection_chat_messages as C
from core.services import projection_drift as D
from core.services.chat_sessions import append_chat_message


def _ro(grænse: float = 5.0) -> None:
    """Vent på de baggrundstråde `append_chat_message` selv starter.

    En brugerbesked udløser `emotion_concepts._safe_persist` i en tråd, og den
    kører `CREATE TABLE IF NOT EXISTS` før sin skrivning — DDL tager en
    eksklusiv lås. Skriver testen næste besked imens, får DEN
    «database is locked» på sit eget `INSERT INTO chat_messages`.

    Det er ikke ledgerens fejl og heller ikke testens: det er systemets egen
    adfærd. Ventetiden skjuler den ikke, den venter bare på den — så det der
    måles er ledgeren og ikke trådenes timing.
    """
    import threading
    import time
    slut = time.monotonic() + grænse
    while time.monotonic() < slut:
        levende = [t for t in threading.enumerate()
                   if t is not threading.current_thread() and t.is_alive()
                   and ("_safe_persist" in t.name or "eventbus-writer" == t.name)]
        if not any("_safe_persist" in t.name for t in levende):
            return
        time.sleep(0.01)

TID = "2026-09-09T10:00:00+00:00"


@pytest.fixture
def sid(isolated_runtime):
    s = "kn-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    return s


def _historik(sid, n):
    for i in range(n):
        append_chat_message(session_id=sid, role="user" if i % 2 == 0 else "assistant",
                            content=f"besked {i}", created_at=TID)
    _ro()


# ── efterfyldningen ──────────────────────────────────────────────────────

def test_historikken_havner_i_ledgeren(sid):
    _historik(sid, 5)
    r = K.backfill(sid)
    assert r["beskeder"] == 5 and r["skrevet"] == 5
    assert L.current_seq(sid) == 5


def test_efterfyldningen_kan_koeres_IGEN_uden_dubletter(sid):
    """Det farlige øjeblik er ikke det første forsøg, men det andet — når
    nogen er i tvivl om det gik godt."""
    _historik(sid, 4)
    K.backfill(sid)
    r = K.backfill(sid)
    assert r["skrevet"] == 0 and r["dubletter"] == 4
    assert L.current_seq(sid) == 4


def test_raekkefoelgen_bevares(sid):
    _historik(sid, 6)
    K.backfill(sid)
    assert [e["payload"]["content"] for e in L.read_session_events(sid)] == \
           [f"besked {i}" for i in range(6)]


def test_en_tom_session_efterfyldes_ikke(sid):
    r = K.backfill(sid)
    assert r["skrevet"] == 0 and "ingen beskeder" in r["grund"]


def test_en_optaget_lease_efterfylder_IKKE_halvt(sid):
    _historik(sid, 3)
    L.acquire_write_lease(sid, owner="en-anden")
    r = K.backfill(sid)
    assert r["skrevet"] == 0 and L.current_seq(sid) == 0


# ── skyggen slås til ─────────────────────────────────────────────────────

def test_efterfyldning_FOER_skifte_giver_enighed(sid):
    _historik(sid, 10)
    r = K.enable_shadow(sid)
    _ro()
    assert r["ok"] is True
    assert r["drift"]["enige"] is True
    assert r["drift"]["ledger"] == r["drift"]["tabel"] == 10
    assert L.storage_mode(sid) == "shadow"


def test_nye_beskeder_efter_skiftet_holder_siderne_enige(sid):
    _historik(sid, 5)
    K.enable_shadow(sid)
    _ro()
    append_chat_message(session_id=sid, role="user", content="ny", created_at=TID)
    d = D.compare(sid)
    assert d["enige"] is True and d["ledger_beskeder"] == 6


def test_sessionen_kan_derefter_SKIFTE(sid):
    """Hele pointen: efter efterfyldning + skygge er porten åben."""
    _historik(sid, 5)
    K.enable_shadow(sid)
    _ro()
    append_chat_message(session_id=sid, role="user", content="ny", created_at=TID)
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is True and "6 beskeder" in hvorfor


def test_UDEN_efterfyldning_kan_porten_aldrig_aabne(sid):
    """Bevis for hvorfor rækkefølgen ikke er en detalje."""
    _historik(sid, 10)
    L.advance_storage_mode(sid, to="shadow")          # skyggen alene, ingen historik
    append_chat_message(session_id=sid, role="user", content="ny", created_at=TID)
    ok, _ = D.may_cut_over(sid)
    assert ok is False


def test_en_session_der_allerede_er_flyttet_roeres_ikke(sid):
    _historik(sid, 3)
    K.enable_shadow(sid)
    r = K.enable_shadow(sid)
    _ro()
    assert r["ok"] is False and "allerede" in r["grund"]


def test_skiftet_kan_fortrydes_og_skrivningen_stopper(sid):
    """Et eksperiment man ikke kan slukke, bliver stående tændt."""
    _historik(sid, 3)
    K.enable_shadow(sid)
    assert L.abandon_shadow(sid) is True
    append_chat_message(session_id=sid, role="user", content="efter", created_at=TID)
    assert L.current_seq(sid) == 3                     # ingen ny hændelse


def test_hele_vejen_igennem_kan_samtalen_genskabes(sid):
    """Efterfyld, skygge, nye beskeder, riv rækkerne ud, byg dem op igen."""
    _historik(sid, 8)
    K.enable_shadow(sid)
    _ro()
    append_chat_message(session_id=sid, role="assistant", content="ny", created_at=TID)
    with connect() as c:
        foer = [dict(r) for r in c.execute(
            "SELECT message_id, role, content, created_at FROM chat_messages "
            "WHERE session_id = ? ORDER BY id", (sid,))]
        c.execute("DELETE FROM chat_messages WHERE session_id = ?", (sid,))
    C.register()
    C.rebuild(sid)
    with connect() as c:
        efter = [dict(r) for r in c.execute(
            "SELECT message_id, role, content, created_at FROM chat_messages "
            "WHERE session_id = ? ORDER BY id", (sid,))]
    assert efter == foer
