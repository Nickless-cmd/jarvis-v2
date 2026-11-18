"""WorkerError bærer sin kode — den må ikke blive til en model-fejl (18/11-2026).

Målt i den levende DB (`agent_runs`, 14 dage): **5 af 5** runs hvis egen
fejltekst var `CANCELLED: agenten blev annulleret` stod med
`error_code='AGENT_FAILED'` og `error_phase='model'`. De 5 var 5 af de 8
`AGENT_FAILED` der findes — over halvdelen af "modelfejlene" i den bunke var
annulleringer af noget der aldrig fejlede.

Årsagen er ikke et gæt. Fejlhandleren i `agent_runtime_spawn` læste
`getattr(exc, "error_code", "")`, men `WorkerError` (`agent_worker_runner.py:50`)
gemmer koden i `.code`. Feltet findes ikke, så hver worker-fejl faldt igennem til
tabellen og påstod at MODELLEN fejlede.

Vagten er et PAR: koden skal med — og en fremmed undtagelse må IKKE stjæles.
`CheapProviderError` bærer også `.code`, men i små bogstaver (`timeout`,
`unreachable`). Derfor gates der på typen, ikke på feltnavnet.
"""
from __future__ import annotations

import ast
from pathlib import Path

from core.runtime.db_agent_contract import error_fra_exception, worker_error_kode

_ROD = Path(__file__).resolve().parents[1]
_RUNNER = _ROD / "core/services/agent_worker_runner.py"


def _worker_koder() -> set[str]:
    """Alle koder `agent_worker_runner` faktisk kaster — læst fra AST'en."""
    trae = ast.parse(_RUNNER.read_text(encoding="utf-8"))
    koder: set[str] = set()
    for knude in ast.walk(trae):
        if not isinstance(knude, ast.Call):
            continue
        if getattr(knude.func, "id", "") != "WorkerError" or not knude.args:
            continue
        foerste = knude.args[0]
        if isinstance(foerste, ast.Constant) and isinstance(foerste.value, str):
            koder.add(foerste.value)
    return koder


def test_hver_worker_kode_har_en_fase():
    """En ny `WorkerError("X", ...)` må ikke kunne snige sig ind umappet."""
    koder = _worker_koder()
    assert koder, "fandt ingen WorkerError-koder — parseren er brudt"
    umappede = [k for k in sorted(koder) if worker_error_kode(k) == ("", "")]
    assert not umappede, (
        f"disse WorkerError-koder falder tilbage til AGENT_FAILED/model: {umappede}")


def test_cancelled_er_en_annullering_ikke_en_modelfejl():
    assert worker_error_kode("CANCELLED") == ("CANCELLED", "cancelled")


def test_fejlhandleren_laeser_workerens_kode():
    from core.services.agent_worker_runner import WorkerError

    kode, fase = error_fra_exception(WorkerError("CANCELLED", "agenten blev annulleret"))
    assert (kode, fase) == ("CANCELLED", "cancelled"), f"fik {(kode, fase)!r}"


def test_fremmed_code_bliver_ikke_stjaalet():
    """`CheapProviderError` bærer også `.code` — i små bogstaver."""
    class CheapProviderError(RuntimeError):
        def __init__(self, code: str) -> None:
            super().__init__(code)
            self.code = code

    kode, fase = error_fra_exception(CheapProviderError("timeout"))
    assert kode != "WORKER_TIMEOUT", "provider-timeout blev stjålet af worker-tabellen"
    assert fase != "execution"


def test_ukendt_worker_kode_falder_tilbage():
    assert worker_error_kode("KODE_FRA_FREMTIDEN") == ("", "")


def test_eksisterende_error_code_felter_vinder():
    class MedFase(RuntimeError):
        error_code = "CLI_BACKEND_FAILED"
        error_phase = "execution"

    assert error_fra_exception(MedFase("x")) == ("CLI_BACKEND_FAILED", "execution")


def test_markeringen_slaar_worker_koden():
    """Markeringen beskriver LEVERANCEN — mere specifik end hvorfor loopet døde."""
    from core.services.agent_worker_runner import WorkerError

    tekst = "UFULDSTÆNDIG (2 ubesvarede spørgsmål) — agentens tekst:\nsvar"
    assert error_fra_exception(WorkerError("CANCELLED", "d"), full=tekst) == (
        "AGENT_INCOMPLETE", "delivery")


# ── Meta-koder, tom etikette og koden-der-kom-bagefter (18/11-2026) ───────────
# Målt på 288 gemte assignments: 26 stod med `error_phase='model'`, og 19 af dem
# blev modsagt af runnets EGEN kode. 14 af de 19 fik koden EFTER assignmentet blev
# terminalt — settle kunne ikke se den. 5 bar en meta-kode (RUN_STALE/RUN_ORPHANED)
# som er "assignmentet blev lukket", ikke "hvorfor".
from core.runtime.db_agent_contract import partial_delivery_error  # noqa: E402


def test_timed_out_har_en_fase_ikke_en_tom_etikette():
    """`timed_out` manglede i begge tabeller — QUEUE_DEADLINE fik ("", "")."""
    kode, fase = partial_delivery_error(full="", registry_status="timed_out")
    assert (kode, fase) != ("", ""), "en terminal status uden fase er en tom etikette"
    assert fase == "budget"


def test_meta_kode_giver_en_aerlig_ukendt_fase():
    """RUN_STALE/RUN_ORPHANED siger at assignmentet blev LUKKET — ikke hvorfor."""
    for meta in ("RUN_STALE", "RUN_ORPHANED"):
        kode, fase = partial_delivery_error(
            full="", registry_status="failed", run_error_code=meta, run_error_phase="recovery")
        assert kode == meta, "koden skal bevares — den er observeret, ikke gættet"
        assert fase == "unknown", f"{meta} må ikke påstå en fase vi ikke kender"


def test_orphan_kode_retter_en_gaettet_fase_bagefter(isolated_runtime):
    """Koden ankommer EFTER settle — assignmentets outcome skal følge med."""
    import json

    import core.runtime.db_agent_contract as mod
    from core.runtime.db_agent_lease import close_orphan_runs
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    create_agent_registry_entry(agent_id="a1", role="scout", goal="g")
    c = mod._conn()
    c.execute("UPDATE agent_registry SET owner_user_id=? WHERE agent_id=?", ("bjorn", "a1"))
    c.commit()
    out = mod.accept_assignment(
        agent_id="a1", owner_user_id="bjorn", origin_session_id="s1", goal="g",
        parent_agent_id="jarvis", parent_run_id="pr1", idempotency_key="k1")
    aid = out["assignment_id"]
    mod.commit_terminal_outcome(
        assignment_id=aid, status="failed", error_code="AGENT_FAILED", error_phase="model")
    # Leasing-stien skriver den ægte kode bagefter — det er defekten.
    close_orphan_runs(mod._conn(), aid, reason="test: assignment_terminal_before_lease_expiry")
    o = json.loads(mod._conn().execute(
        "SELECT outcome_json FROM agent_assignments WHERE assignment_id=?", (aid,)
    ).fetchone()["outcome_json"])
    assert o["error_phase"] != "model", f"fasen blev aldrig rettet: {o}"
    assert o["error_code"] == "RUN_ORPHANED"
