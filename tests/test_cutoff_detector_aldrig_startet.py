"""Turen der aldrig blev startet er ikke en kappet tur.

Målt 31/10-2026: Mikkels tur kl. 11:27:42 blev afvist med HTTP 403 af
enheds-reglen. Beskeden blev persisteret (`channel.chat_message_appended`),
men der blev aldrig oprettet et run — `visible_runs` havde nul rækker for
sessionen. Detektoren kaldte det «tavs cutoff: 0 værktøjskald, 0s» og sendte
fejlsøgningen efter en død stream i timevis, da aarsagen var klientens 403.

Testene her pinner skelnen: blev der overhovedet startet et run?
"""
from __future__ import annotations

import sqlite3

import pytest

from scripts import cutoff_detector as cd


@pytest.fixture()
def con():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, payload_json TEXT, created_at TEXT)"
    )
    return c


SID = "chat-b8a066aa26b14ea59f6d52bd2932748b"
EFTER = "2026-10-31T10:27:42+00:00"


def _event(con, kind: str, sid: str, ts: str = "2026-10-31T10:28:00+00:00") -> None:
    con.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?,?,?)",
        (kind, f'{{"session_id": "{sid}", "run_id": "visible-x"}}', ts),
    )


class TestRunStartetForSession:
    def test_ingen_events_betyder_aldrig_startet(self, con):
        """Præcis Mikkels tilfælde: besked persisteret, intet run."""
        assert cd.run_startet_for_session(con, SID, EFTER) is False

    def test_et_visible_run_tail_betyder_startet(self, con):
        _event(con, "runtime.visible_run_tail", SID)
        assert cd.run_startet_for_session(con, SID, EFTER) is True

    def test_et_autonomt_run_taeller_ogsaa(self, con):
        _event(con, "runtime.autonomous_run_started", SID)
        assert cd.run_startet_for_session(con, SID, EFTER) is True

    def test_event_foer_beskeden_taeller_ikke(self, con):
        """Et run fra en TIDLIGERE tur maa ikke gøre en ny afvist tur til en
        kappet tur — så ville hver anden tur i en travl session blive
        fejldiagnosticeret."""
        _event(con, "runtime.visible_run_tail", SID, ts="2026-10-31T09:00:00+00:00")
        assert cd.run_startet_for_session(con, SID, EFTER) is False

    def test_event_for_en_anden_session_taeller_ikke(self, con):
        _event(con, "runtime.visible_run_tail", "chat-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert cd.run_startet_for_session(con, SID, EFTER) is False

    def test_ukendt_skema_giver_none_ikke_false(self, con):
        """Kan vi ikke afgøre det, må dommen ikke blive skarpere end målingen —
        ellers ville en skema-drift gøre hver tur til «afvist»."""
        con.execute("DROP TABLE events")
        assert cd.run_startet_for_session(con, SID, EFTER) is None


class TestKodeNaegtetKanFoelges:
    """Beskeden skal kunne følges af den klient der FAKTISK får den.

    Målt 31/10-2026: teksten pegede på «Indstillinger → Konto → Enheder», en
    flade der kun findes i desk. jarvis-code-brugeren — den eneste der reelt
    ramte 403'en — har den ikke.
    """

    def test_naevner_desk_vejen(self):
        from core.identity.kode_adgang import KODE_NAEGTET
        assert "Enheder" in KODE_NAEGTET
        assert "totrinskode" in KODE_NAEGTET

    def test_naevner_ogsaa_klienter_uden_desk(self):
        from core.identity.kode_adgang import KODE_NAEGTET
        assert "jarvis-code" in KODE_NAEGTET
        assert "denne-computer" in KODE_NAEGTET
