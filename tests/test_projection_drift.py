"""Drift-detektionen — det der gør skygge-tilstanden mere end dobbelt arbejde.

Fase 1: «drift detection reports no mismatch for canary fixtures». Uden en
sammenligning har man skrevet begge steder i uger og ved stadig ikke om de er
enige.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import projection_drift as D
from core.services.chat_sessions import append_chat_message

TID = "2026-09-09T10:00:00+00:00"


@pytest.fixture
def sid(isolated_runtime):
    s = "dr-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    L.advance_storage_mode(s, to="shadow")
    return s


def _begge(sid: str, rolle: str, tekst: str, **ekstra):
    """Skriv som skygge-tilstanden gør det: begge steder."""
    append_chat_message(session_id=sid, role=rolle, content=tekst,
                        created_at=TID, **ekstra)
    p = {"role": rolle, "content": tekst, "created_at": TID}
    p.update(ekstra)
    t = L.acquire_write_lease(sid, owner="s")
    L.append_session_events(sid, owner="s", token=t, events=[
        {"event_id": f"e{L.current_seq(sid) + 1}", "kind": "message", "payload": p}])
    L.release_write_lease(sid, owner="s", token=t)


def _kun_ledger(sid: str, eid: str, rolle: str, tekst: str, **ekstra):
    p = {"role": rolle, "content": tekst, "created_at": TID}
    p.update(ekstra)
    t = L.acquire_write_lease(sid, owner="s")
    L.append_session_events(sid, owner="s", token=t, events=[
        {"event_id": eid, "kind": "message", "payload": p}])
    L.release_write_lease(sid, owner="s", token=t)


# ── kanarie-fikstur: ingen uenighed ──────────────────────────────────────

def test_en_almindelig_samtale_giver_NUL_uenigheder(sid):
    _begge(sid, "user", "hej")
    _begge(sid, "assistant", "hej selv")
    _begge(sid, "user", "hvad så")
    r = D.compare(sid)
    assert r["enige"] is True and r["uenigheder"] == []
    assert r["ledger_beskeder"] == r["tabel_beskeder"] == 3


def test_raesonnement_og_content_json_taeller_med(sid):
    _begge(sid, "assistant", "svar", reasoning_content="tænkte",
           content_json='[{"type": "text", "text": "svar"}]')
    assert D.compare(sid)["enige"] is True


def test_message_id_er_IKKE_en_uenighed(sid):
    """uuid4 mod et udledt id kan aldrig blive ens — og skal ikke: id'et er en
    nøgle, ikke indhold. At kræve dem ens ville gøre hver session falsk uenig."""
    _begge(sid, "user", "hej")
    with connect() as c:
        ids = [r[0] for r in c.execute(
            "SELECT message_id FROM chat_messages WHERE session_id = ?", (sid,))]
    from core.services.projection_chat_messages import message_id_for
    assert ids[0] != message_id_for(sid, "e1")
    assert D.compare(sid)["enige"] is True


def test_content_json_som_tekst_vs_objekt_er_ikke_uenighed(sid):
    """Forskel i FORM, ikke i indhold. En detektor der flagede den ville
    larme om noget ingen kan rette."""
    append_chat_message(session_id=sid, role="assistant", content="x",
                        created_at=TID, content_json='{"b": 2, "a": 1}')
    _kun_ledger(sid, "e1", "assistant", "x", content_json={"a": 1, "b": 2})
    assert D.compare(sid)["enige"] is True


# ── uenigheder findes, og de siger HVOR ──────────────────────────────────

def test_forskelligt_indhold_peger_paa_plads_og_felt(sid):
    append_chat_message(session_id=sid, role="user", content="tabellen",
                        created_at=TID)
    _kun_ledger(sid, "e1", "user", "ledgeren")
    r = D.compare(sid)
    assert r["enige"] is False
    assert r["uenigheder"] == [{"plads": 0, "felt": "content",
                                "ledger": "ledgeren", "tabel": "tabellen"}]


def test_en_besked_kun_i_ledgeren_ses(sid):
    _begge(sid, "user", "hej")
    _kun_ledger(sid, "e2", "assistant", "kun her")
    r = D.compare(sid)
    assert r["enige"] is False and r["uenigheder"][0]["tabel"] is None


def test_en_besked_kun_i_tabellen_ses(sid):
    _begge(sid, "user", "hej")
    append_chat_message(session_id=sid, role="assistant", content="kun her",
                        created_at=TID)
    r = D.compare(sid)
    assert r["enige"] is False and r["uenigheder"][0]["ledger"] is None


def test_forkert_RAEKKEFOELGE_er_en_uenighed(sid):
    """To sider med de samme beskeder i forskellig orden er ikke enige — det
    er en samtale hvor svaret kommer før spørgsmålet."""
    append_chat_message(session_id=sid, role="user", content="a", created_at=TID)
    append_chat_message(session_id=sid, role="user", content="b", created_at=TID)
    _kun_ledger(sid, "e1", "user", "b")
    _kun_ledger(sid, "e2", "user", "a")
    assert D.compare(sid)["enige"] is False


def test_sammenligningen_SKRIVER_ingenting(sid):
    """En sammenligning der ændrer det den måler, måler ikke."""
    _begge(sid, "user", "hej")
    def _fingeraftryk():
        with connect() as c:
            return (list(c.execute("SELECT * FROM chat_messages WHERE session_id = ?", (sid,))),
                    L.current_seq(sid))
    foer = _fingeraftryk()
    D.compare(sid)
    assert _fingeraftryk() == foer


# ── må sessionen skifte? ─────────────────────────────────────────────────

def test_en_enig_shadow_session_maa_skifte(sid):
    _begge(sid, "user", "hej")
    _begge(sid, "assistant", "hej selv")
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is True and "2 beskeder" in hvorfor


def test_en_TOM_ledger_maa_ALDRIG_skifte(sid):
    """En tom ledger og en tom sammenligning ser ens ud. Et skifte dér ville
    gøre en samtale til ingenting."""
    append_chat_message(session_id=sid, role="user", content="findes kun i tabellen",
                        created_at=TID)
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is False


def test_en_helt_tom_session_maa_heller_ikke_skifte(sid):
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is False and "tom" in hvorfor


def test_uenighed_blokerer_skiftet_og_siger_hvorfor(sid):
    append_chat_message(session_id=sid, role="user", content="tabellen", created_at=TID)
    _kun_ledger(sid, "e1", "user", "ledgeren")
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is False and "uenighed" in hvorfor


def test_et_spring_direkte_fra_LEGACY_afvises(sid, isolated_runtime):
    """Ledgeren skal have været prøvet mod virkeligheden først."""
    s = "dr-legacy-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    ok, hvorfor = D.may_cut_over(s)
    assert ok is False and "legacy" in hvorfor
