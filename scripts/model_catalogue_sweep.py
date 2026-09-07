#!/usr/bin/env python3
"""Ugentlig gennemgang af cheap lane: hvilke modeller lever, og hvad kan de?

Bjørn 7/9-2026: «cheap lane må aldrig dø». Den var ved at gøre det i stilhed —
syv udbydere kørte på 0,0 % success, over 7.000 spildte kald på syv døgn, og
intet opdagede det. Modeller pensioneres (NVIDIA droppede llama-3.1-8b den
26/8), gratis-niveauer forsvinder (cerebras), værter flytter (ollama-gatewayen
fra .45 til .26).

Kørslen PRØVER hver model — den kopierer ikke `/v1/models`. Listet er ikke
kaldbar: LLM7 lister 46 og 3 svarer; NVIDIA lister 81 og én er brugbar inden
for banens tidsloft.

  python scripts/model_catalogue_sweep.py                 # hele cheap lane
  python scripts/model_catalogue_sweep.py --provider xkiro
  python scripts/model_catalogue_sweep.py --toer          # prøv, skriv intet
  python scripts/model_catalogue_sweep.py --stille        # ingen push

Skriver direkte i provider-registret og sender ÉN push til ejeren hvis noget
ændrede sig. Ingen ændringer → ingen push.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Køres som script (og fra en systemd-timer), ikke som modul — så repo-roden
# skal på stien, ellers findes `core` ikke.
_ROD = Path(__file__).resolve().parents[1]
if str(_ROD) not in sys.path:
    sys.path.insert(0, str(_ROD))


def main() -> int:
    a = argparse.ArgumentParser(description="Prøv og opdatér cheap lane's modelkatalog")
    a.add_argument("--provider", action="append", default=None,
                   help="Kun denne udbyder (kan gentages)")
    a.add_argument("--toer", action="store_true",
                   help="Prøv modellerne, men skriv ikke i registret")
    a.add_argument("--stille", action="store_true", help="Send ingen push")
    a.add_argument("--json", action="store_true", help="Rå rapport i stedet for tekst")
    args = a.parse_args()

    from core.services.model_catalogue_sweep import sweep_alle

    skriv = (lambda **kw: False) if args.toer else None
    ud = sweep_alle(providers=args.provider, underret=not (args.stille or args.toer),
                    skriv=skriv)

    if args.json:
        print(json.dumps(ud, indent=2, ensure_ascii=False))
        return 0

    proevet = sum(int(r.get("proevet") or 0) for r in ud["rapporter"])
    print(f"Prøvede {proevet} modeller hos {len(ud['rapporter'])} udbydere.\n")
    for r in ud["rapporter"]:
        linjer = []
        for x in r.get("slaaet_fra") or []:
            linjer.append(f"    ✗ {x['model']} — {x['grund']}")
        for x in r.get("nye") or []:
            linjer.append(f"    + {x['model']} (score {x.get('score')})")
        for x in r.get("genoplivet") or []:
            linjer.append(f"    ↑ {x['model']} (score {x.get('score')})")
        if r.get("fejl"):
            linjer.append(f"    ! {r['fejl']}")
        if linjer:
            print(f"  {r['provider']}:")
            print("\n".join(linjer))
    if ud["besked"]:
        print(f"\nBesked til ejeren{' (sendt)' if ud['underrettet'] else ' (IKKE sendt)'}:")
        print(f"  {ud['besked']}")
    else:
        print("Ingen ændringer — ingen push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
