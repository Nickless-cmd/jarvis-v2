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

    def test_finalize_ligger_FAKTISK_i_en_finally_blok(self):
        """Regressionstesten for selve hullet — verificeret med AST, ikke tekstsøgning.

        Codex 20. aug: den første version af denne test greppede blot efter
        kaldeteksten i hele kildefilen. Den ville være grøn selv hvis linjen
        blev flyttet tilbage ind i en gren — altså præcis den bug den skulle
        fange. Nu parses træet, og kaldet skal ligge i `finalbody` på en
        try-node. Det er dét der giver garantien "alle runs når hertil".
        """
        import ast
        import inspect

        from core.services import visible_runs

        tree = ast.parse(inspect.getsource(visible_runs))

        def _calls_in(body) -> set[str]:
            names = set()
            for stmt in body:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Call):
                        f = sub.func
                        if isinstance(f, ast.Name):
                            names.add(f.id)
                        elif isinstance(f, ast.Attribute):
                            names.add(f.attr)
            return names

        # Det er ikke nok at kaldet ligger i EN finally — hele run-funktionen er
        # pakket ind i en ydre try/finally, så selv et kald inde i en gren ville
        # teknisk være "i en finally". Kravet er at det deler finally med
        # in-flight-oprydningen (`_mark_run_completed`), for DEN blok er
        # beviseligt den der køres for hvert eneste run.
        sammen = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try) and node.finalbody:
                names = _calls_in(node.finalbody)
                if "_finalize_run" in names and "_mark_run_completed" in names:
                    sammen = True
        assert sammen, (
            "_finalize_run deler ikke finally-blok med in-flight-oprydningen. "
            "Enten er den flyttet ind i en gren igen (= den oprindelige bug, "
            "hvor kun agentiske runs rykkede cold_floor), eller "
            "afslutningslogikken er delt op og garantien er væk."
        )

    def test_ingen_konkurrerende_lifecycle_kald_tilbage(self):
        """run_finalization skal have ENE-ejerskab (Codex' note).

        Det gamle gren-kald var idempotent og dermed harmløst, men to ejere af
        samme sideeffekt betyder to steder at holde styr på næste gang nogen
        ændrer afslutningslogikken."""
        import inspect

        from core.services import visible_runs
        src = inspect.getsource(visible_runs)
        assert "_advance_tool_lifecycle(run.session_id)" not in src, \
            "gammelt gren-kald findes stadig — ejerskabet er delt"
