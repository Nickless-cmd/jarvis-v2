"""Skiftet — når ledgeren bliver sandheden og `chat_messages` bliver udledt.

Fase 1's egentlige mål. Alt det andet er forberedelse: hvis en session ikke kan
skifte og BLIVE VED med at virke, har ledgeren ingen værdi.

Det der vender om: for `legacy` og `shadow` skrives rækken, og ledgeren følger
efter. For `ledger` skrives hændelsen, og rækken er noget projektoren laver.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime import session_handle as H
from core.runtime.db import connect
from core.services import ledger_canary as K
from core.services import projection_drift as D
from core.services import projection_runtime as P
from core.services.chat_sessions import (
    append_chat_message, recent_chat_session_messages, store_compact_marker,
)
from core.services.ledger_write_path import LedgerWriteFailed

TID = "2026-09-09T12:00:00+00:00"


def _ro(graense: float = 5.0) -> None:
    """Vent på de baggrundstråde `append_chat_message` selv starter — se
    `tests/test_ledger_canary.py` for hvorfor."""
    import threading
    import time
    slut = time.monotonic() + graense
    while time.monotonic() < slut:
        if not any("_safe_persist" in t.name for t in threading.enumerate()):
            return
        time.sleep(0.01)


@pytest.fixture
def sid(isolated_runtime):
    s = "co-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    return s


def _raekker(sid):
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT message_id, role, content, user_id, reasoning_content, created_at "
            "FROM chat_messages WHERE session_id = ? ORDER BY id", (sid,))]


def _skift(sid, n=5):
    """Den fulde vej: historik → skygge → skifte."""
    for i in range(n):
        append_chat_message(session_id=sid, role="user" if i % 2 == 0 else "assistant",
                            content=f"besked {i}", created_at=TID)
    _ro()
    K.enable_shadow(sid)
    _ro()
    ok, hvorfor = D.may_cut_over(sid)
    assert ok, hvorfor
    assert L.advance_storage_mode(sid, to="ledger")


# ── selve skiftet ────────────────────────────────────────────────────────

def test_porten_skal_vaere_aaben_foer_der_skiftes(sid):
    for i in range(3):
        append_chat_message(session_id=sid, role="user", content=str(i), created_at=TID)
    _ro()
    L.advance_storage_mode(sid, to="shadow")     # skygge UDEN efterfyldning
    ok, _ = D.may_cut_over(sid)
    assert ok is False


def test_samtalen_er_uroert_i_selve_skiftet(sid):
    _historik = None
    for i in range(4):
        append_chat_message(session_id=sid, role="user", content=f"m{i}", created_at=TID)
    _ro()
    K.enable_shadow(sid)
    _ro()
    foer = _raekker(sid)
    L.advance_storage_mode(sid, to="ledger")
    assert _raekker(sid) == foer                 # skiftet flytter ingen rækker


# ── og BLIVER den ved med at virke? ──────────────────────────────────────

def test_en_ny_besked_efter_skiftet_bliver_til_en_RAEKKE(sid):
    """Kernen. Uden projektor-kørslen ville hændelsen lande i ledgeren og
    rækken aldrig komme — samtalen ville holde op med at ændre sig, uden fejl
    og uden tom skærm."""
    _skift(sid)
    n = len(_raekker(sid))
    append_chat_message(session_id=sid, role="user", content="efter skiftet",
                        created_at=TID)
    _ro()
    r = _raekker(sid)
    assert len(r) == n + 1 and r[-1]["content"] == "efter skiftet"


def test_haendelsen_og_raekken_deler_id(sid):
    _skift(sid)
    append_chat_message(session_id=sid, role="assistant", content="svar", created_at=TID)
    _ro()
    assert L.read_session_events(sid)[-1]["event_id"] == _raekker(sid)[-1]["message_id"]


def test_felterne_overlever_vejen_gennem_ledgeren(sid):
    _skift(sid)
    append_chat_message(session_id=sid, role="assistant", content="svar",
                        created_at=TID, user_id="bjorn", workspace_name="w",
                        reasoning_content="tænkte")
    _ro()
    r = _raekker(sid)[-1]
    assert r["user_id"] == "bjorn" and r["reasoning_content"] == "tænkte"


def test_de_almindelige_laesere_ser_beskeden(sid):
    """Det er ikke nok at rækken findes — den skal findes for DEM der læser."""
    _skift(sid)
    append_chat_message(session_id=sid, role="user", content="kan du se mig",
                        created_at=TID)
    _ro()
    tekster = [m["content"] for m in recent_chat_session_messages(sid, limit=3)]
    assert "kan du se mig" in tekster


def test_en_markoer_efter_skiftet_virker_ogsaa(sid):
    _skift(sid)
    mid = store_compact_marker(sid, "opsummering", "sha123")
    _ro()
    with connect() as c:
        r = c.execute("SELECT role, git_sha FROM chat_messages WHERE message_id = ?",
                      (mid,)).fetchone()
    assert r is not None and r[0] == "compact_marker" and r[1] == "sha123"


def test_de_to_sider_er_stadig_enige_efter_flere_beskeder(sid):
    _skift(sid)
    for i in range(6):
        append_chat_message(session_id=sid, role="user", content=f"ny {i}", created_at=TID)
    _ro()
    d = D.compare(sid)
    assert d["enige"] is True and d["ledger_beskeder"] == d["tabel_beskeder"] == 11


# ── ledgeren er nu den ENESTE vej ind ────────────────────────────────────

def test_en_direkte_skrivning_udenom_afvises_stadig(sid):
    """Vagten bliver stående som sikkerhedsnet for enhver ANDEN skriver."""
    from core.services.projection_chat_messages import DirekteSkrivningAfvist, guard_direct_write
    _skift(sid)
    with connect() as c:
        with pytest.raises(DirekteSkrivningAfvist):
            guard_direct_write(sid, conn=c)


def test_en_skrivning_uden_ejerskab_afvises(sid):
    _skift(sid)
    with pytest.raises(PermissionError, match="SessionHandle"):
        L.append_unowned(sid, events=[{"event_id": "x", "kind": "message",
                                       "payload": {"role": "user", "content": "x"}}])


def test_en_optaget_lease_KASTER_frem_for_at_tabe_beskeden(sid):
    """Her er der ingen anden kopi. En tavs fejl ville være tabt data — MED
    VILJE anderledes end skygge-skrivningen."""
    _skift(sid)
    L.acquire_write_lease(sid, owner="en-anden-proces")
    with pytest.raises(LedgerWriteFailed):
        append_chat_message(session_id=sid, role="user", content="må ikke tabes",
                            created_at=TID)


# ── genskabelse er stadig mulig bagefter ─────────────────────────────────

def test_hele_samtalen_kan_stadig_genskabes_fra_tom_cache(sid):
    _skift(sid)
    append_chat_message(session_id=sid, role="user", content="efter", created_at=TID)
    store_compact_marker(sid, "opsummering", "sha")
    _ro()
    foer = _raekker(sid)
    with connect() as c:
        c.execute("DELETE FROM chat_messages WHERE session_id = ?", (sid,))
        c.execute("DELETE FROM projection_checkpoints WHERE session_id = ?", (sid,))
    from core.services import projection_chat_messages as C
    C.register()
    C.rebuild(sid)
    assert _raekker(sid) == foer


def test_en_fejlende_projektion_taber_ikke_haendelsen(sid, monkeypatch):
    """En projektion der er bagud, er ikke en tabt skrivning: foldningen
    fortsætter fra sit checkpoint."""
    _skift(sid)
    monkeypatch.setattr(P, "run_for_session",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    append_chat_message(session_id=sid, role="user", content="stadig gemt", created_at=TID)
    _ro()
    assert L.read_session_events(sid)[-1]["payload"]["content"] == "stadig gemt"
    # INTET monkeypatch.undo() her: `isolated_runtime` bruger selv monkeypatch
    # til at flytte HOME, og et undo() ville rulle DEN tilbage. Fikstur-
    # nedrivningen ordner det.
