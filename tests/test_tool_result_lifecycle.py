"""Tests for core/context/tool_result_lifecycle.py — cache-gaten på cold_floor.

Baggrund (målt 30-08-2026): cold_floor vandrer fremad fra de ældste beskeder,
så de nyligt kolde tool-results er altid de ældste stadig-varme. Hver avancering
omskrev derfor historik TIDLIGT i prompten — rendering med successive gulve viste
at kun 5-48 % af prefixet overlevede. DeepSeek genbruger kun ved fuldt match, og
et miss koster 31,4× et hit.

Gaten udskyder avanceringen til compaction alligevel omskriver historikken, med
en sikkerhedsventil så en værktøjstung session ikke kan vokse ud over vinduet.
"""

from __future__ import annotations

import pytest

from core.context.tool_result_lifecycle import (
    as_bool,
    compute_new_floor,
    estimate_tool_tokens,
    should_advance,
)


class TestShouldAdvance:
    def test_no_compaction_defers(self) -> None:
        """Kernen: uden compaction rører vi ikke historikken."""
        ok, why = should_advance(
            warm_tool_tokens=1000, current_epoch=5, recorded_epoch=5,
            hard_ceiling=100_000,
        )
        assert ok is False
        assert "cache" in why

    def test_compaction_allows_advance(self) -> None:
        ok, why = should_advance(
            warm_tool_tokens=1000, current_epoch=6, recorded_epoch=5,
            hard_ceiling=100_000,
        )
        assert ok is True
        assert "compaction" in why

    def test_first_ever_compaction_allows_advance(self) -> None:
        """Session der lige er blevet komprimeret første gang: epoke 0 -> N."""
        ok, _ = should_advance(
            warm_tool_tokens=10, current_epoch=42, recorded_epoch=0,
            hard_ceiling=100_000,
        )
        assert ok is True

    def test_never_compacted_session_defers(self) -> None:
        """Aldrig komprimeret (0 == 0) → vent. Prompten vokser, men cachet."""
        ok, _ = should_advance(
            warm_tool_tokens=5000, current_epoch=0, recorded_epoch=0,
            hard_ceiling=100_000,
        )
        assert ok is False

    def test_hard_ceiling_overrides_the_gate(self) -> None:
        """Sikkerhedsventil: et for langt prompt fejler HELT — værre end cache-brud."""
        ok, why = should_advance(
            warm_tool_tokens=120_001, current_epoch=5, recorded_epoch=5,
            hard_ceiling=120_000,
        )
        assert ok is True
        assert "sikkerhedsventil" in why

    def test_exactly_at_hard_ceiling_still_defers(self) -> None:
        """Ventilen åbner først når loftet OVERSKRIDES — ikke ved lighed."""
        ok, _ = should_advance(
            warm_tool_tokens=120_000, current_epoch=5, recorded_epoch=5,
            hard_ceiling=120_000,
        )
        assert ok is False

    def test_zero_hard_ceiling_disables_the_valve(self) -> None:
        ok, _ = should_advance(
            warm_tool_tokens=10**9, current_epoch=5, recorded_epoch=5,
            hard_ceiling=0,
        )
        assert ok is False

    def test_gate_can_be_switched_off(self) -> None:
        """Kill-switch: gammel adfærd skal kunne genskabes uden deploy."""
        ok, why = should_advance(
            warm_tool_tokens=0, current_epoch=5, recorded_epoch=5,
            hard_ceiling=100_000, only_on_compact=False,
        )
        assert ok is True
        assert "slået fra" in why

    @pytest.mark.parametrize("warm", [0, 1, 39_999, 40_000])
    def test_below_valve_and_no_compaction_always_defers(self, warm: int) -> None:
        ok, _ = should_advance(
            warm_tool_tokens=warm, current_epoch=3, recorded_epoch=3,
            hard_ceiling=120_000,
        )
        assert ok is False


class TestPureFloorMathUnchanged:
    """Gaten må ikke ændre selve gulv-beregningen — kun HVORNÅR den anvendes."""

    def _msgs(self, n_tools: int, tool_chars: int = 4000) -> list[dict]:
        out: list[dict] = []
        mid = 1
        for i in range(n_tools):
            out.append({"id": mid, "role": "user", "content": "u"}); mid += 1
            out.append({"id": mid, "role": "tool", "content": "x" * tool_chars}); mid += 1
        return out

    def test_estimate_counts_only_tool_rows(self) -> None:
        msgs = [{"id": 1, "role": "user", "content": "x" * 400},
                {"id": 2, "role": "tool", "content": "y" * 400}]
        assert estimate_tool_tokens(msgs) == 100

    def test_floor_is_monotonic(self) -> None:
        msgs = self._msgs(30)
        floor = compute_new_floor(msgs, current_floor=0, run_window=8,
                                  token_ceiling=1000, hysteresis=0.25)
        again = compute_new_floor(msgs, current_floor=floor, run_window=8,
                                  token_ceiling=1000, hysteresis=0.25)
        assert again >= floor

    def test_small_session_stays_at_zero(self) -> None:
        assert compute_new_floor(self._msgs(2), current_floor=0, run_window=8,
                                 token_ceiling=100_000, hysteresis=0.25) == 0


class TestAsBool:
    """bool('off') er True — netop den fælde der har slukket værn i tavshed før."""

    @pytest.mark.parametrize("v", ["off", "false", "no", "0", "nej", "disabled", ""])
    def test_falsey_strings(self, v: str) -> None:
        assert as_bool(v) is False

    @pytest.mark.parametrize("v", ["on", "true", "yes", "1", "ja", "enabled"])
    def test_truthy_strings(self, v: str) -> None:
        assert as_bool(v) is True

    def test_case_and_whitespace_insensitive(self) -> None:
        assert as_bool("  OFF  ") is False
        assert as_bool("On") is True

    def test_missing_uses_default(self) -> None:
        assert as_bool(None, default=True) is True
        assert as_bool(None, default=False) is False

    def test_unknown_value_falls_back_to_default(self) -> None:
        """En tastefejl må ikke slukke værnet i tavshed."""
        assert as_bool("vielleicht", default=True) is True

    def test_real_bools_and_numbers(self) -> None:
        assert as_bool(True) is True and as_bool(False) is False
        assert as_bool(1) is True and as_bool(0) is False


class TestValveGovernsInsteadOfRecency:
    """Ventilen skal slippe TOKEN-drevne avanceringer igennem, ikke recency-drevne.

    Målt 30-08: varme tool-tokens 8.931 mod loft 40.000 — token-kriteriet var
    aldrig bindende. Alle 7 avanceringer kom fra `_candidate_by_runs`, som holder
    de sidste N bruger-ture varme og derfor skubber gulvet ved næsten hver tur.
    """

    VALVE = int(40_000 * 1.25)   # blødt loft + hysterese

    def test_recency_driven_advance_is_filtered_out(self) -> None:
        """Typisk tur: langt under loftet → gulvet skal blive stående."""
        ok, _ = should_advance(
            warm_tool_tokens=8_931, current_epoch=0, recorded_epoch=0,
            hard_ceiling=self.VALVE,
        )
        assert ok is False

    def test_token_driven_advance_passes(self) -> None:
        """Konteksten er reelt ved at løbe løbsk → gulvet SKAL rykke."""
        ok, why = should_advance(
            warm_tool_tokens=self.VALVE + 1, current_epoch=0, recorded_epoch=0,
            hard_ceiling=self.VALVE,
        )
        assert ok is True
        assert "sikkerhedsventil" in why

    def test_context_stays_bounded_without_compaction(self) -> None:
        """Compaction er død på den synlige bane (nyeste markør 22-07), så
        ventilen er den eneste kontekst-grænse. Den skal holde."""
        for warm in (0, 10_000, 40_000, self.VALVE):
            ok, _ = should_advance(
                warm_tool_tokens=warm, current_epoch=0, recorded_epoch=0,
                hard_ceiling=self.VALVE,
            )
            assert ok is False, f"{warm} burde udskydes"
        ok, _ = should_advance(
            warm_tool_tokens=self.VALVE + 1, current_epoch=0, recorded_epoch=0,
            hard_ceiling=self.VALVE,
        )
        assert ok is True


class TestRecencyCriterionOff:
    """`run_window <= 0` slukker recency-kriteriet — modulets egen invariant.

    Headeren siger «NO recency-relative logic (breaks the cache)», men "hold de
    sidste N bruger-ture varme" ER recency-relativt og flyttede gulvet ved stort
    set hver tur.
    """

    def _msgs(self, turns: int, tool_chars: int = 400) -> list[dict]:
        out: list[dict] = []
        mid = 1
        for _ in range(turns):
            out.append({"id": mid, "role": "user", "content": "u"}); mid += 1
            out.append({"id": mid, "role": "tool", "content": "x" * tool_chars}); mid += 1
        return out

    def test_many_turns_alone_no_longer_advance_the_floor(self) -> None:
        """40 ture, men kun ~4k tool-tokens: gulvet skal blive stående."""
        msgs = self._msgs(40)
        assert estimate_tool_tokens(msgs) < 40_000
        assert compute_new_floor(msgs, current_floor=0, run_window=0,
                                 token_ceiling=40_000, hysteresis=0.25) == 0

    def test_same_input_advanced_under_the_old_recency_rule(self) -> None:
        """Kontrast: med recency tændt rykkede præcis det samme input gulvet."""
        msgs = self._msgs(40)
        assert compute_new_floor(msgs, current_floor=0, run_window=8,
                                 token_ceiling=40_000, hysteresis=0.25) > 0

    def test_token_pressure_still_advances_with_recency_off(self) -> None:
        """Den absolutte grænse bunder stadig konteksten."""
        msgs = self._msgs(40, tool_chars=8000)
        assert estimate_tool_tokens(msgs) >= 40_000 * 1.25
        assert compute_new_floor(msgs, current_floor=0, run_window=0,
                                 token_ceiling=40_000, hysteresis=0.25) > 0

    def test_negative_run_window_is_also_off(self) -> None:
        assert compute_new_floor(self._msgs(40), current_floor=0, run_window=-1,
                                 token_ceiling=40_000, hysteresis=0.25) == 0

    def test_still_monotonic_with_recency_off(self) -> None:
        msgs = self._msgs(40, tool_chars=8000)
        f1 = compute_new_floor(msgs, current_floor=0, run_window=0,
                               token_ceiling=40_000, hysteresis=0.25)
        f2 = compute_new_floor(msgs, current_floor=f1, run_window=0,
                               token_ceiling=40_000, hysteresis=0.25)
        assert f2 >= f1
