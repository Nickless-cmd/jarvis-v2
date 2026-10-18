#!/usr/bin/env python3
"""Install or verify the HOST packages Jarvis' own tools require.

## Hvorfor (målt 18/10-2026)

En manglende binær er ikke en ImportError. Den er et værktøj der svarer
`error` i månedsvis, uden at nogen opdager det — og det er præcis hvad der
skete med to af dem:

- `core/tools/code_navigation_tools.py` kalder `rg` og returnerer
  `{"status": "error", "error": "ripgrep not available"}` naar den mangler.
  Maalt: 0 resultater paa et symbol med 26 aegte referencer. Baade
  `find_symbol` og `find_usages` var døde i CT105.
- `core/tools/operator_tools.py` kalder `tesseract` til OCR. Uden den kan
  scannede PDF'er og skaermbilleder slet ikke laeses som tekst.

Begge blev installeret i haanden 18/10-2026, og **intet i repoet skrev det
ned** — en genopbygning af containeren ville tavst tabe dem igen. Dette script
ER den nedskrivning.

Sprogpakkerne til tesseract er ikke en detalje: maalt paa samme fakturabillede
laeser `dan` beloeb og dato korrekt (`12.450,00`, `1. november 2026`) hvor
`eng` giver `12,450.00` og `2028`. En OCR uden den danske model er ikke en
halv loesning, den er en der svarer forkert.

## Brug

    python scripts/install_system_deps.py            # rapportér (ændrer intet)
    python scripts/install_system_deps.py --install  # installér det der mangler

Exit 1 naar noget mangler, saa den kan bruges som vagt i en provisionering.
Idempotent: installerer kun det der faktisk ikke er der.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SystemDep:
    """En binær afhængighed og hvad den koster at mangle."""

    tool: str
    why: str
    packages: dict[str, str] = field(default_factory=dict)
    # Sprog der SKAL vaere tilgaengelige for `tool` (tesseract: dan, eng).
    required_langs: tuple[str, ...] = ()


# Pakkenavnene er ikke ens paa tvaers af pakkemanagere — `rg` heddder
# `ripgrep` overalt undtagen winget, som vi ikke provisionerer herfra.
DEPS: tuple[SystemDep, ...] = (
    SystemDep(
        tool="rg",
        why="find_symbol/find_usages svarer 'ripgrep not available' uden den",
        packages={
            "apt": "ripgrep",
            "dnf": "ripgrep",
            "pacman": "ripgrep",
            "brew": "ripgrep",
        },
    ),
    SystemDep(
        tool="tesseract",
        why="OCR af scannede PDF'er og skaermbilleder er helt doe uden den",
        packages={
            # Sprogpakkerne er separate pakker paa apt — og den danske er
            # den der goer OCR'en brugbar paa dansk materiale.
            "apt": "tesseract-ocr tesseract-ocr-dan tesseract-ocr-eng",
            "dnf": "tesseract tesseract-langpack-dan tesseract-langpack-eng",
            "pacman": "tesseract tesseract-data-dan tesseract-data-eng",
            "brew": "tesseract tesseract-lang",
        },
        required_langs=("dan", "eng"),
    ),
)


def _manager() -> str:
    """Find den pakkemanager der faktisk findes. Tom streng = ingen fundet."""
    for name in ("apt-get", "dnf", "pacman", "brew"):
        if shutil.which(name):
            return name.removeprefix("-get")
    return ""


def _install_command(manager: str, packages: str) -> list[str]:
    """Byg installationskommandoen. apt og dnf skal have sudo foran."""
    pkgs = packages.split()
    if manager == "apt":
        return ["sudo", "apt-get", "install", "-y", *pkgs]
    if manager == "dnf":
        return ["sudo", "dnf", "install", "-y", *pkgs]
    if manager == "pacman":
        return ["sudo", "pacman", "-S", "--noconfirm", "--needed", *pkgs]
    if manager == "brew":
        return ["brew", "install", *pkgs]
    return []


def missing_langs(tool: str, wanted: tuple[str, ...]) -> tuple[str, ...]:
    """Hvilke sprog tesseract ikke kan laese. Kun for tesseract."""
    if not wanted:
        return ()
    try:
        res = subprocess.run(
            [tool, "--list-langs"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        # Kan vi ikke spoerge, ved vi ikke bedre end at antage at det
        # mangler — det er den sikre side for en provisioning-vagt.
        return wanted
    have = set(res.stdout.split()) | set(res.stderr.split())
    return tuple(lang for lang in wanted if lang not in have)


def check(dep: SystemDep) -> tuple[bool, str]:
    """Returnér (ok, forklaring) for én afhaengighed."""
    if not shutil.which(dep.tool):
        return False, f"{dep.tool} mangler — {dep.why}"
    missing = missing_langs(dep.tool, dep.required_langs)
    if missing:
        return False, (
            f"{dep.tool} findes, men sprog mangler: {', '.join(missing)}"
        )
    langs = f" (sprog: {', '.join(dep.required_langs)})" if dep.required_langs else ""
    return True, f"{dep.tool} OK{langs}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Installér eller verificér Jarvis' binære host-afhængigheder."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="installér det der mangler (default: kun rapport)",
    )
    args = parser.parse_args(argv)

    manager = _manager()
    if args.install and not manager:
        print("FEJL: ingen pakkemanager fundet (apt/dnf/pacman/brew).", file=sys.stderr)
        return 2

    failures: list[str] = []
    for dep in DEPS:
        ok, detail = check(dep)
        print(("  OK   " if ok else "  MANGLER ") + detail)
        if ok or not args.install:
            if not ok:
                failures.append(dep.tool)
            continue

        packages = dep.packages.get(manager, "")
        if not packages:
            print(f"         ingen pakke kendt for {manager}", file=sys.stderr)
            failures.append(dep.tool)
            continue

        cmd = _install_command(manager, packages)
        print(f"         installerer: {' '.join(cmd)}")
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"         installation fejlede (exit {res.returncode})", file=sys.stderr)
            failures.append(dep.tool)
            continue
        ok, detail = check(dep)
        print(("  OK   " if ok else "  STADIG MANGLER ") + detail)
        if not ok:
            failures.append(dep.tool)

    if failures:
        print(
            f"\n{len(failures)} afhaengighed(er) mangler: {', '.join(failures)}",
            file=sys.stderr,
        )
        return 1
    print(f"\nAlle {len(DEPS)} afhaengigheder er paa plads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
