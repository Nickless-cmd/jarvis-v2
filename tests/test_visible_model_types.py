"""Tests for core/services/visible_model_types.py.

Typerne er kontrakten mellem provider-adapterne og visible_runs' dispatch.
Rækkefølgen af isinstance-tjek dér afhænger af at typerne er DISTINKTE — en
tanke må aldrig kunne forveksles med et svar. Det er værd at holde fast i en
test, fordi konsekvensen ellers er tavs: ræsonnering der lækker ud i chatten.
"""

from __future__ import annotations

from core.services.visible_model_types import (
    VisibleModelDelta,
    VisibleModelReasoningDelta,
    VisibleModelResult,
    VisibleModelStreamCancelled,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)


def _result() -> VisibleModelResult:
    return VisibleModelResult(text="", input_tokens=0, output_tokens=0, cost_usd=0.0)


class TestReasoningDelta:
    def test_baerer_sin_tekst(self) -> None:
        assert VisibleModelReasoningDelta(delta="lad mig taenke").delta == "lad mig taenke"

    def test_er_ikke_en_svar_delta(self) -> None:
        """Dispatch i visible_runs skelner på type alene."""
        tanke = VisibleModelReasoningDelta(delta="x")
        assert not isinstance(tanke, VisibleModelDelta)
        assert not isinstance(VisibleModelDelta(delta="x"), VisibleModelReasoningDelta)

    def test_slots_forhindrer_smuglegods(self) -> None:
        """slots=True: ingen kan hænge ekstra felter på undervejs."""
        import pytest
        with pytest.raises(AttributeError):
            VisibleModelReasoningDelta(delta="x").visible = True  # type: ignore[attr-defined]


class TestOevrigeTyper:
    def test_de_fire_stroem_typer_er_indbyrdes_distinkte(self) -> None:
        items = [
            VisibleModelDelta(delta="a"),
            VisibleModelReasoningDelta(delta="b"),
            VisibleModelToolCalls(tool_calls=[]),
            VisibleModelStreamDone(result=_result()),
        ]
        for i, a in enumerate(items):
            for j, b in enumerate(items):
                if i != j:
                    assert not isinstance(a, type(b)), f"{type(a)} forveksles med {type(b)}"

    def test_result_har_reasoning_felt(self) -> None:
        """Persistensvejen for ræsonnering — uafhængig af visningen."""
        r = _result()
        assert hasattr(r, "reasoning_content")

    def test_cancelled_er_en_fejl_der_kan_rejses(self) -> None:
        assert issubclass(VisibleModelStreamCancelled, RuntimeError)
