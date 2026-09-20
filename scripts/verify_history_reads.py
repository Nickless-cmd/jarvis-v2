#!/usr/bin/env python
"""Vagt: ingen NYE kaldere der læser en hel samtale-historik synkront.

## Hvorfor (20/9-2026)

`get_chat_session(session_id)` henter HELE beskedhistorikken i ét synkront
kald. Det var den funktion der gjorde min og Bjørns samtale til en nyttelast
på 21,5 MB, og formen inviterer til det: kalderen beder om «samtalen» og får
alt hvad der nogensinde er sagt.

Målt i dag: 45 kaldesteder. **14 af dem læser hele historikken for at bruge
metadata** — en titel, en ejer, et workspace. De betaler for hver eneste
besked i samtalen for at læse ét felt.

DeepSeek-harness traf samme beslutning 9/9-2026 og formulerede den skarpere
end jeg havde gjort: eksisterende kaldere må blive, men NYE er forbudt, og
nye domæner skal designe deres event-felter og deres projektion SAMMEN, så
tilstanden kan genskabes uden at læse historikken igennem. En projektion
læses synkront uden at kræve vilkårlig adgang til loggen.

## Hvad man bruger i stedet

* `get_session_owner(session_id)` — ejeren, ét felt
* `session_version(session_id)` — versionen, uden beskederne
* `recent_chat_session_messages(session_id, limit=N)` — et BUNDET vindue
* `chat_session_messages_since_last_compact(...)` — det der faktisk er nyt

Skal man ægte bruge hele historikken (en fork, en eksport), er det stadig
lovligt — men så skal det stå i grundlinjen som et bevidst valg, ikke opstå
ved et uheld i en ny hjælpefunktion.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
GRUNDLINJE = ROD / "docs/guards/history_read_baseline.json"
OMRAADER = ("core", "apps/api", "scripts")
#: Funktioner der returnerer en HEL historik i ét synkront kald.
FULD_HISTORIK = frozenset({"get_chat_session"})


def _navn(node: ast.Call) -> str:
    f = node.func
    return getattr(f, "id", "") or getattr(f, "attr", "")


def fund_i_fil(sti: Path) -> list[tuple[int, str]]:
    try:
        src = sti.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        print(f"verify-history-reads: kan ikke læse {sti}: {exc}", file=sys.stderr)
        return []
    try:
        traeet = ast.parse(src)
    except SyntaxError:
        # En fil der ikke parser, har ingen kaldesteder at tælle. Den fanges
        # af compileall og skal ikke også vælte den her vagt.
        return []
    # Selve definitionen er ikke et kaldested.
    definerer = {n.name for n in ast.walk(traeet)
                 if isinstance(n, ast.FunctionDef)} & FULD_HISTORIK
    ud = [(n.lineno, _navn(n)) for n in ast.walk(traeet)
          if isinstance(n, ast.Call) and _navn(n) in FULD_HISTORIK]
    if definerer:
        return []
    return ud


def _filer(a) -> list[Path]:
    if a.paths:
        return [Path(p) for p in a.paths if p.endswith(".py")]
    if a.staged:
        r = subprocess.run(["git", "diff", "--cached", "--name-only",
                            "--diff-filter=ACMR"], capture_output=True, text=True,
                           cwd=ROD, check=False)
        toppe = {o.split("/")[0] for o in OMRAADER}
        return [ROD / l for l in r.stdout.splitlines()
                if l.endswith(".py") and l.split("/")[0] in toppe]
    ud: list[Path] = []
    for o in OMRAADER:
        ud += [p for p in (ROD / o).rglob("*.py") if "__pycache__" not in str(p)]
    return ud


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="*")
    p.add_argument("--staged", action="store_true")
    p.add_argument("--skriv-grundlinje", action="store_true")
    a = p.parse_args(argv)

    tal: Counter[str] = Counter()
    fund: dict[str, list[tuple[int, str]]] = {}
    for f in _filer(a):
        abs_sti = f if f.is_absolute() else ROD / f
        rel = str(abs_sti.relative_to(ROD)) if ROD in abs_sti.parents else str(f)
        v = fund_i_fil(abs_sti)
        if v:
            tal[rel] = len(v)
            fund[rel] = v

    if a.skriv_grundlinje:
        GRUNDLINJE.parent.mkdir(parents=True, exist_ok=True)
        GRUNDLINJE.write_text(json.dumps(
            {"_forklaring": "Kaldesteder der læser en HEL samtale-historik "
                            "synkront. Nye er forbudt; færre er en sejr.",
             "i_alt": sum(tal.values()), "pr_fil": dict(sorted(tal.items()))},
            indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"verify-history-reads: grundlinje skrevet — {sum(tal.values())} "
              f"kaldesteder i {len(tal)} filer.")
        return 0

    try:
        grundlinje = json.loads(GRUNDLINJE.read_text(encoding="utf-8"))["pr_fil"]
    except Exception as exc:  # ingen grundlinje = alt er nyt
        print(f"verify-history-reads: ingen grundlinje ({exc})", file=sys.stderr)
        grundlinje = {}

    brud = [(rel, n, grundlinje.get(rel, 0)) for rel, n in sorted(tal.items())
            if n > grundlinje.get(rel, 0)]
    if not brud:
        return 0
    print("\n❌ VERIFY-HISTORY-READS — nyt kald der læser en HEL historik\n")
    for rel, n, loft in brud:
        print(f"  {rel}: {n} kald (grundlinje {loft})")
        for linje, navn in fund[rel][:6]:
            print(f"      {rel}:{linje}  {navn}()")
    print("\n45 kaldesteder findes; 14 af dem læser alt for at bruge ét felt.")
    print("Brug i stedet:")
    print("  • get_session_owner(sid)                      — ejeren")
    print("  • session_version(sid)                        — versionen")
    print("  • recent_chat_session_messages(sid, limit=N)  — et BUNDET vindue")
    print("  • chat_session_messages_since_last_compact(…) — kun det nye")
    print("Skal du ægte bruge hele historikken, så skriv det ind i grundlinjen.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
