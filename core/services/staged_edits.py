"""Staged edits — compose multi-file changes, review, then commit atomically.

Background:
    Today edit_file / write_file write to disk immediately. That's the
    "type-and-pray" feel. For real refactoring (touch 5 files, related
    changes), Jarvis would benefit from a stage-then-commit primitive:

      stage_edit_file(...)         ← repeated for each file
      stage_edit_file(...)
      list_staged_edits()          ← review unified diff for the batch
      commit_staged_edits()        ← atomic apply (rolls back on failure)
            — or —
      discard_staged_edits()       ← throw the batch away

    This is the "diff-stage before apply" feature from the JarvisX
    wishlist. Same mental model as `git add` + `git commit` but for
    Jarvis's tool calls.

Storage:
    Per-session JSON file at:
      ~/.jarvis-v2/state/staged_edits/{session_id}.json
    Falls back to a "_default" session if none is bound on the request.

Atomicity:
    On commit, edits are applied in stage order. On the first failure
    we attempt to roll back already-applied files using their stored
    old_content. We don't try to be clever about deletions — if a
    rollback can't restore (file system error, permissions), we leave
    the partial state and surface a clear error.
"""
from __future__ import annotations

import difflib
import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from core.runtime.config import STATE_DIR

logger = logging.getLogger(__name__)

_STAGED_DIR = Path(STATE_DIR) / "staged_edits"
_LOCK = threading.Lock()


@dataclass
class StagedEdit:
    stage_id: str
    kind: str  # "edit_file" | "write_file"
    path: str  # absolute path
    old_content: str  # content as read from disk at stage time
    new_content: str  # content that would be written on commit
    diff: str  # pre-computed unified diff for display
    staged_at: str
    note: str = ""  # optional human-readable note from the staging caller
    file_existed: bool = True  # for write_file when creating new file

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StagedEdit:
        return cls(
            stage_id=str(d.get("stage_id") or ""),
            kind=str(d.get("kind") or "edit_file"),
            path=str(d.get("path") or ""),
            old_content=str(d.get("old_content") or ""),
            new_content=str(d.get("new_content") or ""),
            diff=str(d.get("diff") or ""),
            staged_at=str(d.get("staged_at") or _now_iso()),
            note=str(d.get("note") or ""),
            file_existed=bool(d.get("file_existed", True)),
        )


@dataclass
class StagedBatch:
    """All staged edits for a single session (the unit of commit/discard)."""
    session_id: str
    edits: list[StagedEdit] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "edits": [e.to_dict() for e in self.edits],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StagedBatch:
        return cls(
            session_id=str(d.get("session_id") or ""),
            edits=[StagedEdit.from_dict(e) for e in (d.get("edits") or [])],
            created_at=str(d.get("created_at") or _now_iso()),
            updated_at=str(d.get("updated_at") or _now_iso()),
        )


# ── Internals ─────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _path_for(session_id: str) -> Path:
    sid = (session_id or "_default").strip().replace("/", "_") or "_default"
    return _STAGED_DIR / f"{sid}.json"


def _load(session_id: str) -> StagedBatch:
    p = _path_for(session_id)
    if not p.exists():
        return StagedBatch(session_id=session_id, created_at=_now_iso(), updated_at=_now_iso())
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return StagedBatch.from_dict(data)
    except Exception as exc:
        logger.warning("staged_edits: load failed for %s: %s", session_id, exc)
        return StagedBatch(session_id=session_id, created_at=_now_iso(), updated_at=_now_iso())


def _save(batch: StagedBatch) -> None:
    _STAGED_DIR.mkdir(parents=True, exist_ok=True)
    batch.updated_at = _now_iso()
    p = _path_for(batch.session_id)
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(batch.to_dict(), fh, indent=2, ensure_ascii=False)
    tmp.replace(p)


def _make_diff(path: str, old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
    )


# ── Public API ────────────────────────────────────────────────────


def stage_edit(
    *,
    session_id: str,
    path: str,
    old_text: str,
    new_text: str,
    replace_all: bool = False,
    note: str = "",
) -> dict[str, Any]:
    """Stage an edit_file-style change without writing to disk.

    Same matching semantics as edit_file: old_text must appear in the
    file; if it appears multiple times, replace_all must be true. Returns
    a stage_id you can later commit or discard.
    """
    target = Path(path).expanduser().resolve()
    if not target.exists():
        return {"status": "error", "error": f"file not found: {path}"}
    if not target.is_file():
        return {"status": "error", "error": f"not a file: {path}"}

    try:
        old_content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"status": "error", "error": f"read failed: {exc}"}

    if old_text not in old_content:
        return {"status": "error", "error": "old_text not found in file"}
    count = old_content.count(old_text)
    if count > 1 and not replace_all:
        return {
            "status": "error",
            "error": f"old_text matches {count} locations — be more specific or pass replace_all=true",
            "match_count": count,
        }

    new_content = old_content.replace(old_text, new_text, -1 if replace_all else 1)
    return _persist_edit(
        session_id=session_id,
        kind="edit_file",
        path=str(target),
        old_content=old_content,
        new_content=new_content,
        note=note,
        file_existed=True,
    )


def stage_write(
    *,
    session_id: str,
    path: str,
    content: str,
    note: str = "",
) -> dict[str, Any]:
    """Stage a write_file-style overwrite/create. If the target exists,
    its current content is recorded so commit can show a meaningful diff
    and rollback can restore it."""
    target = Path(path).expanduser().resolve()
    file_existed = target.is_file()
    old_content = ""
    if file_existed:
        try:
            old_content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return {"status": "error", "error": f"read failed: {exc}"}
    return _persist_edit(
        session_id=session_id,
        kind="write_file",
        path=str(target),
        old_content=old_content,
        new_content=str(content),
        note=note,
        file_existed=file_existed,
    )


def _persist_edit(
    *,
    session_id: str,
    kind: str,
    path: str,
    old_content: str,
    new_content: str,
    note: str,
    file_existed: bool,
) -> dict[str, Any]:
    if old_content == new_content:
        return {
            "status": "noop",
            "message": "no change — old_content == new_content",
            "path": path,
        }
    diff = _make_diff(path, old_content, new_content)
    edit = StagedEdit(
        stage_id=f"stage-{uuid.uuid4().hex[:12]}",
        kind=kind,
        path=path,
        old_content=old_content,
        new_content=new_content,
        diff=diff,
        staged_at=_now_iso(),
        note=note,
        file_existed=file_existed,
    )
    with _LOCK:
        batch = _load(session_id)
        batch.edits.append(edit)
        _save(batch)
    # Compact diff stats for the response
    additions = sum(1 for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    deletions = sum(1 for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---"))
    return {
        "status": "staged",
        "stage_id": edit.stage_id,
        "kind": kind,
        "path": path,
        "additions": additions,
        "deletions": deletions,
        "session_id": session_id,
    }


def list_staged(session_id: str, *, full_diffs: bool = False) -> dict[str, Any]:
    """Return all staged edits for the session.

    With full_diffs=False (default), each edit returns metadata + diff
    stats only, so we don't blow context on large refactors. The UI
    fetches full diffs separately via the /api endpoint.
    """
    with _LOCK:
        batch = _load(session_id)
    items = []
    for e in batch.edits:
        additions = sum(
            1 for ln in e.diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")
        )
        deletions = sum(
            1 for ln in e.diff.splitlines() if ln.startswith("-") and not ln.startswith("---")
        )
        item: dict[str, Any] = {
            "stage_id": e.stage_id,
            "kind": e.kind,
            "path": e.path,
            "staged_at": e.staged_at,
            "additions": additions,
            "deletions": deletions,
            "file_existed": e.file_existed,
            "note": e.note,
        }
        if full_diffs:
            item["diff"] = e.diff
            item["new_content_size"] = len(e.new_content)
        items.append(item)
    return {
        "session_id": session_id,
        "count": len(items),
        "edits": items,
        "updated_at": batch.updated_at,
    }


def commit_staged(
    session_id: str,
    *,
    stage_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Apply staged edits to disk in stage order.

    On the first failure we attempt to roll back already-applied edits
    using their stored old_content (only for edit_file/write_file —
    we don't restore deleted files since we don't yet support staged
    deletes). Surfaces success per stage_id.
    """
    with _LOCK:
        batch = _load(session_id)
        targets = batch.edits
        if stage_ids is not None:
            id_set = set(stage_ids)
            targets = [e for e in batch.edits if e.stage_id in id_set]

        applied: list[StagedEdit] = []
        results: list[dict[str, Any]] = []
        first_error: dict[str, Any] | None = None

        for e in targets:
            try:
                p = Path(e.path)
                p.parent.mkdir(parents=True, exist_ok=True)
                # Conflict detection — if the file changed out of band
                # since we staged, refuse rather than overwrite silently.
                if e.file_existed and p.is_file():
                    current = p.read_text(encoding="utf-8", errors="replace")
                    if current != e.old_content:
                        raise RuntimeError(
                            f"file changed out of band since stage time "
                            f"(was {len(e.old_content)} bytes, now {len(current)} bytes)"
                        )
                p.write_text(e.new_content, encoding="utf-8")
                applied.append(e)
                results.append({
                    "stage_id": e.stage_id,
                    "path": e.path,
                    "status": "applied",
                })
                # Record self-mutation for code-mutation lineage tracking
                try:
                    from core.services.self_mutation_lineage import record_self_mutation
                    record_self_mutation(target_path=e.path, change_type="edit-staged")
                except Exception:
                    pass
            except Exception as exc:
                first_error = {
                    "stage_id": e.stage_id,
                    "path": e.path,
                    "error": str(exc),
                }
                logger.warning("staged_edits: commit failed for %s: %s", e.stage_id, exc)
                break

        if first_error is not None:
            # Roll back applied edits in reverse order
            rollback_results: list[dict[str, Any]] = []
            for ap in reversed(applied):
                try:
                    if ap.file_existed:
                        Path(ap.path).write_text(ap.old_content, encoding="utf-8")
                        rollback_results.append({"stage_id": ap.stage_id, "status": "rolled-back"})
                    else:
                        Path(ap.path).unlink(missing_ok=True)
                        rollback_results.append({"stage_id": ap.stage_id, "status": "rolled-back-deleted"})
                except Exception as exc:
                    rollback_results.append({
                        "stage_id": ap.stage_id,
                        "status": "rollback-failed",
                        "error": str(exc),
                    })
            return {
                "status": "failed",
                "error": first_error,
                "applied_results": results,
                "rollback": rollback_results,
                "remaining_staged": True,
            }

        # All applied — clear staged batch (or just the requested subset)
        if stage_ids is None:
            batch.edits = []
        else:
            id_set = set(stage_ids)
            batch.edits = [e for e in batch.edits if e.stage_id not in id_set]
        _save(batch)
        return {
            "status": "ok",
            "committed_count": len(applied),
            "results": results,
            "remaining_staged": len(batch.edits),
        }


def discard_staged(
    session_id: str,
    *,
    stage_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Drop staged edits without applying."""
    with _LOCK:
        batch = _load(session_id)
        before = len(batch.edits)
        if stage_ids is None:
            batch.edits = []
        else:
            id_set = set(stage_ids)
            batch.edits = [e for e in batch.edits if e.stage_id not in id_set]
        removed = before - len(batch.edits)
        _save(batch)
    return {
        "status": "ok",
        "discarded_count": removed,
        "remaining_staged": len(batch.edits),
    }
