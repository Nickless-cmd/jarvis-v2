#!/usr/bin/env python3
"""Flyt de gamle fælles filer ind i ejerens egen mappe.

Bjørn 4/10-2026: «filer skal være per bruger». Indtil da lå alt i én flad
`~/.jarvis-v2/files/`, og `GET /files/{navn}` slog op direkte i den — enhver
autentificeret husstandsbruger kunne hente alle med sit eget token.

## Hvorfor ALLE går til ejeren

Målt på CT105 før flytningen: 443 chat-beskeder nævner `/files/`, og de bærer
præcis TO distinkte bruger-id'er — ejerens `1246415163603816499` (362) og tom
streng (81). Ingen anden husstandsbruger har nogensinde været i en besked om
en udgiven fil. Tilskrivningen er altså målt, ikke antaget, og ingen mister
adgang til noget der var deres.

Bliver det en dag forkert — en fil der skulle have været en andens — er den
rettelse en `mv`, og den er langt billigere end at have ladet mappen stå åben.

## Hvad der IKKE flyttes

De syv undermapper (`phase5`, `phase6`, `phase7`, `phase7b`, `icons`,
`latency`, `tts-samples`) er eksperiment-output skrevet af `scripts/phase*`.
Ruten kunne aldrig nå dem: `GET /files/{filnavn}` renser til et blot navn, og
listningen filtrerer på `is_file()`. De bliver liggende hvor deres skrivere
forventer dem.

Tørløb som standard. `--udfoer` flytter.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runtime.workspace_paths import _jarvis_home  # noqa: E402


def _hash(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for stykke in iter(lambda: f.read(1 << 20), b""):
            h.update(stykke)
    return h.hexdigest()


def find_ejer() -> str:
    """Ejerens workspace-navn. Tom streng når det ikke kan afgøres."""
    try:
        from core.identity.owner_resolver import owner_user_id
        from core.runtime.workspace_paths import _user_id_to_workspace_name
        uid = str(owner_user_id() or "").strip()
        return _user_id_to_workspace_name(uid) if uid else ""
    except Exception as exc:  # noqa: BLE001
        print(f"  kunne ikke oploese ejeren: {exc}")
        return ""


def migrer(*, udfoer: bool, ejer_ws: str = "") -> int:
    hjem = _jarvis_home()
    gammel = hjem / "files"
    if not gammel.is_dir():
        print(f"ingen filmappe at migrere: {gammel}")
        return 0

    ws = ejer_ws or find_ejer()
    if not ws:
        print("FEJL: ejerens workspace kunne ikke afgoeres — intet flyttet.")
        return 1
    ny = gammel / "u" / ws

    kandidater = sorted(p for p in gammel.iterdir() if p.is_file())
    mapper = sorted(p.name for p in gammel.iterdir() if p.is_dir())
    print(f"hjem      : {hjem}")
    print(f"ejer      : {ws}  →  {ny}")
    print(f"filer     : {len(kandidater)}")
    print(f"mapper    : {len(mapper)} (roeres IKKE: {', '.join(mapper) or 'ingen'})")
    if not kandidater:
        print("intet at flytte.")
        return 0
    if not udfoer:
        print("\nTOERLOEB — intet er flyttet. Koer med --udfoer.")
        for p in kandidater[:5]:
            print(f"  ville flytte {p.name}")
        if len(kandidater) > 5:
            print(f"  … og {len(kandidater) - 5} mere")
        return 0

    ny.mkdir(parents=True, exist_ok=True)
    flyttet = sprunget = 0
    for p in kandidater:
        maal = ny / p.name
        if maal.exists():
            # Idempotent: er den allerede flyttet og identisk, er kilden en
            # rest fra et afbrudt loeb. Afviger de, roerer vi INTET — en
            # overskrivning her er datatab, ikke en migrering.
            if _hash(p) == _hash(maal):
                p.unlink()
                sprunget += 1
                continue
            print(f"  ADVARSEL: {p.name} findes begge steder og AFVIGER — sprunget over")
            sprunget += 1
            continue
        # Hash FOER og EFTER. En migrering der taber indhold uden at sige det
        # er vaerre end ingen migrering.
        foer = _hash(p)
        shutil.move(str(p), str(maal))
        if _hash(maal) != foer:
            print(f"  FEJL: {p.name} aendrede indhold under flytningen")
            return 1
        flyttet += 1
    print(f"\nflyttet: {flyttet}   sprunget: {sprunget}")
    tilbage = [p.name for p in gammel.iterdir() if p.is_file()]
    print(f"tilbage i den faelles mappe: {len(tilbage)}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--udfoer", action="store_true", help="flyt rigtigt (ellers toerloeb)")
    ap.add_argument("--ejer-workspace", default="", help="override af ejerens workspace-navn")
    a = ap.parse_args()
    raise SystemExit(migrer(udfoer=a.udfoer, ejer_ws=a.ejer_workspace))
