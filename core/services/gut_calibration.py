"""Gut-calibration wiring — fodrer cognitive_gut_state fra run-livscyklussen.

Rod-årsag (fundet 2026-06-15): gut_engine's skrive-sti (derive_gut_signal /
record_gut_outcome) var forældreløs — kun build_gut_surface (read) blev kaldt, så
cognitive_gut_state forblev evigt tom. Denne wiring danner en hunch ved run-start
og registrerer udfaldet ved completed/failed/interrupted.

Defensiv kontrakt: ALT er indpakket — en fejl her må ALDRIG vælte run-closure
(kaldes fra run_closure_gate's listener-loop).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# run_id → hunch ("proceed"|"caution"). Begrænset så hukommelsen ikke vokser
# ubegrænset hvis et completed-event nogensinde tabes.
_MAX_PENDING = 256
_pending: dict[str, str] = {}

_OUTCOME_BY_KIND = {
    "runtime.autonomous_run_completed": "completed",
    "runtime.autonomous_run_failed": "error",
    "runtime.autonomous_run_interrupted": "interrupted",
}


def observe_run_event(kind: str, payload: dict) -> None:
    """Dispatch fra run_closure_gate's listener. Kaster aldrig."""
    try:
        if kind == "runtime.autonomous_run_started":
            _on_started(payload)
        elif kind in _OUTCOME_BY_KIND:
            _on_outcome(payload, _OUTCOME_BY_KIND[kind])
    except Exception:
        logger.debug("gut_calibration: observe failed", exc_info=True)


def _on_started(payload: dict) -> None:
    run_id = str(payload.get("run_id") or "")
    if not run_id:
        return
    from core.services.gut_engine import derive_gut_signal
    signal = derive_gut_signal(task_description=str(payload.get("focus") or ""))
    if len(_pending) >= _MAX_PENDING:
        _pending.clear()  # backstop mod læk ved tabte completed-events
    _pending[run_id] = str(signal.get("hunch") or "proceed")


def _on_outcome(payload: dict, actual_outcome: str) -> None:
    run_id = str(payload.get("run_id") or "")
    hunch = _pending.pop(run_id, None)
    if not hunch:
        return  # ingen hunch dannet (fx run startet før wiringen var live)
    from core.services.gut_engine import record_gut_outcome
    record_gut_outcome(hunch=hunch, actual_outcome=actual_outcome)
