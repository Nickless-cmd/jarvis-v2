#!/usr/bin/env python
"""Vagt: vagt-laget må NÆVNE et delsystem, aldrig importere det.

## Hvorfor (20/9-2026)

Bjørn spurgte i formiddags: «hvad med regler om self wakeup og plans og todos
og goals? eller de høre ikk til der?» — om tool-nudgen skulle bære reglerne
for de fire.

DeepSeek-harness' svar er nej, og det står i deres mappestruktur: `plan/`,
`todo/`, `goal/` og `schedule/` er fire selvstændige pakker, og `guard/` er
en femte. Vagten er et LAG, ikke et sted man samler reglerne.

Revideret her samme dag: vi har allerede alle fire — `plan_proposals`,
`agent_todos`, `autonomous_goals`, `self_wakeup` — og alle fire kan nås som
værktøjer. Nudgen peger allerede på to af dem (`schedule_self_wakeup` og
`flag_side_task`) ved at nævne deres værktøjsnavn som en streng.

Det er præcis den grænse der skal holdes. Nævner vagten et værktøj, kan
delsystemet ændre sig uden at røre vagten. Importerer den delsystemet, er
reglen pludselig to steder, og den ene af dem er den man glemmer.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
#: Moduler der er VAGTER: de observerer og rådgiver, de ejer ingen tilstand.
VAGTER = ("core/services/tool_hunt_nudge.py",)
#: Delsystemer en vagt højst må kende ved deres VÆRKTØJSNAVN.
DELSYSTEMER = (
    "core.services.plan_proposals",
    "core.services.agent_todos",
    "core.services.autonomous_goals",
    "core.services.self_wakeup",
    "core.services.session_wakeup",
    "core.services.central_todo",
    "core.services.emergent_goals",
)


def _importerede_moduler(traeet: ast.Module) -> set[str]:
    ud: set[str] = set()
    for n in ast.walk(traeet):
        if isinstance(n, ast.Import):
            ud |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            ud.add(n.module)
            ud |= {f"{n.module}.{a.name}" for a in n.names}
    return ud


def brud() -> list[tuple[str, str]]:
    ud: list[tuple[str, str]] = []
    for rel in VAGTER:
        sti = ROD / rel
        if not sti.is_file():
            ud.append((rel, "vagten findes ikke længere — ret VAGTER-listen"))
            continue
        try:
            traeet = ast.parse(sti.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            ud.append((rel, f"kunne ikke læses: {exc}"))
            continue
        importeret = _importerede_moduler(traeet)
        for d in DELSYSTEMER:
            if any(m == d or m.startswith(d + ".") for m in importeret):
                ud.append((rel, f"importerer {d}"))
    return ud


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    fejl = brud()
    if not fejl:
        print(f"verify-vagt-graenser: {len(VAGTER)} vagt(er), ingen importerer "
              f"et delsystem.")
        return 0
    print("\n❌ VERIFY-VAGT-GRÆNSER — en vagt har taget et delsystems regel ind\n")
    for rel, hvad in fejl:
        print(f"  {rel}: {hvad}")
    print("\nEn vagt må NÆVNE et værktøjsnavn som en streng — fx\n"
          "  VAAGN_VAERKTOEJ = \"schedule_self_wakeup\"\n"
          "— så delsystemet kan ændre sig uden at røre vagten. Importerer\n"
          "den delsystemet, står reglen to steder, og den ene glemmes.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
