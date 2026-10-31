"""Tests for scripts/cutoff_detector.py — detektoren for tavse cutoffs.

Baggrund (14/10-2026): scriptet levede fra 30/8 uden for repoet, uden test, mens
det skrev til `central_incidents`. Flyttet hertil, og de to blinde pletter den
selv dokumenterede er rettet. Testene her pinner netop dem — plus den ene fejl
der IKKE var dokumenteret: parseren der skrev en dato i stedet for et
vaerktoejsnavn.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

from scripts import cutoff_detector as cd


# ── plet 2: parseren af "sidste kald" ───────────────────────────────────────

class TestSidsteVaerktoej:
    """Formatet er MAALT, ikke gaettet: `[tool_result:<id>]\\n[<navn>]: …`."""

    def test_linjeskift_varianten(self):
        """Det faktiske format — et linjeskift mellem klammerne."""
        c = "[tool_result:tool-result-96aeff7b806641f5a8d9e34277d1330c]\n[send_ntfy]: Beskeden er leveret."
        assert cd.sidste_vaerktoej(c) == "send_ntfy"

    def test_mellemrums_varianten(self):
        """Den anden form huset bruger — samme resultat."""
        c = "[tool_result:abc] [bash]: 07:31:18 CEST"
        assert cd.sidste_vaerktoej(c) == "bash"

    def test_rammer_ikke_en_dato_dybt_i_resultatet(self):
        """REGRESSIONEN. Den gamle parser soegte `"] ["` uden anker, fandt
        ingen i headeren, og gled ned i resultatet hvor den greb den foerste
        `] [` den kunne finde. Maalt konsekvens: fundet kl. 05:04:35 skrev
        «sidste kald '2026-10-09'» — en dato, ikke et vaerktoejsnavn."""
        c = ("[tool_result:abc]\n[recall]: Hukommelse for «x» — 8 hit(s):\n"
             "- [sess 2026-10-09] [notat] noget andet\n")
        assert cd.sidste_vaerktoej(c) == "recall"

    def test_den_gamle_parser_fejlede_paa_praecis_dette(self):
        """Bevis for at rettelsen maaler noget: den gamle form giver en dato
        eller et tomt svar paa den samme streng."""
        c = "[tool_result:abc]\n[recall]: Hukommelse\n- [2026-10-09] [x]\n"
        gammel = c.split("] [", 1)[1].split("]", 1)[0][:40] if "] [" in c else "-"
        assert cd.sidste_vaerktoej(c) == "recall"
        assert gammel != "recall"   # den gamle var forkert

    def test_ingen_header_giver_bindestreg_aldrig_et_gaet(self):
        assert cd.sidste_vaerktoej("Use read_tool_result with result_id=…") == "-"
        assert cd.sidste_vaerktoej("") == "-"
        assert cd.sidste_vaerktoej(None) == "-"

    def test_navn_med_linjeskift_deler_ikke_loglinjen(self):
        """Maalt 11/9-2026: et navn med linjeskift delte posten i to loglinjer."""
        assert "\n" not in cd.sidste_vaerktoej("[tool_result:a]\n[ba\nsh]: x")

    def test_navnet_klippes_til_fyrre(self):
        lang = "x" * 60   # inden for moensterets graense — klippes til 40
        assert len(cd.sidste_vaerktoej(f"[tool_result:a]\n[{lang}]: y")) == 40


# ── tidsstrenge: ét sted, ét aerligt svar ───────────────────────────────────

class TestTilUtc:
    """Udskilt 14/10-2026 fra tre ens `try/except`. `None` betyder "ved ikke",
    og den der kalder vaelger selv — at gaette en tid ville skrive et forkert
    tal ind i Centralen."""

    def test_iso_uden_tidzone_bliver_utc(self):
        t = cd.til_utc("2026-10-14T05:04:35")
        assert t is not None and t.tzinfo is not None
        assert t.utcoffset().total_seconds() == 0

    def test_tidzone_bevares(self):
        t = cd.til_utc("2026-10-14T07:04:35+02:00")
        assert t is not None and t.utcoffset().total_seconds() == 7200

    def test_ulaesbar_giver_none_ikke_en_gaettet_tid(self):
        for skrald in ("", "i gaar", "2026-13-45T99:99:99", None, 42):
            assert cd.til_utc(skrald) is None, skrald


# ── plet 1: genstart-skelnen ────────────────────────────────────────────────

class TestApiRestartedNear:
    """Skelnen svarede "nej" VED KONSTRUKTION. Den maa ikke laengere kunne
    forveksle "kunne ikke laese" med "laeste, intet fundet"."""

    @staticmethod
    def _svar(monkeypatch, *, stdout="", stderr="", returncode=0):
        class P:
            pass
        p = P()
        p.stdout, p.stderr, p.returncode = stdout, stderr, returncode
        monkeypatch.setattr(cd.subprocess, "run", lambda *a, **k: p)

    def test_genstart_fundet(self, monkeypatch):
        self._svar(monkeypatch, stdout="INFO: Started server process [123]\n")
        assert cd.api_restarted_near(datetime.now(UTC)) is True

    def test_systemds_egen_besked_taeller_ogsaa(self, monkeypatch):
        """`bs` ER i systemd-journal nu (maalt 14/10) — beskeden er laesbar."""
        self._svar(monkeypatch, stdout="Started jarvis-api.\n")
        assert cd.api_restarted_near(datetime.now(UTC)) is True

    def test_laest_uden_fund_er_et_nej(self, monkeypatch):
        self._svar(monkeypatch, stdout="INFO: noget helt andet\n")
        assert cd.api_restarted_near(datetime.now(UTC)) is False

    def test_naegtet_adgang_er_ved_ikke_ikke_et_nej(self, monkeypatch):
        """Den kritiske: journalen naegter, exit-koden er 0, uddata tomt.
        FOER blev det til "nej (stroemmen doede)" — en dom vi ikke havde."""
        self._svar(monkeypatch, stdout="",
                   stderr="You are currently not seeing messages from other users and the system.")
        assert cd.api_restarted_near(datetime.now(UTC)) is None

    def test_ikke_nul_exit_er_ved_ikke(self, monkeypatch):
        self._svar(monkeypatch, stdout="", stderr="boom", returncode=1)
        assert cd.api_restarted_near(datetime.now(UTC)) is None

    def test_kast_er_ved_ikke(self, monkeypatch):
        def _kast(*a, **k):
            raise OSError("journalctl findes ikke")
        monkeypatch.setattr(cd.subprocess, "run", _kast)
        assert cd.api_restarted_near(datetime.now(UTC)) is None


class TestGenstartDom:
    """`None` maa ikke lyde som et svar i den tekst der gaar i fundet."""

    def test_de_tre_former_er_forskellige(self):
        assert "JA" in cd._genstart_dom(True)
        assert "nej" in cd._genstart_dom(False)
        dom = cd._genstart_dom(None)
        assert "KUNNE IKKE" in dom
        assert dom not in (cd._genstart_dom(True), cd._genstart_dom(False))


# ── turen_koerer_stadig ─────────────────────────────────────────────────────

class TestTurenKoererStadig:
    def test_db_fejl_er_ved_ikke_ikke_et_nej(self):
        """FOER: `return False` — en DB-hikke blev til et FUND."""
        class Doed:
            def execute(self, *a, **k):
                raise sqlite3.OperationalError("no such table")
        assert cd.turen_koerer_stadig(Doed(), "s") is None

    def test_ingen_noegle_er_nej(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE runtime_state_kv (key TEXT, value_json TEXT, updated_at TEXT)")
        assert cd.turen_koerer_stadig(con, "s") is False

    def test_anden_session_er_uafgjort(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE runtime_state_kv (key TEXT, value_json TEXT, updated_at TEXT)")
        con.execute("INSERT INTO runtime_state_kv VALUES (?,?,?)",
                    ("visible_runs.active_run",
                     json.dumps({"active": True, "session_id": "anden"}),
                     datetime.now(UTC).isoformat()))
        assert cd.turen_koerer_stadig(con, "min") is None


# ── ende til ende: main() mod en scratch-DB ─────────────────────────────────

class TestMainEndeTilEnde:
    """Detektoren skal kunne koere uden at roere den rigtige base."""

    @staticmethod
    def _scratch(tmp_path):
        p = tmp_path / "scratch.db"
        con = sqlite3.connect(str(p))
        con.execute("CREATE TABLE chat_messages (message_id TEXT, session_id TEXT, "
                    "role TEXT, content TEXT, created_at TEXT)")
        con.execute("CREATE TABLE visible_runs (run_id TEXT, status TEXT, started_at TEXT, "
                    "error TEXT, lane TEXT, provider TEXT, model TEXT)")
        con.execute("CREATE TABLE runtime_state_kv (key TEXT, value_json TEXT, updated_at TEXT)")
        con.commit()
        return p, con

    def test_strandet_tur_bliver_fundet(self, tmp_path, monkeypatch):
        p, con = self._scratch(tmp_path)
        # FORSKELLIGE tidsstempler — ellers giver ORDER BY created_at DESC en
        # vilkaarlig raekkefoelge, og "user" kan komme foer "tool".
        tidlig = (datetime.now(UTC) - timedelta(minutes=31)).isoformat()
        sen = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
        con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
                    ("m1", "chat-x", "user", "hej", tidlig))
        con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
                    ("m2", "chat-x", "tool",
                     "[tool_result:abc]\n[bash]: 07:31:18 CEST", sen))
        con.commit()
        con.close()

        fundet = []
        monkeypatch.setattr(cd, "DB", str(p))
        monkeypatch.setattr(cd, "STATE", str(tmp_path / "seen.json"))
        monkeypatch.setattr(cd, "LOG", str(tmp_path / "log.txt"))
        monkeypatch.setattr(cd, "api_restarted_near", lambda w: None)
        monkeypatch.setattr(
            "core.runtime.db_central_incidents.record_central_incident",
            lambda **kw: fundet.append(kw))

        assert cd.main() == 0
        assert len(fundet) == 1
        msg = fundet[0]["message"]
        assert "sidste kald 'bash'" in msg          # plet 2: navnet, ikke en dato
        assert "KUNNE IKKE AFGOERES" in msg         # plet 1: aerlig dom
        assert fundet[0]["kind"] == "turn_without_reply"

    def test_afsluttet_tur_er_ikke_et_fund(self, tmp_path, monkeypatch):
        p, con = self._scratch(tmp_path)
        tidlig = (datetime.now(UTC) - timedelta(minutes=31)).isoformat()
        sen = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
        con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
                    ("m1", "chat-y", "user", "hej", tidlig))
        con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
                    ("m2", "chat-y", "assistant", "svar", sen))
        con.commit()
        con.close()

        fundet = []
        monkeypatch.setattr(cd, "DB", str(p))
        monkeypatch.setattr(cd, "STATE", str(tmp_path / "seen.json"))
        monkeypatch.setattr(cd, "LOG", str(tmp_path / "log.txt"))
        monkeypatch.setattr(
            "core.runtime.db_central_incidents.record_central_incident",
            lambda **kw: fundet.append(kw))

        assert cd.main() == 0
        assert fundet == []

    def test_frisk_tur_er_ikke_et_fund(self, tmp_path, monkeypatch):
        """Under STALE_SECONDS kan turen stadig vaere i gang."""
        p, con = self._scratch(tmp_path)
        nu = datetime.now(UTC).isoformat()
        con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
                    ("m1", "chat-z", "tool", "[tool_result:a]\n[bash]: x", nu))
        con.commit()
        con.close()

        fundet = []
        monkeypatch.setattr(cd, "DB", str(p))
        monkeypatch.setattr(cd, "STATE", str(tmp_path / "seen.json"))
        monkeypatch.setattr(cd, "LOG", str(tmp_path / "log.txt"))
        monkeypatch.setattr(
            "core.runtime.db_central_incidents.record_central_incident",
            lambda **kw: fundet.append(kw))

        assert cd.main() == 0
        assert fundet == []

    def test_manglende_db_er_ikke_en_fejl(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cd, "DB", str(tmp_path / "findes-ikke.db"))
        assert cd.main() == 0


# ── plet 4: compact_marker er ikke et manglende svar ───────────────────────

class TestCompactMarker:
    """REGRESSIONEN (maalt 30/10-2026): `compact_marker` skrives EFTER svaret.

    Detektoren sprang kun over `assistant` som nyeste raekke, saa markoeren blev
    laest som en tur uden svar. Maalt i den levende base: 2 sessioner havde
    markoeren som nyeste raekke, og BEGGE var falske alarmer — svaret laa i
    samme tur, blot aeldre end markoeren.

    Rettelsen springer markoeren over, men KUN hvis der ligger et assistent-svar
    i SAMME tur (baglaens til naermeste `user`). Ellers er turen reelt strandet,
    og markoeren maa ikke skjule det.
    """

    @staticmethod
    def _koer(tmp_path, monkeypatch, raekker):
        """raekker = [(role, content)] i KRONOLOGISK orden (aeldste foerst)."""
        p = tmp_path / "scratch.db"
        con = sqlite3.connect(str(p))
        con.execute("CREATE TABLE chat_messages (message_id TEXT, session_id TEXT, "
                    "role TEXT, content TEXT, created_at TEXT)")
        con.execute("CREATE TABLE visible_runs (run_id TEXT, status TEXT, started_at TEXT, "
                    "error TEXT, lane TEXT, provider TEXT, model TEXT)")
        con.execute("CREATE TABLE runtime_state_kv (key TEXT, value_json TEXT, updated_at TEXT)")
        base = datetime.now(UTC) - timedelta(minutes=40)
        for i, (role, content) in enumerate(raekker):
            ts = (base + timedelta(seconds=i * 10)).isoformat()
            con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
                        (f"m{i}", "chat-marker", role, content, ts))
        con.commit()
        con.close()

        fundet = []
        monkeypatch.setattr(cd, "DB", str(p))
        monkeypatch.setattr(cd, "STATE", str(tmp_path / "seen.json"))
        monkeypatch.setattr(cd, "LOG", str(tmp_path / "log.txt"))
        monkeypatch.setattr(cd, "api_restarted_near", lambda w: None)
        monkeypatch.setattr(
            "core.runtime.db_central_incidents.record_central_incident",
            lambda **kw: fundet.append(kw))
        assert cd.main() == 0
        return fundet

    def test_svar_foer_markoer_er_ikke_et_fund(self, tmp_path, monkeypatch):
        """RETNINGEN. user -> tool -> assistant -> compact_marker.

        Markoeren er NYERE end svaret, saa svaret ligger i `rows[1:]` (aeldre).
        Et snit paa `rows[:index]` kigger den forkerte vej og ser intet svar.
        """
        fundet = self._koer(tmp_path, monkeypatch, [
            ("user", "spoergsmaal"),
            ("tool", "[tool_result:abc]\n[bash]: 07:31:18 CEST"),
            ("assistant", "her er svaret"),
            ("compact_marker", "komprimeret"),
        ])
        assert fundet == [], f"FALSK ALARM — markoeren blev laest som et cut: {fundet}"

    def test_strandet_tur_bag_markoeren_er_et_fund(self, tmp_path, monkeypatch):
        """Den aegte: user -> tool -> compact_marker UDEN assistent.

        Uden denne kontrol ville rettelsen skjule et reelt cut.
        """
        fundet = self._koer(tmp_path, monkeypatch, [
            ("user", "spoergsmaal"),
            ("tool", "[tool_result:abc]\n[bash]: 07:31:18 CEST"),
            ("compact_marker", "komprimeret"),
        ])
        assert len(fundet) == 1, f"markoeren skjulte et reelt cut: {fundet}"
        assert fundet[0]["kind"] == "turn_without_reply"

    def test_vaerktoej_efter_svaret_er_valgt(self, tmp_path, monkeypatch):
        """GRAENSEN. user -> assistant -> tool -> compact_marker.

        Rettelsen GODKENDER denne, fordi assistenten findes laengere tilbage.
        BEGRUNDELSE for at beholde det: maalt 30/10 har 1 af de historiske
        tilfaelde (11/10 kl. 19:43) netop et vaerktoejskald mellem svaret og
        markoeren. Strammer man til 'umiddelbar forgangger', ville den tur
        blive meldt som cut paa trods af at den blev besvaret. Prisen for den
        brede regel er nul falske alarmer i det maalte materiale.
        """
        fundet = self._koer(tmp_path, monkeypatch, [
            ("user", "spoergsmaal"),
            ("assistant", "her er svaret"),
            ("tool", "[tool_result:abc]\n[bash]: efterarbejde"),
            ("compact_marker", "komprimeret"),
        ])
        assert fundet == [], "svaret laa laengere tilbage og blev ikke fundet"


# ── systemd-stien ───────────────────────────────────────────────────────────

def test_systemd_enheden_peger_ind_i_repoet():
    """Enheden skal pege paa repo-scriptet, ikke /usr/local/sbin.

    Ligger som fil i scripts/ saa den er versionsstyret — samme moenster som
    jarvis-api.service.
    """
    from pathlib import Path
    rod = Path(__file__).resolve().parents[1]
    enhed = rod / "scripts" / "jarvis-cutoff-detector.service"
    assert enhed.exists(), "service-filen skal versioneres i scripts/"
    # Kravet er praecist: ExecStart skal pege paa repo-scriptet. En kommentar
    # der NAevner den gamle sti er historik, ikke en fejl.
    linjer = [ln.strip() for ln in enhed.read_text().splitlines()
              if ln.strip().startswith("ExecStart=")]
    assert linjer == ["ExecStart=/media/projects/jarvis-v2/scripts/cutoff_detector.py"]


# ── plet 3: svaret blev leveret i en ANDEN session ─────────────────────────

class TestRunIdsPrSession:
    """Koblingen run -> session kommer fra `events`, ikke fra `visible_runs`."""

    @staticmethod
    def _con():
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE events (id INTEGER, kind TEXT, payload_json TEXT, created_at TEXT)")
        return con

    def test_kobler_run_til_session(self):
        con = self._con()
        con.execute("INSERT INTO events VALUES (?,?,?,?)", (
            1, "runtime.autonomous_run_started",
            json.dumps({"run_id": "autonomous-a", "session_id": "auto-recurring-x"}),
            datetime.now(UTC).isoformat()))
        con.commit()
        ud = cd.run_ids_pr_session(con, (datetime.now(UTC) - timedelta(hours=1)).isoformat())
        assert ud == {"auto-recurring-x": ["autonomous-a"]}

    def test_ulaesbar_nyttelast_springes_over(self):
        con = self._con()
        con.execute("INSERT INTO events VALUES (?,?,?,?)", (
            1, "runtime.autonomous_run_started", "{ikke json",
            datetime.now(UTC).isoformat()))
        con.commit()
        assert cd.run_ids_pr_session(con, (datetime.now(UTC) - timedelta(hours=1)).isoformat()) == {}

    def test_uden_events_tabel_giver_tom_ikke_krak(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        assert cd.run_ids_pr_session(con, "2020-01-01T00:00:00+00:00") == {}


class TestSvarLeveretEksternt:
    """Plet 3: et PAENT afsluttet run daemper fundet — alt andet goer ikke."""

    @staticmethod
    def _con(rows):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE visible_runs (run_id TEXT, status TEXT, error TEXT, "
                    "started_at TEXT, finished_at TEXT)")
        for r in rows:
            con.execute("INSERT INTO visible_runs VALUES (?,?,?,?,?)", r)
        con.commit()
        return con

    def test_completed_uden_fejl_daekker_tidspunktet(self):
        start = datetime(2026, 10, 14, 4, 14, 28, tzinfo=UTC)
        slut = datetime(2026, 10, 14, 4, 15, 31, tzinfo=UTC)
        con = self._con([("r1", "completed", "", start.isoformat(), slut.isoformat())])
        midt = datetime(2026, 10, 14, 4, 15, 28, tzinfo=UTC)
        assert cd.svar_leveret_eksternt(con, ["r1"], midt) == "r1"

    def test_fejlet_run_daemper_ikke(self):
        start = datetime(2026, 10, 14, 4, 14, tzinfo=UTC)
        slut = datetime(2026, 10, 14, 4, 16, tzinfo=UTC)
        con = self._con([("r1", "failed", "boom", start.isoformat(), slut.isoformat())])
        assert cd.svar_leveret_eksternt(
            con, ["r1"], datetime(2026, 10, 14, 4, 15, tzinfo=UTC)) is None

    def test_completed_med_fejlstreng_daemper_ikke(self):
        start = datetime(2026, 10, 14, 4, 14, tzinfo=UTC)
        slut = datetime(2026, 10, 14, 4, 16, tzinfo=UTC)
        con = self._con([("r1", "completed", "noget gik galt",
                          start.isoformat(), slut.isoformat())])
        assert cd.svar_leveret_eksternt(
            con, ["r1"], datetime(2026, 10, 14, 4, 15, tzinfo=UTC)) is None

    def test_tidspunkt_uden_for_vinduet_daemper_ikke(self):
        start = datetime(2026, 10, 14, 4, 14, tzinfo=UTC)
        slut = datetime(2026, 10, 14, 4, 15, tzinfo=UTC)
        con = self._con([("r1", "completed", "", start.isoformat(), slut.isoformat())])
        assert cd.svar_leveret_eksternt(
            con, ["r1"], datetime(2026, 10, 14, 5, 0, tzinfo=UTC)) is None

    def test_ingen_runs_giver_none(self):
        con = self._con([])
        assert cd.svar_leveret_eksternt(con, [], datetime.now(UTC)) is None


class TestPlet3EndeTilEnde:
    """Regressionen: nattens falske positiv maa ikke kunne genskabes."""

    @staticmethod
    def _scratch(tmp_path, *, med_completed_run):
        p = tmp_path / "scratch.db"
        con = sqlite3.connect(str(p))
        con.execute("CREATE TABLE chat_messages (message_id TEXT, session_id TEXT, "
                    "role TEXT, content TEXT, created_at TEXT)")
        con.execute("CREATE TABLE visible_runs (run_id TEXT, status TEXT, started_at TEXT, "
                    "error TEXT, lane TEXT, provider TEXT, model TEXT, finished_at TEXT)")
        con.execute("CREATE TABLE runtime_state_kv (key TEXT, value_json TEXT, updated_at TEXT)")
        con.execute("CREATE TABLE events (id INTEGER, kind TEXT, payload_json TEXT, created_at TEXT)")
        # Sessionen gik tavs for 30 min siden — praecis som i nat: kun tool-raekker.
        tavs = datetime.now(UTC) - timedelta(minutes=30)
        con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
                    ("m1", "auto-recurring-x", "tool",
                     "[tool_result:abc]\n[notify_user]: leveret", tavs.isoformat()))
        con.execute("INSERT INTO events VALUES (?,?,?,?)", (
            1, "runtime.autonomous_run_started",
            json.dumps({"run_id": "autonomous-a", "session_id": "auto-recurring-x"}),
            (tavs - timedelta(seconds=20)).isoformat()))
        if med_completed_run:
            con.execute("INSERT INTO visible_runs VALUES (?,?,?,?,?,?,?,?)",
                        ("autonomous-a", "completed",
                         (tavs - timedelta(seconds=20)).isoformat(),
                         "", "primary", "ollama", "m",
                         (tavs + timedelta(seconds=10)).isoformat()))
        con.commit()
        con.close()
        return p

    def _koer(self, p, tmp_path, monkeypatch):
        fundet = []
        monkeypatch.setattr(cd, "DB", str(p))
        monkeypatch.setattr(cd, "STATE", str(tmp_path / "seen.json"))
        monkeypatch.setattr(cd, "LOG", str(tmp_path / "log.txt"))
        monkeypatch.setattr(cd, "api_restarted_near", lambda w: None)
        monkeypatch.setattr(
            "core.runtime.db_central_incidents.record_central_incident",
            lambda **kw: fundet.append(kw))
        assert cd.main() == 0
        return fundet

    def test_svar_i_anden_session_er_ikke_et_fund(self, tmp_path, monkeypatch):
        p = self._scratch(tmp_path, med_completed_run=True)
        fundet = self._koer(p, tmp_path, monkeypatch)
        assert fundet == [], "et svar leveret i en anden session maa ikke blive et fund"

    def test_uden_completed_run_er_fundet_bevaret(self, tmp_path, monkeypatch):
        """Negativ kontrol: uden det paene run SKAL fundet komme."""
        p = self._scratch(tmp_path, med_completed_run=False)
        fundet = self._koer(p, tmp_path, monkeypatch)
        assert len(fundet) == 1, "uden et afsluttet run er det stadig en tavs cutoff"
