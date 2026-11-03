"""Measured, reversible hygiene for per-user ``MEMORY.md`` files.

This module never moves or deletes memory.  It provides three bounded pieces:

* durable section-selection telemetry, so "unused" can eventually be measured;
* a soft-cap that stops automatic writes while keeping candidates in the DB;
* a read-only audit projected to a report and the owner's durable inbox.

Actual archival must be a separately approved operation with a manifest.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from core.runtime.config import STATE_DIR
from core.runtime.db_core import connect
from core.memory.memory_md_writer import normalize_heading


SOFT_CAP_BYTES = 3_000_000
SOFT_CAP_SECTIONS = 2_000
MIN_USAGE_OBSERVATION_DAYS = 30
REPORT_DIR = STATE_DIR / "memory_hygiene"
logger = logging.getLogger(__name__)

_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_OPERATIONAL_HEADING_RE = re.compile(
    r"\b(målt|status|live|færdig|lukket|åben|fix(?:et)?|commit|deploy|kørsel)\b",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b20\d{2}-\d{2}-\d{2}\b|\b\d{1,2}[/.]\d{1,2}[./-]20\d{2}\b"
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _section_key(heading: str) -> str:
    normalized = " ".join(str(heading or "").casefold().split()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_section_usage (
            workspace TEXT NOT NULL,
            section_key TEXT NOT NULL,
            heading TEXT NOT NULL,
            first_selected_at TEXT NOT NULL,
            last_selected_at TEXT NOT NULL,
            selection_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (workspace, section_key)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_hygiene_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace TEXT NOT NULL,
            file_bytes INTEGER NOT NULL,
            section_count INTEGER NOT NULL,
            dated_sections INTEGER NOT NULL,
            undated_sections INTEGER NOT NULL,
            duplicate_groups INTEGER NOT NULL,
            operational_sections INTEGER NOT NULL,
            tracked_sections INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_hygiene_snapshots_workspace "
        "ON memory_hygiene_snapshots(workspace, id DESC)"
    )


def record_section_selections(
    workspace: str,
    headings: Iterable[str],
    *,
    selected_at: str | None = None,
) -> int:
    """Persist actual prompt selections; one transaction per prompt build."""
    workspace_n = str(workspace or "").strip()
    unique = {
        _section_key(heading): " ".join(str(heading).split()).strip()
        for heading in headings
        if str(heading or "").strip()
    }
    if not workspace_n or not unique:
        return 0
    now = str(selected_at or _now_iso())
    with connect() as conn:
        _ensure_tables(conn)
        for key, heading in unique.items():
            conn.execute(
                """
                INSERT INTO memory_section_usage (
                    workspace, section_key, heading, first_selected_at,
                    last_selected_at, selection_count
                ) VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(workspace, section_key) DO UPDATE SET
                    heading = excluded.heading,
                    last_selected_at = excluded.last_selected_at,
                    selection_count = memory_section_usage.selection_count + 1
                """,
                (workspace_n, key, heading, now, now),
            )
    return len(unique)


def auto_write_allowed(workspace: str, *, path: Path | None = None) -> bool:
    """Backpressure only: candidates remain proposed when the file is over cap."""
    memory_path = path or _workspace_memory_path(workspace)
    if not memory_path.exists():
        return True
    try:
        size = memory_path.stat().st_size
    except OSError as exc:
        logger.warning("memory hygiene could not stat %s: %s", memory_path, exc)
        return False
    if size >= SOFT_CAP_BYTES:
        return False
    section_count = 0
    try:
        handle = memory_path.open("r", encoding="utf-8")
    except OSError as exc:
        logger.warning("memory hygiene could not read %s: %s", memory_path, exc)
        return False
    with handle:
        for line in handle:
            if _H2_RE.match(line.rstrip("\r\n")):
                section_count += 1
                if section_count >= SOFT_CAP_SECTIONS:
                    return False
    return True


def _workspace_memory_path(workspace: str) -> Path:
    from core.runtime.config import WORKSPACES_DIR

    return WORKSPACES_DIR / str(workspace or "bjorn") / "MEMORY.md"


def _parse_h2_sections(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = _H2_RE.match(line.rstrip("\r\n"))
        if match:
            starts.append((index, match.group(1).strip()))
    sections: list[dict[str, Any]] = []
    for position, (start, heading) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        body = "".join(lines[start:end])
        sections.append(
            {
                "heading": heading,
                "line": start + 1,
                "bytes": len(body.encode("utf-8")),
                "has_date": bool(_DATE_RE.search(body)),
            }
        )
    return sections


def _normalize_heading(heading: str) -> str:
    return normalize_heading(heading)


def _usage_summary(workspace: str) -> dict[str, Any]:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            """
            SELECT COUNT(*) AS tracked, MIN(first_selected_at) AS first_at,
                   MAX(last_selected_at) AS last_at,
                   COALESCE(SUM(selection_count), 0) AS selections
            FROM memory_section_usage WHERE workspace = ?
            """,
            (workspace,),
        ).fetchone()
    return {
        "tracked_sections": int(row[0] or 0),
        "first_selected_at": str(row[1] or ""),
        "last_selected_at": str(row[2] or ""),
        "selection_count": int(row[3] or 0),
    }


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:  # temporary may already have been replaced or removed
            pass
        raise


def audit_workspace(
    workspace: str,
    *,
    path: Path | None = None,
    publish_inbox: bool = True,
) -> dict[str, Any]:
    """Create a read-only hygiene report.  Never moves or rewrites memory."""
    workspace_n = str(workspace or "").strip()
    memory_path = path or _workspace_memory_path(workspace_n)
    text = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
    sections = _parse_h2_sections(text)

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for section in sections:
        key = _normalize_heading(section["heading"])
        if key:
            groups[key].append(section)
    duplicates = [items for items in groups.values() if len(items) > 1]
    operational = [
        section for section in sections
        if _OPERATIONAL_HEADING_RE.search(str(section["heading"]))
    ]
    usage = _usage_summary(workspace_n)
    file_bytes = len(text.encode("utf-8"))
    breached = file_bytes >= SOFT_CAP_BYTES or len(sections) >= SOFT_CAP_SECTIONS
    report = {
        "workspace": workspace_n,
        "memory_path": str(memory_path),
        "created_at": _now_iso(),
        "file_bytes": file_bytes,
        "section_count": len(sections),
        "dated_sections": sum(1 for section in sections if section["has_date"]),
        "undated_sections": sum(1 for section in sections if not section["has_date"]),
        "duplicate_groups": len(duplicates),
        "duplicate_sections": sum(len(items) for items in duplicates),
        "operational_heading_count": len(operational),
        "soft_cap_breached": breached,
        "automatic_writes_allowed": not breached,
        "usage": usage,
        "move_ready": False,
        "move_blocked_reason": (
            "Durable section-use telemetry must observe at least "
            f"{MIN_USAGE_OBSERVATION_DAYS} days before unused sections can be claimed."
        ),
        "candidates": {
            "duplicate_groups": [
                [{"heading": item["heading"], "line": item["line"]} for item in group]
                for group in duplicates[:14]
            ],
            "operational_headings": [
                {"heading": item["heading"], "line": item["line"], "bytes": item["bytes"]}
                for item in operational[:14]
            ],
        },
        "policy": {
            "mutation": "none",
            "archive_requires_explicit_approval": True,
            "archive_destination": "memory/curated/",
            "manifest_required": True,
            "delete_allowed": False,
        },
    }

    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO memory_hygiene_snapshots (
                workspace, file_bytes, section_count, dated_sections,
                undated_sections, duplicate_groups, operational_sections,
                tracked_sections, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workspace_n, file_bytes, len(sections), report["dated_sections"],
                report["undated_sections"], len(duplicates), len(operational),
                usage["tracked_sections"], report["created_at"],
            ),
        )

    report_path = REPORT_DIR / f"{workspace_n}.json"
    report["report_path"] = str(report_path)
    _atomic_json(report_path, report)
    report["report_bytes"] = report_path.stat().st_size

    if publish_inbox and breached:
        report["inbox"] = _publish_inbox(workspace_n, report)
    return report


def _publish_inbox(workspace: str, report: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.services.inbox_state import bruger_for_workspace, registrer_kilde

        user_id = bruger_for_workspace(workspace)
        if not user_id:
            return {"status": "skipped", "reason": "workspace has no inbox user"}
        description = (
            f"MEMORY.md har {report['file_bytes']:,} bytes og "
            f"{report['section_count']} topsektioner. Audit fandt "
            f"{report['duplicate_groups']} dubletgrupper og "
            f"{report['operational_heading_count']} driftsprægede overskrifter. "
            "Ingen minder er flyttet eller slettet. Automatiske MEMORY.md-skrivninger "
            "er sat under backpressure; kandidater bevares i DB. Brugstelemetri samles "
            f"før en flytteplan kan godkendes. Rapport: {report['report_path']}"
        )
        return registrer_kilde(
            bruger_id=user_id,
            kildetype="proposal",
            kilde_id=f"memory-hygiene:{workspace}",
            paastaaet_ejer="huset",
            beskrivelse=description,
            output_sti=str(report["report_path"]),
            output_bytes=int(report.get("report_bytes") or 0),
            importance="high",
        )
    except Exception as exc:
        logger.warning("memory hygiene inbox projection failed for %s: %s", workspace, exc)
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
