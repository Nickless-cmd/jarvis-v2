"""Regression: _post_process må ikke stille blive en generator (dræber pipelinen).

Rod-årsag 2026-06-14→06-21: et `yield` blev tilføjet i _post_process (deklareret
-> None), hvilket gjorde den til en generator-funktion. `Thread(target=_post_process)`
skabte derefter bare et generator-OBJEKT uden at køre kroppen → fact_gate, diagnosis,
fabrikations-nudge, memory-postprocess og auto-continuation døde STILLE i en uge.
Se reference_post_process_generator_death.
"""
from __future__ import annotations

import inspect
import threading
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "core" / "services" / "visible_runs.py"


def test_thread_target_generator_principle():
    """Bevis-låsning: Thread(target=generatorfunc) kører IKKE kroppen; drain gør."""
    ran: list[str] = []

    def genfunc():
        ran.append("body")
        yield 1

    assert inspect.isgeneratorfunction(genfunc)
    t = threading.Thread(target=genfunc, daemon=True)
    t.start(); t.join()
    assert ran == []                        # naiv Thread-start: krop kørte ALDRIG

    def drain():
        for _ in genfunc():
            pass

    t2 = threading.Thread(target=drain, daemon=True)
    t2.start(); t2.join()
    assert ran == ["body"]                  # drain kører kroppen


def test_post_process_callsite_has_generator_guard():
    """Source-regression: call-sitet SKAL have isgeneratorfunction-guarden, så en
    fremtidig yield aldrig igen kan dræbe pipelinen stille."""
    src = _SRC.read_text(encoding="utf-8")
    assert "isgeneratorfunction(_post_process)" in src, (
        "Generator-guard på _post_process-call-sitet mangler — pipelinen kan dø stille igen"
    )


# ── Post-done-kanalen (25/10-2026) ───────────────────────────────────────────
#
# Sideopgaven «scan_correction kan aldrig nå klienten — yield i post-done-tråd»
# hævdede at `scan_correction` blev yieldet inde i `_post_process`, som kører i
# en tråd. Målt i kilden 25/10: `_post_process` har NUL yields, og begge
# `scan_correction`-yields ligger i `_stream_visible_run` — før first-pass-
# grenens terminale `done`. Præmissen var altså forkert.
#
# Men advarslen i guard-kommentaren er stadig sand, og den er værd at værne:
# et `yield` i en post-done-tråd kan pr. definition aldrig nå klienten. Den
# eksisterende guard fanger kun tilfældet hvor HELE `_post_process` bliver en
# generator-funktion. Disse to tests fanger det tidligere: ved at måle kilden
# og ved at måle at eventet faktisk forlader serveren.


def _funktion_yields(nawn: str) -> list[int]:
    """Linjenumre for yields DIREKTE i funktionen ``nawn`` (ikke indlejrede)."""
    import ast

    tree = ast.parse(_SRC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == nawn:
            fundet: list[int] = []

            class _F(ast.NodeVisitor):
                def visit_Yield(self, n: ast.Yield) -> None:
                    fundet.append(n.lineno)

                def visit_YieldFrom(self, n: ast.YieldFrom) -> None:
                    fundet.append(n.lineno)

                def visit_FunctionDef(self, n: ast.FunctionDef) -> None:
                    if n is node:
                        self.generic_visit(n)

                visit_AsyncFunctionDef = visit_FunctionDef

            _F().visit(node)
            return sorted(fundet)
    raise AssertionError(f"funktionen {nawn} findes ikke i visible_runs.py")


def test_post_process_har_ingen_yields() -> None:
    """Et `yield` i `_post_process` er død kode — tråden kan ikke sende noget.

    MUTATION: indsæt `yield 1` i `_post_process` → fejler.
    """
    assert _funktion_yields("_post_process") == [], (
        "_post_process har fået et yield. Den kører i en tråd, så eventet kan "
        "aldrig nå klienten — brug event_bus/run-follow, eller flyt koden "
        "FØR det terminale `done` i _stream_visible_run."
    )
    assert _funktion_yields("_drain_post_process") == [], (
        "_drain_post_process må kun dræne — et yield dér sendes ingen steder hen."
    )


def test_scan_correction_forlader_serveren() -> None:
    """Den ægte måling: eventet skal komme UD af v2-translatoren.

    Sideopgaven krævede bevis i den anden ende — «se eventet forlade serveren,
    ikke se at DB'en er rigtig». DB'en har været rigtig hele tiden; det er
    derfor fejlen overlevede tre commits.

    MUTATION: fjern videresendelsen i translatoren → `RETTET` forsvinder → fejler.
    """
    import asyncio
    import json

    from core.services.visible_runs_sse_v2 import translate_to_v2

    def sse(ev: str, data: dict) -> str:
        return f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def legacy():
        yield sse("delta", {"type": "delta", "run_id": "r1", "delta": "rå tekst"})
        yield sse(
            "scan_correction",
            {"type": "scan_correction", "run_id": "r1", "corrected": "RETTET tekst"},
        )
        yield sse("done", {"type": "done", "run_id": "r1", "status": "completed"})

    async def koer() -> str:
        ud: list[str] = []
        async for ev in translate_to_v2(
            legacy(), run_id="r1", model="m", provider="p", lane="primary"
        ):
            ud.append(ev)
        return "\n".join(ud)

    blob = asyncio.run(koer())
    assert "scan_correction" in blob, (
        "scan_correction blev kastet væk i oversættelsen — den rettede tekst "
        "kan ikke nå skærmen, uanset hvad DB'en siger."
    )
    assert "RETTET tekst" in blob, (
        "event-navnet kom igennem, men den rettede tekst gjorde ikke. "
        "Frontend kan ikke rette noget den ikke har fået."
    )
