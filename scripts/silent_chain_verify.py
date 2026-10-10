#!/usr/bin/env python3
"""Bagud-maaling af tavse kaede-knaek (10/10-2026).

Detektoren `core/services/silent_chain_break.py` ser exit-koden i det ojeblik
den findes og skriver en lesson, naar en REN `&&`-kaede braekker. Men uden
exit-koden i `events` kunne den kun maales i NUET — spoergsmaalet «hvor ofte
knaekker mine kaeder?» havde intet svar bagud, for exit-koden findes kun i
`result` og blev smidt vaek ved udgivelsen.

Fra 10/10-2026 baerer `tool.completed` `exit_code` og `command` for
shell-vaerktoejer. Denne vagt afspiller historikken gennem den AEGTE funktion
i stedet for at gaette:

1. Laes shell-kald med en exit-kode fra `events` (kind='tool.completed').
2. Koer `silent_chain_break(command, exit_code)` paa hvert kald.
3. Rapportér pr. vaerktoej: hvor mange kald, hvor mange knaek.

Vagtens andet tal er `lessons`, hvor detektoren skriver sine fund i DRIFT.
De to skal moedes: et knaek i historikken uden en tilsvarende lesson betyder
at detektoren ikke koerte paa det kald — fx fordi vaerktoejet laa uden for
dens daekning, eller at den ikke var live endnu.

Brug:
    python scripts/silent_chain_verify.py
    python scripts/silent_chain_verify.py --since 2026-10-10
    python scripts/silent_chain_verify.py --all
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
ROD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROD))

# Den aegte funktion — ikke en kopi. Kopierer vi logikken her, maaler vi en
# skygge: aendrer detektoren sig, ville vagten stadig maale den gamle regel.
from core.services.silent_chain_break import silent_chain_break  # noqa: E402

#: Persisteringen landede her. Foer den findes der ingen exit-kode at maale.
LANDEDE = "2026-10-10"


def _kald(db: Path, since: str | None) -> list[dict]:
    """Shell-kald der baerer en exit-kode — substansen bagud-maalingen kraever."""
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    sql = (
        "SELECT created_at, payload_json FROM events "
        "WHERE kind = 'tool.completed' "
        "AND json_extract(payload_json, '$.exit_code') IS NOT NULL "
    )
    params: tuple = ()
    if since:
        sql += "AND created_at > ? "
        params = (since,)
    sql += "ORDER BY created_at DESC"
    ud: list[dict] = []
    for r in c.execute(sql, params):
        ud.append({"created_at": r["created_at"], **json.loads(r["payload_json"])})
    return ud


def _knaek(kald: list[dict]) -> list[dict]:
    """Afspil den aegte detektor over historikken."""
    ud: list[dict] = []
    for k in kald:
        fund = silent_chain_break(k.get("command"), k.get("exit_code"))
        if fund:
            ud.append({**k, **fund})
    return ud


def _lessons(db: Path) -> int:
    """Hvor mange fund har detektoren selv skrevet i drift?"""
    c = sqlite3.connect(str(db))
    r = c.execute(
        "SELECT coalesce(sum(evidence_count), 0) FROM lessons "
        "WHERE signature LIKE 'silent_chain_break%'"
    ).fetchone()
    return int(r[0] or 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", default=None, help=f"ISO-tid (default: {LANDEDE})")
    ap.add_argument("--all", action="store_true", help="hele historikken")
    ap.add_argument("--db", default=None, help=f"anden database (default: {DB})")
    a = ap.parse_args()
    db = Path(a.db) if a.db else DB
    since = None if a.all else (a.since or LANDEDE)

    kald = _kald(db, since)
    if not kald:
        print(f"ingen shell-kald med exit-kode siden {since or 'altid'}.")
        print(f"persisteringen landede {LANDEDE} — foer det findes der intet at maale.")
        return 0

    knaek = _knaek(kald)
    pr_tool: dict[str, dict[str, int]] = {}
    for k in kald:
        d = pr_tool.setdefault(str(k.get("tool") or "?"), {"kald": 0, "knaek": 0})
        d["kald"] += 1
    for k in knaek:
        pr_tool[str(k.get("tool") or "?")]["knaek"] += 1

    print(f"=== shell-kald med exit-kode: {len(kald)} (siden {since or 'altid'}) ===")
    print(f"{'vaerktoej':<18}{'kald':>8}{'knaek':>8}{'andel':>8}")
    for navn in sorted(pr_tool, key=lambda n: -pr_tool[n]["kald"]):
        d = pr_tool[navn]
        andel = f"{100 * d['knaek'] / d['kald']:.1f}%"
        print(f"{navn:<18}{d['kald']:>8}{d['knaek']:>8}{andel:>8}")

    print()
    print(f"knaek i alt: {len(knaek)} af {len(kald)} kald")
    print(f"lessons skrevet af detektoren i drift: {_lessons(db)}")

    if knaek:
        print()
        print("--- de 10 nyeste ---")
        for k in knaek[:10]:
            print(
                f"{k['created_at'][:19]} | {k.get('tool')} | exit {k['exit_code']} "
                f"| {k['led']} led | {str(k.get('command'))[:90]}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
