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


class TestRutinekoersler:
    """En rutinekørsel persisterer sine beskeder ved AFLUTNING.

    Målt 21/11-2026 (incident 17698): nattrutinen «Sansernes Arkiv» kørte
    `run_0a40d4c0be…` fra 21:02:43 til 21:05:19 og skrev BÅDE bruger- og
    assistent-rækken kl. 21:05:19.355217. Detektoren kaldte turen «aldrig
    startet», fordi den kun kiggede efter events EFTER beskedens tidsstempel —
    og rutinens start ligger 157 sekunder FØR den.

    Rutinekørsler skriver ingen af de to event-kinds; deres levetid står i
    `routine_runs`, og `session_id` er tom i 235 af 238 rækker. Koblingen går
    derfor gennem navnet: sessionen er `routine-<routine_id>`.
    """

    RUTINE_ID = "routine_migrated_f3114fc76f97624200dfc519"
    RUTINE_SID = "routine-" + RUTINE_ID
    BESKED = "2026-11-21T21:05:19.355217+00:00"

    @staticmethod
    def _rutine(con, finished: str) -> None:
        con.execute("CREATE TABLE routine_runs (routine_id TEXT, finished_at TEXT)")
        con.execute(
            "INSERT INTO routine_runs (routine_id, finished_at) VALUES (?,?)",
            (TestRutinekoersler.RUTINE_ID, finished))

    def test_koersel_der_sluttede_ved_beskeden_taeller(self, con):
        """Præcis 17698: finished 21:05:19.352489, besked 21:05:19.355217."""
        self._rutine(con, "2026-11-21T21:05:19.352489+00:00")
        assert cd.run_startet_for_session(con, self.RUTINE_SID, self.BESKED) is True

    def test_gammel_rutinekoersel_taeller_ikke(self, con):
        """Et run fra i GÅR må ikke gøre en afvist tur til en kappet tur."""
        self._rutine(con, "2026-11-20T21:05:35.752938+00:00")
        assert cd.run_startet_for_session(con, self.RUTINE_SID, self.BESKED) is False

    def test_rutine_uden_koersel_er_aldrig_startet(self, con):
        """En rutine-session uden run ER den ægte «aldrig startet»."""
        con.execute("CREATE TABLE routine_runs (routine_id TEXT, finished_at TEXT)")
        assert cd.run_startet_for_session(con, self.RUTINE_SID, self.BESKED) is False

    def test_manglende_rutinetabel_giver_none(self, con):
        """Ældre db uden `routine_runs`: «ved ikke», ikke «afvist»."""
        assert cd.run_startet_for_session(con, self.RUTINE_SID, self.BESKED) is None

    def test_anden_rutine_taeller_ikke(self, con):
        self._rutine(con, "2026-11-21T21:05:19.352489+00:00")
        anden = "routine-routine_migrated_000000000000000000000000"
        assert cd.run_startet_for_session(con, anden, self.BESKED) is False


class TestTieBreakPaaIdentiskTidsstempel:
    """Bruger- og assistent-rækken kan have PRÆCIS samme `created_at`.

    Målt 21/11-2026 (incident 17698): begge rækker stod på 21:05:19.355217.
    Uden `id DESC` som andet sorteringsled returnerede SQLite `user` først, og
    detektoren så en tur uden svar — selv om assistent-svaret lå på næste linje.
    """

    SID = "routine-routine_migrated_f3114fc76f97624200dfc519"
    TS = "2026-11-21T21:05:19.355217+00:00"

    @pytest.fixture()
    def con_beskeder(self):
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        c.execute(
            "CREATE TABLE chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "message_id TEXT, session_id TEXT, role TEXT, content TEXT, created_at TEXT)"
        )
        c.execute(
            "INSERT INTO chat_messages (message_id, session_id, role, content, created_at) "
            "VALUES ('m-user','x','user','natrutine','" + self.TS + "')")
        c.execute(
            "INSERT INTO chat_messages (message_id, session_id, role, content, created_at) "
            "VALUES ('m-assistant','x','assistant','svar','" + self.TS + "')")
        return c

    def test_assistent_svaret_kommer_foerst(self, con_beskeder):
        rows = cd.beskeder_for_session(con_beskeder, "x")
        assert rows[0]["role"] == "assistant", (
            "identisk created_at: insertionsrækkefølgen skal afgøre, ellers "
            "ser detektoren en tur uden svar der faktisk svarede")


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
