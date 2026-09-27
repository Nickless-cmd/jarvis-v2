#!/usr/bin/env python
"""Krypter de medlems-chatbeskeder der allerede ligger i klartekst (task 3.3).

Fremadrettet fødes en medlems-række krypteret (`chat_crypto` i projektoren og
i den gamle skrivevej). Denne kørsel tager dem der blev skrevet FØR det —
målt 27/9-2026: Mikkel 778, Lotte 231, Michelle 162.

## Rækværket fra planen, i kode

Planen (§16, «Rækværk pr. task») kræver dry-run først, kørsel på en kopi før
den ægte, og verificeret rundtur FØR klarteksten er væk. Alle tre er bygget
ind her frem for at være noget man husker:

* **Dry-run er standard.** Uden `--gør-det` rører den ingenting.
* **Rundturen verificeres pr. række, inde i transaktionen.** Hver række læses
  tilbage fra databasen efter skrivningen, dekrypteres, og sammenlignes med
  den oprindelige tekst. Ét afvig → hele transaktionen rulles tilbage.
* **`--kopi <sti>`** kører mod en kopi i stedet for den rigtige database.

## FTS følger med af sig selv

`chat_messages_fts` er et external-content-indeks med en AFTER UPDATE-trigger
der sletter den gamle værdi og indsætter den nye. En UPDATE her fjerner altså
klarteksten fra søgeindekset og lægger cifferteksten ind i stedet. Det er ikke
en bivirkning vi håber på — uden den ville beskederne stadig kunne søges frem
i klartekst.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services.chat_crypto import (  # noqa: E402
    dekrypter, er_krypteret, krypter, medlem_for_raekke,
)

FELTER = ("content", "reasoning_content", "content_json")


def _db_sti() -> str:
    return os.path.expanduser("~/.jarvis-v2/state/jarvis.db")


def find_kandidater(conn: sqlite3.Connection) -> list[tuple]:
    """Rækker der tilhører en NON-owner og endnu ikke er krypteret."""
    raekker = conn.execute(
        "SELECT id, workspace_name, user_id, content, reasoning_content, content_json "
        "FROM chat_messages WHERE COALESCE(encrypted, 0) = 0"
    ).fetchall()
    ud = []
    for r in raekker:
        medlem = medlem_for_raekke(workspace_name=r[1] or "", user_id=r[2] or "")
        if medlem is None:
            continue
        if any(er_krypteret(r[i]) for i in (3, 4, 5)):
            continue
        ud.append((r, medlem))
    return ud


def koer(sti: str, *, goer_det: bool) -> int:
    conn = sqlite3.connect(sti, timeout=120)
    conn.execute("PRAGMA busy_timeout=120000")
    try:
        kandidater = find_kandidater(conn)
        pr_medlem: dict[str, int] = {}
        tegn = 0
        for r, medlem in kandidater:
            pr_medlem[medlem] = pr_medlem.get(medlem, 0) + 1
            tegn += sum(len(str(r[i] or "")) for i in (3, 4, 5))
        print("kandidater: %d rækker, %.0f KB klartekst" % (len(kandidater), tegn / 1000))
        for medlem, n in sorted(pr_medlem.items()):
            ws = conn.execute(
                "SELECT workspace_name, COUNT(*) FROM chat_messages "
                "WHERE user_id = ? OR workspace_name IN "
                "(SELECT workspace_name FROM chat_messages WHERE user_id = ?) "
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 1", (medlem, medlem)).fetchone()
            print("   %-36s %5d rækker   (workspace %s)" % (medlem, n, ws[0] if ws else "?"))
        if not kandidater:
            print("intet at gøre.")
            return 0
        if not goer_det:
            print()
            print("DRY-RUN — intet blev ændret. Kør med --gør-det for at skrive.")
            return 0

        conn.execute("BEGIN IMMEDIATE")
        skrevet = 0
        for r, medlem in kandidater:
            raekke_id = r[0]
            original = {f: r[3 + i] for i, f in enumerate(FELTER)}
            nye = {}
            for f, v in original.items():
                nye[f] = krypter(v, medlem) if isinstance(v, str) and v else v
            conn.execute(
                "UPDATE chat_messages SET content = ?, reasoning_content = ?, "
                "content_json = ?, encrypted = 1 WHERE id = ?",
                (nye["content"], nye["reasoning_content"], nye["content_json"], raekke_id),
            )
            # RUNDTUREN, inde i transaktionen: læs tilbage fra DATABASEN — ikke
            # fra `nye` — og dekryptér. Sammenligner vi med vores egen variabel,
            # beviser vi kun at vi kan huske hvad vi skrev.
            tilbage = conn.execute(
                "SELECT content, reasoning_content, content_json, encrypted "
                "FROM chat_messages WHERE id = ?", (raekke_id,)).fetchone()
            if int(tilbage[3] or 0) != 1:
                conn.rollback()
                raise SystemExit("AFBRUDT: encrypted blev ikke sat på række %s" % raekke_id)
            for i, f in enumerate(FELTER):
                vent = original[f]
                fik = tilbage[i]
                if isinstance(vent, str) and vent:
                    fik = dekrypter(fik, medlem)
                if fik != vent:
                    conn.rollback()
                    raise SystemExit(
                        "AFBRUDT: rundturen holdt ikke for række %s, felt %s — "
                        "INTET er ændret" % (raekke_id, f))
            skrevet += 1
        conn.commit()
        print()
        print("skrevet: %d rækker, rundtur verificeret for hver enkelt" % skrevet)
        rest = len(find_kandidater(conn))
        print("kandidater tilbage efter kørslen: %d (skal være 0)" % rest)
        return skrevet
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kopi", help="kør mod denne fil i stedet for den rigtige database")
    ap.add_argument("--gør-det", dest="goer_det", action="store_true",
                    help="skriv faktisk (uden dette: dry-run)")
    args = ap.parse_args()
    sti = args.kopi or _db_sti()
    print("database:", sti)
    if not os.path.exists(sti):
        print("findes ikke:", sti)
        return 1
    koer(sti, goer_det=args.goer_det)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
