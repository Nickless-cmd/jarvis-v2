"""Vagt for suggest-noten i turens hale.

MÅLT 30/10-2026 (Bjørn): «hvordan gør vi dig bedre til at huske
suggest_next_task i code mode før du afslutter med slut beskeden?»

Reglen fandtes i PRÆFIKSET (~30.000 tegn fra beslutningen), og vagten der
kunne tvinge den var slået fra fordi den skubber `done` og giver
«teleportering». Noten her er den tredje vej: gratis, i halen, tæt på
beslutningen.

Testene dækker fire ting, og den sidste er den vigtigste:
  1. noten siger hvad den skal, og ikke mere
  2. den kan slås fra (ét kald pr. tur)
  3. den lægges som runde-note, aldrig som vedvarende
  4. den er FAKTISK koblet på løkken — målt på AST, ikke på en grep

Hvorfor AST og ikke en grep (30/10-2026): den første version af test 4 læste
filen som tekst og ledte efter `suggest_tail_note`. Men kommentaren oven over
kaldet nævner både værktøjsnavnet og `tilfoej_runde` — så en grep ville være
GRØN selv hvis nogen slettede selve kaldet og lod kommentaren stå. En vagt der
kan overleve at det den vogter forsvinder, måler ingenting. AST ser kun rigtig
kode: kommentarer findes ikke i træet, og et kald er en `ast.Call`, ikke en
streng der tilfældigvis står i en fil.
"""

from __future__ import annotations

import ast
from pathlib import Path

from core.services.suggest_tail_note import suggest_tail_note

_VISIBLE_RUNS = Path(__file__).resolve().parents[1] / "core" / "services" / "visible_runs.py"


def test_noten_naevner_vaerktoejet_og_placeringen() -> None:
    """Uden navnet og placeringen er noten en henstilling uden indhold."""
    tekst = suggest_tail_note()
    assert "suggest_next_task" in tekst
    assert "FØR" in tekst
    # Kort nok til at den ikke bliver baggrundsstøj som prompt-linjen blev.
    assert len(tekst) < 600, len(tekst)


def test_noten_tillader_et_nej() -> None:
    """En gate der altid siger «bliv ved» må ikke kunne holde turen i live."""
    tekst = suggest_tail_note()
    assert "spring det over" in tekst


def test_allerede_lagt_giver_tom_streng() -> None:
    """Ét kald pr. tur: anden gang er der intet at lægge i halen."""
    assert suggest_tail_note(already_sent=True) == ""


def _runde_loekken(traee: ast.Module) -> ast.For:
    """Find den `for`-løkke der itererer agentic-runder.

    Løkken er ankeret: alt nedenfor måles INDE i den. Ligger kaldet udenfor,
    fyrer noten ikke pr. runde, og så er den død vægt.
    """
    for node in ast.walk(traee):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            if node.target.id == "_agentic_round":
                return node
    raise AssertionError(
        "agentic-rundeløkken findes ikke — er den omdøbt? Så holder denne vagt "
        "op med at måle noget, og det skal den sige højt i stedet for at sove.")


def _foraeldre(traee: ast.Module) -> dict[ast.AST, ast.AST]:
    """Barn → forælder, så vi kan gå OP fra et kald og finde dets betingelse."""
    par: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(traee):
        for barn in ast.iter_child_nodes(node):
            par[barn] = node
    return par


def _kald(loekke: ast.For, *navne: str) -> list[ast.Call]:
    """Alle kald indeni løkken hvis funktionsnavn står i `navne`.

    Navnet er enten bart (`_stn`) eller punktsepareret (`_tur_hale.tilfoej_runde`).
    """
    fund: list[ast.Call] = []
    for node in ast.walk(loekke):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in navne:
            fund.append(node)
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if f"{func.value.id}.{func.attr}" in navne:
                fund.append(node)
    return fund


def test_noten_er_koblet_paa_den_levende_loekke() -> None:
    """Struktur-vagt — målt på AST, fordi en grep ikke kan se forskel på kode og kommentar.

    Fire krav, alle bindende. Fjernes ét af dem, holder noten op med at virke
    uden at nogen test bliver rød — og det er præcis den tavse fejl Bjørn
    peger på når han siger at en mekanisme der aldrig kaldes er teater.
    """
    traee = ast.parse(_VISIBLE_RUNS.read_text(encoding="utf-8"))
    loekke = _runde_loekken(traee)

    # 1) Noten bygges INDE i løkken. Uden dette kald er der ingen note.
    stn_kald = _kald(loekke, "_stn")
    assert stn_kald, (
        "`_stn()` kaldes ikke inde i rundeløkken — noten bliver aldrig sendt")

    # 2) Resultatet lægges i halen som RUNDE-note. `tilfoej_vedvarende` ville
    #    gen-sende noten i hver runde (målt op til 40 gange i én tur) og er
    #    derfor en regression, ikke en variant.
    runde_kald = _kald(loekke, "_tur_hale.tilfoej_runde")
    assert any(
        isinstance(arg, ast.Name) and arg.id == "_suggest_note"
        for kald in runde_kald for arg in kald.args
    ), "`_suggest_note` lægges ikke i turens hale via `tilfoej_runde`"

    assert not _kald(traee, "_tur_hale.tilfoej_vedvarende") or not any(
        isinstance(arg, ast.Name) and arg.id == "_suggest_note"
        for kald in _kald(traee, "_tur_hale.tilfoej_vedvarende") for arg in kald.args
    ), "noten er faldet tilbage til «resten af turen» — den gen-sendes hver runde"

    # 3) Betingelsen skal udelukke den sidste runde: der fjernes værktøjerne
    #    fysisk, så noten kan ikke virke — den ville være støj i den dyreste runde.
    par = _foraeldre(traee)
    omsluttende = None
    cur: ast.AST | None = stn_kald[0]
    while cur is not None and cur in par:
        cur = par[cur]
        if isinstance(cur, ast.If):
            omsluttende = cur
            break
    assert omsluttende is not None, "`_stn()` står ikke under en betingelse"
    betingelse = ast.unparse(omsluttende.test)
    assert "_is_last_round" in betingelse, (
        f"noten fyrer også i den sidste runde, hvor værktøjerne er fjernet "
        f"(betingelse: {betingelse!r})")

    # 4) Den skal først fyre når der ER arbejde at afrunde — runde 0 er den
    #    første tur og har intet at opsummere endnu.
    assert "_agentic_round" in betingelse, (
        f"noten fyrer allerede i første runde (betingelse: {betingelse!r})")

