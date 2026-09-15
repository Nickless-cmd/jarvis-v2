"""Engangs-oprydning: luk flows hvis opgave allerede er afsluttet.

## Hvorfor (15/9-2026)

4.969 flows stod som `queued`. 4.872 hoerte til opgaver der var `succeeded`,
93 til opgaver der blev skyllet ud i haanden 17/4 (`expired`). Opgaven blev
afsluttet; flowet fulgte aldrig med, for intet i koden satte et flow til
faerdigt. Rettet ved kilden i `runtime_tasks.update_task` — dette script rydder
det der allerede ligger.

## Hvad det goer

Kun flows i `queued`/`running`/`blocked` hvis opgave er afsluttet. Udfaldet
foelger opgaven; `expired` bliver `cancelled`, fordi flows ikke har den status.
Flows hvis opgave stadig er aaben, roeres ikke.

## Testdata i drift-databasen

15/5-2026 kl. 11:09–11:25 skrev en testkoersel 32 opgaver i den RIGTIGE
database (foer skjoldet i tests/conftest.py fandtes): ejer `test`, typer som
`some-other-kind`, maal som «x» og testens egne curriculum-tekster. 13 af dem
stod stadig aabne. De annulleres her; de afsluttede bliver staaende som historik.

Toerkoersel som standard. `--anvend` skriver en backup af de gamle tilstande
til ~/.jarvis-v2/state/backups/ FOER opdateringen, og opdaterer i én
transaktion.

    python scripts/luk_foraeldede_flows.py            # vis hvad der ville ske
    python scripts/luk_foraeldede_flows.py --anvend   # goer det
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

#: opgavens status -> flowets nye status
UDFALD = {"succeeded": "succeeded", "failed": "failed",
          "cancelled": "cancelled", "expired": "cancelled"}
AABNE_FLOWS = ("queued", "running", "blocked")

#: Vinduet hvor en testkoersel skrev i drift-DB'en. Kun AABNE opgaver herfra.
TESTDATA_VINDUE = ("2026-05-15T11:09:00", "2026-05-15T11:25:00")
AABNE_OPGAVER = ("queued", "running", "blocked")


def find_testdata(conn) -> list[dict[str, str]]:
    raekker = conn.execute(
        f"""
        SELECT task_id, status, kind, goal FROM runtime_tasks
        WHERE created_at >= ? AND created_at < ?
          AND status IN ({",".join("?" * len(AABNE_OPGAVER))})
        """,
        (*TESTDATA_VINDUE, *AABNE_OPGAVER),
    ).fetchall()
    return [{"task_id": r[0], "status": r[1], "kind": r[2], "goal": (r[3] or "")[:80]}
            for r in raekker]


def annuller_testdata(conn, testdata: list[dict[str, str]]) -> int:
    nu = datetime.now(UTC).isoformat()
    for t in testdata:
        conn.execute(
            "UPDATE runtime_tasks SET status = 'cancelled', updated_at = ?, "
            "result_summary = 'annulleret: testdata skrevet i drift-DB 15/5-2026' "
            "WHERE task_id = ? AND status = ?",
            (nu, t["task_id"], t["status"]),
        )
    return len(testdata)


def find_foraeldede(conn) -> list[dict[str, str]]:
    raekker = conn.execute(
        f"""
        SELECT f.flow_id, f.status, f.step_state, t.status
        FROM runtime_flows f JOIN runtime_tasks t ON t.task_id = f.task_id
        WHERE f.status IN ({",".join("?" * len(AABNE_FLOWS))})
          AND t.status IN ({",".join("?" * len(UDFALD))})
        """,
        (*AABNE_FLOWS, *UDFALD),
    ).fetchall()
    return [{"flow_id": r[0], "status": r[1], "step_state": r[2] or "",
             "opgave_status": r[3], "ny_status": UDFALD[r[3]]} for r in raekker]


def luk(conn, foraeldede: list[dict[str, str]]) -> int:
    nu = datetime.now(UTC).isoformat()
    conn.execute("BEGIN")
    try:
        for f in foraeldede:
            conn.execute(
                "UPDATE runtime_flows SET status = ?, step_state = 'done', updated_at = ? "
                "WHERE flow_id = ? AND status = ?",
                (f["ny_status"], nu, f["flow_id"], f["status"]),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return len(foraeldede)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anvend", action="store_true", help="skriv backup og opdater")
    args = ap.parse_args(argv)

    import sqlite3

    from core.runtime.config import STATE_DIR
    from core.runtime.db_core import DB_PATH

    conn = sqlite3.connect(str(DB_PATH), isolation_level=None)
    try:
        testdata = find_testdata(conn)
        print(f"{len(testdata)} aaben(e) opgave(r) fra testdata-vinduet 15/5:")
        for t in testdata:
            print(f"  {t['status']:<8} {t['kind']:<22} {t['goal']}")
        foraeldede = find_foraeldede(conn)
        pr: dict[str, int] = {}
        for f in foraeldede:
            noegle = f"{f['status']} -> {f['ny_status']} (opgave {f['opgave_status']})"
            pr[noegle] = pr.get(noegle, 0) + 1
        print(f"{len(foraeldede)} flow(s) med afsluttet opgave:")
        for noegle, n in sorted(pr.items(), key=lambda kv: -kv[1]):
            print(f"  {n:>6}  {noegle}")
        if not args.anvend:
            print("Toerkoersel — intet aendret. Brug --anvend.")
            return 0
        backup_dir = Path(STATE_DIR) / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"runtime_flows-foer-lukning-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
        backup.write_text(json.dumps({"opgaver": testdata, "flows": foraeldede},
                                     ensure_ascii=False), encoding="utf-8")
        print(f"Backup: {backup}")
        conn.execute("BEGIN")
        try:
            print(f"Annulleret testdata: {annuller_testdata(conn, testdata)}")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        # Testdataens flows hoerer nu til afsluttede opgaver — find dem igen.
        print(f"Lukket: {luk(conn, find_foraeldede(conn))}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
