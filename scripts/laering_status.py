#!/usr/bin/env python3
"""Hvad fangede laeringskredsloebet siden nulpunktet?

Bygget 7/9-2026 efter at kredsloebet blev koblet helt: aegte fejl taeller,
brugerafbrydelser goer ikke, Bjoerns rettelser udsendes nu som haendelser, og
en lektie skrives ogsaa naar Jarvis SELV indroemmer at han tog fejl.

Nulpunktet er `~/.jarvis-v2/state/laering-nulpunkt-20260907.json`. Uden det er
tallene bare tal — man kan ikke se om noget er sket.

    python3 scripts/laering_status.py
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

NUL = pathlib.Path.home() / ".jarvis-v2" / "state" / "laering-nulpunkt-20260907.json"
DB = "file:%s/.jarvis-v2/state/jarvis.db?mode=ro" % pathlib.Path.home()


def main() -> None:
    if not NUL.exists():
        print("intet nulpunkt at sammenligne med:", NUL)
        return
    nul = json.loads(NUL.read_text(encoding="utf-8"))
    con = sqlite3.connect(DB, uri=True)

    def t(sql: str) -> int:
        return con.execute(sql).fetchone()[0]

    nu = {
        "lessons_i_alt": t("SELECT count(*) FROM lessons"),
        "events_user_append": t("SELECT count(*) FROM events WHERE kind='channel.chat_message_appended'"),
        "visible_runs": t("SELECT count(*) FROM visible_runs"),
        "runs_med_fejl": t("SELECT count(*) FROM visible_runs WHERE error IS NOT NULL AND error != ''"),
        "approval_requested": t("SELECT count(*) FROM events WHERE kind='tool.approval_requested'"),
        "approval_resolved": t("SELECT count(*) FROM events WHERE kind='tool.approval_resolved'"),
    }
    print("nulpunkt taget: %s\n" % nul.get("taget"))
    print("%-22s %8s %8s %8s" % ("", "foer", "nu", "nye"))
    for k, v in nu.items():
        f = int(nul.get(k) or 0)
        print("%-22s %8d %8d %+8d" % (k, f, v, v - f))

    print("\n=== lektier pr. kilde ===")
    for kilde, status, n in con.execute(
        "SELECT source, status, count(*) FROM lessons GROUP BY 1, 2 ORDER BY 3 DESC"
    ):
        print("  %-14s %-10s %d" % (kilde, status, n))

    print("\n=== nye lektier siden nulpunktet ===")
    raekker = con.execute(
        "SELECT id, source, status, evidence_count, lesson FROM lessons "
        "WHERE first_at > ? ORDER BY id", (str(nul.get("taget")),)
    ).fetchall()
    if not raekker:
        print("  (ingen endnu)")
    for lid, kilde, status, ev, tekst in raekker:
        print("  #%-3s %-10s %-9s ev=%s  %s" % (lid, kilde, status, ev, str(tekst)[:88]))

    # Beslutnings-anmelderen: saa kun de foerste 20 af 45 indtil 7/9. Nu hvor
    # den ser alle, er det her tallet der viser om halen faktisk bliver maalt.
    print("\n=== beslutninger: bliver halen maalt nu? ===")
    ialt, uden = con.execute(
        "SELECT count(*), sum(adherence_score IS NULL) FROM behavioral_decisions "
        "WHERE status='active'").fetchone()
    print("  aktive %s  ·  uden score %s  (var 8 den 7/9)" % (ialt, uden))
    friske = con.execute(
        "SELECT count(*) FROM behavioral_decisions WHERE status='active' "
        "AND last_reviewed_at > ?", (str(nul.get("taget")),)).fetchone()[0]
    print("  anmeldt siden nulpunktet: %s" % friske)
    print("  --- de daarligst efterlevede ---")
    for a, d in con.execute(
        "SELECT adherence_score, directive FROM behavioral_decisions "
        "WHERE status='active' AND adherence_score IS NOT NULL "
        "ORDER BY adherence_score ASC LIMIT 5"):
        print("    %.3f  %s" % (a, str(d)[:66]))

    # Det tal der afgoer om [HUKOMMELSE] faktisk viser noget.
    print("\n=== hvad han FAKTISK ser i prompten ===")
    try:
        import sys
        sys.path.insert(0, "/media/projects/jarvis-v2")
        from core.services.lessons import build_lessons_section
        s = build_lessons_section("hvordan gaar det?") or ""
        print("  [HUKOMMELSE]: %d tegn" % len(s))
        if s:
            print("  " + s.replace("\n", "\n  ")[:500])
    except Exception as exc:
        print("  kunne ikke bygge sektionen:", exc)
    con.close()


if __name__ == "__main__":
    main()
