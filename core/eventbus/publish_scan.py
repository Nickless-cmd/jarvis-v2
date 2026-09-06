"""Find hver `publish("familie.navn")` i kildekoden — statisk, uden at koere noget.

Baggrund: tre gange paa to dage fandt vi det samme moenster — noget bygget, men
kun *naesten* tilsluttet:

  · `tool_discovery.nudge` blev afvist af ALLOWED_EVENT_FAMILIES; kaldstedets
    except slugte det til en debug-linje, og skygge-maalingen ville have vist
    nul i ugevis.
  · `pause_and_ask`-resultater blev aldrig parset i desk — spoergsmaalet stod
    som raa JSON.
  · `threshold_proposed` blev beregnet gennem 656 beslutninger og aldrig anvendt.

Kun den foerste klasse er statisk afgoerbar, og den er til gengaeld eksakt:
`publish()` kalder `Event.create()` som kalder `validate()`, saa en familie der
ikke staar i ALLOWED_EVENT_FAMILIES raiser — hver gang, tavst.

Maalt 6/9-2026: **64 familier** publiceres i core/apps/scripts uden at vaere
tilladt. Nul events i databasen for dem alle.
"""

from __future__ import annotations

import re
from pathlib import Path

# `publish("familie.navn"` — baade event_bus.publish og bus.publish.
#
# Navne-delen er bevidst bred (`[^'"]+`): et foerste forsoeg brugte
# [a-zA-Z0-9_.{}] og var dermed BLIND for navne med aeoaa. Min egen
# verifikations-proeve slap igennem, fordi jeg havde doebt den «haendelse».
# En scanner med et hul er vaerre end ingen scanner: den giver falsk tryghed.
_PUBLISH = re.compile(r'publish\(\s*[\'"]([a-zA-Z_][a-zA-Z0-9_]*)\.([^\'"]+)[\'"]')

_ROEDDER = ("core", "apps", "scripts")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def scan_published_families(rod: Path | None = None) -> dict[str, list[str]]:
    """familie → liste af "sti:linje" hvor den publiceres.

    Worktrees og node_modules udelades: de er kopier, og de ville faa hvert fund
    til at taelle flere gange.
    """
    base = rod or _repo_root()
    ud: dict[str, list[str]] = {}
    for navn in _ROEDDER:
        for p in (base / navn).rglob("*.py"):
            s = str(p)
            if "node_modules" in s or ".worktrees" in s:
                continue
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for m in _PUBLISH.finditer(txt):
                linje = txt[: m.start()].count("\n") + 1
                ud.setdefault(m.group(1), []).append(f"{p.relative_to(base)}:{linje}")
    return ud


def unregistered_families(rod: Path | None = None) -> dict[str, list[str]]:
    """De publicerede familier der IKKE er tilladt → publish raiser tavst."""
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES

    return {
        f: steder
        for f, steder in scan_published_families(rod).items()
        if f not in ALLOWED_EVENT_FAMILIES
    }
