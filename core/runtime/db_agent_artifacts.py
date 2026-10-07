"""Artefaktlager for agentkoersler (agent-contract-v1, leverance C1, spec 9 og 12.1).

Hvert run faar en mappe ``~/.jarvis-v2/state/agent-artifacts/<agent_id>/<run_id>/`` med
``assignment.json``, ``events.jsonl``, ``stdout.log``, ``stderr.log``, ``result.json`` og
``final.txt`` efter relevans. Filer skrives som ``*.tmp``, flushes og fsync'es og omdoebes
atomisk, og DB gemmer sti, stoerrelse og checksum. Filsystem og DB kan ikke committes
atomisk sammen: resultatfilen faerdiggoeres FOER den terminale DB-transaktion, og
``reconcile`` finder baade foraeldreloese faerdige filer og DB-poster med manglende eller
korrupt fil. En manglende artefakt vises aldrig som fuldt tilgaengeligt output.

Adgang gaar ALTID gennem DB-posten (ejer + checksum): en sti kommer aldrig fra kalderen.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from core.runtime.db_agent_contract import ContractError, _conn, _now_iso, _row

logger = logging.getLogger(__name__)

ALLOWED_NAMES = frozenset({"assignment.json", "events.jsonl", "stdout.log", "stderr.log",
                           "result.json", "final.txt", "diff.patch", "changes.json",
                           "worktree.bundle"})
#: Fuldt agentoutput maa bruge 2 GiB pr. run som standard (§12.3).
MAX_RUN_BYTES = 2 * 1024 ** 3
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,127}$")
_STALE_TMP_SECONDS = 3600.0


class ArtifactTooLarge(ContractError):
    def __init__(self, detail: str = "") -> None:
        super().__init__("CAPACITY", detail or "run-artefakter over graensen")


def artifact_root() -> Path:
    """Beregnes ved kald (ikke ved import), saa HOME-omdirigering i tests virker."""
    return Path("~/.jarvis-v2/state/agent-artifacts").expanduser()


def ensure_artifact_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_artifacts (
            run_id TEXT NOT NULL,
            name TEXT NOT NULL,
            assignment_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            path TEXT NOT NULL,
            size INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'complete',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (run_id, name)
        )
        """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_artifacts_assignment "
                 "ON agent_artifacts(assignment_id)")


def _safe_id(value: str, what: str) -> str:
    value = str(value or "")
    if not _ID.match(value) or ".." in value:
        raise ContractError("INVALID_SCOPE", f"ugyldigt {what}")
    return value


def _run_dir(agent_id: str, run_id: str) -> Path:
    return artifact_root() / _safe_id(agent_id, "agent_id") / _safe_id(run_id, "run_id")


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def run_bytes(run_id: str) -> int:
    return int(_conn().execute("SELECT COALESCE(SUM(size),0) FROM agent_artifacts "
                               "WHERE run_id=?", (run_id,)).fetchone()[0])


def write_artifact(*, agent_id: str, run_id: str, name: str, data: bytes | str,
                   assignment_id: str, owner_user_id: str, status: str = "complete") -> dict[str, Any]:
    """Skriv én artefakt atomisk og registrer den. Erstatter en tidligere version af samme navn.
    Over graensen: ``ArtifactTooLarge`` og INGEN fil - deloutput maa gemmes som ``partial``."""
    if name not in ALLOWED_NAMES:
        raise ContractError("INVALID_SCOPE", f"ukendt artefaktnavn {name!r}")
    if status not in ("complete", "partial"):
        raise ContractError("INVALID_TRANSITION", status)
    payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    conn = _conn()
    prior = conn.execute("SELECT size FROM agent_artifacts WHERE run_id=? AND name=?",
                         (run_id, name)).fetchone()
    if run_bytes(run_id) - (prior["size"] if prior else 0) + len(payload) > MAX_RUN_BYTES:
        raise ArtifactTooLarge(f"{run_id}: {len(payload)} bytes ville overskride {MAX_RUN_BYTES}")
    directory = _run_dir(agent_id, run_id)
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / name
    tmp = directory / f"{name}.{os.getpid()}.{time.monotonic_ns()}.tmp"
    try:
        with open(tmp, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, final)
        _fsync_dir(directory)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    digest = hashlib.sha256(payload).hexdigest()
    now = _now_iso()
    conn.execute(
        "INSERT INTO agent_artifacts (run_id, name, assignment_id, agent_id, owner_user_id, path, "
        "size, sha256, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(run_id, name) DO UPDATE SET size=excluded.size, sha256=excluded.sha256, "
        "status=excluded.status, path=excluded.path, updated_at=excluded.updated_at",
        (run_id, name, assignment_id, agent_id, owner_user_id, str(final), len(payload),
         digest, status, now, now))
    conn.commit()
    return get_artifact_record(run_id=run_id, name=name) or {}


def get_artifact_record(*, run_id: str, name: str) -> dict[str, Any] | None:
    return _row(_conn().execute("SELECT * FROM agent_artifacts WHERE run_id=? AND name=?",
                                (run_id, name)).fetchone())


def artifact_ref(run_id: str, name: str) -> str:
    return f"{run_id}/{name}"


def read_artifact(*, owner_user_id: str, ref: str, offset: int = 0,
                  limit: int = 20000) -> dict[str, Any]:
    """Adgangskontrolleret laesning via en reference ``<run_id>/<navn>``.

    Svarer kun med indhold naar posten tilhoerer ejeren, filen findes og checksummen
    passer. Ellers en praecis status (NOT_FOUND / MISSING / CORRUPT / EXPIRED) - aldrig
    tavs tomhed og aldrig en anden ejers fil."""
    run_id, _, name = str(ref or "").partition("/")
    rec = _row(_conn().execute("SELECT * FROM agent_artifacts WHERE run_id=? AND name=? "
                               "AND owner_user_id=?", (run_id, name, owner_user_id or "\0")).fetchone())
    if rec is None:
        return {"status": "NOT_FOUND", "ref": ref}
    if rec["status"] == "expired":
        return {"status": "EXPIRED", "ref": ref, "expired_at": rec["updated_at"]}
    try:
        raw = Path(rec["path"]).read_bytes()
    except FileNotFoundError:
        logger.warning("artefakt %s mangler paa disk (%s)", ref, rec["path"])
        return {"status": "MISSING", "ref": ref}
    if hashlib.sha256(raw).hexdigest() != rec["sha256"]:
        return {"status": "CORRUPT", "ref": ref}
    text = raw.decode("utf-8", errors="replace")
    off, lim = max(0, int(offset)), max(1, int(limit))
    return {"status": "ok", "ref": ref, "partial": rec["status"] == "partial", "size": rec["size"],
            "offset": off, "content": text[off:off + lim], "truncated": off + lim < len(text)}


def manifest(*, owner_user_id: str, assignment_id: str) -> list[dict[str, Any]]:
    """Alle forsoegs' artefakter for ét assignment (et fejlet foerste forsoeg forsvinder ikke)."""
    rows = _conn().execute(
        "SELECT a.run_id, a.name, a.size, a.sha256, a.status, r.attempt_no FROM agent_artifacts a "
        "LEFT JOIN agent_runs r ON r.run_id = a.run_id WHERE a.assignment_id=? AND a.owner_user_id=? "
        "ORDER BY r.attempt_no, a.name", (assignment_id, owner_user_id)).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]


def reconcile() -> dict[str, list[str]]:
    """Afstem DB mod disk. Markerer poster med manglende/korrupt fil, finder foraeldreloese
    faerdige filer og rydder gamle ``*.tmp``. Roerer aldrig indhold af en intakt fil."""
    conn = _conn()
    out: dict[str, list[str]] = {"missing": [], "corrupt": [], "orphans": [], "tmp_removed": []}
    known: set[str] = set()
    for r in conn.execute("SELECT run_id, name, path, sha256, status FROM agent_artifacts").fetchall():
        known.add(r["path"])
        if r["status"] in ("expired", "missing", "corrupt"):
            continue
        p = Path(r["path"])
        if not p.exists():
            out["missing"].append(artifact_ref(r["run_id"], r["name"]))
            conn.execute("UPDATE agent_artifacts SET status='missing', updated_at=? WHERE run_id=? "
                         "AND name=?", (_now_iso(), r["run_id"], r["name"]))
        elif hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]:
            out["corrupt"].append(artifact_ref(r["run_id"], r["name"]))
            conn.execute("UPDATE agent_artifacts SET status='corrupt', updated_at=? WHERE run_id=? "
                         "AND name=?", (_now_iso(), r["run_id"], r["name"]))
    conn.commit()
    root = artifact_root()
    if root.exists():
        cutoff = time.time() - _STALE_TMP_SECONDS
        for f in root.glob("*/*/*"):
            if f.name.endswith(".tmp"):
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
                    out["tmp_removed"].append(str(f))
            elif str(f) not in known and f.name in ALLOWED_NAMES:
                out["orphans"].append(str(f))
    return out


def write_terminal_artifacts(*, agent_id: str, assignment_id: str, owner_user_id: str,
                             status: str, reply: str, summary: str, error_code: str = "",
                             error_phase: str = "", worktree: dict | None = None) -> dict[str, str]:
    """Skriv ``result.json`` (+ ``final.txt`` og ``events.jsonl``) for assignmentets SIDSTE run
    FOER den terminale DB-transaktion. Returnerer ``{"artifact_ref", "artifact_error"}``;
    en fejl her aendrer aldrig udfaldet - den bliver en synlig markering (§9)."""
    import json

    conn = _conn()
    last = conn.execute("SELECT run_id, attempt_no FROM agent_runs WHERE assignment_id=? "
                        "ORDER BY attempt_no DESC LIMIT 1", (assignment_id,)).fetchone()
    if last is None:
        return {"artifact_ref": "", "artifact_error": "intet run at gemme artefakter for"}
    run_id = last["run_id"]
    attempts = [r["run_id"] for r in conn.execute(
        "SELECT run_id FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no",
        (assignment_id,)).fetchall()]
    common = dict(agent_id=agent_id, run_id=run_id, assignment_id=assignment_id,
                  owner_user_id=owner_user_id)
    try:
        if reply:
            write_artifact(name="final.txt", data=reply, **common)
        try:
            from core.services.agent_transcript import read_events
            events = read_events(agent_id)
            if events:
                write_artifact(name="events.jsonl", data="\n".join(
                    json.dumps(e, ensure_ascii=False, default=str) for e in events) + "\n", **common)
        except Exception:
            logger.warning("events.jsonl kunne ikke gemmes for %s", run_id, exc_info=True)
        write_artifact(name="result.json", data=json.dumps({
            "assignment_id": assignment_id, "agent_id": agent_id, "run_id": run_id,
            "attempt_run_ids": attempts, "status": status, "summary": summary,
            "error_code": error_code, "error_phase": error_phase,
            "has_final_text": bool(reply), "worktree": worktree}, ensure_ascii=False, indent=2),
            **common)
    except Exception as exc:
        logger.warning("terminale artefakter kunne ikke gemmes for %s", assignment_id, exc_info=True)
        return {"artifact_ref": "", "artifact_error": f"{type(exc).__name__}: {exc}"[:200]}
    return {"artifact_ref": artifact_ref(run_id, "result.json"), "artifact_error": ""}
