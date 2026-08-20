"""cold_floor skal rykke ved ALLE afsluttede runs — ikke kun agentiske.

Bug'en (målt live 20. aug 2026 på Bjørns session): `_advance_tool_lifecycle`
blev kaldt ét sted, inde i den agentiske followup-gren. Men et run kan
afsluttes ad mindst otte veje. Floor'en stod på 104207 fra kl. 18:05 mens
otte afsluttede runs (18:23-18:31) passerede uden at flytte den. Et manuelt
`evaluate_and_advance` gav straks 104207 → 104311, flyttede 61 tool-results
fra warm til cold og sparede 3.641 tokens i hver efterfølgende prompt.

Diagnosen kom fra Codex, som forudsagde både floor-tallet og effekten korrekt.
"""
from __future__ import annotations

from unittest.mock import patch

from core.services.visible_runs_sections.run_finalization import (
    advance_tool_lifecycle,
    finalize_run,
)


class TestFinalizeRun:
    def test_completed_rykker_floor(self):
        with patch("core.context.tool_result_lifecycle.evaluate_and_advance") as adv:
            finalize_run("sess-1", status="completed")
        adv.assert_called_once_with("sess-1")

    def test_afbrudt_run_rykker_IKKE(self):
        """Et afbrudt run kan have efterladt halve tool-exchanges — fryser vi
        dem til stubs, taber Jarvis kontekst han stadig skal bruge."""
        for status in ("interrupted", "failed", "cancelled"):
            with patch("core.context.tool_result_lifecycle.evaluate_and_advance") as adv:
                finalize_run("sess-1", status=status)
            assert adv.call_count == 0, f"{status} måtte ikke rykke floor"

    def test_tom_session_id_er_no_op(self):
        with patch("core.context.tool_result_lifecycle.evaluate_and_advance") as adv:
            finalize_run("", status="completed")
        assert adv.call_count == 0


class TestSelvSikkerhed:
    def test_fejl_i_lifecycle_vaelter_ikke_run_afslutningen(self):
        """Kaldet sker i run-afslutningens finally. Kaster den, mister vi
        in-flight-oprydningen bagefter og runnet står som 'hængende'."""
        with patch("core.context.tool_result_lifecycle.evaluate_and_advance",
                   side_effect=RuntimeError("DB nede")):
            advance_tool_lifecycle("sess-1")   # må ikke kaste
            finalize_run("sess-1", status="completed")

    def test_manglende_modul_haandteres(self):
        with patch("core.context.tool_result_lifecycle.evaluate_and_advance",
                   side_effect=ImportError):
            advance_tool_lifecycle("sess-1")


class TestBagudkompatibilitet:
    def test_gammelt_navn_virker_stadig(self):
        """visible_runs._advance_tool_lifecycle re-eksporteres — call-sites og
        monkeypatches i eksisterende tests må ikke knække."""
        from core.services import visible_runs
        assert visible_runs._advance_tool_lifecycle is advance_tool_lifecycle

    def test_finally_grenen_kalder_finalize(self):
        """Regressionstesten for selve hullet: kaldet SKAL stå i den finally-blok
        alle runs nåar — ikke kun i den agentiske gren."""
        import inspect

        from core.services import visible_runs
        src = inspect.getsource(visible_runs)
        assert "_finalize_run(run.session_id, status=_final_run_status)" in src, \
            "finally-blokkens lifecycle-kald mangler — bug'en er tilbage"
