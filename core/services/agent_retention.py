"""Retention for agentartefakter og agentens hukommelse (agent-contract-v1 leverance C, hul 4; spec 12.1).

Samme moenster som ``agent_worktrees.sweep``: en idempotent runde der kun kigger paa DB-poster med en
KENDT ejer, aldrig sletter noget den ikke kan klassificere, og aldrig sletter foer udfaldet er afleveret
OG behandlet. Koeres fra ``agent_contract_service.supervise`` (højst hver time).

Artefakter (``agent_artifacts``), pr. assignment:

* behandlet succes bevares 30 dage, fejl/stop/timeout 90 dage - regnet fra det SENESTE af det terminale
  tidspunkt og kvitteringen (``acknowledged``);
* BESKYTTET (slettes aldrig): ikke-terminalt assignment, ``outcome_unknown`` / uafsluttet vaerktoejskald,
  aaben approval (``pending``/``approved``) eller parkeret checkpoint, aktiv wait-kontrakt, en terminalbesked der
  ikke er kvitteret - eller slet ingen besked - samt diff/aendringer/bundle mens worktree'et stadig
  bevares. Et ubehandlet resultat slettes ALDRIG af denne runde; efter 90 dage rapporteres det som
  ``attention`` (synlig paamindelse) i stedet;
* en udloebet artefakt bliver en TOMBSTONE: filen slettes, posten faar status ``expired`` (laesning svarer
  ``EXPIRED``, erindringen viser ``[udloebet]``). Rækken og dens checksum bevares som revisionsspor.

Hukommelse (``agent_memory_*``): et aktivt/suspenderet/tilgaengeligt agents resuméer og noter roeres ALDRIG;
ved ``closed`` bevares de 90 dage fra ``closed_at`` og slettes foerst naar intet af agentens resultater er
ubehandlet. ``legacy_unscoped`` og ejerloese raekker roeres aldrig.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.runtime import db_agent_artifacts as art
from core.runtime.db_agent_contract import ASSIGNMENT_TERMINAL, LEGACY_UNSCOPED, _conn, _now_iso

logger = logging.getLogger(__name__)

SUCCESS_RETENTION = timedelta(days=30)
FAILURE_RETENTION = timedelta(days=90)          # fejl, stop, timeout og arkiverede worktrees
UNPROCESSED_ATTENTION = timedelta(days=90)
MEMORY_AFTER_CLOSE = timedelta(days=90)
RUN_EVERY_S = 3600.0
#: Artefakter der hoerer til worktree'et og foelger dets livscyklus.
WORKTREE_ARTIFACTS = frozenset({"diff.patch", "changes.json", "worktree.bundle"})
_WORKTREE_LIVE = ("reserved", "creating", "active", "retained", "decided", "unknown")

_last_run = 0.0
_run_lock = threading.Lock()


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        logger.warning("ugyldigt tidspunkt %r i retention", value)
        return None


def _assignment_state(conn, assignment_id: str, names_worktree: bool) -> dict[str, Any]:
    """Hvorfor (``reason``) et assignments artefakter er beskyttet - eller hvornaar de udloeber (``expires``)."""
    a = conn.execute("SELECT * FROM agent_assignments WHERE assignment_id=?", (assignment_id,)).fetchone()
    if a is None:
        return {"reason": "no_assignment"}
    if not a["owner_user_id"] or a["owner_user_id"] == LEGACY_UNSCOPED:
        return {"reason": "legacy_or_unowned"}
    if a["status"] not in ASSIGNMENT_TERMINAL:
        return {"reason": "not_terminal"}
    runs = [r["run_id"] for r in conn.execute("SELECT run_id FROM agent_runs WHERE assignment_id=?",
                                              (assignment_id,)).fetchall()]
    marks = ",".join("?" * len(runs)) or "''"
    if conn.execute(f"SELECT 1 FROM agent_runs WHERE run_id IN ({marks}) AND status='outcome_unknown'",
                    runs).fetchone() or conn.execute(
            f"SELECT 1 FROM agent_tool_calls WHERE run_id IN ({marks}) AND started_at != '' AND "
            f"(finished_at = '' OR finished_at IS NULL)", runs).fetchone():
        return {"reason": "outcome_unknown"}
    if conn.execute("SELECT 1 FROM agent_approvals WHERE assignment_id=? AND status IN ('pending','approved')",
                    (assignment_id,)).fetchone():
        return {"reason": "open_approval"}
    if conn.execute("SELECT 1 FROM agent_checkpoints WHERE assignment_id=? AND status='parked'",
                    (assignment_id,)).fetchone():
        return {"reason": "parked"}
    if conn.execute("SELECT 1 FROM agent_wait_contracts WHERE status='registered' AND "
                    "assignment_ids_json LIKE ?", (f'%"{assignment_id}"%',)).fetchone():
        return {"reason": "wait_contract"}
    msgs = conn.execute("SELECT delivery_status, updated_at FROM agent_result_outbox WHERE assignment_id=?",
                        (assignment_id,)).fetchall()
    terminal_at = _parse(a["terminal_at"])
    if not msgs or terminal_at is None:
        return {"reason": "no_receipt"}
    if any(m["delivery_status"] != "acknowledged" for m in msgs):
        return {"reason": "unprocessed", "since": terminal_at}
    base = max([terminal_at, *[t for t in (_parse(m["updated_at"]) for m in msgs) if t]])
    retention = SUCCESS_RETENTION if a["status"] == "completed" else FAILURE_RETENTION
    wt = conn.execute("SELECT status, closed_at FROM agent_worktrees WHERE assignment_id=?",
                      (assignment_id,)).fetchone()
    if names_worktree and wt is not None:
        if wt["status"] in _WORKTREE_LIVE:
            return {"reason": "worktree_held"}
        if wt["status"] == "archived":                     # arkivet foelger 90-dages fejlretention (12.1)
            closed = _parse(wt["closed_at"])
            if closed is None:
                return {"reason": "worktree_held"}
            base, retention = max(base, closed), FAILURE_RETENTION
    return {"reason": "", "expires": base + retention}


def _expire(conn, rec, now: datetime) -> bool:
    """Slet filen (kun hvis stien er den forventede) og goer posten til en tombstone. Idempotent."""
    expected = art._run_dir(rec["agent_id"], rec["run_id"]) / rec["name"]
    root = art.artifact_root().resolve()
    p = Path(rec["path"])
    if p != expected or root not in p.resolve().parents:
        logger.error("retention afviste artefakt %s/%s: stien %s er ikke den forventede", rec["run_id"],
                     rec["name"], rec["path"])
        return False
    try:
        p.unlink()
    except FileNotFoundError:
        logger.debug("artefakten %s var allerede vaek fra disken", p)
    except OSError:
        logger.warning("kunne ikke slette %s - proever igen naeste runde", p, exc_info=True)
        return False
    for parent in (p.parent, p.parent.parent):
        try:
            parent.rmdir()
        except OSError:
            break          # mappen er ikke tom (andre artefakter) - ikke en fejl
    conn.execute("UPDATE agent_artifacts SET status='expired', size=0, updated_at=? WHERE run_id=? AND name=?",
                 (_iso(now), rec["run_id"], rec["name"]))
    conn.commit()
    return True


def sweep_artifacts(*, now: datetime | None = None) -> dict[str, Any]:
    t = now or datetime.now(UTC)
    conn = _conn()
    out: dict[str, Any] = {"expired": [], "protected": {}, "attention": [], "refused": []}
    states: dict[tuple[str, bool], dict[str, Any]] = {}
    rows = conn.execute("SELECT * FROM agent_artifacts WHERE status != 'expired' ORDER BY run_id, name").fetchall()
    for rec in rows:
        key = (rec["assignment_id"], rec["name"] in WORKTREE_ARTIFACTS)
        st = states.get(key) or states.setdefault(key, _assignment_state(conn, *key))
        if not rec["owner_user_id"] or rec["owner_user_id"] == LEGACY_UNSCOPED:
            st = {"reason": "legacy_or_unowned"}
        if st["reason"]:
            out["protected"][st["reason"]] = out["protected"].get(st["reason"], 0) + 1
            if st["reason"] == "unprocessed" and t - st["since"] >= UNPROCESSED_ATTENTION \
                    and rec["assignment_id"] not in out["attention"]:
                out["attention"].append(rec["assignment_id"])
            continue
        if t < st["expires"]:
            continue
        ref = art.artifact_ref(rec["run_id"], rec["name"])
        (out["expired"] if _expire(conn, rec, t) else out["refused"]).append(ref)
    # tombstones hvis fil er blevet liggende (nedbrud mellem DB og disk)
    for rec in conn.execute("SELECT * FROM agent_artifacts WHERE status='expired'").fetchall():
        if Path(rec["path"]).exists() and Path(rec["path"]) == art._run_dir(rec["agent_id"], rec["run_id"]) / rec["name"]:
            Path(rec["path"]).unlink(missing_ok=True)
    return out


def sweep_memory(*, now: datetime | None = None) -> dict[str, Any]:
    """Luk-retention for agentens egen hukommelse. Roerer aldrig en agent der ikke er ``closed``."""
    t = now or datetime.now(UTC)
    conn = _conn()
    out: dict[str, Any] = {"deleted": [], "stamped": [], "protected": {}}
    for ag in conn.execute("SELECT agent_id, owner_user_id, closed_at FROM agent_registry WHERE "
                           "lifecycle_status='closed'").fetchall():
        aid, owner = ag["agent_id"], ag["owner_user_id"]
        if not owner or owner == LEGACY_UNSCOPED:
            out["protected"]["legacy_or_unowned"] = out["protected"].get("legacy_or_unowned", 0) + 1
            continue
        closed = _parse(ag["closed_at"])
        if closed is None:        # lukket foer closed_at fandtes: uret starter nu (aldrig tidligere sletning)
            conn.execute("UPDATE agent_registry SET closed_at=? WHERE agent_id=? AND closed_at=''", (_iso(t), aid))
            conn.commit()
            out["stamped"].append(aid)
            continue
        if t - closed < MEMORY_AFTER_CLOSE:
            continue
        busy = conn.execute(
            "SELECT 1 FROM agent_assignments a WHERE a.agent_id=? AND (a.status NOT IN ('completed','failed',"
            "'cancelled','timed_out') OR NOT EXISTS (SELECT 1 FROM agent_result_outbox o WHERE "
            "o.assignment_id=a.assignment_id) OR EXISTS (SELECT 1 FROM agent_result_outbox o WHERE "
            "o.assignment_id=a.assignment_id AND o.delivery_status != 'acknowledged')) LIMIT 1", (aid,)).fetchone()
        if busy:
            out["protected"]["unprocessed_or_open"] = out["protected"].get("unprocessed_or_open", 0) + 1
            continue
        n = 0
        for table in ("agent_memory_summaries", "agent_memory_notes", "agent_memory_errors",
                      "agent_session_relations"):
            n += conn.execute(f"DELETE FROM {table} WHERE agent_id=?", (aid,)).rowcount
        conn.commit()
        if n:
            out["deleted"].append({"agent_id": aid, "rows": n})
    return out


def run(*, now: datetime | None = None) -> dict[str, Any]:
    """Hele retentionrunden: worktrees (7/14/30 dage), artefakter, hukommelse. Hver del er uafhaengig."""
    result: dict[str, Any] = {"at": _now_iso(), "errors": []}
    from core.services import agent_worktrees as wtm

    for name, fn in (("worktrees", lambda: wtm.sweep(now=now)),
                     ("artifacts", lambda: sweep_artifacts(now=now)),
                     ("memory", lambda: sweep_memory(now=now))):
        try:
            result[name] = fn()
        except Exception as exc:
            logger.warning("retention: %s fejlede", name, exc_info=True)
            result["errors"].append(f"{name}: {type(exc).__name__}: {exc}"[:200])
    return result


def run_if_due() -> dict[str, Any] | None:
    """Throttlet til højst én runde i timen pr. proces (runden er idempotent, saa to processer er ufarligt)."""
    global _last_run
    with _run_lock:
        if time.monotonic() - _last_run < RUN_EVERY_S and _last_run:
            return None
        _last_run = time.monotonic()
    return run()
