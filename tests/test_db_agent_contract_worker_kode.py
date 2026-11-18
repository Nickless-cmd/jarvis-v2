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
