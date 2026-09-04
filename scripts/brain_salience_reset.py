"""One-off: cap runaway salience_bumps in Jarvis' brain (memory repair 2026-09-04, R1).

Before the importance cap in ``search_brain`` and the once-per-day bump rule,
auto-inject bumped the same entries every turn: the top entry reached 17.794
bumps and 11 entries were above 1.000. Those numbers would still dominate the
``log2(1+bumps)`` term for years, so they are capped once.

The markdown file is the source of truth; the index is updated in the same
pass. Dry-run by default.

Usage:
    python scripts/brain_salience_reset.py            # dry-run, prints what would change
    python scripts/brain_salience_reset.py --apply    # rewrite files + index
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone


def reset_salience_bumps(*, cap: int = 20, apply: bool = True) -> int:
    """Cap ``salience_bumps`` at ``cap`` for every entry above it.

    Returns the number of entries changed (or that would change in dry-run).
    """
    from core.services import jarvis_brain

    conn = jarvis_brain.connect_index()
    try:
        rows = conn.execute(
            "SELECT id, salience_bumps FROM brain_index WHERE salience_bumps > ?",
            (int(cap),),
        ).fetchall()
    finally:
        conn.close()

    changed = 0
    now = datetime.now(timezone.utc)
    for entry_id, bumps in rows:
        changed += 1
        if not apply:
            print(f"would cap {entry_id}: {bumps} -> {cap}")
            continue
        entry = jarvis_brain.read_entry(entry_id)
        entry.salience_bumps = int(cap)
        entry.updated_at = now
        md = jarvis_brain.render_entry_markdown(entry)
        fpath = jarvis_brain._workspace_root() / jarvis_brain._index_path_for(entry_id)
        jarvis_brain._atomic_write(fpath, md)
        fhash = jarvis_brain._file_hash(md)
        conn = jarvis_brain.connect_index()
        try:
            conn.execute(
                "UPDATE brain_index SET salience_bumps = ?, updated_at = ?, "
                "file_hash = ?, indexed_at = ? WHERE id = ?",
                (int(cap), jarvis_brain._iso(now), fhash, jarvis_brain._iso(now), entry_id),
            )
            conn.commit()
        finally:
            conn.close()
        print(f"capped {entry_id}: {bumps} -> {cap}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cap", type=int, default=20)
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = parser.parse_args()
    n = reset_salience_bumps(cap=args.cap, apply=args.apply)
    print(f"{'changed' if args.apply else 'would change'}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
