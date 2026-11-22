"""Et kort der afgoeres EFTER svaret er ikke en tavs tur.

Maalt 22/11-2026 (incident 17722): turen svarede kl. 22:28:07 og sluttede
paent. Ni minutter senere blev to godkendelses-kort afgjort, og
`resolve_pending_approval` skrev `approval_request` + `tool` ind i SAMTALEN —
efter svaret. Detektoren kigger paa den NYESTE raekke, saa den skrev
«tavs cutoff: turen endte uden assistent-svar» i Centralen om en tur der
havde svaret.

Det modsatte tilfaelde er lige saa vigtigt: et AFVENTENDE kort blev vist MIDT
i turen. Doer turen med et aabent kort, ER den tavs — og posten skal blive
staaende. Testene her pinner begge sider.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from scripts import cutoff_detector as cd


def _nu_minus(minutter: int) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutter)).isoformat()


@pytest.fixture()
def con():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE chat_messages (message_id TEXT, session_id TEXT, role TEXT, "
        "content TEXT, created_at TEXT, content_json TEXT)"
    )
    return c


def _raekke(con, mid: str, rolle: str, ts: str, udfald: str = "") -> None:
    cj = None
    if udfald:
        cj = '[{"type": "approval", "status": "%s"}]' % udfald
    con.execute(
        "INSERT INTO chat_messages (message_id, session_id, role, content, "
        "created_at, content_json) VALUES (?,?,?,?,?,?)",
        (mid, "chat-x", rolle, "[tool_result:%s]" % mid, ts, cj),
    )


def _rows(con, sid: str = "chat-x") -> list:
    return cd.beskeder_for_session(con, sid)


class TestSvarFoerSeneKort:
    def test_afgjorte_kort_efter_svaret_taeller_som_svaret(self, con):
        """Praecis 17722: svar, derefter to afgjorte kort med parrede tool-svar."""
        _raekke(con, "m1", "user", _nu_minus(31))
        _raekke(con, "m2", "assistant", _nu_minus(30))
        _raekke(con, "m3", "tool", _nu_minus(25))
        _raekke(con, "m4", "approval_request", _nu_minus(25), udfald="approved")
        _raekke(con, "m5", "tool", _nu_minus(24))
        _raekke(con, "m6", "approval_request", _nu_minus(24), udfald="approved")
        assert cd.svar_foer_sene_kort(con, _rows(con)) is True

    def test_afventende_kort_er_midt_i_turen(self, con):
        """Et aabent kort blev vist FOER svaret — turen er reelt tavs."""
        _raekke(con, "m1", "user", _nu_minus(31))
        _raekke(con, "m2", "tool", _nu_minus(30))
        _raekke(con, "m3", "approval_request", _nu_minus(30), udfald="pending")
        assert cd.svar_foer_sene_kort(con, _rows(con)) is False

    def test_aegte_cutoff_uden_kort_er_stadig_en_cutoff(self, con):
        """Maalt 20/11 (17616): svaret kom, derefter et tool-svar fra runnet — og
        saa dode turen. Det er praecis det detektoren SKAL fange."""
        _raekke(con, "m1", "user", _nu_minus(31))
        _raekke(con, "m2", "assistant", _nu_minus(30))
        _raekke(con, "m3", "tool", _nu_minus(29))
        assert cd.svar_foer_sene_kort(con, _rows(con)) is False

    def test_kort_uden_ulaesbart_udfald_behandles_som_afventende(self, con):
        """Tvivl maa ikke goere en tavs tur til en besvaret tur."""
        _raekke(con, "m1", "user", _nu_minus(31))
        _raekke(con, "m2", "assistant", _nu_minus(30))
        con.execute(
            "INSERT INTO chat_messages (message_id, session_id, role, content, "
            "created_at, content_json) VALUES (?,?,?,?,?,?)",
            ("m3", "chat-x", "approval_request", "skrald", _nu_minus(29), "ikke-json"),
        )
        assert cd.svar_foer_sene_kort(con, _rows(con)) is False

    def test_skema_uden_content_json_svarer_afventende(self):
        """Aeldre db uden kolonnen: «ved ikke» — ikke «besvaret»."""
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        c.execute(
            "CREATE TABLE chat_messages (message_id TEXT, session_id TEXT, role TEXT, "
            "content TEXT, created_at TEXT)"
        )
        c.execute(
            "INSERT INTO chat_messages VALUES (?,?,?,?,?)",
            ("m1", "chat-x", "approval_request", "x", _nu_minus(5)),
        )
        assert cd.svar_foer_sene_kort(c, cd.beskeder_for_session(c, "chat-x")) is False


class TestHeleKoerslen:
    """Ende-til-ende: hvad der faktisk bliver skrevet i Centralen."""

    @staticmethod
    def _scratch(tmp_path):
        p = tmp_path / "scratch.db"
        c = sqlite3.connect(str(p))
        c.execute("CREATE TABLE chat_messages (message_id TEXT, session_id TEXT, "
                  "role TEXT, content TEXT, created_at TEXT, content_json TEXT)")
        c.execute("CREATE TABLE visible_runs (run_id TEXT, status TEXT, started_at TEXT, "
                  "error TEXT, lane TEXT, provider TEXT, model TEXT)")
        c.execute("CREATE TABLE runtime_state_kv (key TEXT, value_json TEXT, updated_at TEXT)")
        c.commit()
        return p, c

    @staticmethod
    def _koer(tmp_path, monkeypatch, p):
        fundet = []
        monkeypatch.setattr(cd, "DB", str(p))
        monkeypatch.setattr(cd, "STATE", str(tmp_path / "seen.json"))
        monkeypatch.setattr(cd, "LOG", str(tmp_path / "log.txt"))
        monkeypatch.setattr(cd, "api_restarted_near", lambda w: None)
        monkeypatch.setattr(
            "core.runtime.db_central_incidents.record_central_incident",
            lambda **kw: fundet.append(kw),
        )
        cd.main()
        return fundet

    def test_sent_afgjort_kort_giver_ingen_fejlpost(self, tmp_path, monkeypatch):
        p, c = self._scratch(tmp_path)
        _raekke(c, "m1", "user", _nu_minus(31))
        _raekke(c, "m2", "assistant", _nu_minus(30))
        _raekke(c, "m3", "tool", _nu_minus(25))
        _raekke(c, "m4", "approval_request", _nu_minus(25), udfald="approved")
        _raekke(c, "m5", "approval_request", _nu_minus(24), udfald="approved")
        c.commit()
        c.close()

        fundet = self._koer(tmp_path, monkeypatch, p)
        assert [f for f in fundet if f.get("nerve") == "silent_cutoff"] == []

    def test_strandet_tur_bliver_stadig_fundet(self, tmp_path, monkeypatch):
        p, c = self._scratch(tmp_path)
        _raekke(c, "m1", "user", _nu_minus(31))
        _raekke(c, "m2", "tool", _nu_minus(30))
        c.commit()
        c.close()

        fundet = self._koer(tmp_path, monkeypatch, p)
        assert [f for f in fundet if f.get("nerve") == "silent_cutoff"]
