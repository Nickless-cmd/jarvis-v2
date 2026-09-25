#!/usr/bin/env python
"""Flyt seks moduler fra `shared/runtime/*.json` til `state_store`.

Engangs-flytning, skrevet 25/9-2026. Kør den ÉN gang på hver maskine der har
data, FØR tjenesterne genstartes på den nye kode — den gamle kode læser stadig
den gamle sti indtil genstarten, så flytningen kan ske uden nedetid.

HVORFOR FLYTNINGEN

`core/runtime/state_store.py` fandtes allerede med 49 brugere. De seks moduler
fik hver sin håndskrevne load/save mod `shared_dir()/runtime/`, og det kostede
mere end gentagelsen: `tests/conftest.py` har en **autouse**-fixture
(`_guard_prod_state_dir`) der peger `state_store._STATE_DIR` mod en tmp-mappe
for hver eneste test. `shared_dir()` har ingen sådan skærm. Målt samme dag
skrev `pytest tests/test_body_memory.py` i den RIGTIGE
`~/.jarvis-v2/shared/runtime/body_memory.json`. Det er samme mønster som
`in_flight_runs.json`-hændelsen 17/9, hvor testfikstur blev til rigtige
synlige kørsler — og skærmen blev skrevet netop for det.

Formatet er uændret: JSON-indholdet kopieres ordret, kun stien flytter.

SIKKERHED

- Skriver aldrig oven i en state_store-fil der allerede har indhold.
- Rører ikke den gamle fil. Den bliver liggende som en bagdør indtil den
  ryddes manuelt; ingen læser den efter genstarten.
- `--toerloeb` viser hvad der ville ske uden at skrive noget.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runtime import state_store  # noqa: E402
from core.runtime.workspace_paths import shared_dir  # noqa: E402

#: Modulerne der flyttede. Nøglen er både filnavnet og `state_store`-nøglen.
MODULER = (
    "body_memory",
    "forgetting_curve",
    "decision_ghosts",
    "memory_tattoos",
    "ghost_networks",
    "text_resonance",
)


def _gammel_sti(navn: str) -> Path:
    return shared_dir() / "runtime" / f"{navn}.json"


def _har_indhold(data: object) -> bool:
    """Tom liste/dict tæller ikke som indhold — så må den gerne overskrives."""
    if data is None:
        return False
    if isinstance(data, (list, dict, str)):
        return len(data) > 0
    return True


def flyt(navn: str, *, toerloeb: bool) -> tuple[str, str]:
    """Returnér (status, forklaring) for ét modul."""
    kilde = _gammel_sti(navn)
    if not kilde.exists():
        return "sprunget", "ingen gammel fil"

    try:
        gammel = json.loads(kilde.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # baeres videre som FEJL, ikke som «sprunget»
        return "fejl", f"kunne ikke læses: {exc}"

    if not _har_indhold(gammel):
        return "sprunget", "den gamle fil er tom"

    nuvaerende = state_store.load_json(navn, None)
    if _har_indhold(nuvaerende):
        return "sprunget", "state_store har allerede indhold — rører den ikke"

    stoerrelse = len(gammel) if isinstance(gammel, (list, dict)) else 1
    if toerloeb:
        return "ville flytte", f"{stoerrelse} poster fra {kilde}"

    state_store.save_json_strict(navn, gammel)
    kontrol = state_store.load_json(navn, None)
    if kontrol != gammel:
        return "fejl", "skrev, men læsningen bagefter gav noget andet"
    return "flyttet", f"{stoerrelse} poster"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--toerloeb", action="store_true",
                   help="vis hvad der ville ske; skriv intet")
    a = p.parse_args(argv)

    fejl = 0
    for navn in MODULER:
        status, hvorfor = flyt(navn, toerloeb=a.toerloeb)
        print(f"  {navn:<20} {status:<14} {hvorfor}")
        if status == "fejl":
            fejl += 1

    if fejl:
        print(f"\n{fejl} modul(er) fejlede — tjenesterne bør IKKE genstartes endnu.")
        return 1
    print("\nFærdig. Den gamle `shared/runtime/`-fil ligger urørt som bagdør.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
