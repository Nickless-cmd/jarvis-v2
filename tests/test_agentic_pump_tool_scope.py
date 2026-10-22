"""Den agentiske runde skal bygge sin prompt med runnets tool-scope.

## Hvorfor testen findes

Maalt 22/10-2026 paa Bjorns egen tur (`visible-0d94113a…`, 30 model-kald):
samme run byggede TO prompts.

* runde 1: ``CODE MODE`` — korrekt, fordi ``pump_first_pass`` saetter scopet
  EKSPLICIT inde i worker-traaden.
* runde 2+: ``uden mode-signal`` — fordi ``_pump_agentic`` kun arvede via
  ``copy_context()``, og ``stream_visible_followup`` kalder prompt-byggeren
  inde i worker-traaden.

Konsekvensen var ikke kosmetisk: mode-orienteringen — den sektion der skal
fortaelle modellen hvilket rum den er i — blev kastet vaek i hver runde efter
den foerste. Det er praecis derfor Bjorn maatte bede om at der ikke blev kodet
i chat mode: orienteringen, der skulle sige det, var vaek.

## Hvad testene maaler — og hvad de IKKE maaler

Den foerste udgave af denne fil matchede paa tekst i kilden. Den var groen
ogsaa efter en mutation der neutraliserede rettelsen, saa den beviste intet.
Den anden udgave maalte mekanismen isoleret — ogsaa groen efter mutationen,
fordi den aldrig roerte ``_pump_agentic``.

Testene herunder maaler den AEGTE soem: de kalder den faktiske
prompt-bygger inde i en worker-traad og laeser hvilken orientering der kom ud.
Mutationen der skal faelde dem er at fjerne ``set_tool_scope`` fra
``_pump_agentic`` — se ``test_pump_agentic_sets_scope_explicitly``.
"""
from __future__ import annotations

import contextvars
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.prompt_contract import (  # noqa: E402
    _visible_mode_orientation_instruction,
)
from core.tools.tool_scoping import (  # noqa: E402
    current_tool_scope,
    reset_tool_scope,
    set_tool_scope,
)


def _run_in_worker(fn):
    """Kør ``fn`` i en worker-traad med en kopi af den aktuelle kontekst.

    Det er praecis den vej ``_pump_agentic`` bruger: ``copy_context()`` +
    ``run_in_executor``. En test der kalder ``fn`` direkte ville vaere groen
    selv om ContextVar'en ikke fulgte med.
    """
    out: list[object] = []
    ctx = contextvars.copy_context()
    t = threading.Thread(target=lambda: ctx.run(lambda: out.append(fn())))
    t.start()
    t.join()
    return out[0] if out else None


def test_orientation_follows_scope_set_inside_the_worker():
    """Den aegte soem: scope sat i traaden → rigtig orientering i prompten.

    Det er hvad ``_pump_agentic`` nu goer. Uden det byggede runde 2+ sin
    prompt med tomt scope og fik «uden mode-signal».
    """

    def worker() -> str:
        tok = set_tool_scope("code")
        try:
            return _visible_mode_orientation_instruction(compact=False) or ""
        finally:
            reset_tool_scope(tok)

    text = _run_in_worker(worker)
    assert "CODE MODE" in text, f"orienteringen var {text[:80]!r}"


def test_orientation_is_wrong_without_the_explicit_set():
    """Modstykket: uden ``set_tool_scope`` i traaden bliver orienteringen tom.

    Denne test dokumenterer HVORFOR rettelsen er noedvendig. Den er ikke en
    vagt mod regression — den beskriver den maalte fejlform.
    """

    def worker() -> str:
        return _visible_mode_orientation_instruction(compact=False) or ""

    text = _run_in_worker(worker)
    assert "CODE MODE" not in text
    assert "CHAT MODE" not in text


def test_scope_does_not_leak_between_reused_threads():
    """Executor-traade genbruges — scopet maa ikke blive haengende.

    Uden ``reset_tool_scope`` i ``finally`` ville en senere prompt-assembly i
    samme traad arve det forrige runs scope.
    """

    def worker() -> tuple[str, str]:
        tok = set_tool_scope("code")
        inside = current_tool_scope()
        reset_tool_scope(tok)
        return inside, current_tool_scope()

    inside, after = _run_in_worker(worker)
    assert inside == "code"
    assert after == "", f"scopet laekkede videre: {after!r}"


def test_pump_agentic_sets_scope_explicitly():
    """KILDE-vagt: asymmetrien mellem de to pumper maa ikke vende tilbage.

    Den parser AST'en i stedet for at grep'e efter en streng. Maalt 22/10-2026:
    en streng-match var groen ogsaa efter mutationen ``if False:``, fordi
    teksten stadig stod i kilden. En vagt der ikke kan faelde er vaerdiloes.
    """
    import ast
    import inspect

    from core.services.visible_first_pass_pump import pump_first_pass
    import core.services.visible_runs as vr

    fp_src = inspect.getsource(pump_first_pass)
    assert "set_tool_scope" in fp_src, "first-pass saetter ikke scopet"

    # Parse HELE modulet og find funktionen i AST'en. Et tekstvindue er
    # skroebeligigt: pumpen ligger indlejret i en loekke med blandet
    # indrykning, saa `textwrap.dedent` fejler paa den.
    tree = ast.parse(inspect.getsource(vr))
    pump = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_pump_agentic":
            pump = node
            break
    assert pump is not None, "_pump_agentic findes ikke — er funktionen omdoebt?"

    called: set[str] = set()
    for node in ast.walk(pump):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name:
                called.add(name)

    params = {a.arg for a in pump.args.args} | {a.arg for a in pump.args.kwonlyargs}

    assert "_set_scope_ag" in called or "set_tool_scope" in called, (
        "den agentiske pumpe KALDER ikke set_tool_scope; den hviler paa "
        "copy_context(), som maalt 22/10-2026 ikke er nok"
    )
    assert "_reset_scope_ag" in called or "reset_tool_scope" in called, (
        "den agentiske pumpe rydder ikke scopet — executor-traade genbruges, "
        "saa scopet ville laekke til naeste koersel"
    )
    assert "pump_tool_scope" in params, (
        "den agentiske pumpe tager ikke scopet som parameter"
    )
