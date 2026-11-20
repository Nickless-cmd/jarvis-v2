#!/usr/bin/env python3
"""Søg i en bundtet app (asar) og få MODULSTIEN med, ikke bare et byte-offset.

## Hvorfor den findes

MÅLT 20/11-2026: al reverse-engineering af GPT-appen blev gjort med
engangskommandoer over broen — `grep -abo` på `/opt/codex-desktop/resources/
app.asar` — og en node-parser skrevet ind i `/tmp/asar-x.js`. Intet af det
overlevede: `/tmp` bliver ryddet, broen er lukket fra containeren, og
`~/rea/all` fra 18/11 findes ikke længere. Næste session startede derfor
forfra hver gang. Det er den adfærd «bliv bedre til app reverse engineering»
peger på — ikke manglende evne, men manglende varighed.

`grep -abo` giver et byte-offset. Et offset er ikke et svar: for at vide OM
noget er værd at læse, skal offsettet mappes tilbage til den modulsti det kom
fra (`dil_text/src/rendering/DILStreamingText`). Det kræver asar-headeren, og
det er præcis det dette værktøj gør — i ren Python, uden node og uden `npx`.

## Formatet — ikke gættet

Layoutet er læst ud af den node-parser der faktisk parrede den ægte 622 MB
fil på Bjørns maskine (artefakt `tool-result-f649667e44104b9e86efd2fbdf395d98`):

    [0:4]   uint32LE = 4
    [4:8]   uint32LE = header-størrelse (blokken der starter ved 8)
    [8:12]  uint32LE (4)
    [12:16] uint32LE = længden af JSON-headeren
    [16:16+n] JSON-header
    data starter ved 8 + header-størrelse

Hver fil i headeren bærer `{size, offset}`, hvor `offset` er relativ til
data-start. Derfor: `modul_offset = absolut_offset - data_start`.

## Brug

    python scripts/bundt_soeg.py --fil app.asar --soeg DILStreamingText
    python scripts/bundt_soeg.py --fil app.asar --liste | head -40
    python scripts/bundt_soeg.py --fil app.asar --soeg snappyStreaming --kontekst 120

Kan filen ikke læses som asar, falder den tilbage til rå søgning: offsettet
vises stadig, men uden modulsti — og det siges højt i outputtet, så et
manglende svar ikke ligner et tomt svar.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

#: Hvor mange tegn der vises på hver side af et træf som standard.
STANDARD_KONTEKST = 80


def laes_header(sti: Path) -> tuple[dict, int]:
    """Returnér (header-JSON, data-start). Rejser ValueError hvis filen ikke er en asar."""
    with sti.open("rb") as f:
        forside = f.read(16)
        if len(forside) < 16:
            raise ValueError("filen er kortere end en asar-header (16 byte)")
        header_stoerrelse = struct.unpack("<I", forside[4:8])[0]
        if header_stoerrelse == 0 or header_stoerrelse > 64 * 1024 * 1024:
            raise ValueError(f"urimelig header-størrelse: {header_stoerrelse}")
        # MÅLT 20/11-2026: header-blokken starter ved absolut 8 — IKKE ved 16.
        # Læser man 16 byte først og fortsætter, læses de fire første byte af
        # JSON'en som længdefelt, og HVER ægte asar ser ugyldig ud. Fejlen var
        # tavs, fordi fallbacken søger råt videre uden modulstier.
        f.seek(8)
        blok = f.read(header_stoerrelse)
        if len(blok) < header_stoerrelse:
            raise ValueError("filen slutter midt i headeren")
    tekst_laengde = struct.unpack("<I", blok[4:8])[0]
    if tekst_laengde > header_stoerrelse:
        raise ValueError("header-længden peger ud over header-blokken")
    raa = blok[8:8 + tekst_laengde]
    try:
        header = json.loads(raa.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # Headeren er ikke JSON: filen er ikke en asar, og vi skal ikke gætte
        # videre på et halvt format — kalderen falder tilbage til rå søgning.
        raise ValueError(f"headeren er ikke gyldig JSON: {exc}") from exc
    if not isinstance(header, dict):
        raise ValueError("headeren er ikke et objekt")
    return header, 8 + header_stoerrelse


def filkort(header: dict) -> dict[str, tuple[int, int]]:
    """Returnér {modulsti: (offset, størrelse)} for alle filer i headeren."""
    ud: dict[str, tuple[int, int]] = {}

    def gaa(node: dict, praefiks: str) -> None:
        for navn, post in (node.get("files") or {}).items():
            sti = f"{praefiks}/{navn}" if praefiks else str(navn)
            if not isinstance(post, dict):
                continue
            if "files" in post:
                gaa(post, sti)
                continue
            if "link" in post:
                continue
            try:
                offset = int(post.get("offset") or 0)
                stoerrelse = int(post.get("size") or 0)
            except (TypeError, ValueError):
                # En post uden tal kan ikke slås op; den springes over frem for
                # at få offset 0, som ville pege på den første fil i bundlen.
                continue
            ud[sti] = (offset, stoerrelse)

    gaa(header, "")
    return ud


def modul_for(offset_i_data: int, kort: dict[str, tuple[int, int]]) -> str:
    """Find modulstien der dækker et offset relativt til data-start."""
    for sti, (offset, stoerrelse) in kort.items():
        if offset <= offset_i_data < offset + max(stoerrelse, 1):
            return sti
    return ""


def soeg(fil: Path, moenster: bytes, *, kontekst: int, maks: int) -> list[dict[str, object]]:
    """Søg efter `moenster` og berig hvert træf med modulsti."""
    raa = fil.read_bytes()
    try:
        header, data_start = laes_header(fil)
        kort = filkort(header)
    except (ValueError, OSError) as exc:
        # Ikke en asar: vi søger stadig, men siger at modulstien mangler, så et
        # tomt modulfelt ikke læses som «filen hører ikke til noget modul».
        print(f"ikke en asar ({exc}) — søger råt, uden modulstier", file=sys.stderr)
        kort, data_start = {}, 0
    traef: list[dict[str, object]] = []
    start = 0
    while len(traef) < maks:
        fundet = raa.find(moenster, start)
        if fundet < 0:
            break
        start = fundet + 1
        modul_offset = fundet - data_start
        traef.append({
            "absolut": fundet,
            "modul_offset": modul_offset,
            "modul": modul_for(modul_offset, kort) if kort and modul_offset >= 0 else "",
            "foer": raa[max(0, fundet - kontekst):fundet].decode("utf-8", "replace"),
            "efter": raa[fundet + len(moenster):fundet + len(moenster) + kontekst].decode("utf-8", "replace"),
        })
    return traef


def _hoved(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Søg i en asar og få modulstien med.")
    p.add_argument("--fil", required=True, type=Path)
    p.add_argument("--soeg", default="", help="tekst eller byte-mønster")
    p.add_argument("--liste", action="store_true", help="vis moduler i stedet for at søge")
    p.add_argument("--kontekst", type=int, default=STANDARD_KONTEKST)
    p.add_argument("--maks", type=int, default=20)
    a = p.parse_args(argv)

    if not a.fil.is_file():
        print(f"findes ikke: {a.fil}", file=sys.stderr)
        return 2

    if a.liste:
        try:
            header, data_start = laes_header(a.fil)
        except (ValueError, OSError) as exc:
            print(f"ikke en asar: {exc}", file=sys.stderr)
            return 1
        kort = filkort(header)
        print(f"data starter ved {data_start} · {len(kort)} filer")
        for sti in sorted(kort):
            offset, stoerrelse = kort[sti]
            print(f"{offset:>12}  {stoerrelse:>10}  {sti}")
        return 0

    if not a.soeg:
        print("angiv --soeg eller --liste", file=sys.stderr)
        return 2

    traef = soeg(a.fil, a.soeg.encode("utf-8"), kontekst=a.kontekst, maks=a.maks)
    if not traef:
        print(f"0 træf på {a.soeg!r}")
        return 1
    print(f"{len(traef)} træf på {a.soeg!r}")
    for t in traef:
        modul = t["modul"] or "(ukendt modul)"
        print(f"\n--- {modul}  @data+{t['modul_offset']} (abs {t['absolut']})")
        print(f"    …{t['foer']}⟦{a.soeg}⟧{t['efter']}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(_hoved())
