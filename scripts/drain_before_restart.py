#!/usr/bin/env python
"""Vent til ingen tur er levende, så en genstart ikke kapper en.

Bjørn/Jarvis målte 11/9-2026 hvad en genstart midt i en tur koster:

    13:27:11  Shutting down — turen står i runde 3
    13:27:41  ERROR: Cancel 1 running task(s), timeout graceful shutdown exceeded
    13:27:43  ny proces klar

Mellem de to linjer kørte turen runde 3 → 10. Syv runder, fjorten bash-kald,
udført EFTER shutdown-signalet og derefter smidt væk. `--timeout-graceful-
shutdown 30` er sandt om hensigten og forkert om hvad der sker: agentic-løkken
ser aldrig signalet, så de 30 sekunder er spild frem for udsættelse.

At sænke timeouten hjælper ikke — man taber de samme runder, bare hurtigere.
Det der hjælper er at vente til turen er færdig af sig selv. Så tager
genstarten 2 sekunder og der er intet arbejde at smide væk.

## Hvorfor dette signal

`visible_runs.active_run` friskes MIDT i et værktøjskald, ikke kun ved
runde-grænser: målt flyttede `updated_at` 60,5 s på 60 s under et langt kald.
Kadencerne i kilden er 5,0 s (first-pass), 15,0 s (agentic), 5,0 s (build-
input) — alle langt under de 180 s vi kalder frisk.

## Semantikken er en ANDEN end detektorens

Detektoren spørger «lever DENNE session». Gaten skal spørge «lever NOGET» —
nøglen holder ét run ad gangen, så et samtidigt autonomt run kan stå der i
stedet for den synlige tur. For en genstart er det lige meget hvis tur det er;
alt levende arbejde tabes. (Jarvis' fund, 11/9-2026.)
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from datetime import UTC, datetime

DB = os.environ.get("JARVIS_DB") or os.path.expanduser("~/.jarvis-v2/state/jarvis.db")
FRISK_SEKUNDER = 180.0
POLL_SEKUNDER = 2.0
STANDARD_LOFT = 300.0


def levende(db: str = DB) -> bool | None:
    """Er der et levende run lige nu? `None` = kunne ikke afgøres.

    Tre tilstande, ikke to. En DB-hikke må ikke læses som «der er frit» —
    det ville lade en genstart køre netop når vi er mindst sikre.
    """
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        try:
            r = con.execute(
                "SELECT value_json, updated_at FROM runtime_state_kv WHERE key = ?",
                ("visible_runs.active_run",)).fetchone()
        finally:
            con.close()
        if not r:
            return False
        if not (json.loads(r["value_json"] or "{}") or {}).get("active"):
            return False
        t = datetime.fromisoformat(str(r["updated_at"]))
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        return (datetime.now(UTC) - t).total_seconds() < FRISK_SEKUNDER
    except Exception:
        return None


def vent(loft: float = STANDARD_LOFT, db: str = DB) -> int:
    """0 = frit, kan genstarte. 1 = loftet nået mens noget stadig kørte."""
    start = time.monotonic()
    uafgjort = 0
    while True:
        svar = levende(db)
        if svar is False:
            gik = time.monotonic() - start
            print(f"frit efter {gik:.0f}s — genstart kapper ingen tur")
            return 0
        if svar is None:
            uafgjort += 1
            # Uafgjort er ikke «frit». Men kan vi ALDRIG afgøre det, er det
            # heller ikke en grund til at vente i det uendelige.
            if uafgjort >= 5:
                print("kunne ikke afgøre om noget kørte (5 forsøg) — venter ikke længere",
                      file=sys.stderr)
                return 2
        if time.monotonic() - start >= loft:
            print(f"loftet på {loft:.0f}s nået mens noget stadig kørte", file=sys.stderr)
            return 1
        time.sleep(POLL_SEKUNDER)


if __name__ == "__main__":
    _loft = float(sys.argv[1]) if len(sys.argv) > 1 else STANDARD_LOFT
    raise SystemExit(vent(_loft))
