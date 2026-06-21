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
