"""Spol tilbage og fortryd — Claude Desktops kontrakt (cc-desktop-chatview.md §8)."""
from __future__ import annotations

import pytest

import core.runtime.db_chat_rewind as cr
from core.runtime.db import connect
from core.services.chat_sessions import append_chat_message, create_chat_session


@pytest.fixture
def samtale(isolated_runtime, monkeypatch):
    monkeypatch.setattr(cr, "_koerer", lambda sid: False)
    sid = create_chat_session(title="rewind")["id"]
    ids = []
    for rolle, tekst in [("user", "første spørgsmål"), ("assistant", "første svar"),
                         ("user", "andet spørgsmål"), ("assistant", "andet svar"),
                         ("tool", "[tool_result:x] [bash]: ok")]:
        m = append_chat_message(session_id=sid, role=rolle, content=tekst)
        ids.append(str(m["id"]))
    return sid, ids


def _indhold(sid):
    with connect() as c:
        return [r[0] for r in c.execute("SELECT content FROM chat_messages WHERE session_id=? ORDER BY id", (sid,))]


def test_spol_tilbage_fjerner_beskeden_og_alt_efter_og_giver_teksten(samtale):
    sid, ids = samtale
    svar = cr.spol_tilbage(sid, ids[2])
    assert svar["fjernet"] == 3 and svar["tekst"] == "andet spørgsmål"
    assert _indhold(sid) == ["første spørgsmål", "første svar"]


def test_fortryd_laegger_dem_tilbage_med_samme_id(samtale):
    sid, ids = samtale
    with connect() as c:
        foer = c.execute("SELECT id, message_id FROM chat_messages WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    rid = cr.spol_tilbage(sid, ids[2])["rewind_id"]
    assert cr.fortryd(sid, rid)["genskabt"] == 3
    with connect() as c:
        efter = c.execute("SELECT id, message_id FROM chat_messages WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    assert [tuple(r) for r in efter] == [tuple(r) for r in foer]


def test_fortryd_lukker_ved_naeste_besked(samtale):
    sid, ids = samtale
    rid = cr.spol_tilbage(sid, ids[2])["rewind_id"]
    append_chat_message(session_id=sid, role="user", content="en ny vej")
    with pytest.raises(cr.RewindFejl) as e:
        cr.fortryd(sid, rid)
    assert e.value.kode == 409
    # Intet skæres væk: arkivet ligger der stadig.
    with connect() as c:
        assert c.execute(f"SELECT COUNT(*) FROM {cr.ARKIV} WHERE rewind_id=?", (rid,)).fetchone()[0] == 3


def test_kun_til_en_brugerbesked(samtale):
    sid, ids = samtale
    with pytest.raises(cr.RewindFejl) as e:
        cr.spol_tilbage(sid, ids[1])
    assert e.value.kode == 400
    assert len(_indhold(sid)) == 5


def test_ikke_mens_et_svar_koerer(samtale, monkeypatch):
    sid, ids = samtale
    monkeypatch.setattr(cr, "_koerer", lambda s: True)
    with pytest.raises(cr.RewindFejl) as e:
        cr.spol_tilbage(sid, ids[2])
    assert "stop svaret" in str(e.value)
    assert len(_indhold(sid)) == 5


def test_soegning_foelger_med(samtale):
    """FTS-triggerne: en tilbagespolet besked kan ikke findes; en fortrudt kan."""
    sid, ids = samtale
    def fundet():
        with connect() as c:
            return c.execute("SELECT COUNT(*) FROM chat_messages_fts WHERE chat_messages_fts MATCH 'andet'").fetchone()[0]
    assert fundet() == 2
    rid = cr.spol_tilbage(sid, ids[2])["rewind_id"]
    assert fundet() == 0
    cr.fortryd(sid, rid)
    assert fundet() == 2


def test_ukendt_besked_og_ukendt_fortryd(samtale):
    sid, _ = samtale
    with pytest.raises(cr.RewindFejl) as e:
        cr.spol_tilbage(sid, "findes-ikke")
    assert e.value.kode == 404
    with pytest.raises(cr.RewindFejl) as e:
        cr.fortryd(sid, "rw-findes-ikke")
    assert e.value.kode == 404
