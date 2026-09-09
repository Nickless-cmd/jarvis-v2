#!/usr/bin/env python
"""Generalprøve: kan ledgeren holde RIGTIGE samtaler?

    conda activate ai
    python scripts/ledger_rehearsal.py [--antal 5]

## Hvorfor den findes ved siden af 97 grønne tests

Enhedstesterne leverer selv deres hændelser. En test der selv skriver inputtet
kan aldrig opdage at virkeligheden ser anderledes ud — tomme felter, `NULL` i
`content_json`, tegn ingen har tænkt på, roller ingen har forudset.

Denne prøve tager rigtige samtaler fra den levende database, skriver dem i
ledgeren, RIVER `chat_messages`-rækkerne ud og genskaber dem fra ledgeren
alene. Kriteriet er byte-lighed. Er der én forskel, er ledgeren ikke sandheden
og ingen session må flyttes.

## Den rører aldrig den levende database

Sessionerne kopieres til en midlertidig fil, og den ægte åbnes `mode=ro`. En
prøve der kan ødelægge det den prøver, er ikke en prøve.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

LIVE = pathlib.Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
KOL = ("role, content, user_id, workspace_name, reasoning_content, "
       "git_sha, content_json, created_at")


def kopiér(antal: int, mindst: int, hoejst: int) -> pathlib.Path:
    src = sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    kand = src.execute(
        "SELECT session_id, COUNT(*) n FROM chat_messages "
        "WHERE role != 'compact_marker' GROUP BY session_id "
        "HAVING n BETWEEN ? AND ? ORDER BY n DESC LIMIT ?",
        (mindst, hoejst, antal),
    ).fetchall()
    ud = pathlib.Path(tempfile.mkdtemp(prefix="ledger-proeve-")) / "proeve.db"
    dst = sqlite3.connect(ud)
    for t in ("chat_messages", "chat_sessions"):
        dst.execute(src.execute(
            "SELECT sql FROM sqlite_master WHERE name = ?", (t,)).fetchone()[0])
    km = [r[1] for r in src.execute("PRAGMA table_info(chat_messages)")]
    ks = [r[1] for r in src.execute("PRAGMA table_info(chat_sessions)")]
    for r in kand:
        s = r["session_id"]
        row = src.execute("SELECT * FROM chat_sessions WHERE session_id = ?", (s,)).fetchone()
        if row is None:
            continue
        dst.execute(f"INSERT INTO chat_sessions ({','.join(ks)}) "
                    f"VALUES ({','.join('?' * len(ks))})", tuple(row))
        for m in src.execute("SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id", (s,)):
            dst.execute(f"INSERT INTO chat_messages ({','.join(km)}) "
                        f"VALUES ({','.join('?' * len(km))})", tuple(m))
    dst.commit()
    dst.close()
    return ud


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--antal", type=int, default=5)
    ap.add_argument("--mindst", type=int, default=20)
    ap.add_argument("--hoejst", type=int, default=400)
    a = ap.parse_args()

    if not LIVE.exists():
        print(f"ingen database på {LIVE}", file=sys.stderr)
        return 2

    proeve = kopiér(a.antal, a.mindst, a.hoejst)
    import core.runtime.db_core as dbc
    dbc.DB_PATH = proeve

    from core.runtime.db import connect
    from core.services import ledger_canary as K
    from core.services import projection_chat_messages as C
    from core.services import projection_drift as D
    C.register()

    with connect() as c:
        sids = [r[0] for r in c.execute("SELECT DISTINCT session_id FROM chat_messages")]

    print(f"{'session':26} {'besk':>5} {'ledger':>7} {'enige':>6} {'genskabt':>8} {'byte-lig':>8}")
    alt_ok = bool(sids)
    for sid in sids:
        with connect() as c:
            raa = [dict(r) for r in c.execute(
                f"SELECT message_id, {KOL} FROM chat_messages WHERE session_id = ? "
                "AND role != 'compact_marker' ORDER BY id", (sid,))]

        # Den RIGTIGE vej: samme kald som en ægte overførsel ville bruge.
        # En prøve der går uden om produktionsvejen, prøver ikke den vej.
        k = K.enable_shadow(sid)
        r = D.compare(sid)

        # Den ægte prøve: riv rækkerne ud og byg dem af ledgeren alene.
        with connect() as c:
            c.execute("DELETE FROM chat_messages WHERE session_id = ? "
                      "AND role != 'compact_marker'", (sid,))
        C.rebuild(sid)
        with connect() as c:
            efter = [dict(x) for x in c.execute(
                f"SELECT message_id, {KOL} FROM chat_messages WHERE session_id = ? "
                "AND role != 'compact_marker' ORDER BY id", (sid,))]

        lige = efter == raa
        alt_ok = alt_ok and lige and r["enige"]
        print(f"{sid[:26]:26} {len(raa):5} {r['ledger_beskeder']:7} "
              f"{str(r['enige']):>6} {len(efter):8} {str(lige):>8}")
        if not lige:
            for x, y in zip(raa, efter):
                if x != y:
                    for k in x:
                        if x[k] != y[k]:
                            print(f"    FORSKEL {k!r}: {str(x[k])[:90]!r} vs {str(y[k])[:90]!r}")
                    break

    print()
    print("ALT GENSKABT BYTE-FOR-BYTE" if alt_ok else "DER ER FORSKELLE — ingen session må flyttes")
    try:
        os.remove(proeve)
        proeve.parent.rmdir()
    except Exception:
        pass
    return 0 if alt_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
