#!/usr/bin/env python3
"""Vagt for hollow-promise-fixet (a19939854, 9/10-2026).

Fixet flytter kald som værnet TVANG frem (``tool_choice="required"``) op FØR
Jarvis' afsluttende tekst, så klientens skillerum (sidste ``tool_use``) ikke
ender under kvitteringen.

Denne vagt måler det i DRIFT — ikke i en unit-test:

1. Find hollow_promise-fyringer efter fix-tidspunktet (``--since``).
2. For hver ramt run: læs den persisterede assistent-besked.
3. Find det sidste ``tool_use`` og se hvad der staar umiddelbart foer det.
4. FEJL hvis det sidste kald er et bogfoerings-kald OG der ligger tekst
   foer det — saa skubber klientens skillerum svaret ind i «arbejde».

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
    """Maal blok-raekkefoelgen mod klientens skillerum.

    Klienten saetter skillerummet EFTER det sidste ``tool_use``: alt tekst
    derefter er svaret, alt foer er «arbejde». To former er defekter:

    * et kald der ligger efter den SIDSTE tekstblok, og
    * et bogfoerings-kald hvis naermeste synlige forgænger er TEKST — kaldet
      i midten.

    Den foerste udgave sammenlignede «sidste tekst» med «sidste kald» og
    fandt derfor KUN den foerste form. Maalt 9/10-2026 var den dominerende
    form netop kaldet i MIDTEN: et 2.413-tegns svar, saa
    ``suggest_next_task``, saa en afrunding. Begge tal pegede «rigtigt»
    (teksten laa sidst) mens svaret alligevel var begravet — vagten havde
    samme blinde plet som det fix den skulle maale.
    """
    from core.services.visible_turn_accumulator import _INTERNE_HALE_VAERKTOEJER

    def _synligt(b: dict) -> bool:
        """Resultater, etiketter og spor er ikke fortælling."""
        return b.get("type") not in ("tool_result", "tool_use_summary", "progress")

    tool_ix = [i for i, b in enumerate(blokke) if b.get("type") == "tool_use"]
    sidste_tool = max(tool_ix, default=-1)
    sidste_text = max(
        (i for i, b in enumerate(blokke) if b.get("type") == "text"), default=-1
    )
    efter = [blokke[i].get("name") for i in tool_ix if i > sidste_text]

    midten: list[str] = []
    if sidste_tool >= 0:
        navn = str(blokke[sidste_tool].get("name") or "")
        if navn in _INTERNE_HALE_VAERKTOEJER:
            j = sidste_tool - 1
            while j >= 0 and not _synligt(blokke[j]):
                j -= 1
            if (j >= 0 and blokke[j].get("type") == "text"
                    and str(blokke[j].get("text") or "").strip()):
                midten.append(navn)

    return {
        "antal_blokke": len(blokke),
        "sidste_text": sidste_text,
        "sidste_tool_use": sidste_tool,
        "kald_efter_svaret": len(efter),
        "navne_efter_svaret": efter[:8],
        "kald_i_midten": len(midten),
        "navne_i_midten": midten[:8],
        "ok": not efter and not midten,
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
                f"| efter={r['kald_efter_svaret']} {r['navne_efter_svaret']} "
                f"| midten={r['kald_i_midten']} {r['navne_i_midten']}"
            )

    print()
    if fejl:
        print(f"RESULTAT: {fejl} besked(er) med et internt kald efter svaret — fixet virker IKKE.")
        return 1
    print("RESULTAT: intet internt kald efter svaret. Fixet holder i drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
