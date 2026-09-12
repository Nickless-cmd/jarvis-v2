"""Fastgoer og arkivér en samtale.

Bjoern bad om fire handlinger i en 3-punkts-menu "ligesom i desk appen": slet,
pin, arkivér, omdoeb. Maalt 12/9-2026 kan desk-appen kun TO af dem - rename og
delete - og serveren havde praecis de to endpoints. Hverken pin eller archive
fandtes noget sted, og chat_sessions havde ingen kolonne til dem.

Denne fil daekker de to nye.
"""
from __future__ import annotations

import pytest

from core.runtime.db import connect
from core.services.chat_sessions import list_chat_sessions, set_session_flags


@pytest.fixture
def sid(isolated_runtime):
    s = "flag-test-1"
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, "2026-09-01T00:00:00+00:00",
                                            "2026-09-01T00:00:00+00:00"))
    return s


def test_fastgjort_kommer_oeverst(sid):
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES ('nyere', 'N', ?, ?)", ("2026-09-09T00:00:00+00:00",
                                                  "2026-09-09T00:00:00+00:00"))
    assert list_chat_sessions()[0]["id"] == "nyere"   # kontrolarm: nyeste foerst
    set_session_flags(sid, pinned=True)
    assert list_chat_sessions()[0]["id"] == sid


def test_arkiveret_falder_ud_af_listen(sid):
    assert any(x["id"] == sid for x in list_chat_sessions())
    set_session_flags(sid, archived=True)
    assert not any(x["id"] == sid for x in list_chat_sessions())
    assert any(x["id"] == sid for x in list_chat_sessions(inkluder_arkiverede=True))


def test_arkivering_frigoer_fastgoerelsen(sid):
    """En samtale man har lagt vaek skal ikke staa oeverst."""
    set_session_flags(sid, pinned=True)
    r = set_session_flags(sid, archived=True)
    assert r["pinned"] is False and r["archived"] is True


def test_fastgoerelse_hiver_den_ud_af_arkivet(sid):
    set_session_flags(sid, archived=True)
    r = set_session_flags(sid, pinned=True)
    assert r["archived"] is False and r["pinned"] is True


def test_None_betyder_roer_ikke(sid):
    """Uden den skelnen ville et kald der kun vil arkivere ogsaa frigoere en
    fastgjort samtale."""
    set_session_flags(sid, pinned=True)
    set_session_flags(sid, archived=False)      # roerer kun archived
    e = [x for x in list_chat_sessions() if x["id"] == sid][0]
    assert e["pinned"] is True


def test_intet_at_aendre_er_en_fejl(sid):
    assert set_session_flags(sid)["status"] == "error"


def test_ukendt_samtale_er_en_fejl(isolated_runtime):
    assert "ukendt" in set_session_flags("findes-ikke", pinned=True)["error"]


def test_listen_baerer_felterne(sid):
    e = [x for x in list_chat_sessions() if x["id"] == sid][0]
    assert e["pinned"] is False and e["archived"] is False


def test_kolonnerne_sikres_ogsaa_fra_LISTNINGEN(isolated_runtime):
    """Foerste udgave migrerede kun fra saetteren, saa SELECT s.pinned fejlede
    med «no such column» for ALLE lister paa en base hvor ingen endnu havde
    fastgjort noget. Listningen skal kunne staa alene."""
    with connect() as c:
        for k in ("pinned", "archived"):
            try:
                c.execute(f"ALTER TABLE chat_sessions DROP COLUMN {k}")
            except Exception:
                pass
    list_chat_sessions()   # maa ikke kaste
