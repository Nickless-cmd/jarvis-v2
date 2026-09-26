"""De aktive opgaver — fra begge kilder."""
import pytest

from core.services import background_jobs as bj

_ægte_scout_jobs = bj._scout_jobs
_ægte_shell_sessioner = bj._shell_sessioner


def _bro(stdout, status="ok"):
    def _exec(navn, args):
        assert navn == "operator_bash"
        return {"status": status, "result": {"stdout": stdout}}
    return _exec


@pytest.fixture(autouse=True)
def ingen_supervisor(monkeypatch):
    monkeypatch.setattr(bj, "_supervisor_jobs", lambda: [])
    monkeypatch.setattr(bj, "_scout_jobs", lambda: [])
    # Shell-sessionerne slaas fra som de to andre kilder. De tests der
    # handler OM dem taender dem igen med deres egen patch.
    monkeypatch.setattr(bj, "_shell_sessioner", lambda: [])


def test_en_standset_shell_er_PAUSET_ikke_koerende(monkeypatch):
    # `ps -o stat=` giver T for en standset proces. Uden det felt skulle
    # pause-tilstanden gaettes.
    monkeypatch.setattr(bj, "_nu", lambda: 1_000_100.0)
    j = bj.liste(exec_fn=_bro("bg_a|4242|T||1000000|sleep 5\n"))["jobs"]
    assert [x["status"] for x in j] == ["paused"]
    assert j[0]["sekunder"] == 100
    assert j[0]["can_pause"] is True


def test_en_LYKKEDES_opgave_forsvinder(monkeypatch):
    # Bjoern: «de skal automatisk forsvinde naar opgave er fuldfoert».
    monkeypatch.setattr(bj, "_nu", lambda: 1_000_100.0)
    assert bj.liste(exec_fn=_bro("bg_a|1|dead|0|1000000|ok\n"))["jobs"] == []


def test_en_FEJLET_opgave_bliver_staaende(monkeypatch):
    # Det er ikke «fuldfoert», det er gaaet galt - og det er netop dem man
    # skal se. Skjulte man dem, ville en fejl stille forsvinde.
    monkeypatch.setattr(bj, "_nu", lambda: 1_000_100.0)
    j = bj.liste(exec_fn=_bro("bg_a|1|dead|3|1000000|boom\n"))["jobs"]
    assert len(j) == 1 and j[0]["exit_code"] == 3


def test_en_DOED_bro_siges_hoejt_frem_for_at_lade_listen_se_tom_ud(monkeypatch):
    # «Vi ved ikke hvad der koerer derovre» og «der koerer ingenting» er stik
    # modsat.
    ud = bj.liste(exec_fn=_bro("", status="error"))
    assert ud["jobs"] == [] and ud["bridge_ok"] is False


def test_en_levende_bro_med_tom_liste_er_IKKE_en_fejl(monkeypatch):
    ud = bj.liste(exec_fn=_bro(""))
    assert ud["jobs"] == [] and ud["bridge_ok"] is True


def test_supervisor_og_operator_staar_i_SAMME_liste(monkeypatch):
    monkeypatch.setattr(bj, "_supervisor_jobs", lambda: [{
        "id": "grid-bot", "kilde": "supervisor", "navn": "grid-bot",
        "kommando": "python3 -m grid", "status": "running", "pid": 7,
        "sekunder": 900, "exit_code": None, "can_pause": True,
    }])
    monkeypatch.setattr(bj, "_nu", lambda: 1_000_100.0)
    j = bj.liste(exec_fn=_bro("bg_a|9|S||1000000|npm test\n"))["jobs"]
    assert {x["kilde"] for x in j} == {"supervisor", "operator"}


def test_laengst_koerende_staar_oeverst(monkeypatch):
    monkeypatch.setattr(bj, "_nu", lambda: 1_000_100.0)
    ud = "bg_kort|1|S||1000090|kort\nbg_lang|2|S||1000000|lang\n"
    j = bj.liste(exec_fn=_bro(ud))["jobs"]
    assert [x["id"] for x in j] == ["bg_lang", "bg_kort"]


def test_vroevlede_linjer_springes_over_frem_for_at_braekke_listen(monkeypatch):
    monkeypatch.setattr(bj, "_nu", lambda: 1_000_100.0)
    j = bj.liste(exec_fn=_bro("noget vrøvl\n\nbg_a|1|S||1000000|ok\n"))["jobs"]
    assert [x["id"] for x in j] == ["bg_a"]


def test_UDEN_bro_vises_kun_supervisor_og_broen_meldes_ok(monkeypatch):
    # Kalderen der slet ikke HAR en bro (fx en intern kalder) skal ikke se
    # «bro nede» - den spurgte ikke.
    monkeypatch.setattr(bj, "_supervisor_jobs", lambda: [])
    assert bj.liste()["bridge_ok"] is True



# ── scout-agenter (17/9-2026) ───────────────────────────────────────────

def _scout(**kw):
    base = {"agent_id": "agent-" + "a" * 32, "role": "researcher", "tool_policy": "read-only-runtime",
            "status": "running", "goal": "Hvor bor cheap lane-værnet?\n\nKig flere steder.",
            "created_at": "2026-09-17T17:00:00Z", "updated_at": "2026-09-17T17:00:30Z", "completed_at": None}
    base.update(kw)
    return base


def test_en_koerende_scout_vises_som_baggrundsjob(monkeypatch):
    """Bjørn: «scout agenter [skal] vises i baggrundsjob panel i desk»."""
    import core.runtime.db_agent_runtime as db
    from datetime import datetime
    monkeypatch.setattr(bj, "_scout_jobs", _ægte_scout_jobs)
    monkeypatch.setattr(db, "list_agent_registry_entries", lambda **kw: [
        _scout(), _scout(agent_id="agent-" + "b" * 32, role="planner"),
        _scout(agent_id="agent-" + "c" * 32, tool_policy="full"),
    ])
    monkeypatch.setattr(bj, "_nu", lambda: datetime.fromisoformat("2026-09-17T17:00:42+00:00").timestamp())
    j = bj.liste()["jobs"]
    assert len(j) == 1, "kun scout-agenter — ikke andre agent-roller"
    assert j[0]["kilde"] == "agent" and j[0]["status"] == "running"
    assert j[0]["kommando"] == "Hvor bor cheap lane-værnet?"
    assert j[0]["sekunder"] == 42 and j[0]["can_pause"] is False


def test_faerdig_scout_forsvinder_og_fejlet_bliver_staaende(monkeypatch):
    import core.runtime.db_agent_runtime as db
    from datetime import datetime
    monkeypatch.setattr(bj, "_scout_jobs", _ægte_scout_jobs)
    monkeypatch.setattr(db, "list_agent_registry_entries", lambda **kw: [
        _scout(status="completed", completed_at="2026-09-17T17:00:20Z"),
        _scout(agent_id="agent-" + "d" * 32, status="failed", completed_at="2026-09-17T17:00:25Z"),
        _scout(agent_id="agent-" + "e" * 32, status="completed", completed_at="2026-09-17T12:00:00Z"),
    ])
    monkeypatch.setattr(bj, "_nu", lambda: datetime.fromisoformat("2026-09-17T17:05:00+00:00").timestamp())
    aktive = bj.liste()["jobs"]
    assert [x["exit_code"] for x in aktive] == [1], "en fejlet scout skal ses; en lykkedes skal ikke"
    alle = bj.liste(kun_aktive=False)["jobs"]
    assert len(alle) == 2, "en scout der blev færdig for 5 timer siden ældes ud"
    assert {x["sekunder"] for x in alle} == {20, 25}


def test_et_brudt_register_vaelter_ikke_panelet(monkeypatch):
    import core.runtime.db_agent_runtime as db
    monkeypatch.setattr(bj, "_scout_jobs", _ægte_scout_jobs)
    monkeypatch.setattr(db, "list_agent_registry_entries",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")))
    monkeypatch.setattr(bj, "_supervisor_jobs", lambda: [{"id": "x", "kilde": "supervisor", "status": "running",
                                                          "sekunder": 1, "exit_code": None}])
    assert [x["id"] for x in bj.liste()["jobs"]] == ["x"]


# ── Åbne shell-sessioner (26/9-2026) ────────────────────────────────────
#
# Bjoern: «hans bash og operator_bash [skal] ramme baggrundsjobs panelet...
# simple vising med en stop knap». De to vaerktoejsfiler er URØRT; panelet
# bruger deres egne `list` og `close`.
#
# NB: den ægte funktion sættes tilbage med `_ægte_shell_sessioner` — IKKE med
# `monkeypatch.undo()`, som ville rulle conftests produktions-værn tilbage
# sammen med autouse-fiksturet her.


def _taend_shells(monkeypatch):
    monkeypatch.setattr(bj, "_shell_sessioner", _ægte_shell_sessioner)


def _monter_lokal(monkeypatch, sessioner, *, pid=4242, kaldt=None):
    """Attrap for bash_session: pid-porten og daemonens svar."""
    import core.tools.bash_session as bs
    def _list(_args):
        if kaldt is not None:
            kaldt.append("list")
        return {"status": "ok", "sessions": sessioner}
    monkeypatch.setattr(bs, "_read_daemon_pid", lambda: pid)
    monkeypatch.setattr(bs, "_pid_is_our_daemon", lambda _p: pid is not None)
    monkeypatch.setattr(bs, "_exec_bash_session_list", _list)


def _monter_operator(monkeypatch, sessioner):
    import core.tools.operator_bash_session as ops
    monkeypatch.setattr(ops, "_exec_operator_bash_session_list",
                        lambda _a: {"status": "ok", "sessions": sessioner})


def test_en_aaben_shell_paa_serveren_vises_som_baggrundsjob(monkeypatch):
    _taend_shells(monkeypatch)
    _monter_lokal(monkeypatch, [{"session_id": "bsh-115cd823bf",
                                 "alive": True, "idle_seconds": 606}])
    _monter_operator(monkeypatch, [])
    j = bj.liste()["jobs"]
    assert len(j) == 1
    assert j[0]["id"] == "bsh-115cd823bf"
    assert j[0]["kilde"] == "shell"
    assert j[0]["status"] == "running"
    assert j[0]["sekunder"] == 606
    # Der er ingen pause: en kommando i sessionen blokerer kaldet og er
    # loftet til 300 s, saa der findes ikke et oejeblik at standse den i.
    assert j[0]["can_pause"] is False


def test_panelet_maa_ikke_STARTE_daemonen_for_at_kigge_efter_den(monkeypatch):
    # `_exec_bash_session_list` gaar gennem `_ensure_daemon_running()`, som
    # spawner en daemon naar der ikke er nogen. Panelet poller hvert femte
    # sekund; uden pid-porten ville visningen SKABE det den observerer.
    _taend_shells(monkeypatch)
    kaldt = []
    _monter_lokal(monkeypatch, [{"session_id": "bsh-0123456789",
                                 "alive": True, "idle_seconds": 1}],
                  pid=None, kaldt=kaldt)
    _monter_operator(monkeypatch, [])
    assert bj.liste()["jobs"] == []
    assert kaldt == [], "der blev lavet IPC selv om der ingen daemon var"


def test_en_doed_shell_udelades_frem_for_at_staa_som_faerdig(monkeypatch):
    # Daemonen beholder en lukket session til den reapes. Den kan ikke
    # stoppes (stop-knappen vises ikke paa noget faerdigt) og kan ikke
    # ryddes — den ville bare ligge der for evigt.
    _taend_shells(monkeypatch)
    _monter_lokal(monkeypatch, [{"session_id": "bsh-doed000000",
                                 "alive": False, "idle_seconds": 9}])
    _monter_operator(monkeypatch, [])
    assert bj.liste(kun_aktive=False)["jobs"] == []


def test_en_operator_shell_siger_HANS_maskine_ikke_serveren(monkeypatch):
    _taend_shells(monkeypatch)
    _monter_lokal(monkeypatch, [], pid=None)
    _monter_operator(monkeypatch, [{"session_id": "opsess-0123456789ab",
                                    "cwd": "/media/projects", "idle_s": 12.4}])
    j = bj.liste()["jobs"]
    assert len(j) == 1
    assert j[0]["kilde"] == "shell_operator"
    assert "/media/projects" in j[0]["kommando"]
    # Tallet er UBERØRT tid, ikke levetid: hverken daemonen eller
    # operator-dict'en gemmer et foedselstidspunkt.
    assert j[0]["sekunder"] == 12


def test_den_ene_shell_kilde_maa_ikke_kunne_tie_den_anden(monkeypatch):
    _taend_shells(monkeypatch)
    import core.tools.bash_session as bs
    def _sprang(_args):
        raise RuntimeError("daemonen svarede ikke")
    monkeypatch.setattr(bs, "_read_daemon_pid", lambda: 4242)
    monkeypatch.setattr(bs, "_pid_is_our_daemon", lambda _p: True)
    monkeypatch.setattr(bs, "_exec_bash_session_list", _sprang)
    _monter_operator(monkeypatch, [{"session_id": "opsess-0123456789ab",
                                    "cwd": "~", "idle_s": 1}])
    assert [x["kilde"] for x in bj.liste()["jobs"]] == ["shell_operator"]


def test_to_doede_shell_kilder_vaelter_ikke_de_oevrige_jobs(monkeypatch):
    # Shell-sessionerne er en TILFOEJELSE til panelet, ikke dets fundament:
    # supervisor- og operator-jobbene skal stadig vises.
    _taend_shells(monkeypatch)
    monkeypatch.setattr(bj, "_supervisor_jobs",
                        lambda: [{"id": "grid-bot", "kilde": "supervisor",
                                  "navn": "grid-bot", "kommando": "bot",
                                  "status": "running", "pid": 7, "sekunder": 5,
                                  "exit_code": None, "can_pause": True}])
    import core.tools.bash_session as bs
    import core.tools.operator_bash_session as ops
    def _bang(*_a, **_k):
        raise RuntimeError("nede")
    monkeypatch.setattr(bs, "_read_daemon_pid", _bang)
    monkeypatch.setattr(ops, "_exec_operator_bash_session_list", _bang)
    assert [x["id"] for x in bj.liste()["jobs"]] == ["grid-bot"]


def test_arbejds_shellen_maerkes_op_saa_den_ikke_ligner_en_stray(monkeypatch):
    # Det almindelige `bash`-vaerktoej genbruger EN delt session. Den staar i
    # daemonens liste side om side med dem der er aabnet med vilje, og et stop
    # paa den smider Jarvis' cd/env/venv vaek midt i en opgave.
    _taend_shells(monkeypatch)
    import core.tools.simple_tools_web as stw
    monkeypatch.setattr(stw, "_DEFAULT_BASH_SESSION_ID", "bsh-aaaaaaaaaa", raising=False)
    _monter_lokal(monkeypatch, [
        {"session_id": "bsh-aaaaaaaaaa", "alive": True, "idle_seconds": 4},
        {"session_id": "bsh-bbbbbbbbbb", "alive": True, "idle_seconds": 9},
    ])
    _monter_operator(monkeypatch, [])
    kort = {j["id"]: j["kommando"] for j in bj.liste()["jobs"]}
    assert "arbejds-shell" in kort["bsh-aaaaaaaaaa"]
    assert "arbejds-shell" not in kort["bsh-bbbbbbbbbb"]


def test_tallets_betydning_er_forskellig_paa_de_to_kilder(monkeypatch):
    # `_Session.run` saetter `last_used` ved kommandoens START; operator-siden
    # saetter `last` EFTER kaldet er vendt tilbage. Panelet maa ikke kalde de
    # to det samme — foerste udgave skrev «tomgang» paa begge.
    _taend_shells(monkeypatch)
    _monter_lokal(monkeypatch, [{"session_id": "bsh-0123456789",
                                 "alive": True, "idle_seconds": 3}])
    _monter_operator(monkeypatch, [{"session_id": "opsess-0123456789ab",
                                    "cwd": "~", "idle_s": 3}])
    kort = {j["kilde"]: j["kommando"] for j in bj.liste()["jobs"]}
    assert "sidste kommando startede" in kort["shell"]
    assert "sidste kommando sluttede" in kort["shell_operator"]


def test_en_shell_der_KOERER_viser_kommandoen_og_dens_koeretid(monkeypatch):
    # Det er kortet fra Bjoerns billede: «koerer / 19m20s / hvad det er».
    # `last_used` saettes ved kommandoens START, saa idle_seconds ER koeretiden.
    _taend_shells(monkeypatch)
    _monter_lokal(monkeypatch, [{"session_id": "bsh-0123456789", "alive": True,
                                 "idle_seconds": 1160, "busy": True,
                                 "command": "npm run build -- --watch"}])
    _monter_operator(monkeypatch, [])
    j = bj.liste()["jobs"][0]
    assert j["kommando"] == "kører: npm run build -- --watch"
    assert j["sekunder"] == 1160


def test_en_daemon_uden_busy_feltet_paastaar_ingenting(monkeypatch):
    # En daemon startet foer 26/9-2026 svarer uden `busy`. Kortet maa saa
    # falde tilbage til den neutrale tekst, ikke gaette at der er ledigt.
    _taend_shells(monkeypatch)
    _monter_lokal(monkeypatch, [{"session_id": "bsh-0123456789",
                                 "alive": True, "idle_seconds": 7}])
    _monter_operator(monkeypatch, [])
    kommando = bj.liste()["jobs"][0]["kommando"]
    assert "kører:" not in kommando
    assert "åben shell" in kommando
