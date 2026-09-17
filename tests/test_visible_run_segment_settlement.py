"""`visible_run_segment_settlement` — modulets egen overflade.

Fejlklasse-matrixen for de tolv udgange står i
`tests/test_visible_run_failure_classes.py`; her står det modulet selv ejer:
hvordan en grund oversættes til en klasse, og hvad der sker når journalen
svigter.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr
from core.services.visible_run_recovery_coordinator import FailureClass
from core.services.visible_run_segment_settlement import (
    SegmentUdfald,
    failure_class_for,
    settle_segment_exit,
)


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(ifr, "_save", lambda v: (poster.clear(),
                                                 poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    return poster


@pytest.mark.parametrize("grund,klasse", [
    ("shutdown", FailureClass.PROCESS),
    ("user-cancelled", FailureClass.CANCELLATION),
    ("provider-not-supported", FailureClass.PROVIDER),
    ("provider-round-timeout", FailureClass.WATCHDOG),     # uret, ikke udbyderen
    ("relay_source_idle_timeout", FailureClass.WATCHDOG),
    ("research-deadline", FailureClass.RESEARCH),
    ("runtime-ValueError", FailureClass.RUNTIME),
    ("noget-vi-aldrig-har-set", FailureClass.RUNTIME),
])
def test_grunden_oversaettes_til_en_klasse(grund, klasse):
    assert failure_class_for(grund) is klasse


def test_kalderens_klasse_vinder_over_gaettet():
    """Kaldestedet ved hvad der skete; navnet er kun et spor."""
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    ud = settle_segment_exit(run_id="r1", session_id="s1", exit_reason="shutdown",
                             failure_class=FailureClass.RUNTIME)
    assert ud.failure_class is FailureClass.RUNTIME


def test_udfaldet_baerer_baade_dom_post_og_besked():
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    ud = settle_segment_exit(run_id="r1", session_id="s1", exit_reason="shutdown")
    assert isinstance(ud, SegmentUdfald)
    assert ud.record["status"] == "recovering"
    assert ud.event_payload["reason"] == "shutdown"
    assert ud.decision.should_continue is True


def test_task_id_bruges_naar_det_er_et_andet_end_run_id():
    """Et segment er ikke opgaven: fortsættelsen hører til opgaven."""
    ifr.mark_started(run_id="task-1", session_id="s1", user_message="x")
    ud = settle_segment_exit(run_id="segment-2", session_id="s1", task_id="task-1",
                             exit_reason="shutdown")
    assert ud.record["task_id"] == "task-1"
    assert "segment-2" not in ifr._load()
