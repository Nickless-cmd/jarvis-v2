"""Den delte vagt — den halvdel af en udskiftning der ikke er projektionen.

Vagten laa i `projection_chat_messages` indtil 12/9-2026 og blev kaldt fra
`chat_sessions`. Da drift-sammenligneren blev gjort genbrugelig til flere
projektioner, fulgte vagten ikke med, og den anden projektions skrivested stod
uvogtet. Den bor her nu.

Denne fil proever vagten SELV. At den virker gennem de to projektioner staar i
deres egne filer; her staar de tre ting man ellers kun ville tro paa:

* de tre tilstande, hver for sig
* fail-open naar tilstanden ikke kan laeses — og at den ikke er tavs
* at re-eksporten er den SAMME klasse, ikke en kopi
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import projection_guard as G


@pytest.fixture
def sid(isolated_runtime):
    s = "pg-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, "2026-09-09T09:00:00+00:00",
                                            "2026-09-09T09:00:00+00:00"))
    return s


def _vagt(sid: str, conn=None):
    G.guard_direct_write(sid, projektion="proeve", tabel="en_tabel", conn=conn)


# ── de tre tilstande ─────────────────────────────────────────────────────

def test_legacy_slipper_igennem(sid):
    """Kontrolarm. Uden den kunne vagten afvise ALT og stadig se rigtig ud."""
    with connect() as c:
        _vagt(sid, c)  # ingen undtagelse


def test_shadow_slipper_ogsaa_igennem(sid):
    """I skygge skrives der BEGGE steder. En vagt der spaerrede her ville
    goere drift-sammenligningen umulig — og dermed et skifte ubegrundet."""
    L.advance_storage_mode(sid, to="shadow")
    with connect() as c:
        _vagt(sid, c)


def test_ledger_afvises(sid):
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    with connect() as c:
        with pytest.raises(G.DirekteSkrivningAfvist):
            _vagt(sid, c)


def test_afvisningen_siger_hvad_man_skal_goere_i_stedet(sid):
    """En vagt der kun siger nej efterlader kalderen uden vej videre."""
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    with connect() as c:
        with pytest.raises(G.DirekteSkrivningAfvist) as ei:
            _vagt(sid, c)
    tekst = str(ei.value)
    assert "en_tabel" in tekst
    assert "hovedbogen" in tekst
    assert sid in tekst


# ── fail-open, og at den ikke er tavs ────────────────────────────────────

def test_ulaeselig_tilstand_TILLADER_skrivningen(monkeypatch, sid):
    """En utilgaengelig tilstands-kolonne maa ikke goere en samtale
    skrivebeskyttet. Valget er bevidst og staar i docstringen."""
    import core.runtime.db_session_ledger as DL

    def _sprang(*a, **k):
        raise RuntimeError("databasen svarer ikke")

    monkeypatch.setattr(DL, "storage_mode", _sprang)
    _vagt(sid)  # ingen undtagelse


def test_men_den_logger_naar_den_giver_op(monkeypatch, sid, caplog):
    """Fail-open er et valg; fail-open i TAVSHED er en vagt der er holdt op
    med at virke uden at nogen opdager det."""
    import logging

    import core.runtime.db_session_ledger as DL

    def _sprang(*a, **k):
        raise RuntimeError("databasen svarer ikke")

    monkeypatch.setattr(DL, "storage_mode", _sprang)
    with caplog.at_level(logging.WARNING):
        _vagt(sid)
    assert any("storage_mode" in r.message or "storage_mode" in r.getMessage()
               for r in caplog.records)


# ── re-eksporten ─────────────────────────────────────────────────────────

def test_de_to_projektioner_deler_SAMME_undtagelsesklasse():
    """`chat_sessions` og de gamle tests fanger klassen via
    `projection_chat_messages`. Var re-eksporten en kopi, ville `isinstance`
    holde op med at virke uden at nogen import braekkede — altsaa tavst."""
    from core.services.projection_chat_messages import (
        DirekteSkrivningAfvist as fra_chat)
    from core.services.projection_tool_router import (
        DirekteSkrivningAfvist as fra_router)
    assert fra_chat is G.DirekteSkrivningAfvist
    assert fra_router is G.DirekteSkrivningAfvist
