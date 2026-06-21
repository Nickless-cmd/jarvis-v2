"""Ende-til-ende-smoke: en nerve kører gennem Centralen, trace + verdict hænger sammen."""
from __future__ import annotations

from core.services.central_core import Central
from core.services.central_trace import TraceSink
from core.services.gate_kernel import Decision, GateClass


def test_full_cycle_decide_then_observe_traced_together():
    sink = TraceSink(maxlen=100)
    c = Central(sink=sink, emit=lambda k, p: None)
    v = c.decide("tool_budget", {"run_id": "rX", "session_id": "sX"},
                 lambda ctx: {"decision": "yellow", "reason": "tool-only=5"},
                 cluster="loop", klass=GateClass.COGNITIVE)
    c.observe({"run_id": "rX", "session_id": "sX", "cluster": "loop",
               "nerve": "tool_budget", "rounds": 5})
    recs = sink.records_for_run("rX")
    kinds = [r.kind for r in recs]
    assert v.decision is Decision.YELLOW
    assert "decide" in kinds and "observe" in kinds      # hele kæden på ét run_id
