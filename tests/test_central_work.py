"""`/central/work` — arbejdet med sin næste handling i samme række.

## Hvorfor ruten findes

`_runtime_work_surface()` beregnede allerede køede, kørende og blokerede
opgaver, deres flows, og `flows.next_action` — feltet der svarer på «hvad venter
den på?». Målt 13/9-2026: **ingen klient havde nogensinde læst den.** Hver
forekomst af nøglen `runtime_work` var server-intern.

Den sidste test i filen er den vigtigste: den kræver at ruten faktisk er
monteret. En flade ingen kan nå er nøjagtig den fejl der lod den første stå
usynlig i månedsvis.
"""
from __future__ import annotations

import pytest

from apps.api.jarvis_api.routes import central_absorb_routes as cw


@pytest.fixture(autouse=True)
def _ejer(monkeypatch):
    monkeypatch.setattr(cw, "require_central_owner", lambda: None)
    monkeypatch.setattr(cw, "absorb", lambda *a, **k: None)


def _lagre(monkeypatch, opgaver: list[dict], flows: list[dict]):
    """Byt de to lagre ud. De hentes DOVENT inde i ruten, så de patches der."""
    import core.runtime.db_runtime_flows as dff
    import core.runtime.db_runtime_tasks as dft
    monkeypatch.setattr(dft, "list_runtime_tasks",
                        lambda status="", limit=0: [t for t in opgaver
                                                    if t.get("status") == status])
    monkeypatch.setattr(dff, "list_runtime_flows",
                        lambda status="", limit=0: [f for f in flows
                                                    if f.get("status") == status])


def test_opgave_og_flow_staar_i_SAMME_raekke(monkeypatch):
    """Den gamle flade gav to adskilte lister. Et cockpit kan ikke bruge det:
    for at vise «denne opgave venter paa dét» skal nogen sammenfoeje paa
    `flow_id` — og goer hver klient det selv, goer de det forskelligt."""
    _lagre(monkeypatch,
           [{"task_id": "t1", "flow_id": "f1", "status": "running",
             "goal": "byg noget", "kind": "kode"}],
           [{"flow_id": "f1", "status": "running", "current_step": "tester",
             "next_action": "afventer gruppe-godkendelse"}])
    ud = cw.get_work()
    assert len(ud["arbejde"]) == 1
    r = ud["arbejde"][0]
    assert r["task_id"] == "t1" and r["goal"] == "byg noget"
    assert r["next_action"] == "afventer gruppe-godkendelse"
    assert r["current_step"] == "tester"


def test_next_action_OG_blocked_reason_er_med(monkeypatch):
    """De svarer paa hvert sit spoergsmaal: «hvad er naeste skridt» og «hvorfor
    staar den stille». Et cockpit der kun har det ene kan ikke sige forskel paa
    en opgave der arbejder og en der er gaaet i staa."""
    _lagre(monkeypatch,
           [{"task_id": "t1", "flow_id": "f1", "status": "blocked",
             "blocked_reason": "testen fejlede"}],
           [{"flow_id": "f1", "status": "blocked", "next_action": "ret testen"}])
    r = cw.get_work()["arbejde"][0]
    assert r["blocked_reason"] == "testen fejlede"
    assert r["next_action"] == "ret testen"


def test_blokeret_arbejde_TAELLES(monkeypatch):
    _lagre(monkeypatch,
           [{"task_id": "a", "status": "blocked", "flow_id": ""},
            {"task_id": "b", "status": "running", "flow_id": ""},
            {"task_id": "c", "status": "queued", "flow_id": ""}],
           [])
    antal = cw.get_work()["antal"]
    assert antal["blocked"] == 1 and antal["running"] == 1 and antal["queued"] == 1


def test_blokeret_arbejde_FLAGES(monkeypatch):
    """En blokeret opgave der ikke flages er en opgave ingen opdager."""
    set_flag: dict = {}
    monkeypatch.setattr(cw, "absorb",
                        lambda *a, **k: set_flag.update(
                            {"flaget": bool(k.get("flag_if") and k["flag_if"](a[2]))}))
    _lagre(monkeypatch, [{"task_id": "a", "status": "blocked", "flow_id": ""}], [])
    cw.get_work()
    assert set_flag.get("flaget") is True


def test_intet_blokeret_giver_intet_flag(monkeypatch):
    set_flag: dict = {}
    monkeypatch.setattr(cw, "absorb",
                        lambda *a, **k: set_flag.update(
                            {"flaget": bool(k.get("flag_if") and k["flag_if"](a[2]))}))
    _lagre(monkeypatch, [{"task_id": "a", "status": "running", "flow_id": ""}], [])
    cw.get_work()
    assert set_flag.get("flaget") is False


def test_foraeldreloese_flows_SKJULES_ikke(monkeypatch):
    """Et flow uden en opgave er ikke stoej — det er arbejde uden ejer, og
    praecis den slags der ellers koerer videre uden at nogen ved det."""
    _lagre(monkeypatch,
           [{"task_id": "t1", "flow_id": "f1", "status": "running"}],
           [{"flow_id": "f1", "status": "running"},
            {"flow_id": "FORLADT", "status": "running", "next_action": "?"}])
    ud = cw.get_work()
    assert len(ud["foraeldreloese_flows"]) == 1
    assert ud["foraeldreloese_flows"][0]["flow_id"] == "FORLADT"
    assert ud["antal"]["foraeldreloese_flows"] == 1


def test_opgave_uden_flow_falder_ikke_ud(monkeypatch):
    """En opgave uden flow er stadig arbejde. Et indre join ville tabe den."""
    _lagre(monkeypatch, [{"task_id": "t1", "flow_id": "", "status": "queued",
                          "goal": "noget"}], [])
    ud = cw.get_work()
    assert len(ud["arbejde"]) == 1
    assert ud["arbejde"][0]["next_action"] == ""


def test_alle_tre_statusser_hentes(monkeypatch):
    """Kun `running` ville skjule netop det arbejde der er gaaet i staa."""
    hentede: list[str] = []
    import core.runtime.db_runtime_flows as dff
    import core.runtime.db_runtime_tasks as dft
    monkeypatch.setattr(dft, "list_runtime_tasks",
                        lambda status="", limit=0: hentede.append(status) or [])
    monkeypatch.setattr(dff, "list_runtime_flows", lambda status="", limit=0: [])
    cw.get_work()
    assert set(hentede) == {"running", "blocked", "queued"}


def test_ruten_vaelter_ALDRIG_paa_et_braekket_lager(monkeypatch):
    """Et cockpit der gaar ned naar noget er galt, er nede praecis naar man
    skal bruge det."""
    import core.runtime.db_runtime_tasks as dft
    monkeypatch.setattr(dft, "list_runtime_tasks",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("nede")))
    import core.runtime.db_runtime_flows as dff
    monkeypatch.setattr(dff, "list_runtime_flows", lambda **k: [])
    ud = cw.get_work()
    assert ud["arbejde"] == []
    assert ud["active"] is False


def test_ejer_gaten_haandhaeves(monkeypatch):
    """En profil-oversigt over hvad Jarvis arbejder paa er ikke noget et
    husstandsmedlem skal kunne kortlaegge."""
    kaldt: list[int] = []
    monkeypatch.setattr(cw, "require_central_owner", lambda: kaldt.append(1))
    import core.runtime.db_runtime_flows as dff
    import core.runtime.db_runtime_tasks as dft
    monkeypatch.setattr(dft, "list_runtime_tasks", lambda **k: [])
    monkeypatch.setattr(dff, "list_runtime_flows", lambda **k: [])
    cw.get_work()
    assert kaldt == [1]


# ------------------------------------------------- fladen skal kunne NAAS

def test_ruten_er_MONTERET_i_appen():
    """Den vigtigste test i filen.

    `_runtime_work_surface()` var korrekt, komplet og usynlig, fordi ingen
    kunne naa den. En rute der findes i en fil men ikke i appen, er samme fejl
    en gang til.
    """
    from apps.api.jarvis_api.app import app
    stier = {getattr(r, "path", "") for r in app.routes}
    assert "/central/work" in stier, \
        "arbejds-fladen er ikke monteret — den er usynlig, praecis som den foerste"


# --------------------------------------- fladen skal VISES, ikke bare kunne naas

def test_central_cli_har_en_WORK_fane():
    """En rute ingen viser er den samme fejl som en flade ingen laeser.

    `_runtime_work_surface()` var korrekt og usynlig i maanedsvis. At bygge en
    rute og stoppe dér ville have gentaget det praecist.
    """
    import pathlib
    hud = pathlib.Path("apps/central_cli/central_cli/hud.py").read_text()
    assert '("work", "Work", False)' in hud, "Work-fanen findes ikke i HUD'en"
    assert '"work"' in hud


def test_central_cli_HENTER_arbejdet():
    """Kilde-vagt paa kalderen, ikke paa koden. AST, ikke tekstsoegning."""
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path(
        "apps/central_cli/central_cli/hud_populate.py").read_text())
    fn = next((n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
               and n.name == "_populate_work"), None)
    assert fn is not None, "_populate_work findes ikke"
    # datasource.work(...) skal kaldes
    kaldt = {getattr(k.func, "attr", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "work" in kaldt, "fanen henter ikke arbejdet — den ville staa tom"


def test_datakilden_peger_paa_den_RIGTIGE_rute():
    import pathlib
    ds = pathlib.Path("apps/central_cli/central_cli/datasource.py").read_text()
    assert '"/central/work"' in ds


def test_blokeret_arbejde_sorteres_OEVERST():
    """En liste sorteret efter tid begraver det arbejde der er gaaet i staa —
    og det er det eneste der kraever et menneske."""
    import pathlib
    kilde = pathlib.Path("apps/central_cli/central_cli/hud_populate.py").read_text()
    assert '_orden = {"blocked": 0, "running": 1, "queued": 2}' in kilde


# ------------------------------------------------- rod og ophav paa fladen

def test_fladen_baerer_BAADE_rod_og_ophav(monkeypatch):
    """To felter, to spoergsmaal: `work_ref` siger HVILKET stykke arbejde det
    er, `origin_ref` siger HVORFOR det findes.

    Smeltede de sammen, kunne et cockpit ikke skelne «denne opgave» fra
    «tidspunktet den blev foedt» — og det var praecis den forveksling der lod
    kolonnen hedde `run_id` og indeholde et tick.
    """
    _lagre(monkeypatch,
           [{"task_id": "t1", "status": "running", "flow_id": "",
             "origin_ref": "tick:036bd93e"}], [])
    r = cw.get_work()["arbejde"][0]
    assert r["work_ref"] == "task:t1"
    assert r["origin_ref"] == "tick:036bd93e"


def test_roden_kan_oploeses_af_den_faelles_vej(monkeypatch):
    from core.runtime.work_ref import opløs
    _lagre(monkeypatch, [{"task_id": "t1", "status": "running", "flow_id": ""}], [])
    r = cw.get_work()["arbejde"][0]
    assert opløs(r["work_ref"]) == ("task", "t1")


def test_manglende_reference_vaelter_ikke_cockpittet(monkeypatch):
    """En opgave uden id er en fejl et andet sted. Cockpittet skal stadig
    kunne vise resten."""
    _lagre(monkeypatch, [{"task_id": "", "status": "running", "flow_id": ""}], [])
    r = cw.get_work()["arbejde"][0]
    assert r["work_ref"] == ""
