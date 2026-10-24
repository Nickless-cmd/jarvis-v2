"""Force-handler-tabellen skal kunne IMPORTERES og hver handler være kaldbar.

Fejlen der gav denne test (målt 23/10-2026): `core/tools/force_handlers.py`
importerede `_exec_operator_bash` fra `core/tools/operator_bash_session.py`,
hvor funktionen aldrig har boet. Importen fejlede ved **modul-load**, så hele
force-handler-tabellen var ubrugelig for `operator_bash` — ikke kun den
godkendte vej. Rettet i `8e55045f6`.

Hvorfor de eksisterende tests ikke fangede det
---------------------------------------------
`tests/test_force_handlers.py` og `tests/test_approval_har_force_handler.py`
var **14/14 grønne** mens værktøjet var totalt brudt. De importerer
`_FORCE_HANDLERS` inde fra en allerede indlæst `simple_tools` — altså gennem
en proces hvor importen allerede var faldet til ro (eller hvor testmiljøet
patch'ede sig udenom). Ingen af dem:

  * loadede `force_handlers` i en FRISK proces (den eneste tilstand hvor en
    brudt modul-load faktisk viser sig), eller
  * krævede at handlerne er ``callable()`` — kun at nøglen findes i en dict.
    En dict kan pege på `None`, en streng eller en halvt initialiseret
    funktion og stadig se rigtig ud i `assert "x" in _FORCE_HANDLERS`.

Det er samme klasse som «en grøn vagt der ikke kan se bruddet»: testen målte
tilstedeværelse i en tabel, ikke om tabellen kunne bruges.

Testen her måler de to ting der faktisk fejlede. Den er verificeret mod den
gamle importlinje (se `_GAMMEL_IMPORT` nedenfor) — den fælder fejlen.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_ROD = Path(__file__).resolve().parents[1]

#: Den importlinje der var brudt før 8e55045f6. Bruges af
#: `test_friskg_proces_import_fejler_paa_den_gamle_linje` til at bevise at
#: testen ikke bare er grøn fordi alt er grønt.
_GAMMEL_IMPORT = (
    "from core.tools.operator_bash_session import _exec_operator_bash"
)


def _frisk_proces(kode: str) -> subprocess.CompletedProcess[str]:
    """Kør Python-kode i en NY proces med repoet på stien.

    Frisk proces er ikke en detalje: en brudt import i et allerede indlæst
    modul er usynlig i den kørende proces, fordi Python cacher modulet i
    `sys.modules`. Kun en ny proces rammer import-stien igen.
    """
    return subprocess.run(
        [sys.executable, "-c", kode],
        cwd=str(_ROD),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_frisk_proces_kan_importere_force_handlers():
    """(a) Importen må ikke kaste i en ren proces.

    Det er præcis her `_exec_operator_bash`-fejlen levede: ikke ved kald, men
    ved modul-load. En `ImportError` her gør HELE tabellen ubrugelig.
    """
    r = _frisk_proces(
        "import core.tools.force_handlers as fh; "
        "print(len(fh._FORCE_HANDLERS))"
    )
    assert r.returncode == 0, (
        "core.tools.force_handlers kan ikke importeres i en frisk proces — "
        "så er force-handler-tabellen ubrugelig, og et godkendt kald svarer "
        "med en ImportError i stedet for at køre.\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr[-2000:]}"
    )
    antal = int(r.stdout.strip().splitlines()[-1])
    assert antal >= 10, (
        f"kun {antal} force-handlere efter import — tabellen ser tom ud. "
        "En import der 'lykkes' med en tom tabel er også et brud."
    )


def test_hver_force_handler_er_kaldbar():
    """(b) Hver nøgle skal pege på noget der kan kaldes — ikke bare findes.

    `assert "x" in _FORCE_HANDLERS` består selv hvis værdien er `None`. Det
    var den blinde plet: tabellen SÅ rigtig ud. `callable()` er kravet der
    faktisk betyder «denne handler kan udføre et kald».
    """
    from core.tools.force_handlers import _FORCE_HANDLERS

    ikke_kaldbare = sorted(
        navn for navn, handler in _FORCE_HANDLERS.items() if not callable(handler)
    )
    assert not ikke_kaldbare, (
        "Disse force-handlere er ikke kaldbare, så et godkendt kald vil fejle "
        f"eller løbe i ring: {ikke_kaldbare}"
    )


def test_operator_bash_har_en_kaldbar_force_handler():
    """Den konkrete regression: `operator_bash` var værktøjet der døde.

    Testen er navngivet efter værktøjet og ikke efter modulet, så den stadig
    fanger fejlen hvis nogen flytter handleren til et tredje modul.
    """
    from core.tools.force_handlers import _FORCE_HANDLERS

    assert "operator_bash" in _FORCE_HANDLERS, (
        "operator_bash mangler i _FORCE_HANDLERS — et godkendt kald ville "
        "ramme sin egen approval-gren igen"
    )
    assert callable(_FORCE_HANDLERS["operator_bash"]), (
        "operator_bash's force-handler er ikke kaldbar"
    )


@pytest.mark.parametrize("modul", [
    "core.tools.force_handlers",
    "core.tools.simple_tools",
])
def test_importkæden_holder_i_frisk_proces(modul: str):
    """Også `simple_tools` skal kunne importeres rent.

    `simple_tools` importerer `_FORCE_HANDLERS` fra `force_handlers`. Er den
    ene brudt, er den anden det også — men fejlen viser sig først i en proces
    der ikke allerede har modulerne i `sys.modules`.
    """
    r = _frisk_proces(f"import {modul}")
    assert r.returncode == 0, (
        f"{modul} kan ikke importeres i en frisk proces.\n"
        f"stderr: {r.stderr[-2000:]}"
    )


def test_frisk_proces_import_fejler_paa_den_gamle_linje():
    """Bevis: testen kan FEJLE. Uden dette er den bare endnu en grøn vagt.

    Vi kører den gamle, brudte importlinje i en frisk proces og kræver at den
    faktisk kaster. Gør den ikke det, er forudsætningen for hele testfilen
    væk — og så skal det siges højt frem for at lade de andre tests være
    grønne på et falsk grundlag.
    """
    r = _frisk_proces(_GAMMEL_IMPORT)
    assert r.returncode != 0, (
        "Den gamle importlinje importerer nu UDEN fejl. Så er denne testfils "
        "præmis ændret — funktionen er blevet flyttet til "
        "operator_bash_session, og testen herover måler ikke længere det den "
        "tror. Opdatér _GAMMEL_IMPORT eller fjern testen.\n"
        f"stdout: {r.stdout}"
    )
    assert "ImportError" in r.stderr or "cannot import name" in r.stderr, (
        "den gamle linje fejlede, men ikke med en ImportError — "
        f"undersøg hvorfor: {r.stderr[-800:]}"
    )
