"""Kobling: skill-fladen skal baade SENDES og GEMMES af det synlige run.

`skill_flade_event` og `TurnAccumulator.skill_surface` er testet hver for sig.
Det hyppigste moenster i dette repo er kode der virker men som ingen kalder
(se reference_built_but_not_connected) — denne test fanger at koblingen i
`_stream_visible_run` forsvinder. Et fuldt stream-run kan ikke koeres i en
unit-test uden at mocke hele udbyder-laget, saa kildeteksten maales.
"""
import inspect

from core.services import visible_runs


def _kilde() -> str:
    return inspect.getsource(visible_runs._stream_visible_run)


def test_eventet_sendes_efter_prompt_bygningen():
    k = _kilde()
    i_foerste = k.index("_fp_first = True")
    i_event = k.index('_sse("skill_surface"')
    assert i_foerste < i_event, "eventet skal sendes naar prompten ER bygget (foerste token)"
    assert "skill_flade_event(run.user_message)" in k


def test_fladen_gemmes_paa_turen_der_bygger_blokkene():
    k = _kilde()
    assert "_turn.skill_surface = _skill_flade" in k
    assert "_turn.build_blocks(" in k


def test_v2_kender_kind():
    from core.services.visible_runs_sse_v2 import _KNOWN_SYSTEM_EVENT_KINDS
    assert "skill_surface" in _KNOWN_SYSTEM_EVENT_KINDS
