"""Tests for goal_signal_synthesizer — signal-indsamling (12/10-2026).

Baggrund: `_gather_signals` kaldte `recent_dream_excerpts` fra
`dream_distillation_daemon`. Den funktion findes ikke i modulet, og kaldet laa
i et bart `except Exception: pass` med kommentaren «may not have this exact
API — skip silently». Synthesizeren har derfor ALDRIG laest en droem — den
faldt tavst tilbage til tom streng hver gang.

Den rigtige kilde er `get_dream_residue_for_prompt()`, som returnerer den
aktive droemmerest som en faerdig tekstblok (samme funktion prompt-laget og
dreaming_session bruger).

Testene her holder to ting fast:
1. `dreams`-noeglen fyldes fra den RIGTIGE funktion.
2. Ingen import i modulet peger paa et navn der ikke findes.
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

from core.services import goal_signal_synthesizer as gss

_MODUL_STI = Path(gss.__file__)


def test_dreams_fyldes_fra_den_rigtige_funktion(monkeypatch):
    """`dreams` skal komme fra `get_dream_residue_for_prompt`, ikke et doedt navn."""
    from core.services import dream_distillation_daemon as dd

    kaldt = {"n": 0}

    def _falsk_residue(*, max_chars: int = 180) -> str:
        kaldt["n"] += 1
        return "## Drømmerest (lavmælt carry-over)\nEn testdroem om noget der venter."

    monkeypatch.setattr(dd, "get_dream_residue_for_prompt", _falsk_residue)
    # De to andre kilder holdes ude af billedet, saa vi maaler praecist paa droemme-vejen.
    monkeypatch.setattr(gss, "_gather_signals", gss._gather_signals)

    out = gss._gather_signals()

    assert kaldt["n"] == 1, "get_dream_residue_for_prompt blev ikke kaldt"
    assert "En testdroem" in out["dreams"], (
        f"dreams blev ikke fyldt fra den rigtige funktion — fik: {out['dreams']!r}"
    )


def test_dreams_er_tom_naar_der_ikke_er_nogen_residue(monkeypatch):
    """Ingen aktiv droemmerest → tom streng, ikke en fejl."""
    from core.services import dream_distillation_daemon as dd

    monkeypatch.setattr(dd, "get_dream_residue_for_prompt", lambda **kw: "")

    out = gss._gather_signals()

    assert out["dreams"] == ""


def test_ingen_import_i_modulet_peger_paa_et_doedt_navn():
    """Fanger den klasse fejl der skjulte sig bag `except Exception: pass`.

    Et `from X import navn` hvor `navn` ikke findes i X kaster ImportError ved
    kald — og hvis kaldet ligger i en tavs except, forsvinder fejlen. Denne test
    laeser modulet statisk og importerer hvert navn for at bevise det findes.
    """
    tree = ast.parse(_MODUL_STI.read_text(encoding="utf-8"))
    doede: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        try:
            modul = importlib.import_module(node.module)
        except Exception as exc:  # modulet selv kan ikke importeres
            doede.append(f"{node.module}: {exc}")
            continue
        for alias in node.names:
            if not hasattr(modul, alias.name):
                doede.append(f"{node.module}.{alias.name}")

    assert not doede, "imports der peger paa navne der ikke findes:\n" + "\n".join(doede)
