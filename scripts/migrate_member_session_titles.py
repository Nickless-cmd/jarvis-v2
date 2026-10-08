"""Encrypt existing member chat titles without printing private text."""
from __future__ import annotations

import argparse

from core.runtime.db import connect
from core.services import chat_crypto


def migrate(*, dry_run: bool = True, batch_size: int = 100) -> dict[str, int]:
    counts = {"encrypted": 0, "already_encrypted": 0, "unknown": 0, "placeholder": 0}
    cursor = 0
    while True:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id, session_id, title FROM chat_sessions WHERE id>? "
                "ORDER BY id LIMIT ?", (cursor, max(1, min(batch_size, 500))),
            ).fetchall()
            if not rows:
                break
            for row in rows:
                cursor = int(row[0])
                sid, title = str(row[1]), str(row[2] or "")
                if chat_crypto.er_krypteret(title):
                    counts["already_encrypted"] += 1
                    continue
                member = chat_crypto.medlem_for_session(sid, conn=conn)
                if not member:
                    counts["unknown"] += 1
                    continue
                if title in {"", "New chat", "Ny samtale"}:
                    counts["placeholder"] += 1
                    continue
                if not dry_run:
                    conn.execute("UPDATE chat_sessions SET title=? WHERE id=?",
                                 (chat_crypto.krypter(title, member), cursor))
                counts["encrypted"] += 1
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report counts only")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    print(migrate(dry_run=args.dry_run, batch_size=args.batch_size))
