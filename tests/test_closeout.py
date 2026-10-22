"""Triggerne der binder de lavt-scorende lukke-beslutninger til et øjeblik.

## Hvorfor testen findes

Målt 22/10-2026: 80 aktive beslutninger, **0** bundet til en trigger. To
triggere fandtes, så mekanismen kørte hver runde og matchede intet. Adherence
0,726, og de 12 laveste var alle lukke-regler uden et øjeblik at hænge på.

Testen vogter to ting der begge kan gå i stykker uden at nogen ser det:

1. **At triggerne faktisk registreres.** `_TRIGGER_REGISTRY` fyldes ved import
   af pakken. Glemmer nogen `from . import closeout`, forsvinder triggeren —
   og `_active_decisions_with_triggers()` matcher stadig rækkerne, så der
   kommer ingen fejl. Kun en tom fyring.
2. **At de læser tool_calls' ÆGTE form.** Formen er rå model-dicts
   (`{"function": {"name", "arguments"}}`), ikke flade felter. En trigger der
   læser `call["name"]` alene fyrer aldrig i produktion — men ville være grøn
   mod en opdigtet fixture.
"""
from __future__ import annotations

import core.services.decision_triggers  # noqa: F401 — registrerer pakken
from core.services.decision_signals import TriggerContext, _TRIGGER_REGISTRY
from core.services.decision_triggers.closeout import (
    closing_round_with_tools,
    commit_just_made,
)


def _ctx(**over) -> TriggerContext:
    base = dict(
        user_message="hej",
        session_id="s1",
        run_id="r1",
        consecutive_tool_only_rounds=0,
        recent_tool_calls=[],
        recent_assistant_text="",
        agentic_round_seq=0,
        timestamp="2026-10-22T00:00:00Z",
    )
    base.update(over)
    return TriggerContext(**base)


def _bash(cmd: str) -> dict:
    """En tool_call i den form modellen faktisk producerer."""
    return {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": {"command": cmd}}}


def test_pakken_alene_registrerer_triggerne():
    """Den ægte søm: import af PAKKEN skal registrere triggerne.

    Testen kører i en frisk proces med vilje. Importerer den selv
    `closeout`-modulet (som de andre tests gør for at kalde funktionerne),
    registreres triggerne uanset om `__init__.py` nævner dem — og så er
    vagten grøn på trods af at pakken ikke længere registrerer noget.
    Målt 22/10-2026: præcis det skete, og mutationsprøven fældede ikke.
    """
    import subprocess
    import sys
    from pathlib import Path

    kode = (
        "import core.services.decision_triggers\n"
        "from core.services.decision_signals import _TRIGGER_REGISTRY\n"
        "mangler = {'commit_just_made', 'closing_round_with_tools'} - set(_TRIGGER_REGISTRY)\n"
        "raise SystemExit(1 if mangler else 0)\n"
    )
    rod = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-c", kode], capture_output=True, text=True, cwd=str(rod)
    )
    assert r.returncode == 0, (
        "import af pakken registrerede ikke closeout-triggerne — "
        "så matcher beslutningerne intet og signalet fyrer aldrig. "
        f"stderr: {r.stderr[-400:]}"
    )


def test_commit_fyrer_paa_en_faktisk_commit():
    assert commit_just_made(_ctx(recent_tool_calls=[_bash("cd repo && git commit -m 'x'")])) is True


def test_commit_fyrer_ikke_paa_andet_bash():
    assert commit_just_made(_ctx(recent_tool_calls=[_bash("ls -la"), _bash("git status")])) is False


def test_commit_laeser_argumenter_som_json_streng():
    """Ollama sender argumenterne som en JSON-streng — ikke et dict."""
    call = {"function": {"name": "bash", "arguments": '{"command": "git commit -m y"}'}}
    assert commit_just_made(_ctx(recent_tool_calls=[call])) is True


def test_commit_fyrer_ikke_paa_git_log_der_naevner_commit():
    """`git log --grep=commit` er ikke en commit. Strengen må ikke være nok."""
    assert commit_just_made(_ctx(recent_tool_calls=[_bash("git log --grep=commit")])) is False


def test_sen_runde_med_vaerktoejer_fyrer():
    assert closing_round_with_tools(_ctx(agentic_round_seq=2, recent_tool_calls=[_bash("ls")])) is True


def test_foerste_runde_fyrer_ikke():
    """Overtrædelsen sker ikke i runde 1 — den sker når jeg er dybt i arbejdet."""
    assert closing_round_with_tools(_ctx(agentic_round_seq=1, recent_tool_calls=[_bash("ls")])) is False


def test_sen_runde_uden_vaerktoejer_fyrer_ikke():
    assert closing_round_with_tools(_ctx(agentic_round_seq=4, recent_tool_calls=[])) is False
