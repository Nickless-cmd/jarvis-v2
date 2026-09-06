"""One-off data cleanup after the memory repair (2026-09-04, Task 8).

Dry-run by default: prints what WOULD change. ``--apply`` requires
``--backup-dir`` and takes a consistent SQLite backup of jarvis.db plus a copy
of the owner's MEMORY.md before touching anything.

Steps (in order):
  brain-salience         cap salience_bumps at 20 (11 entries were >1000, top 17.794)
  policies-dedupe        one generalized_policies row per specific_rule_key (26.997 → 8)
  experiential-empty     delete cognitive_experiential_memories without key_lesson
  partner-facts          delete told-by-jarvis facts from autonomous sessions / older than 30 d
  embeddings-released    delete memory_embeddings for released/archived private_brain rows
  retained-templates     delete private_retained_memory_records + promotion decisions without substance
  md-proposals-stale     runtime_memory_md_update_proposals fresh > 7 d → stale
  fts-rebuild            (re)build FTS5 tables over session_summaries + chat_messages
  memory-md-dedupe       merge duplicate `## ` headings in the owner's MEMORY.md

Usage:
    python scripts/memory_noise_cleanup.py                      # dry-run, all steps
    python scripts/memory_noise_cleanup.py --only policies-dedupe
    python scripts/memory_noise_cleanup.py --apply --backup-dir ~/.jarvis-v2/backups/memory-repair
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from core.runtime.db import connect

STEPS: list[str] = [
    "brain-salience", "policies-dedupe", "experiential-empty", "partner-facts",
    "embeddings-released", "retained-templates", "md-proposals-stale", "fts-rebuild",
    "memory-md-dedupe",
]

_AUTONOMOUS_LIKE = ("auto-%", "autonomous-%", "auto_%", "heartbeat%", "dream%", "wakeup%")


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


# ── steps ───────────────────────────────────────────────────────────────


def step_brain_salience(apply: bool) -> dict[str, Any]:
    from scripts.brain_salience_reset import reset_salience_bumps
    n = reset_salience_bumps(cap=20, apply=apply)
    return {"would_change" if not apply else "changed": n}


def step_policies_dedupe(apply: bool) -> dict[str, Any]:
    with connect() as conn:
        if not _table_exists(conn, "generalized_policies"):
            return {"skipped": "no table"}
        total = conn.execute("SELECT count(*) FROM generalized_policies").fetchone()[0]
        keys = conn.execute("SELECT count(DISTINCT specific_rule_key) FROM generalized_policies").fetchone()[0]
        out = {"rows": int(total), "distinct_keys": int(keys), "would_delete": int(total) - int(keys)}
        if not apply or out["would_delete"] <= 0:
            return out
        # survivor = newest row per key; it inherits the summed match_count + duplicates
        rows = conn.execute(
            "SELECT specific_rule_key, MAX(updated_at) AS u, COUNT(*) AS c, SUM(match_count) AS m "
            "FROM generalized_policies GROUP BY specific_rule_key"
        ).fetchall()
        deleted = 0
        for key, newest, count, matches in rows:
            survivor = conn.execute(
                "SELECT policy_id FROM generalized_policies WHERE specific_rule_key=? AND updated_at=? LIMIT 1",
                (key, newest),
            ).fetchone()[0]
            cur = conn.execute(
                "DELETE FROM generalized_policies WHERE specific_rule_key=? AND policy_id != ?", (key, survivor)
            )
            deleted += cur.rowcount
            conn.execute(
                "UPDATE generalized_policies SET match_count = ? WHERE policy_id = ?",
                (int(matches or 0) + int(count) - 1, survivor),
            )
        conn.commit()
        out["deleted"] = deleted
        return out


def step_experiential_empty(apply: bool) -> dict[str, Any]:
    with connect() as conn:
        if not _table_exists(conn, "cognitive_experiential_memories"):
            return {"skipped": "no table"}
        n = conn.execute(
            "SELECT count(*) FROM cognitive_experiential_memories WHERE key_lesson IS NULL OR key_lesson = ''"
        ).fetchone()[0]
        out = {"would_delete": int(n)}
        if apply and n:
            conn.execute("DELETE FROM cognitive_experiential_memories WHERE key_lesson IS NULL OR key_lesson = ''")
            conn.commit()
            out["deleted"] = int(n)
        return out


def step_partner_facts(apply: bool) -> dict[str, Any]:
    cutoff = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    where = (
        "origin = 'told-by-jarvis' AND (" + " OR ".join("session_id LIKE ?" for _ in _AUTONOMOUS_LIKE)
        + " OR last_at < ?)"
    )
    params: list[Any] = [*_AUTONOMOUS_LIKE, cutoff]
    with connect() as conn:
        if not _table_exists(conn, "partner_knowledge_facts"):
            return {"skipped": "no table"}
        n = conn.execute(f"SELECT count(*) FROM partner_knowledge_facts WHERE {where}", params).fetchone()[0]
        out = {"would_delete": int(n)}
        if apply and n:
            conn.execute(f"DELETE FROM partner_knowledge_facts WHERE {where}", params)
            conn.commit()
            out["deleted"] = int(n)
        return out


def step_embeddings_released(apply: bool) -> dict[str, Any]:
    sql_where = (
        "source_table = 'private_brain_records' AND source_id IN ("
        "SELECT record_id FROM private_brain_records WHERE status IN ('released','archived','superseded','deleted'))"
    )
    with connect() as conn:
        if not (_table_exists(conn, "memory_embeddings") and _table_exists(conn, "private_brain_records")):
            return {"skipped": "no table"}
        n = conn.execute(f"SELECT count(*) FROM memory_embeddings WHERE {sql_where}").fetchone()[0]
        out = {"would_delete": int(n)}
        if apply and n:
            conn.execute(f"DELETE FROM memory_embeddings WHERE {sql_where}")
            conn.commit()
            out["deleted"] = int(n)
        return out


def step_retained_templates(apply: bool) -> dict[str, Any]:
    from core.memory.promotion_substance import has_substance
    out: dict[str, Any] = {}
    with connect() as conn:
        for table, col, idcol in (
            ("private_retained_memory_records", "retained_value", "id"),
            ("private_promotion_decisions", "promotion_target", "id"),
        ):
            if not _table_exists(conn, table):
                out[table] = "skipped"
                continue
            rows = conn.execute(f"SELECT {idcol}, {col} FROM {table}").fetchall()
            doomed = [r[0] for r in rows if not has_substance(str(r[1] or ""))]
            out[table] = {"rows": len(rows), "would_delete": len(doomed)}
            if apply and doomed:
                conn.executemany(f"DELETE FROM {table} WHERE {idcol} = ?", [(d,) for d in doomed])
                conn.commit()
                out[table]["deleted"] = len(doomed)
    return out


def step_md_proposals_stale(apply: bool) -> dict[str, Any]:
    cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    with connect() as conn:
        if not _table_exists(conn, "runtime_memory_md_update_proposals"):
            return {"skipped": "no table"}
        n = conn.execute(
            "SELECT count(*) FROM runtime_memory_md_update_proposals WHERE status='fresh' AND created_at < ?",
            (cutoff,),
        ).fetchone()[0]
        out = {"would_mark_stale": int(n)}
        if apply and n:
            conn.execute(
                "UPDATE runtime_memory_md_update_proposals SET status='stale', updated_at=?, "
                "status_reason='Marked stale by memory_noise_cleanup (fresh > 7 days).' "
                "WHERE status='fresh' AND created_at < ?",
                (datetime.now(UTC).isoformat(), cutoff),
            )
            conn.commit()
            out["marked_stale"] = int(n)
        return out


def step_fts_rebuild(apply: bool) -> dict[str, Any]:
    if not apply:
        return {"would_rebuild": ["session_summaries_fts", "chat_messages_fts"]}
    from core.runtime.db_fts import rebuild_fts
    return {"rebuilt": rebuild_fts()}


def step_memory_md_dedupe(apply: bool) -> dict[str, Any]:
    from core.runtime.workspace_paths import workspace_dir_or_owner
    from scripts.memory_md_dedupe_headings import dedupe_file
    path = workspace_dir_or_owner() / "MEMORY.md"
    if not path.exists():
        return {"skipped": f"missing {path}"}
    merged = dedupe_file(path, apply=apply)
    return {"path": str(path), "merged" if apply else "would_merge": merged}


STEP_FUNCS: dict[str, Callable[[bool], dict[str, Any]]] = {
    "brain-salience": step_brain_salience,
    "policies-dedupe": step_policies_dedupe,
    "experiential-empty": step_experiential_empty,
    "partner-facts": step_partner_facts,
    "embeddings-released": step_embeddings_released,
    "retained-templates": step_retained_templates,
    "md-proposals-stale": step_md_proposals_stale,
    "fts-rebuild": step_fts_rebuild,
    "memory-md-dedupe": step_memory_md_dedupe,
}


# ── backup + driver ─────────────────────────────────────────────────────


def backup(backup_dir: Path) -> dict[str, str]:
    """Consistent SQLite backup (sqlite3 backup API, safe with WAL) + MEMORY.md copy."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out: dict[str, str] = {}
    db_target = backup_dir / f"jarvis.db.bak-{stamp}"
    with connect() as src:
        dst = sqlite3.connect(db_target)
        try:
            src.backup(dst)
        finally:
            dst.close()
    out["jarvis.db"] = str(db_target)
    try:
        from core.runtime.workspace_paths import workspace_dir_or_owner
        md = workspace_dir_or_owner() / "MEMORY.md"
        if md.exists():
            target = backup_dir / f"MEMORY.md.bak-{stamp}"
            shutil.copy2(md, target)
            out["MEMORY.md"] = str(target)
    except Exception as exc:
        out["MEMORY.md"] = f"skipped: {exc}"
    return out


def run(*, apply: bool, only: list[str] | None = None, backup_dir: Path | None = None) -> dict[str, Any]:
    steps = [s for s in STEPS if not only or s in only]
    report: dict[str, Any] = {"apply": apply, "steps": {}}
    if apply:
        if backup_dir is None:
            raise SystemExit("--apply requires --backup-dir")
        report["backup"] = backup(backup_dir)
    for name in steps:
        try:
            report["steps"][name] = STEP_FUNCS[name](apply)
        except Exception as exc:
            report["steps"][name] = {"error": str(exc)[:200]}
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--only", action="append", choices=STEPS)
    args = parser.parse_args(argv)
    report = run(apply=args.apply, only=args.only, backup_dir=args.backup_dir)
    import json
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
