"""flag_side_task: budgettet skal overleve begge grene af _exec_flag_side_task.

Målt 4/11-2026: finding-grenen (finding_kind sat) tabte autonomy_mode,
max_minutes og max_tool_calls og gemte none/20/12 — uden fejl til kalderen.
"""
import ast
import inspect
from contextlib import nullcontext

import pytest

from core.services import run_finding_accounting, side_tasks

_BUDGET = {"autonomy_mode": "inspect", "max_minutes": 45, "max_tool_calls": 40}
_FELTER = ("autonomy_mode", "max_minutes", "max_tool_calls")


@pytest.fixture
def lager(monkeypatch):
    tasks: list[dict] = []
    findings: list[dict] = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _k, _d: list(tasks))
    monkeypatch.setattr(side_tasks, "save_json", lambda _k, rows: tasks.__setitem__(slice(None), rows))
    monkeypatch.setattr(side_tasks, "med_laas", lambda _k: nullcontext())
    monkeypatch.setattr(run_finding_accounting, "load_json", lambda _k, _d: list(findings))
    monkeypatch.setattr(run_finding_accounting, "save_json", lambda _k, rows: findings.__setitem__(slice(None), rows))
    monkeypatch.setattr(run_finding_accounting, "med_laas", lambda _k: nullcontext())
    return tasks


def _gemt(tasks: list[dict]) -> dict:
    assert len(tasks) == 1
    return {k: tasks[0][k] for k in _FELTER}


def _finding_args(**extra) -> dict:
    return {
        "finding_kind": "coverage_gap", "disposition": "side_task",
        "path": "core/x.py", "behavior": "tabt budget", "evidence": "målt 4/11",
        "title": "Finding-opgave", "prompt": "Ret det", "session_id": "chat-1",
        **extra,
    }


def _plain_args(**extra) -> dict:
    return {"title": "Plain-opgave", "prompt": "Ret det", "session_id": "chat-1", **extra}


def test_finding_grenen_gemmer_det_bedte_budget(lager):
    result = side_tasks._exec_flag_side_task(_finding_args(**_BUDGET))
    assert result["status"] == "ok"
    assert _gemt(lager) == _BUDGET


def test_begge_grene_gemmer_identiske_budgetfelter(lager):
    side_tasks._exec_flag_side_task(_finding_args(**_BUDGET))
    fra_finding = _gemt(lager)
    lager.clear()
    side_tasks._exec_flag_side_task(_plain_args(**_BUDGET))
    assert _gemt(lager) == fra_finding == _BUDGET


@pytest.mark.parametrize("args_fn", [_finding_args, _plain_args])
def test_uden_budget_gemmes_default_i_begge_grene(lager, args_fn):
    assert side_tasks._exec_flag_side_task(args_fn())["status"] == "ok"
    assert _gemt(lager) == {"autonomy_mode": "none", "max_minutes": 20, "max_tool_calls": 12}


def test_ugyldigt_budget_i_finding_grenen_afvises_ikke_tavst(lager):
    result = side_tasks._exec_flag_side_task(_finding_args(autonomy_mode="bogus"))
    assert result == {"status": "error", "error": "unknown autonomy_mode"}
    assert lager == []


def test_hver_gren_i_exec_flag_side_task_videresender_budgettet():
    """Guard: en FREMTIDIG gren der kalder flag()/record_finding() uden budget fanges her.

    Formen findes, men en ny vej uden om den ses ellers ikke — det var fejlen.
    """
    træ = ast.parse(inspect.getsource(side_tasks._exec_flag_side_task))
    kald = [
        n for n in ast.walk(træ)
        if isinstance(n, ast.Call)
        and getattr(n.func, "id", getattr(n.func, "attr", "")) in {"flag", "record_finding"}
    ]
    assert len(kald) >= 2, "forventer både finding-grenen og den almindelige gren"
    for k in kald:
        navngivne = {kw.arg for kw in k.keywords if kw.arg}
        udfoldet = [kw.value for kw in k.keywords if kw.arg is None]
        via_budget = any(
            isinstance(v, ast.Name) and v.id == "budget" for v in udfoldet
        )
        assert via_budget or set(_FELTER) <= navngivne, (
            f"{ast.unparse(k.func)} (linje {k.lineno}) videresender ikke budgettet"
        )
