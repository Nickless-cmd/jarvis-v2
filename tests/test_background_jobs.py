"""De aktive opgaver — fra begge kilder."""
import pytest

from core.services import background_jobs as bj

_ægte_scout_jobs = bj._scout_jobs


def _bro(stdout, status="ok"):
    def _exec(navn, args):
        assert navn == "operator_bash"
        return {"status": status, "result": {"stdout": stdout}}
    return _exec


@pytest.fixture(autouse=True)
def ingen_supervisor(monkeypatch):
    monkeypatch.setattr(bj, "_supervisor_jobs", lambda: [])
    monkeypatch.setattr(bj, "_scout_jobs", lambda: [])


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
