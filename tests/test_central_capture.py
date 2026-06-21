"""Tests for boundary-capture (§10): safe_call kaster ALDRIG."""
from __future__ import annotations

from core.services.central_capture import safe_call, ErrorRecord
from core.services.gate_kernel import GateClass


def test_safe_call_success_returns_result_and_no_error():
    result, err = safe_call(lambda c: {"decision": "green"}, {"run_id": "r1"}, nerve="n")
    assert result == {"decision": "green"} and err is None


def test_safe_call_exception_is_captured_not_raised():
    def boom(c):
        raise ValueError("nede")
    result, err = safe_call(boom, {"run_id": "r1", "session_id": "s1"},
                            nerve="n", cluster="loop", klass=GateClass.SECURITY)
    assert result is None
    assert isinstance(err, ErrorRecord)
    assert err.kind == "exception" and "ValueError" in err.message
    assert err.nerve == "n" and err.cluster == "loop" and err.klass is GateClass.SECURITY
    assert err.signal == {"run_id": "r1", "session_id": "s1"}
    assert err.stack  # ikke-tom stacktrace


def test_safe_call_malformed_ctx_is_captured():
    result, err = safe_call(lambda c: None, "ikke-en-dict", nerve="n")
    assert result is None and err.kind == "malformed"
