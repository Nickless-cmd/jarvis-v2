#!/usr/bin/env python3
"""Compare the live SQLite schema with its reviewed, per-table snapshot.

Read-only and never used in the runtime request path. Timestamp formats are
observations of stored created_at values, not claims about all future writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path.home() / ".jarvis-v2/state/jarvis.db"
DEFAULT_SNAPSHOT = ROOT / "docs/persistens/sqlite-schema.json"


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def timestamp_format(value: object) -> str:
    if value is None:
        return "unobserved"
    text = str(value)
    if re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", text):
        return "sqlite_utc_seconds"
    if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+00:00", text):
        return "iso_utc_offset"
    if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", text):
        return "iso_utc_z"
    if isinstance(value, (int, float)):
        return "unix_epoch"
    return "unknown"


def _timestamp_formats(conn: sqlite3.Connection, table: str) -> list[str]:
    quoted = _quote(table)
    # First and last stored values catch a writer changing its format while
    # keeping the scan bounded. Empty tables remain explicitly unobserved.
    values = []
    for direction in ("ASC", "DESC"):
        try:
            rows = conn.execute(
                f"SELECT created_at FROM {quoted} WHERE created_at IS NOT NULL "
                f"ORDER BY rowid {direction} LIMIT 3"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute(
                f"SELECT created_at FROM {quoted} WHERE created_at IS NOT NULL LIMIT 3"
            ).fetchall()  # WITHOUT ROWID table
        values.extend(row[0] for row in rows)
    return sorted({timestamp_format(value) for value in values}) or ["unobserved"]


def inventory(conn: sqlite3.Connection) -> dict[str, object]:
    tables: dict[str, object] = {}
    names = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    for name in names:
        cols = [
            {"name": row[1], "type": row[2], "nullable": not bool(row[3]),
             "default": row[4], "pk": row[5], "hidden": row[6]}
            for row in conn.execute(f"PRAGMA table_xinfo({_quote(name)})")
        ]
        cols.sort(key=lambda item: item["name"])
        indexes = []
        for idx in conn.execute(f"PRAGMA index_list({_quote(name)})"):
            definition = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (idx[1],)
            ).fetchone()
            parts = [
                {"column": part[2], "descending": bool(part[3]), "key": bool(part[5])}
                for part in conn.execute(f"PRAGMA index_xinfo({_quote(idx[1])})")
            ]
            indexes.append({"name": idx[1], "unique": bool(idx[2]),
                            "origin": idx[3], "partial": bool(idx[4]), "parts": parts,
                            "sql": " ".join(definition[0].split()) if definition and definition[0] else None})
        indexes.sort(key=lambda item: item["name"])
        schema = {"columns": cols, "indexes": indexes}
        canonical = json.dumps(schema, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        hexdigest = hashlib.sha256(canonical.encode()).hexdigest()
        tables[name] = {
            "digest": ":".join(hexdigest[i:i + 2] for i in range(0, len(hexdigest), 2)),
            "schema": schema,
            "created_at_formats": _timestamp_formats(conn, name)
            if any(col["name"] == "created_at" for col in cols) else [],
        }
    return {"version": 1, "tables": tables}


def compare(current: dict, expected: dict) -> list[str]:
    actual_tables = current["tables"]
    saved_tables = expected.get("tables", {})
    issues = []
    for name in sorted(actual_tables.keys() | saved_tables.keys()):
        if name not in saved_tables:
            issues.append(f"NEW {name}")
        elif name not in actual_tables:
            issues.append(f"MISSING {name}")
        else:
            for field in ("digest", "created_at_formats"):
                if actual_tables[name][field] != saved_tables[name].get(field):
                    issues.append(f"CHANGED {name}.{field}: "
                                  f"{saved_tables[name].get(field)} -> {actual_tables[name][field]}")
    return issues


def _forklar(issues: list[str], snapshot: Path) -> None:
    """Sig hvad der skal ske. En vagt der kun siger NEJ er en blokade.

    Den der bliver stoppet her er som regel Jarvis, midt i noget andet. Uden
    en vej videre er valget mellem at gaette og at give op — og begge dele er
    vaerre end det skema-drift koster.
    """
    tid = [i for i in issues if "created_at_formats" in i]
    nye = [i for i in issues if i.startswith("NEW ")]
    vaek = [i for i in issues if i.startswith("MISSING ")]

    print("\n── Skemaet er ikke det samme som det gennemgaaede. Saadan kommer du videre ──")
    print("\n1. LAES listen ovenfor. Hver linje er én forskel, ikke en fejl.")
    if nye:
        print(f"   NEW ({len(nye)}): tabeller der findes nu og ikke stod i snapshottet.")
    if vaek:
        print(f"   MISSING ({len(vaek)}): tabeller der ER VAEK. Det er den alvorlige.")
        print("   Er en tabel forsvundet uden at du fjernede den, saa STOP og find ud af hvorfor.")
    if tid:
        print(f"   created_at_formats ({len(tid)}): en skriver har skiftet TIDSFORMAT.")
        print("   Det er den dyre. To tabeller med hvert sit format kostede fire")
        print("   forkerte maalinger paa ét doegn — hver gang med et troværdigt tal")
        print("   som resultat (0 % eller 100 %), aldrig en fejl. Find skriveren.")

    print("\n2. VAR DET DIG?")
    print("   JA  — du aendrede et skema med vilje: opdater snapshottet og")
    print("         forklar HVORFOR i commit-beskeden:")
    print(f"           /opt/conda/envs/ai/bin/python scripts/verify_sqlite_schema.py --write-snapshot")
    print(f"           git add -- {snapshot}")
    print("   NEJ — saa har noget ANDET aendret skemaet. Det er praecis hvad")
    print("         vagten findes for. Find ud af hvad foer du opdaterer")
    print("         snapshottet; et blindt --write-snapshot goer vagten til pynt.")

    print("\n3. Har du travlt og er forskellen harmloes, saa opdatér snapshottet")
    print("   og SKRIV I COMMIT-BESKEDEN at du ikke naaede at undersoege den.")
    print("   En noteret usikkerhed kan nogen finde senere. En tavs kan ingen.")
    print("\nVagten koerer KUN paa CT105 (--only-host). Skemaet dér er det rigtige.\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--write-snapshot", action="store_true")
    parser.add_argument("--require-db", action="store_true",
                        help="fail when the runtime DB is unavailable (for explicit audits)")
    parser.add_argument("--only-host", help="skip unless this is the snapshot's runtime host")
    args = parser.parse_args(argv)
    if args.only_host and socket.gethostname().lower() != args.only_host.lower():
        print(f"verify-sqlite-schema: skipped on {socket.gethostname()}; "
              f"runtime host is {args.only_host}")
        return 0
    if not args.db.is_file():
        print(f"verify-sqlite-schema: DB missing: {args.db}")
        return 2 if args.require_db or args.write_snapshot else 0
    try:
        uri = args.db.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            conn.execute("BEGIN")  # one consistent schema/data view despite concurrent writers
            current = inventory(conn)
    except sqlite3.Error as exc:
        print(f"verify-sqlite-schema: cannot inspect DB: {exc}")
        return 2
    if args.write_snapshot:
        current["source_host"] = socket.gethostname()
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
        print(f"verify-sqlite-schema: wrote {len(current['tables'])} tables")
        return 0
    try:
        expected = json.loads(args.snapshot.read_text())
    except (OSError, ValueError) as exc:
        print(f"verify-sqlite-schema: cannot read snapshot: {exc}")
        return 2
    if args.only_host and str(expected.get("source_host", "")).lower() != args.only_host.lower():
        print(f"verify-sqlite-schema: snapshot source is not {args.only_host}")
        return 2
    issues = compare(current, expected)
    for issue in issues:
        print(issue)
    print(f"verify-sqlite-schema: {len(current['tables'])} tables, {len(issues)} differences")
    if issues:
        _forklar(issues, args.snapshot)
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
