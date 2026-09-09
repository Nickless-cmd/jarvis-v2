"""Skrivevejen for en session hvor LEDGEREN er sandheden.

Det der vender om: for `legacy` og `shadow` skrives rækken, og ledgeren følger
efter. Her skrives hændelsen, og RÆKKEN er noget projektoren laver.

Kontrasten til skygge-skrivningen er hele pointen og prøves eksplicit: dér
tier en fejl, her kaster den — fordi der ikke er nogen anden kopi af beskeden.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import ledger_write_path as W

TID = "2026-09-09T12:00:00+00:00"


@pytest.fixture
def sid(isolated_runtime):
    s = "wp-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    L.advance_storage_mode(s, to="shadow")
    L.advance_storage_mode(s, to="ledger")
    return s


def _raekke(mid):
    with connect() as c:
        r = c.execute("SELECT role, content, user_id, reasoning_content, git_sha, "
                      "created_at FROM chat_messages WHERE message_id = ?", (mid,)).fetchone()
    return None if r is None else dict(zip(
        ("role", "content", "user_id", "reasoning_content", "git_sha", "created_at"), r))


# ── hændelsen først, rækken bagefter ─────────────────────────────────────

def test_beskeden_bliver_til_baade_haendelse_og_raekke(sid):
    r = W.append_message(sid, role="user", content="hej", created_at=TID)
    e = L.read_session_events(sid)
    assert len(e) == 1 and e[0]["event_id"] == r["message_id"]
    assert _raekke(r["message_id"])["content"] == "hej"


def test_kalderen_faar_foerst_svar_naar_RAEKKEN_findes(sid):
    """Ellers kunne kaldet returnere en besked ingen læser kan se endnu."""
    r = W.append_message(sid, role="assistant", content="svar", created_at=TID)
    assert _raekke(r["message_id"]) is not None


def test_alle_felter_naar_frem(sid):
    r = W.append_message(sid, role="assistant", content="svar", created_at=TID,
                         user_id="bjorn", workspace_name="w",
                         reasoning_content="tænkte", git_sha="abc123")
    x = _raekke(r["message_id"])
    assert x["user_id"] == "bjorn" and x["reasoning_content"] == "tænkte"
    assert x["git_sha"] == "abc123" and x["created_at"] == TID


def test_content_json_som_objekt_bliver_til_tekst(sid):
    r = W.append_message(sid, role="assistant", content="x", created_at=TID,
                         content_json=[{"type": "text", "text": "x"}])
    with connect() as c:
        cj = c.execute("SELECT content_json FROM chat_messages WHERE message_id = ?",
                       (r["message_id"],)).fetchone()[0]
    assert '"type": "text"' in cj


# ── id og tid ────────────────────────────────────────────────────────────

def test_et_givet_message_id_bruges(sid):
    r = W.append_message(sid, role="user", content="x", created_at=TID,
                         message_id="message-mit-eget")
    assert r["message_id"] == "message-mit-eget"
    assert _raekke("message-mit-eget") is not None


def test_uden_id_laves_der_et(sid):
    r = W.append_message(sid, role="user", content="x", created_at=TID)
    assert r["message_id"].startswith("message-")


def test_samme_id_to_gange_giver_EN_haendelse(sid):
    W.append_message(sid, role="user", content="x", created_at=TID, message_id="m1")
    W.append_message(sid, role="user", content="x", created_at=TID, message_id="m1")
    assert L.current_seq(sid) == 1


def test_uden_tid_saettes_den_nu(sid):
    r = W.append_message(sid, role="user", content="x")
    assert r["created_at"] and _raekke(r["message_id"])["created_at"] == r["created_at"]


# ── her KASTER den, hvor skyggen tier ────────────────────────────────────

def test_en_optaget_lease_KASTER(sid):
    """Skygge-skrivningen tier ved en fejl, fordi `chat_messages` stadig er
    sandheden. Her er der ingen anden kopi: en tavs fejl ville være tabt data."""
    L.acquire_write_lease(sid, owner="en-anden-proces")
    with pytest.raises(W.LedgerWriteFailed, match="skriveretten"):
        W.append_message(sid, role="user", content="må ikke tabes", created_at=TID)
    assert L.current_seq(sid) == 0


def test_intet_skrives_naar_skriveretten_mangler(sid):
    L.acquire_write_lease(sid, owner="tyv")
    with pytest.raises(W.LedgerWriteFailed):
        W.append_message(sid, role="user", content="x", created_at=TID)
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
                         (sid,)).fetchone()[0] == 0


def test_et_UKENDT_format_afvises_frem_for_at_skrive_halvt(sid):
    import json
    from core.runtime import session_handle as H
    with connect() as c:
        H._ensure_header_column(c)
        c.execute("UPDATE chat_sessions SET ledger_header = ? WHERE session_id = ?",
                  (json.dumps({"session_id": sid, "generation": 99, "created_at": TID}), sid))
    with pytest.raises(H.SessionFormatError):
        W.append_message(sid, role="user", content="x", created_at=TID)


# ── leasen holdes ikke fast ──────────────────────────────────────────────

def test_leasen_gives_fra_sig_efter_hver_besked(sid):
    """Ellers ville den første besked spærre sessionen i fem minutter."""
    for i in range(3):
        W.append_message(sid, role="user", content=str(i), created_at=TID)
    assert L.acquire_write_lease(sid, owner="nogen-anden") is not None


def test_leasen_gives_fra_sig_ogsaa_naar_skrivningen_fejler(sid, monkeypatch):
    monkeypatch.setattr(L, "append_session_events",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    with pytest.raises(RuntimeError):
        W.append_message(sid, role="user", content="x", created_at=TID)
    monkeypatch.setattr(L, "append_session_events", L.append_session_events)
    assert L.acquire_write_lease(sid, owner="nogen-anden") is not None
