"""Sporet gennem en kørsel — og at udskillelsen ikke brækkede noget.

Testene her handler om det en UDSKILLELSE kan ødelægge, ikke om det funktionen
gjorde i forvejen: at imports stadig peger rigtigt, at tilstanden kun findes ét
sted, og at kaldet blev liggende hvor det skal fyre.
"""
from __future__ import annotations

from core.services import visible_run_trace as vrt


class _Run:
    run_id = "visible-abc"
    lane = "visible"
    provider = "deepseek"
    model = "deepseek-v4-flash"


# ───────────────────────────────────────────────── bagudkompatibilitet

def test_alt_er_gen_eksporteret_fra_visible_runs():
    """Målt før flytningen: getteren har tre eksterne kaldere,
    trace-opdateringen seks, runde-publiceringen fire — heraf tests der griber
    direkte i `visible_runs`-navnerummet. En udskillelse der brækker dem, er
    ikke en udskillelse men en flytning med fejl."""
    from core.services import visible_runs as vr
    for navn in ("get_last_visible_execution_trace", "_start_visible_execution_trace",
                 "_update_visible_execution_trace", "_set_last_visible_execution_trace",
                 "_visible_trace_payload", "_publish_agentic_round_start"):
        assert hasattr(vr, navn), f"{navn} kan ikke naas fra visible_runs laengere"


def test_gen_eksporten_peger_paa_SAMME_funktion():
    """Ikke bare et navn der findes — det SAMME objekt. To kopier ville betyde
    to tilstande, og sporet ville blive skrevet ét sted og læst et andet."""
    from core.services import visible_runs as vr
    assert vr._publish_agentic_round_start is vrt._publish_agentic_round_start
    assert vr.get_last_visible_execution_trace is vrt.get_last_visible_execution_trace


def test_tilstanden_findes_KUN_ét_sted():
    """CLAUDE.md: «No dual truth». Første forsøg efterlod
    `_LAST_VISIBLE_EXECUTION_TRACE` begge steder — den slags viser sig som et
    spor der opdateres ét sted og læses et andet."""
    import pathlib
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    assert "_LAST_VISIBLE_EXECUTION_TRACE" not in kilde


def test_gen_eksport_blokken_til_de_ANDRE_udskillelser_er_intakt():
    """Første forsøg skar blokken ud paa LINJENUMRE og tog filens sidste
    gen-eksport-blok med. 22 tests gik roede paa
    «has no attribute '_track_runtime_candidates'». Vagten her ville have
    fanget det med det samme."""
    from core.services import visible_runs as vr
    for navn in ("_track_runtime_candidates", "_track_step_failed",
                 "_persist_visible_run_outcome", "resolve_pending_approval"):
        assert hasattr(vr, navn), f"{navn} forsvandt med udskillelsen"


# ───────────────────────────────────────────────────────── selve sporet

def test_et_spor_starter_og_kan_laeses_tilbage(monkeypatch):
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt._start_visible_execution_trace(_Run())
    spor = vrt.get_last_visible_execution_trace() or {}
    assert spor["run_id"] == "visible-abc"
    assert spor["final_status"] == "running"


def test_en_opdatering_FLETTER_frem_for_at_erstatte(monkeypatch):
    """Et spor der blev overskrevet ville tabe alt det tidligere trin skrev."""
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt._start_visible_execution_trace(_Run())
    vrt._update_visible_execution_trace(_Run(), {"invoke_status": "invoked"})
    spor = vrt.get_last_visible_execution_trace() or {}
    assert spor["invoke_status"] == "invoked"
    assert spor["final_status"] == "running", "de oevrige felter forsvandt"


def test_getteren_giver_en_KOPI(monkeypatch):
    """Ellers kunne en kalder ændre husets spor ved et uheld."""
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt._start_visible_execution_trace(_Run())
    a = vrt.get_last_visible_execution_trace() or {}
    a["final_status"] = "roert udefra"
    b = vrt.get_last_visible_execution_trace() or {}
    assert b["final_status"] == "running"


def test_hver_opdatering_UDSENDES(monkeypatch):
    """Sporet er til for at kunne ses. Et spor ingen faar besked om, er en
    variabel."""
    sendt: list[str] = []
    monkeypatch.setattr(vrt.event_bus, "publish", lambda navn, *a, **k: sendt.append(navn))
    vrt._start_visible_execution_trace(_Run())
    assert sendt == ["runtime.visible_run_execution_trace"]


# ──────────────────────────────────────── kaldet blev hvor det skal fyre

def test_runde_publiceringen_kaldes_stadig_fra_loekken():
    """Kun DEFINITIONEN flyttede. Fyrede kaldet et andet sted, ville
    runde-kæderne i den kausale graf miste deres forælder — og
    `test_process_lifecycle` kraever desuden at nedluknings-vagten staar foer
    det."""
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path("core/services/visible_runs.py").read_text())
    # BAADE `FunctionDef` og `AsyncFunctionDef`: `_stream_visible_run` er en
    # generator-funktion, og en vagt der kun kender den ene form finder ingenting
    # og ser ud som om kaldet er væk.
    fn = next((n for n in ast.walk(træ)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == "_stream_visible_run"), None)
    assert fn is not None, "_stream_visible_run er flyttet"
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "_publish_agentic_round_start" in kaldt
