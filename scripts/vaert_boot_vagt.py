#!/usr/bin/env python3
"""Boot-vagt paa pve i9: klassificér hver boot som REN eller CUT.

    python scripts/vaert_boot_vagt.py                 # læs via ssh, rapportér nye
    python scripts/vaert_boot_vagt.py --alle           # vis hele boot-historikken
    python scripts/vaert_boot_vagt.py --stdin < fil    # test uden ssh

HVORFOR DEN FINDES
------------------
`beacon_vagt.py` opdager at vaerten ER genstartet (uptime falder). Den siger
ikke HVORDAN. Forskellen er hele pointen: en planlagt genstart efterlader
`systemd-shutdown` og `Journal stopped`; et haardt cut efterlader ingenting —
journalen stopper midt i en normal driftslinje.

Maalt 17/11-2026 paa 16/11-bootene: boot -5 sluttede med `systemd-shutdown`
(REN), mens -6, -4, -3, -2 og -1 alle stoppede midt i drift med nul
shutdown-markoerer (CUT). Uden den skelnen kan man ikke afgoere om et fix
virkede — kun at maskinen "genstartede".

DEN KOERENDE BOOT KLASSIFICERES IKKE
------------------------------------
`journalctl --list-boots` nummererer den nuværende boot som 0, og den har pr.
definition ingen nedlukning endnu. Klassificerede man den alligevel, svarede
den CUT hver gang — en falsk ADVARSEL ved hver eneste koersel, som ville goere
scriptet ubrugeligt netop til det det skal: skelne nye cut fra ny stoej.
Boot 0 vises derfor som "koerer" og indgaar ikke i cut-taellingen.

MAALEBLINDHED — LAES DENNE FOER DU KONKLUDERER
----------------------------------------------
`sensors` ser kun fan1, fan4, fan5, fan7. To blaesere sidder paa fan-hub-
boardet og rapporterer IKKE dertil. Beacon-loggen er bedre: den skriver
fan1..fan7 hver 5. sekund, saa hub-blaeserne (fan2, fan3, fan6) ER maalt der.
Brug beacon-loggen, ikke `sensors`, naar koelingen skal vurderes.

fan5 = 5600-5700 RPM er TILSIGTET (vandpumpe, pwm5=255). Ikke en fejl.
fan4 og fan7 staar paa 0 og har gjort det hele perioden — ingen blaser monteret.

Brug:
    ssh root@10.0.0.36 'journalctl --list-boots --no-pager' | python scripts/vaert_boot_vagt.py --stdin
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

STANDARD_STATE = Path.home() / ".jarvis-v2" / "state" / "vaert_boot_vagt.json"
STANDARD_HOST = "root@10.0.0.36"

# Markoerer der KUN kan optraede i en planlagt nedlukning.
REN_MARKOERER = (
    "Reached target Shutdown",
    "Reached target Power-Off",
    "Reached target System Reboot",
    "systemd-shutdown[1]",
    "Journal stopped",
)

_BOOT_LINJE = re.compile(
    r"^\s*(-?\d+)\s+([0-9a-f]{32})\s+(\S+ \S+ \S+ \S+)\s+(\S+ \S+ \S+ \S+)\s*$"
)


@dataclass
class Boot:
    idx: int
    boot_id: str
    start: str
    slut: str
    ren: bool | None = None  # None = ikke maalt endnu
    koerer: bool = False  # idx 0 = den nuværende boot, har ingen nedlukning

    @property
    def udfald(self) -> str:
        if self.koerer:
            return "koerer"
        if self.ren is None:
            return "umaalt"
        return "REN" if self.ren else "CUT"

    @property
    def varighed_s(self) -> float | None:
        """Sekunder mellem start og slut. Korte boots er i sig selv et signal."""
        try:
            a = datetime.strptime(self.start, "%a %Y-%m-%d %H:%M:%S %Z")
            b = datetime.strptime(self.slut, "%a %Y-%m-%d %H:%M:%S %Z")
        except ValueError:
            # En boot-linje kan mangle tidszone eller vaere afkortet, og saa kan
            # varigheden ikke beregnes. Det koster kun DETTE ene signal: REN/CUT
            # afgoeres af journal-halen, ikke af laengden. Vi afviser at gaette
            # en varighed, for et gaet ville se ud som en maaling.
            return None
        return (b - a).total_seconds()


def parse_boot_liste(tekst: str) -> list[Boot]:
    """`journalctl --list-boots` → Boot-objekter. Header og tomme linjer springes over.

    Idx 0 markeres som koerende: det er formatets semantik, ikke et gaet — den
    nuværende boot har pr. definition ingen nedlukning at klassificere.
    """
    boots: list[Boot] = []
    for linje in tekst.splitlines():
        m = _BOOT_LINJE.match(linje)
        if not m:
            continue
        idx = int(m.group(1))
        boots.append(
            Boot(
                idx=idx,
                boot_id=m.group(2),
                start=m.group(3),
                slut=m.group(4),
                koerer=idx == 0,
            )
        )
    return boots


def klassificer(haler: str) -> bool:
    """Journal-halen for ÉN boot → True hvis REN nedlukning, False hvis CUT.

    Et cut er ikke "en tom hale" — det er en hale der slutter midt i normal
    drift. Derfor kraever REN en positiv markoer; fravaer af markoer er CUT.
    """
    return any(markoer in haler for markoer in REN_MARKOERER)


def _ssh(host: str, kommando: str, timeout: int = 60) -> str:
    res = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, kommando],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if res.returncode != 0:
        raise RuntimeError(f"ssh fejlede ({res.returncode}): {res.stderr.strip()[:300]}")
    return res.stdout


def maal(host: str, antal: int = 8) -> list[Boot]:
    """Hent boot-liste og klassificér de nyeste `antal` boots.

    Den koerende boot springes over: dens journal er ikke afsluttet, saa der
    findes intet udfald at maale.
    """
    boots = parse_boot_liste(_ssh(host, "journalctl --list-boots --no-pager"))
    for b in boots[-antal:]:
        if b.koerer:
            continue
        hale = _ssh(
            host,
            f"journalctl -b {b.idx} --no-pager -o short-iso 2>/dev/null | tail -8",
        )
        b.ren = klassificer(hale)
    return boots


def nye_siden(boots: list[Boot], kendte: set[str]) -> list[Boot]:
    """Boots der ikke er rapporteret foer. Boot-id er noeglen — idx flytter sig."""
    return [b for b in boots if b.boot_id not in kendte]


def indlaes_state(sti: Path) -> dict:
    try:
        return json.loads(sti.read_text())
    except (OSError, json.JSONDecodeError):
        # Foerste koersel har ingen state-fil, og en afbrudt skrivning kan
        # efterlade ugyldig JSON. Begge betyder "intet er rapporteret endnu",
        # ikke at maalingen er ubrugelig — saa vi starter tomt. At kaste her
        # ville goere en manglende fil til en fejl i selve maalingen.
        return {"kendte": [], "sidste_koersel": None}


def gem_state(sti: Path, kendte: list[str]) -> None:
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_text(
        json.dumps(
            {"kendte": kendte[-200:], "sidste_koersel": datetime.now().isoformat(timespec="seconds")},
            indent=2,
        )
    )


def rapport(boots: list[Boot], nye: list[Boot]) -> str:
    linjer: list[str] = []
    cut = [b for b in boots if b.ren is False]
    rene = [b for b in boots if b.ren is True]
    linjer.append(f"Boots maalt: {len(boots)} · cut: {len(cut)} · rene: {len(rene)}")
    for b in boots:
        var = b.varighed_s
        varighed = f"{var / 60:.0f} min" if var is not None and var >= 60 else (
            f"{var:.0f} s" if var is not None else "?"
        )
        mark = "  ← NY" if b in nye else ""
        linjer.append(f"  [{b.idx:>3}] {b.start} → {b.slut}  {varighed:>8}  {b.udfald}{mark}")
    if nye:
        cut_nye = [b for b in nye if b.ren is False]
        rene_nye = [b for b in nye if b.ren is True]
        linjer.append("")
        if cut_nye:
            linjer.append(f"ADVARSEL: {len(cut_nye)} ny(e) boot(s) uden ren nedlukning:")
            for b in cut_nye:
                linjer.append(f"  {b.start} (boot {b.idx})")
        elif rene_nye:
            linjer.append(f"{len(rene_nye)} ny(e) boot(s), alle med ren nedlukning.")
        else:
            # Kun den koerende boot er ny — den har intet udfald endnu, og det
            # skal ikke lyde som en ren nedlukning.
            linjer.append("Ny boot registreret, men den koerer endnu — intet udfald at melde.")
    return "\n".join(linjer)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Klassificér pve i9-boots som REN eller CUT.")
    ap.add_argument("--host", default=STANDARD_HOST)
    ap.add_argument("--state", type=Path, default=STANDARD_STATE)
    ap.add_argument("--antal", type=int, default=8, help="hvor mange nyeste boots der klassificeres")
    ap.add_argument("--alle", action="store_true", help="vis hele listen, ikke kun nye")
    ap.add_argument("--stdin", action="store_true", help="læs boot-liste fra stdin (ingen ssh)")
    ap.add_argument("--json", action="store_true", help="maskinlæsbar udskrift")
    args = ap.parse_args(argv)

    if args.stdin:
        boots = parse_boot_liste(sys.stdin.read())
        # Uden ssh kan halen ikke hentes — udfaldet forbliver umaalt.
    else:
        try:
            boots = maal(args.host, args.antal)
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            print(f"kunne ikke maale: {e}", file=sys.stderr)
            return 2

    state = indlaes_state(args.state)
    kendte = set(state.get("kendte", []))
    nye = nye_siden(boots, kendte)

    if args.json:
        print(json.dumps(
            [{"idx": b.idx, "boot_id": b.boot_id, "start": b.start, "slut": b.slut,
              "udfald": b.udfald, "ny": b in nye} for b in boots],
            indent=2,
        ))
    else:
        print(rapport(boots if args.alle else boots[-args.antal:], nye))

    if not args.stdin:
        gem_state(args.state, [b.boot_id for b in boots])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
