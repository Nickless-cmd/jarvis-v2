"""Årsagen skal nå TILSTANDSMASKINEN, ikke kun kaldet.

Målt 18/11-2026: atten ``cancelled``-rækker i ``visible_runs`` stod med
``error = NULL`` — på alle varigheder, fra 3,5 s til 198 s. Det var ikke en
varigheds-ting; det var en rækkefølge-ting.

Kæden er:

1. grenen kalder ``set_last_visible_run_outcome(error=X)`` → X skrives
2. ``_post_process`` i ``finally`` kalder SAMME funktion med
   ``error=_outcome_state.error``
3. har grenen kun sat X i kaldet — og ikke i tilstandsmaskinen — er
   ``_outcome_state.error`` ``None``
4. ``ON CONFLICT(run_id) DO UPDATE SET error = excluded.error`` **overskriver
   X med NULL**

Derfor er det ikke nok at kaldet bærer årsagen. Tilstandsmaskinen skal kende
den FØR outcome skrives, ellers sletter ``finally`` den igen.

Beviset i produktion: grene der bruger ``_outcome_state.set_error(...)``
(agentisk løkke, tool-exec) havde korrekt årsag i basen; grene der kun sendte
``error=`` i kaldet stod med NULL. Seks steder havde fejlformen.

Testen er strukturel med vilje. Den driver ikke den 5.500-linjer store
generator — den læser de faktiske ``Call``-noder, så et NYT kaldested med
samme fejlform bliver fanget, uanset hvilken gren det ligger i.
"""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
KILDE = REPO / "core" / "services" / "visible_runs.py"

#: Udtryk der LÆSER tilstandsmaskinen. De er pr. definition korrekte: kilden
#: til årsagen ER maskinen, så der er intet at sammenligne med.
_MASKINE_UDTRYK = ("_outcome_state",)


def _kaldenavn(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _keyword(node: ast.Call, navn: str):
    for kw in node.keywords:
        if kw.arg == navn:
            return kw.value
    return None


def _funktion_for(linjer: list[str], linje: int) -> int:
    """Indeks for den nærmeste omkransende ``def`` (1-baseret linje)."""
    for i in range(linje - 1, -1, -1):
        raekke = linjer[i]
        if raekke.lstrip().startswith(("def ", "async def ")):
            return i + 1
    return 1


def manglende_aarsager(tekst: str) -> list[str]:
    """Returnér de outcome-kald hvis årsag tilstandsmaskinen ikke kender.

    Et kald er i orden når et af disse gælder:

    * det sender ingen ``error`` (fx ``completed`` uden fejl), eller
    * ``error``-udtrykket læser tilstandsmaskinen selv, eller
    * det samme udtryk er sat på maskinen TIDLIGERE i samme funktion —
      via ``mark(..., error=<udtryk>)`` eller ``set_error(<udtryk>)``.
    """
    tree = ast.parse(tekst)
    linjer = tekst.splitlines()

    outcome: list[tuple[int, str]] = []
    maskine: list[tuple[int, str, int]] = []  # (linje, udtryk, funktion)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        navn = _kaldenavn(node)
        linje = node.lineno
        fn = _funktion_for(linjer, linje)

        if navn == "set_last_visible_run_outcome":
            v = _keyword(node, "error")
            if v is not None:
                outcome.append((linje, ast.unparse(v)))
        elif navn == "mark":
            v = _keyword(node, "error")
            if v is not None:
                maskine.append((linje, ast.unparse(v), fn))
        elif navn == "set_error":
            if node.args:
                maskine.append((linje, ast.unparse(node.args[0]), fn))

    mangler: list[str] = []
    for linje, udtryk in outcome:
        if any(m in udtryk for m in _MASKINE_UDTRYK):
            continue
        fn = _funktion_for(linjer, linje)
        kendt = any(
            m_udtryk == udtryk and m_fn == fn and m_linje < linje
            for m_linje, m_udtryk, m_fn in maskine
        )
        if not kendt:
            mangler.append(f"linje {linje}: error={udtryk} (funktion fra {fn})")
    return mangler


# ── den faktiske fil ─────────────────────────────────────────────────────
def test_hver_outcome_aarsag_er_kendt_af_tilstandsmaskinen():
    mangler = manglende_aarsager(KILDE.read_text(encoding="utf-8"))
    assert not mangler, (
        "outcome-kald bærer en årsag som _outcome_state ikke kender — "
        "_post_process i finally overskriver den med NULL:\n  "
        + "\n  ".join(mangler)
    )


# ── vagten skal faktisk kunne fejle ──────────────────────────────────────
def test_vagten_fejler_paa_den_gamle_kode():
    """Modkontrol: før rettelsen stod seks kaldesteder med fejlformen.

    Uden dette ben er en grøn vagt ikke bevis for noget — den kunne lige så
    godt matche nul kald.
    """
    try:
        gammel = subprocess.run(
            ["git", "show", "c558ca126:core/services/visible_runs.py"],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        pytest.skip("git utilgængelig")
    if gammel.returncode != 0:
        pytest.skip("den gamle revision er ikke i dette worktree")

    mangler = manglende_aarsager(gammel.stdout)
    assert len(mangler) == 6, (
        "ventede seks kaldesteder med fejlformen i den gamle kode, "
        f"fandt {len(mangler)}:\n  " + "\n  ".join(mangler)
    )


def test_vagten_ser_et_syntetisk_brud():
    """Vagten skal fange fejlformen, også når den skrives i en ny gren."""
    syntetisk = '''
async def _gren(run):
    _outcome_state.mark("cancelled")
    set_last_visible_run_outcome(run, status="cancelled", error=_cancel_reason)
'''
    mangler = manglende_aarsager(syntetisk)
    assert len(manglende_aarsager(syntetisk)) == 1
    assert "_cancel_reason" in mangler[0]


def test_vagten_accepterer_maskinen_som_kilde():
    """``error=_outcome_state.error`` ER den korrekte form og må ikke flagges."""
    syntetisk = '''
async def _gren(run):
    _outcome_state.set_error("user-cancelled-during-agentic-loop")
    _outcome_state.mark("cancelled", finalized=False)
    set_last_visible_run_outcome(
        run, status=_outcome_state.status, error=_outcome_state.error)
'''
    assert manglende_aarsager(syntetisk) == []
