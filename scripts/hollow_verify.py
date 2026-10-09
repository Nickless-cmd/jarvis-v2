#!/usr/bin/env python3
"""Vagt for hollow-promise-fixet (a19939854, 9/10-2026).

Fixet flytter kald som værnet TVANG frem (``tool_choice="required"``) op FØR
Jarvis' afsluttende tekst, så klientens skillerum (sidste ``tool_use``) ikke
ender under kvitteringen.

Denne vagt måler det i DRIFT — ikke i en unit-test:

1. Find hollow_promise-fyringer efter fix-tidspunktet (``--since``).
2. For hver ramt run: læs den persisterede assistent-besked.
3. Find den sidste ``text``-blok og den sidste ``tool_use``-blok.
4. FEJL hvis den sidste ``tool_use`` ligger EFTER den sidste ``text``
   — det er præcis den fejl fixet skulle fjerne.

Brug:
    python scripts/hollow_verify.py                 # siden fixet
    python scripts/hollow_verify.py --since 2026-10-09T12:54:32Z
    python scripts/hollow_verify.py --all           # alle fyringer (baseline)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
FIX_TID = "2026-10-09T12:54:32Z"  # a19939854, commit-tid i UTC


def _fyringer(since: str | None) -> list[dict]:
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    sql = (
        "SELECT created_at, payload_json FROM events "
        "WHERE kind = 'runtime.hollow_promise_detected' "
    )
    params: tuple = ()
    if since:
        sql += "AND created_at > ? "
        params = (since,)
    sql += "ORDER BY created_at DESC"
    out = []
    for r in c.execute(sql, params):
        p = json.loads(r["payload_json"])
        out.append(
            {
                "created_at": r["created_at"],
                "run_id": str(p.get("run_id") or ""),
                "session_id": str(p.get("session_id") or ""),
                "round": p.get("round"),
                "forced": p.get("forced"),
            }
        )
    return out


def _beskeder(run_id: str, session_id: str, created_at: str) -> list[dict]:
    """Beskeden for et run — filtreret på SESSION + tidsvindue.

    ``LIKE '%run_id%'`` over hele chat_messages er en fuld scanning af en
    4,1 GB tabel med 130 KB-blobs; den timede ud (målt 9/10-2026). Der er
    indeks på ``session_id`` og ``(role, created_at)``, så vi filtrerer
    derned og leder efter run_id i Python på de få ramte rækker.
    """
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    # Trin 1: kun id + tid (billigt — ingen blobs) for sessionens assistent-turer.
    kandidater = c.execute(
        "SELECT id, created_at FROM chat_messages "
        "WHERE session_id = ? AND role = 'assistant' "
        "ORDER BY id DESC LIMIT 400",
        (session_id,),
    ).fetchall()
    # Trin 2: tidsvinduet i Python — beskeden persisteres når runnet slutter,
    # ikke når værnet fyrer, så vi ser op til en time frem.
    from datetime import datetime, timedelta

    try:
        t0 = datetime.fromisoformat(created_at)
    except Exception:
        t0 = None
    ids: list[int] = []
    for r in kandidater:
        if t0 is None:
            ids.append(r["id"])
            continue
        try:
            ts = datetime.fromisoformat(str(r["created_at"]))
        except Exception:  # ulaeseligt tidsstempel = raekken kan ikke tids-afgraenses
            continue
        if t0 <= ts <= t0 + timedelta(hours=1):
            ids.append(r["id"])
    if not ids:
        return []
    # Trin 3: læs kun de ramte rækkers indhold, og bekræft run_id.
    pl = ",".join("?" * len(ids))
    rows = c.execute(
        f"SELECT id, content_json FROM chat_messages WHERE id IN ({pl})",
        tuple(ids),
    ).fetchall()
    return [
        {"id": r["id"], "content_json": r["content_json"]}
        for r in rows
        if run_id and run_id in (r["content_json"] or "")
    ]


def _blokke(content_json: str | None) -> list[dict]:
    if not content_json:
        return []
    try:
        cj = json.loads(content_json)
    except Exception:  # ugyldig JSON = ingen blokke at maale paa
        return []
    if isinstance(cj, list):
        return [b for b in cj if isinstance(b, dict)]
    if isinstance(cj, dict):
        b = cj.get("blocks")
        return [x for x in b if isinstance(x, dict)] if isinstance(b, list) else []
    return []


def _maal(blokke: list[dict]) -> dict:
    """Find sidste text og sidste tool_use — og om rækkefølgen er rigtig."""
    sidste_text = max(
        (i for i, b in enumerate(blokke) if b.get("type") == "text"), default=-1
    )
    tool_ix = [i for i, b in enumerate(blokke) if b.get("type") == "tool_use"]
    sidste_tool = max(tool_ix, default=-1)
    navne = [blokke[i].get("name") for i in tool_ix if i > sidste_text]
    return {
        "antal_blokke": len(blokke),
        "sidste_text": sidste_text,
        "sidste_tool_use": sidste_tool,
        "kald_efter_svaret": len(navne),
        "navne_efter_svaret": navne[:8],
        "ok": not (sidste_tool > sidste_text and sidste_text >= 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=FIX_TID)
    ap.add_argument("--all", action="store_true", help="alle fyringer (baseline)")
    args = ap.parse_args()

    since = None if args.all else args.since
    fyr = _fyringer(since)
    print(f"hollow-fyringer: {len(fyr)}" + (f" (siden {since})" if since else " (alle)"))
    if not fyr:
        print("INGEN fyringer i vinduet — fixet kan ikke verificeres i drift endnu.")
        return 0

    fejl = 0
    for f in fyr:
        for m in _beskeder(f["run_id"], f["session_id"], f["created_at"]):
            blokke = _blokke(m["content_json"])
            if not blokke:
                continue
            r = _maal(blokke)
            flag = "OK  " if r["ok"] else "FEJL"
            if not r["ok"]:
                fejl += 1
            print(
                f"{flag} | {f['created_at'][:19]} | runde {f['round']} "
                f"| msg {m['id']} | blokke={r['antal_blokke']} "
                f"| sidste_text={r['sidste_text']} sidste_tool={r['sidste_tool_use']} "
                f"| kald-efter-svar={r['kald_efter_svaret']} {r['navne_efter_svaret']}"
            )

    print()
    if fejl:
        print(f"RESULTAT: {fejl} besked(er) med kald EFTER svaret — fixet virker IKKE.")
        return 1
    print("RESULTAT: alle målte runs slutter i tekst. Fixet holder i drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
