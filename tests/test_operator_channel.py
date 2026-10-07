"""Operator-kanalen: bash gaar over paa Bjoerns maskine — kun for Bjoern.

Kanalen fjerner en godkendelse pr. kald. Det er kun forsvarligt saa laenge
owner-gaten holder ved HVER indgang, saa det er dét disse tests handler om.
"""
import time

import pytest

from core.services import operator_channel as oc


@pytest.fixture(autouse=True)
def _ren_tilstand(monkeypatch):
    """Kanalens lager i hukommelsen.

    `_opdater_post` skriver ÉN nøgle (målt og rettet 7/10-2026). Før skrev
    `_save` HELE ordbogen tilbage, og netop det kunne slette en anden sessions
    kanal. Stubben spejler derfor den atomare form — ikke den gamle.
    """
    st: dict = {}
    monkeypatch.setattr(oc, "_load", lambda: dict(st))

    def _gem(sid, post):
        st[str(sid)] = dict(post)

    monkeypatch.setattr(oc, "_opdater_post", _gem)
    yield st


def test_kun_owner_kan_aabne():
    r = oc.open_channel("s1", is_owner=False)
    assert r["status"] == "error"
    assert oc.is_open("s1") is False


def test_owner_kan_aabne_og_lukke():
    assert oc.open_channel("s1", is_owner=True)["open"] is True
    assert oc.is_open("s1") is True
    assert oc.close_channel("s1", is_owner=True)["open"] is False
    assert oc.is_open("s1") is False


def test_ikke_owner_kan_ikke_lukke_andres_kanal():
    oc.open_channel("s1", is_owner=True)
    assert oc.close_channel("s1", is_owner=False)["status"] == "error"
    assert oc.is_open("s1") is True


def test_kanalen_udloeber_af_sig_selv(_ren_tilstand):
    oc.open_channel("s1", is_owner=True)
    _ren_tilstand["s1"]["aabnet"] = time.time() - (oc._TTL_S + 1)
    assert oc.is_open("s1") is False, "en glemt kanal maa ikke staa aaben i morgen"


def test_kanalen_er_pr_session():
    oc.open_channel("s1", is_owner=True)
    assert oc.is_open("s2") is False


def test_reroute_sker_ikke_for_ikke_owner(monkeypatch):
    oc.open_channel("s1", is_owner=True)
    kaldt = []
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda n, a: kaldt.append(n) or {"status": "ok"})
    assert oc.maybe_reroute_bash("ls /", None, is_owner=False, session_id="s1") is None
    assert kaldt == []


def test_reroute_sker_ikke_naar_kanalen_er_lukket(monkeypatch):
    kaldt = []
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda n, a: kaldt.append(n) or {"status": "ok"})
    assert oc.maybe_reroute_bash("ls /", None, is_owner=True, session_id="s1") is None
    assert kaldt == []


def test_aaben_kanal_sender_bash_over_broen(monkeypatch):
    oc.open_channel("s1", is_owner=True)
    set_kald = {}

    def _falsk(navn, args):
        set_kald["navn"] = navn
        set_kald["args"] = args
        return {"status": "ok", "text": "fra hans maskine"}

    monkeypatch.setattr("core.tools.simple_tools.execute_tool", _falsk)
    r = oc.maybe_reroute_bash("ls /media/projects", "/tmp",
                              is_owner=True, session_id="s1")
    assert set_kald["navn"] == "operator_bash"
    assert set_kald["args"]["command"] == "ls /media/projects"
    assert set_kald["args"]["cwd"] == "/tmp"
    assert r["via"] == "operator-kanal"


def test_broen_nede_bliver_en_fejl_ikke_et_styrt(monkeypatch):
    oc.open_channel("s1", is_owner=True)

    def _sprang(navn, args):
        raise RuntimeError("broen svarer ikke")

    monkeypatch.setattr("core.tools.simple_tools.execute_tool", _sprang)
    r = oc.maybe_reroute_bash("ls", None, is_owner=True, session_id="s1")
    assert r["status"] == "error"
    assert "kunne ikke nå din maskine" in r["error"]


def test_aabning_kvitterer_ikke_hvis_tilstanden_ikke_blev_gemt(monkeypatch):
    def _db_nede(_sid, _post):
        raise OSError("database unavailable")

    monkeypatch.setattr(oc, "_opdater_post", _db_nede)
    r = oc.open_channel("s1", is_owner=True)
    assert r["status"] == "error"
    assert r.get("open") is not True


def test_tilstandslaesning_skjuler_ikke_db_fejl(monkeypatch):
    monkeypatch.undo()
    from core.runtime.db_core import clear_runtime_state_cache
    clear_runtime_state_cache()

    def _db_nede(*_args, **_kwargs):
        raise OSError("database unavailable")

    monkeypatch.setattr("core.runtime.db_core.connect", _db_nede)
    with pytest.raises(OSError, match="database unavailable"):
        oc._load()


def test_bash_koerer_ikke_paa_server_naar_kanaltilstand_ikke_kan_laeses(monkeypatch):
    from core.tools import simple_tools_web as web

    def _db_nede():
        raise OSError("database unavailable")

    monkeypatch.setattr(oc, "_load", _db_nede)
    monkeypatch.setattr(oc, "current_is_owner", lambda: True)
    monkeypatch.setattr(web, "_get_or_open_default_bash_session",
                        lambda: pytest.fail("bash må ikke køre på serveren"))
    r = web._exec_bash({"command": "echo workstation", "_runtime_session_id": "s1"})
    assert r["status"] == "error"
    assert "operator-kanal" in r["error"]


def test_hint_kun_naar_stien_peger_paa_hans_maskine():
    assert oc.closed_channel_hint("ls /media/projects", None,
                                  is_owner=True, session_id="s1")
    assert oc.closed_channel_hint("ls /etc", None,
                                  is_owner=True, session_id="s1") == ""


def test_hint_tier_naar_kanalen_allerede_er_aaben():
    oc.open_channel("s1", is_owner=True)
    assert oc.closed_channel_hint("ls /media/projects", None,
                                  is_owner=True, session_id="s1") == ""


def test_owner_gaten_fejler_LUKKET(monkeypatch):
    """Kan rollen ikke afgoeres, er svaret nej — ikke ja."""
    def _sprang():
        raise RuntimeError("ingen kontekst")

    monkeypatch.setattr("core.identity.workspace_context.current_role", _sprang)
    assert oc.current_is_owner() is False


# ── Kanalen falder og genopstår (målt og fixet 5/10-2026) ───────────────────
#
# Bjørn: «fiks kanalen så du får besked med det samme den ryger, og en
# reconnect-mekanisme så medmindre du selv har lukket kanalen eller jeg har, så
# reconnecter den.»
#
# To ting blev målt samme dag: (1) BEGGE opslags-kilder i `current_session_id`
# var døde imports — `visible_run_context` og `chat_sessions.
# current_session_id_ctx` findes ikke — så nøglen blev `_default` for ALLE
# sessioner, og én sessions lukning faldt en anden i ryggen midt i en tur;
# (2) når kanalen faldt, kørte bash på containeren uden et ord.


def _udloeb(st, sid="s1", *, alder_s=None):
    """Åbn kanalen og skub `aabnet` tilbage så TTL er passeret."""
    oc.open_channel(sid, is_owner=True)
    st[sid]["aabnet"] = time.time() - (oc._TTL_S + (alder_s if alder_s else 60))


def test_besked_naar_kanalen_faldt_af_sig_selv(_ren_tilstand):
    """Faldt den af sig selv og er for gammel til at genopstå, skal svaret SIGE det."""
    _udloeb(_ren_tilstand, alder_s=oc._GENOPRET_FRIST_S + 3600)
    note = oc.kanal_note("s1")
    assert "udløb" in note
    assert "serveren" in note


def test_ingen_besked_naar_kanalen_er_aaben():
    oc.open_channel("s1", is_owner=True)
    assert oc.kanal_note("s1") == ""


def test_ingen_besked_naar_bevidst_lukket(_ren_tilstand):
    """Bjørn lukkede den selv — så er der intet at advare om."""
    oc.open_channel("s1", is_owner=True)
    oc.close_channel("s1", is_owner=True)
    assert oc.kanal_note("s1") == ""


def test_lukket_kanal_genopstaar_ikke(monkeypatch):
    """Den vigtigste grænse: bevidst lukning skal RESPEKTERES."""
    oc.open_channel("s1", is_owner=True)
    oc.close_channel("s1", is_owner=True)
    kaldt = []
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda n, a: kaldt.append(n) or {"status": "ok"})
    assert oc.maybe_reroute_bash("ls", None, is_owner=True, session_id="s1") is None
    assert kaldt == [], "en bevidst lukket kanal maa ikke genaabne sig selv"


def test_udloebet_kanal_genopstaar_naar_broen_svarer(_ren_tilstand, monkeypatch):
    _udloeb(_ren_tilstand)
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda n, a: {"status": "ok", "text": "fra hans maskine"})
    r = oc.maybe_reroute_bash("ls /media/projects", None,
                              is_owner=True, session_id="s1")
    assert r is not None, "en udloebet kanal skal forsoeges genoprettet"
    assert r["kanal"]["genaabnet"] is True
    assert oc.is_open("s1") is True, "broen svarede — kanalen skal staa aaben igen"


def test_fejlet_fornyelse_skjuler_ikke_udfoert_fjernkommando(_ren_tilstand, monkeypatch):
    _udloeb(_ren_tilstand)
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda n, a: {"status": "ok", "text": "udført på workstation"})
    monkeypatch.setattr(oc, "_opdater_post",
                        lambda _sid, _post: (_ for _ in ()).throw(OSError("DB nede")))
    r = oc.maybe_reroute_bash("echo once", None, is_owner=True, session_id="s1")
    assert r["status"] == "ok"
    assert r["text"] == "udført på workstation"
    assert "ikke gemmes" in r["kanal"]["note"]


def test_udloebet_kanal_fornyes_IKKE_naar_broen_er_nede(_ren_tilstand, monkeypatch):
    """En kanal der ikke kan naa sin maskine skal ikke staa aaben."""
    _udloeb(_ren_tilstand)

    def _sprang(n, a):
        raise RuntimeError("broen svarer ikke")

    monkeypatch.setattr("core.tools.simple_tools.execute_tool", _sprang)
    r = oc.maybe_reroute_bash("ls", None, is_owner=True, session_id="s1")
    assert r["status"] == "error"
    assert oc.is_open("s1") is False, "fejlede broen, maa kanalen ikke fornyes"


def test_gammel_kanal_genopstaar_ikke(_ren_tilstand, monkeypatch):
    """En kanal fra sidste uge maa ikke vaagne af en tilfaeldig kommando."""
    _udloeb(_ren_tilstand, alder_s=oc._GENOPRET_FRIST_S + 7200)
    kaldt = []
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda n, a: kaldt.append(n) or {"status": "ok"})
    assert oc.maybe_reroute_bash("ls", None, is_owner=True, session_id="s1") is None
    assert kaldt == []


def test_aabning_og_status_bruger_kaldets_eget_id():
    """Rod-aarsagen: noeglen kom fra to doede kilder og blev `_default` for alle."""
    from core.tools.simple_tools_native import _exec_operator_channel
    oc.open_channel("session-A", is_owner=True)
    r = _exec_operator_channel({"_runtime_session_id": "session-A",
                                "action": "status"})
    assert r["open"] is True, "aabningen skal se kanalen under kaldets eget id"
    # Og et ANDET id maa ikke se den — det var netop fejlen at alle delte én.
    r2 = _exec_operator_channel({"_runtime_session_id": "session-B",
                                 "action": "status"})
    assert r2["open"] is False, "to sessioner maa ikke dele én kanal"


def test_bash_sender_kaldets_eget_id(monkeypatch):
    """Bash skal slaa kanalen op under PRAECIS det id executoren gav kaldet."""
    from core.tools import simple_tools_web as web
    from core.services import operator_channel as _oc
    fanget = {}

    def _fang(command, cwd, *, is_owner, session_id):
        fanget["sid"] = session_id
        return None

    monkeypatch.setattr(_oc, "maybe_reroute_bash", _fang)
    monkeypatch.setattr(_oc, "kanal_note", lambda sid: "")
    web._exec_bash({"command": "echo hej", "_runtime_session_id": "session-A"})
    assert fanget.get("sid") == "session-A"


def test_bash_svaret_baerer_noten_paa_BEGGE_shell_veje(monkeypatch):
    """Noten skal staa PAA svaret — og paa BEGGE veje.

    Den mest brugte shell-vej var engang den mest tavse (K10). En test der kun
    rammer den ene gren beviser kun den ene gren.
    """
    from core.tools import simple_tools_web as web
    from core.services import operator_channel as _oc
    monkeypatch.setattr(_oc, "maybe_reroute_bash", lambda *a, **k: None)
    monkeypatch.setattr(_oc, "kanal_note", lambda sid: "[operator-kanal] note")

    # (a) den vedvarende, delte shell
    monkeypatch.setattr(web, "_get_or_open_default_bash_session", lambda: "sess-1")
    monkeypatch.setattr("core.tools.bash_session._exec_bash_session_run",
                        lambda a: {"status": "ok", "exit_code": 0, "output": "hej"})
    r1 = web._exec_bash({"command": "echo hej"})
    assert r1.get("kanal", {}).get("note") == "[operator-kanal] note", "vedvarende vej"

    # (b) reserve-vejen (engangs-subprocess)
    def _ingen_daemon():
        raise RuntimeError("ingen daemon")

    monkeypatch.setattr(web, "_get_or_open_default_bash_session", _ingen_daemon)
    r2 = web._exec_bash({"command": "echo hej"})
    assert r2.get("kanal", {}).get("note") == "[operator-kanal] note", "reserve-vejen"


def test_lukning_bevarer_sporet_saa_bevidst_kan_skelnes(_ren_tilstand):
    """Uden sporet kan «lukket af et menneske» ikke skelnes fra «aldrig aabnet»."""
    oc.open_channel("s1", is_owner=True)
    oc.close_channel("s1", is_owner=True)
    assert _ren_tilstand["s1"]["open"] is False


def test_udloebet_er_falsk_for_bevidst_lukket(_ren_tilstand):
    """Genopretningen maa ikke kunne se en bevidst lukket kanal som udloebet.

    Posten skal baere BAADE et gammelt `aabnet` OG `open: False` — ellers
    bestaar testen af den forkerte grund (et manglende `aabnet` giver ogsaa
    False, men af en anden aarsag end den vi vil maale).
    """
    _ren_tilstand["s1"] = {"open": False, "aabnet": time.time() - (oc._TTL_S + 60)}
    assert oc._udloebet(_ren_tilstand["s1"]) is False


# ── «Kanalen glapper» — målt og rettet 7/10-2026 ────────────────────────────
#
# Bjørn: «operator kanalen.. den er virkelig ustabil og glipper ofte».
# Målt: `_load()` læste gennem en 2-sekunders cache, og `_save()` skrev HELE
# ordbogen tilbage. To processer (api + runtime) med hver sit forældede
# billede kunne derfor skrive hinandens arbejde væk — en frisk åbning blev
# slettet af en anden skrivers gamle kopi, uden at nogen havde lukket den.


def test_aabning_sletter_ikke_en_anden_kanal(monkeypatch, tmp_path):
    """Den maalte fejlform: hel-ordbog-skriv ovenpaa et foraeldet billede.

    Testen maaler den RIGTIGE skrivning mod en isoleret DB — ikke hukommelses-
    stubben fra `_ren_tilstand`. En stub der tilfaeldigtvis skriver atomart
    ville bestaa uden at sige noget om den kode der korer i drift.
    """
    import json
    import sqlite3

    import core.runtime.db_core as dbc

    monkeypatch.undo()          # drop hukommelses-stubben
    p = tmp_path / "kanal.db"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE runtime_state_kv (key TEXT PRIMARY KEY, "
              "value_json TEXT NOT NULL, updated_at TEXT NOT NULL)")
    c.commit()
    c.close()
    monkeypatch.setattr(dbc, "DB_PATH", p)

    oc.open_channel("s1", is_owner=True)

    # En anden skriver (fx runtime-processen) har et billede fra FØR s1 blev
    # åbnet. Skriver den sit billede tilbage, maa s1 ikke forsvinde.
    monkeypatch.setattr(oc, "_load", lambda: {"s1": {"open": False, "lukket": 1.0}})
    oc.open_channel("s2", is_owner=True)

    conn = sqlite3.connect(p)
    row = conn.execute("SELECT value_json FROM runtime_state_kv WHERE key = ?",
                       (oc._KEY,)).fetchone()
    conn.close()
    st = json.loads(row[0])
    assert st["s1"]["open"] is True, \
        "s1 blev slettet af et forældet billede — det er «kanalen glapper»"
    assert st["s2"]["open"] is True


def test_note_fejl_blokerer_ikke_lokal_bash(monkeypatch):
    """Noten er kosmetisk: fejler den, skal kommandoen stadig køre lokalt.

    Den laa foer inde i fail-closed-blokken, saa et DB-hikke blokerede AL bash
    — ogsaa naar kanalen med sikkerhed var lukket og kommandoen hoerte hjemme
    her. Det er en spaerring af hans arbejdsredskab for en kommentars skyld.
    """
    from core.tools import simple_tools_web as web
    from core.services import operator_channel as _oc

    monkeypatch.setattr(_oc, "maybe_reroute_bash", lambda *a, **k: None)
    monkeypatch.setattr(_oc, "kanal_note",
                        lambda sid: (_ for _ in ()).throw(OSError("DB nede")))
    monkeypatch.setattr(web, "_get_or_open_default_bash_session", lambda: "sess-1")
    monkeypatch.setattr("core.tools.bash_session._exec_bash_session_run",
                        lambda a: {"status": "ok", "exit_code": 0, "output": "lokal"})
    r = web._exec_bash({"command": "echo lokal", "_runtime_session_id": "s1"})
    assert r.get("status") == "ok", r
    assert "lokal" in str(r)


def test_open_uden_session_id_afvises(monkeypatch):
    """Et kald uden id maa ikke skrive `_default` — bash bruger `chat-<session>`.

    Maalt 7/10-2026: desk'ens kontakt og mobilens «Luk» sendte intet id, saa
    panelet viste «Aaben» om en kanal bash aldrig saa. En tavs no-op er vaerre
    end et afslag, fordi den ligner en kvittering.
    """
    from fastapi import HTTPException

    from apps.api.jarvis_api.routes import workbench as wb

    monkeypatch.setattr(oc, "current_session_id", lambda: "_default")
    with pytest.raises(HTTPException) as e:
        wb._session_id({}, kraev=True)
    assert e.value.status_code == 400
    # Med et id skal kaldet glide igennem — og en laesning uden krav maa ikke kaste.
    assert wb._session_id({"session_id": "chat-1"}, kraev=True) == "chat-1"
    assert wb._session_id({}) == "_default"
