#!/usr/bin/env python3
"""Døb de sessioner der aldrig fik et navn, efter deres første brugerbesked.

Rettelsen i `_er_pladsholder` (16/9-2026) får fremtidige sessioner til at blive
døbt rigtigt. Men de sessioner der ALLEREDE sidder fast på «Kode-session» bliver
ikke rørt af den: navngivningen sker når en besked gemmes, og i en session der
er lagt til side kommer der ikke flere beskeder.

Derfor denne engangs-kørsel. Den gør præcis det navngivningen ville have gjort
dengang — intet mere:

  * kun titler der ER pladsholdere (samme funktion som runtimen selv bruger,
    ikke en kopi der kan komme i utakt)
  * kun sessioner der HAR en brugerbesked at tage navnet fra
  * teksten normaliseres af `_normalize_title`, som runtimen også gør

Tør-løb som standard. `--anvend` skriver, og skriver en backup først.
"""
from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anvend", action="store_true", help="skriv aendringerne (ellers toer-loeb)")
    args = p.parse_args()

    from core.runtime.db import connect
    from core.services.chat_sessions import _er_pladsholder, _normalize_title

    with connect() as conn:
        conn.row_factory = __import__("sqlite3").Row
        raekker = conn.execute(
            "SELECT session_id, title FROM chat_sessions ORDER BY updated_at DESC"
        ).fetchall()

        planlagt: list[tuple[str, str, str]] = []
        for r in raekker:
            if not _er_pladsholder(r["title"]):
                continue
            besked = conn.execute(
                "SELECT content FROM chat_messages WHERE session_id = ? AND role = 'user' "
                "ORDER BY id LIMIT 1", (r["session_id"],)).fetchone()
            tekst = " ".join(str((besked or {"content": ""})["content"] or "").split()).strip()
            if not tekst:
                # Ingen brugerbesked = intet at doebe den efter. En session uden
                # indhold skal ikke have et opdigtet navn.
                continue
            planlagt.append((r["session_id"], str(r["title"] or ""), _normalize_title(tekst)))

        print(f"{len(raekker)} sessioner gennemgaaet, {len(planlagt)} kan doebes\n")
        for sid, gammel, ny in planlagt:
            print(f"  {sid[:18]:20s} {gammel!r:16s} → {ny!r}")

        if not planlagt:
            return 0
        if not args.anvend:
            print("\n(toer-loeb — koer med --anvend for at skrive)")
            return 0

        from core.runtime.config import JARVIS_HOME
        db = Path(JARVIS_HOME) / "state" / "jarvis.db"
        sik = db.with_name(f"jarvis.db.bak-{datetime.now(UTC):%Y%m%dT%H%M%S}")
        shutil.copy2(db, sik)
        print(f"\nbackup: {sik}")

        for sid, _gammel, ny in planlagt:
            conn.execute("UPDATE chat_sessions SET title = ? WHERE session_id = ?", (ny, sid))
        conn.commit()
        print(f"{len(planlagt)} sessioner doebt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
