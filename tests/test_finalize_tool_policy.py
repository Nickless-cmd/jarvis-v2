"""Den tvungne afslutning maa kun smide vaerktoejslisten vaek naar den SKAL.

Prompten er [systemprompt, vaerktoejsliste, samtale], og praefiks-cachen
genkender fra begyndelsen og fremad. Fjernes listen, er alt efter
systemprompten nyt. Maalt paa CT105 28/9-2026, run f3897d2bde28:

    runde 43   hit 99.584   miss  77.175
    runde 44   hit  9.600   miss 118.211   <- vaerktoejerne fjernet

41.036 tokens for én runde — turens dyreste, og det er den der skriver svaret.

Listen blev fjernet fordi mange modeller ignorerer `tool_choice="none"` og saa
aldrig gav brugeren prosa. Men DeepSeek adlyder det (maalt tre gange, se
finalize_tool_policy), saa dér er den kolde runde en unoedig pris.
"""
from __future__ import annotations

import ast
import pathlib

from core.services.finalize_tool_policy import behold_vaerktoejer_paa_finalize as behold


def test_deepseek_beholder_listen():
    assert behold("deepseek") is True


def test_de_oevrige_faar_stadig_den_fysiske_fjernelse():
    """Hos dem er den kolde runde prisen for et garanteret svar."""
    for p in ("ollama", "openai-codex", "github-copilot", "groq", "mistral"):
        assert behold(p) is False, p


def test_en_UKENDT_udbyder_falder_til_den_sikre_side():
    """Hvidliste, ikke sortliste. Gaetter vi forkert her, koster det tokens.
    Gaetter vi forkert den anden vej, koster det brugeren sit svar."""
    for p in ("en-ny-udbyder", "", None, "   "):
        assert behold(p) is False, repr(p)


def test_navnet_normaliseres():
    """Udbydernavne kommer fra config og traileren med varierende form."""
    assert behold(" DeepSeek ") is True
    assert behold("DEEPSEEK") is True


def test_fjernelsen_ligger_under_POLITIKKENS_else():
    """Kravet er praecist: nulstillingen skal ligge i else-grenen af netop den
    if der spoerger politikken.

    Foerste udgave af denne test spurgte bare «ligger linjen i en gren?». Den
    var groen baade foer og efter rettelsen, fordi linjen allerede laa inde i
    `if _is_last_round:`. Den maalte ingenting — mutationen gik lige igennem.
    """
    kilde = pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")
    traeet = ast.parse(kilde)

    def er_politik_kaldet(node) -> bool:
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "_behold")

    def nulstiller_vaerktoejer(krop) -> bool:
        for barn in krop:
            for n in ast.walk(barn):
                if not isinstance(n, ast.Assign):
                    continue
                if "_round_tool_definitions" not in [
                        t.id for t in n.targets if isinstance(t, ast.Name)]:
                    continue
                if isinstance(n.value, ast.Constant) and n.value.value is None:
                    return True
        return False

    fundet = [n for n in ast.walk(traeet)
              if isinstance(n, ast.If) and er_politik_kaldet(n.test)
              and nulstiller_vaerktoejer(n.orelse)]
    assert fundet, (
        "ingen `if _behold(...): ... else: _round_tool_definitions = None` — "
        "enten spoerges politikken ikke, eller fjernelsen sker uanset svaret")

    # ... og ingen ANDEN nulstilling paa finalize-stien maa snige sig udenom.
    i_else = {n.lineno for f in fundet for b in f.orelse for n in ast.walk(b)
              if hasattr(n, "lineno")}
    udenfor = []
    for n in ast.walk(traeet):
        if isinstance(n, ast.Assign) and "_round_tool_definitions" in [
                t.id for t in n.targets if isinstance(t, ast.Name)]:
            if isinstance(n.value, ast.Constant) and n.value.value is None:
                if n.lineno not in i_else:
                    udenfor.append(n.lineno)
    assert not udenfor, f"vaerktoejerne nulstilles ogsaa udenom politikken: linje {udenfor}"


def test_politikken_er_faktisk_koblet_paa():
    """En politik ingen kalder er en fil, ikke en rettelse."""
    kilde = pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")
    traeet = ast.parse(kilde)
    importeret = any(
        isinstance(n, ast.ImportFrom) and (n.module or "").endswith("finalize_tool_policy")
        for n in ast.walk(traeet))
    assert importeret, "visible_runs importerer ikke finalize_tool_policy"
