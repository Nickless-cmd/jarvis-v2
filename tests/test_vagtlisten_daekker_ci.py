"""Vagten over CI-listen: en vagt-test der aldrig kører er ingen vagt.

## Hvorfor (målt 24/11-2026)

`scripts/verify_guard_tests.py` kræver at hver hook i `.pre-commit-config.yaml`
har en test der ser den SIGE NEJ. Den tjekker ikke om testen kører nogen
steder automatisk.

Målt 24/11-2026: **5 af 17** pre-commit-vagter havde en test der aldrig kørte
i CI. Den tydeligste var `verify_memory_status` — 25 tests, 0,50 s, statisk,
ingen DB, ingen netværk — der vogter MEMORY.md mod statuspåstande uden spor.
Den var grøn hele tiden, og ingen kørte den.

`tests/vagter.txt` kan ikke rådne i den ENE retning: peger en linje på en fil
der ikke findes, fejler pytest med exit 4. Denne fil dækker den ANDEN retning:
en vagt-test der findes, er grøn — og aldrig bliver listet.

## Hvorfor mappingen genbruges

Testen findes ved at spørge `verify_guard_tests` hvilke filer der nævner
scriptets modul. Et navnemønster (`scripts/verify_x.py` → `tests/test_verify_x.py`)
blev prøvet først og gav falske positiver: `verify_memory_status` har en
fuldt gyldig test der hedder `tests/test_memory_status_guard.py`. Navnet er
ikke invarianten — håndhævelsen er.
"""
from __future__ import annotations

from pathlib import Path

from scripts import verify_guard_tests as vg

#: Vagt-tests der med vilje ikke kører i CI, med grunden skrevet ned.
#: En undtagelse uden en grund er en tavs undtagelse — derfor testes det.
UNDTAGET: dict[str, str] = {
    "docs_drift_check": (
        "miljø-følsom: appen monterer 77 routes i et rent venv mod 612 i det "
        "fulde miljø, så generatoren falder tilbage til AST og testen ville "
        "være rød fra dag ét i CI (målt 20/9-2026). Dækket af pre-commit-hooket "
        "«Docs drift», hvor det fulde miljø findes."
    ),
}

#: Denne fil skal selv stå i listen — ellers kører vagten aldrig.
SELV = "tests/test_vagtlisten_daekker_ci.py"


def _listet() -> set[str]:
    """Stierne CI faktisk kører, som de står skrevet i `tests/vagter.txt`."""
    fil = vg.ROD / "tests" / "vagter.txt"
    return {
        linje.strip()
        for linje in fil.read_text(encoding="utf-8").splitlines()
        if linje.strip() and not linje.strip().startswith("#")
    }


def mangler_ci_daekning(
    vagter: list[str] | None = None,
    find_tester=None,
    listet: set[str] | None = None,
) -> list[tuple[str, list[str]]]:
    """(vagt, dens testfiler) for hver vagt hvis test ikke står i CI-listen.

    ``vagter``/``find_tester``/``listet`` kan injiceres, så testen kan vise at
    den afviser noget — ellers er den kun bevist på den tilstand den selv står i.
    """
    vagter = vg.vagter() if vagter is None else vagter
    find_tester = vg._tester_der_naevner if find_tester is None else find_tester
    listet = _listet() if listet is None else listet

    ud: list[tuple[str, list[str]]] = []
    for modul in vagter:
        if modul in UNDTAGET:
            continue
        filer = find_tester(modul)
        if not filer:
            # Ingen test overhovedet er verify_guard_tests' domæne, ikke denne.
            continue
        navne = [f"tests/{Path(p).name}" for p in filer]
        if not any(n in listet for n in navne):
            ud.append((modul, navne))
    return ud


def test_alle_vagt_tests_koerer_i_ci() -> None:
    huller = mangler_ci_daekning()
    assert not huller, (
        "disse pre-commit-vagter har en test der aldrig kører i CI:\n"
        + "\n".join(f"  {m} → {', '.join(f)}" for m, f in huller)
        + "\n\nFøj testen til tests/vagter.txt — eller skriv den i UNDTAGET med en grund."
    )


def test_vagten_selv_staar_i_listen() -> None:
    assert SELV in _listet(), (
        f"{SELV} står ikke i tests/vagter.txt — så kører denne vagt aldrig selv, "
        "og den gentager præcis den fejl den findes for at forhindre."
    )


def test_en_vagt_test_uden_for_listen_afvises() -> None:
    """Vagten skal kunne ses sige nej — ellers er den grøn af den forkerte grund."""
    huller = mangler_ci_daekning(
        vagter=["min_vagt"],
        find_tester=lambda _m: [Path("test_min_vagt.py")],
        listet=set(),
    )
    assert huller == [("min_vagt", ["tests/test_min_vagt.py"])], huller


def test_en_listet_vagt_test_er_nok() -> None:
    huller = mangler_ci_daekning(
        vagter=["min_vagt"],
        find_tester=lambda _m: [Path("test_min_vagt.py")],
        listet={"tests/test_min_vagt.py"},
    )
    assert huller == [], huller


def test_en_vagt_uden_nogen_test_er_ikke_dennes_domæne() -> None:
    """Uden test er der intet at liste — det fanger verify_guard_tests."""
    huller = mangler_ci_daekning(
        vagter=["min_vagt"], find_tester=lambda _m: [], listet=set()
    )
    assert huller == [], huller


def test_hver_undtagelse_har_en_grund() -> None:
    for modul, grund in UNDTAGET.items():
        assert isinstance(grund, str) and len(grund.strip()) >= 40, (
            f"undtagelsen for {modul} mangler en brugbar grund"
        )
