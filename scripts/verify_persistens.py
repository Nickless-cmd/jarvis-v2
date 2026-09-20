#!/usr/bin/env python
"""Vagt: et nyt varigt format skal skrives ind i registret med en dato.

## Hvorfor (20/9-2026)

DeepSeek-harness indførte `docs/persistence-changes/`: hver ændring i et
persisteret format får en DATERET record med en tvungen klassifikation —
tilføj et valgfrit felt er `same-version`; gør et felt påkrævet, omdøb eller
fjern er `version-bump`. Uden en record går ændringen ikke igennem.

Samme dag jeg læste det, havde jeg selv indført et nyt varigt format —
`device_presence.json`, med en håndskrevet «ignorér ukendte felter»-regel —
uden at registrere det nogen steder. Der var intet sted at registrere det.

Målt: 47 varige nøgler under `state_store`, spredt over hele træet, uden en
samlet fortegnelse. Ingen kunne svare på «hvad skriver vi egentlig til
disken, og hvem ejer det» uden at grepe.

## Hvad den kan — og ikke kan

Den kan se at en NØGLE opstår eller forsvinder, og kræve at den står i
registret med en ejer, en beskrivelse og en dato.

Den kan **ikke** se at et FELT inde i en nøgle skifter form. Deres mekanisme
kan, fordi TypeScript giver dem en typegraf at hashe; Python-dicts giver
ingen. Det er en ægte begrænsning og ikke noget der bliver sandt af at blive
fortiet: registret fanger nye formater, ikke ændrede felter.
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
REGISTER = ROD / "docs/persistens/register.json"
OMRAADER = ("core", "apps/api", "scripts")
SKRIVERE = ("save_json", "save_json_strict")
LAESERE = ("load_json",)


def _strengkonstanter(traeet: ast.Module) -> dict[str, str]:
    """Modul-globale strenge, så `save_json(_NAVN, …)` kan slås op."""
    ud = {}
    for n in traeet.body:
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)):
            ud[n.targets[0].id] = n.value.value
    return ud


def noegler_i_traeet() -> dict[str, set[str]]:
    """nøgle -> filer der skriver eller læser den."""
    fundet: dict[str, set[str]] = defaultdict(set)
    for omraade in OMRAADER:
        for p in (ROD / omraade).rglob("*.py"):
            if "__pycache__" in str(p):
                continue
            try:
                traeet = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue  # ikke-parsende filer fanges af compileall
            konst = _strengkonstanter(traeet)
            for n in ast.walk(traeet):
                if not isinstance(n, ast.Call) or not n.args:
                    continue
                navn = getattr(n.func, "id", "") or getattr(n.func, "attr", "")
                if navn not in SKRIVERE + LAESERE:
                    continue
                a = n.args[0]
                noegle = ""
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    noegle = a.value
                elif isinstance(a, ast.Name):
                    noegle = konst.get(a.id, "")
                if noegle:
                    fundet[noegle].add(str(p.relative_to(ROD)))
    return dict(fundet)


#: Beskrivelser der ikke siger noget. Tolereres for de 47 formater der var
#: der da registret blev oprettet; forbudt for nye.
TOM_BESKRIVELSE = "UDFYLD"


def _modulbeskrivelse(rel_sti: str) -> str:
    """Første linje af ejerens modul-docstring, eller en UDFYLD-plads."""
    try:
        traeet = ast.parse((ROD / rel_sti).read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        # Ejeren kan ikke læses; så bliver beskrivelsen et efterslæb frem for
        # et gæt. Årsagen står i selve teksten der havner i registret.
        return f"{TOM_BESKRIVELSE}: kunne ikke læse {rel_sti}"
    doc = (ast.get_docstring(traeet) or "").strip().splitlines()
    return doc[0].strip() if doc else f"{TOM_BESKRIVELSE}: {rel_sti} har ingen docstring"


def _register() -> dict[str, dict]:
    try:
        return json.loads(REGISTER.read_text(encoding="utf-8"))["formater"]
    except (OSError, json.JSONDecodeError, KeyError):
        return {}   # intet register endnu = alt er nyt


def afvigelser() -> tuple[list[str], list[str]]:
    """(uregistrerede nøgler, registrerede nøgler ingen rører længere)."""
    i_koden = noegler_i_traeet()
    i_register = _register()
    nye = sorted(k for k in i_koden if k not in i_register)
    forsvundne = sorted(k for k in i_register if k not in i_koden)
    return nye, forsvundne


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--skriv-register", action="store_true",
                   help="fastfrys de nuværende nøgler som register")
    a = p.parse_args(argv)

    if a.skriv_register:
        i_koden = noegler_i_traeet()
        gammelt = _register()
        i_dag = __import__("time").strftime("%Y-%m-%d")
        formater = {
            k: gammelt.get(k) or {
                "ejer": sorted(filer)[0],
                # Ejerens egen modul-docstring er ægte information og et
                # bedre udgangspunkt end en UDFYLD-plads, som ingen retter.
                "beskrivelse": _modulbeskrivelse(sorted(filer)[0]),
                "registreret": i_dag,
            }
            for k, filer in sorted(i_koden.items())
        }
        REGISTER.parent.mkdir(parents=True, exist_ok=True)
        REGISTER.write_text(json.dumps(
            {"_forklaring": "Varige formater under state_store. Et nyt format "
                            "skal stå her med ejer, beskrivelse og dato. "
                            "Registret fanger nye NØGLER, ikke ændrede felter.",
             "formater": formater}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"verify-persistens: register skrevet — {len(formater)} formater.")
        return 0

    nye, forsvundne = afvigelser()
    tomme = sorted(k for k, v in _register().items()
                   if str(v.get("beskrivelse") or "").startswith(TOM_BESKRIVELSE))
    if not nye and not forsvundne:
        if tomme:
            print(f"verify-persistens: {len(_register())} formater registreret "
                  f"— {len(tomme)} mangler stadig en rigtig beskrivelse "
                  f"(efterslæb, blokerer ikke).")
            return 0
        print(f"verify-persistens: {len(_register())} formater, alle registreret.")
        return 0
    print("\n❌ VERIFY-PERSISTENS — et varigt format uden en registrering\n")
    for k in nye:
        print(f"  NY: «{k}» skrives til disken, men står ikke i registret")
    for k in forsvundne:
        print(f"  VÆK: «{k}» står i registret, men ingen rører den længere "
              f"— er der data på disken der skal ryddes?")
    print(f"\nSkriv den ind i {REGISTER.relative_to(ROD)} med ejer, beskrivelse "
          f"og dato (`--skriv-register` laver skabelonen), og overvej om "
          f"ændringen fortjener en note under docs/notes/.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
