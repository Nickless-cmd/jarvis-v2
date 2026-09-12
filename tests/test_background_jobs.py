"""De aktive opgaver — fra begge kilder."""
import pytest

from core.services import background_jobs as bj


def _bro(stdout, status="ok"):
    def _exec(navn, args):
        assert navn == "operator_bash"
        return {"status": status, "result": {"stdout": stdout}}
    return _exec


@pytest.fixture(autouse=True)
def ingen_supervisor(monkeypatch):
    monkeypatch.setattr(bj, "_supervisor_jobs", lambda: [])


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
