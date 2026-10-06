"""Lad central_cli-testene teste DERES EGET traee.

`central_cli` er en editable install, og dens sti peger paa HOVED-checkoutet
(`/media/projects/jarvis-v2/apps/central_cli`). Uden denne fil importerer en
test i en worktree derfor hovedtraeets `hud.py` — ikke worktree'ens.

Maalt 6/10-2026: tre mutationer i en worktree (fjernet «work»-fanen, en
opdigtet post i `_TABLE_TABS`, panelet gjort permanent synligt) gav ALLE
«184 passed». Testene maalte en fil ingen havde aendret. Det er den vaerste
slags groen: den bekraefter en rettelse man ikke har foretaget.

**Stien fjernes igen med vilje.** `apps/central_cli/` indeholder ogsaa en mappe
der heder `tests`, praecis som repo-roden, og ingen af dem har `__init__.py`.
Blev stien liggende paa `sys.path[0]` for resten af pytest-processen, kunne
`from tests.conftest import kald_rute` (brugt i et dusin rute-tests) begynde at
loese op mod den forkerte `tests`. Modulet skal kun bindes ÉN gang; naar
`central_cli` staar i `sys.modules`, bruger alle senere importer — ogsaa
undermoduler som `central_cli.hud_actions` — pakkens egen `__path__`, som
peger i worktree'en.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_APP = Path(__file__).resolve().parents[1]


def _bind_lokal_central_cli() -> None:
    allerede = sys.modules.get("central_cli")
    if allerede is not None and str(_APP) in str(getattr(allerede, "__file__", "")):
        return                      # peger allerede rigtigt
    for navn in [n for n in sys.modules if n == "central_cli" or n.startswith("central_cli.")]:
        del sys.modules[navn]       # ellers vinder den installerede kopi
    sys.path.insert(0, str(_APP))
    try:
        importlib.import_module("central_cli")
    finally:
        try:
            sys.path.remove(str(_APP))
        except ValueError:  # en anden conftest kan have fjernet den
            pass


_bind_lokal_central_cli()
