#!/usr/bin/env python3
"""Ryd ejerløse kandidater i runtime_contract_candidates.

Baggrund (10/10-2026): owner_workspace-kolonnen blev tilføjet 9/10, og de
eksisterende rækker stod uden ejer. Migreringen stemplede 21.559 rækker, men
3.666 kunne ikke opløses. Dette script tager resten:

  1. Stempl kandidater hvis session opløser til et workspace der FINDES.
  2. Afvis (status='rejected') forældreløse PROPOSED-kandidater — de kan ikke
     opløses til et ophav og må derfor ikke kunne skrive (fail-closed).
  3. Rør intet andet. Døde rækker (superseded/rejected) og allerede-skrevne
     (applied) efterlades urørt: applied-rækker bærer historik, og deres ejer
     har ingen fremtidig effekt.

Kør med --apply for at skrive. Uden flaget er det en tør-kørsel.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services.candidate_tracking import _owner_workspace_for_session  # noqa: E402

DB = os.path.expanduser("~/.jarvis-v2/state/jarvis.db")
WS_ROOT = os.path.expanduser("~/.jarvis-v2/workspaces")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="skriv ændringerne")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    con.execute("PRAGMA busy_timeout=30000")

    rows = con.execute(
        "SELECT id, session_id, status FROM runtime_contract_candidates "
        "WHERE COALESCE(owner_workspace,'')=''"
    ).fetchall()

    stamp: list[tuple[str, int]] = []
    reject: list[int] = []
    untouched = Counter()

    for cid, sid, status in rows:
        if status in ("superseded", "rejected"):
            untouched[status] += 1
            continue
        if status == "applied":
            # Allerede skrevet. Ejer har ingen fremtidig effekt; rør den ikke.
            untouched["applied"] += 1
            continue
        owner = _owner_workspace_for_session(sid or "")
        if owner and os.path.isdir(os.path.join(WS_ROOT, owner)):
            stamp.append((owner, cid))
        else:
            reject.append(cid)

    print(f"stempl: {len(stamp)}  afvis: {len(reject)}  urørt: {dict(untouched)}")

    if not args.apply:
        print("(tør-kørsel — intet skrevet)")
        return 0

    with con:  # atomisk
        for owner, cid in stamp:
            con.execute(
                "UPDATE runtime_contract_candidates SET owner_workspace=? WHERE id=?",
                (owner, cid),
            )
        for cid in reject:
            con.execute(
                "UPDATE runtime_contract_candidates SET status='rejected' WHERE id=?",
                (cid,),
            )
    print(f"skrevet: {len(stamp)} stempler, {len(reject)} afvisninger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
