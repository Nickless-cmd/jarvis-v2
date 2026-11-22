"""Tests for core.tools.tool_execution_gateway — schema/lifecycle/observation-gateway.

Testene rammer adfærden, ikke implementeringen: at den interne vej ikke går
gennem modellens lifecycle, at en blokerende hook faktisk forhindrer
``execute`` i at køre, og at en fejlende hook ikke kan dræbe resultatet.
"""
from __future__ import annotations

import pytest

from core.services import tool_lifecycle_hooks as hooks
from core.tools.tool_execution_gateway import (
    execute_force_tool_call,
    execute_tool_call,
)


class _BlokerendeHook:
    """Blokerer ethvert kald — beviser at before_tool kan stoppe udførelsen."""

    def before_tool(self, tool_name: str, arguments: dict) -> hooks.HookDecision:
        return hooks.HookDecision.block("test-blok")

    def after_tool(self, tool_name: str, arguments: dict, result: dict) -> None:
        return None


class _FejlendeHook:
    """Kaster i begge faser — resultatet skal overleve alligevel."""

    def before_tool(self, tool_name: str, arguments: dict) -> None:
        raise RuntimeError("before fejler")

    def after_tool(self, tool_name: str, arguments: dict, result: dict) -> None:
        raise RuntimeError("after fejler")


class _OptællendeHook:
    """Noterer hvilke faser der blev kørt — så bypass kan måles, ikke antages."""

    def __init__(self) -> None:
        self.kald: list[tuple[str, str]] = []

    def before_tool(self, tool_name: str, arguments: dict) -> None:
        self.kald.append(("before", tool_name))

    def after_tool(self, tool_name: str, arguments: dict, result: dict) -> None:
        self.kald.append(("after", tool_name))


@pytest.fixture(autouse=True)
def _ryd_hooks():
    hooks.clear_hooks()
    hooks.set_enabled(True)
    yield
    hooks.clear_hooks()
    hooks.set_enabled(False)


def _executor(svar: dict):
    kaldt: list[bool] = []

    def execute() -> dict:
        kaldt.append(True)
        return svar

    return execute, kaldt


def test_internal_bypasser_hooks() -> None:
    """Interne kald er runtime'ets egne og skal ikke gennem modellens lifecycle."""
    hook = _OptællendeHook()
    hooks.register_hook(hook)
    execute, kaldt = _executor({"status": "ok"})

    resultat = execute_tool_call("test", {}, execute=execute, internal=True)

    assert resultat == {"status": "ok"}
    assert kaldt == [True]
    assert hook.kald == []


def test_blokerende_hook_stopper_udfoerelsen() -> None:
    hooks.register_hook(_BlokerendeHook())
    execute, kaldt = _executor({"status": "ok"})

    resultat = execute_tool_call("test", {}, execute=execute, internal=False)

    assert resultat["status"] == "error"
    assert resultat["error"] == "tool_blocked_by_lifecycle_hook"
    assert kaldt == [], "execute må ikke kaldes når hooken blokerer"


def test_fejlende_hook_draeber_ikke_resultatet() -> None:
    hooks.register_hook(_FejlendeHook())
    execute, kaldt = _executor({"status": "ok"})

    resultat = execute_tool_call("test", {}, execute=execute, internal=False)

    assert resultat == {"status": "ok"}
    assert kaldt == [True]


def test_force_stien_gaar_ogsaa_gennem_hooks() -> None:
    """Den autonome/approved vej må ikke være et hul uden om lifecycle."""
    hooks.register_hook(_BlokerendeHook())
    execute, kaldt = _executor({"status": "ok"})

    resultat = execute_force_tool_call("test", {}, execute=execute, internal=False)

    assert resultat["status"] == "error"
    assert kaldt == []


def test_force_internal_bypasser_hooks() -> None:
    hook = _OptællendeHook()
    hooks.register_hook(hook)
    execute, kaldt = _executor({"status": "ok"})

    resultat = execute_force_tool_call("test", {}, execute=execute, internal=True)

    assert resultat == {"status": "ok"}
    assert hook.kald == []
