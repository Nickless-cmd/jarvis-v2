"""Varige approvals til agenters handlinger (agent-contract-v1 F4a, spec 8.2).

Naar en agent vil udfoere en handling der kraever godkendelse, stopper den FOER vaerktoejskaldet og her
oprettes en varig approval: ``approval_id``, autentificeret ejer, oprindelsessession, parent-/agent-/
assignment-/run-id, target, det konkrete vaerktoej, normaliserede argumenter (sikker visning), en
digest af netop dette kald, risikoklasse og udloebstid.

Reglerne, som tabellen haandhaever (ikke en prompt):

* Kun et MENNESKE kan afgoere (``actor_kind == "human"``), og kun assignmentets ejer eller platformens
  ejer. Jarvis, en agent, en model eller et andet barn kan det aldrig - et forsoeg afvises og auditeres.
* En beslutning bindes til DEN ene ``approval_id`` og kaldets noejagtige digest. Er argumenterne
  aendret siden anmodningen, passer digesten ikke, og der skal bruges en NY approval.
* Den bruges HOEJST EN GANG: ``consume`` er en atomisk overgang ``approved -> consumed`` paa digest.
* Afslag, udloeb og annullering er endelige; samme handling (samme digest) kan ikke anmodes igen i
  samme assignment - heller ikke via et andet vaerktoej eller en anden klient, fordi digesten dækker
  vaerktoej + argumenter + target.
* Alt ligger i DB, saa en genstart rekonstruerer ventende approvals uden at genudfoere noget.

Inde i en BEGIN IMMEDIATE bruges KUN den medgivne ``conn`` - ``connect()`` ruller en aaben
transaktion tilbage hvis den kaldes igen paa traaden.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_agent_contract import ContractError, _conn, _now_iso, _require, _row

logger = logging.getLogger(__name__)

APPROVAL_TTL = timedelta(hours=48)               # §12.3: menneskelig approval højst 48 timer
SAFE_VIEW_LIMIT = 2000
HUMAN = "human"

PENDING, APPROVED, DENIED, EXPIRED, CONSUMED, CANCELLED = (
    "pending", "approved", "denied", "expired", "consumed", "cancelled")
FINAL = (DENIED, EXPIRED, CONSUMED, CANCELLED)


def ensure_approval_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_approvals (
            approval_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL DEFAULT 'tool_call',
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            assignment_id TEXT NOT NULL,
            run_id TEXT NOT NULL DEFAULT '',
            parent_agent_id TEXT NOT NULL DEFAULT '',
            parent_run_id TEXT NOT NULL DEFAULT '',
            target TEXT NOT NULL DEFAULT 'runtime-container',
            tool_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL DEFAULT '{}',
            safe_view TEXT NOT NULL DEFAULT '',
            args_digest TEXT NOT NULL,
            risk_class TEXT NOT NULL DEFAULT 'write',
            requested_by TEXT NOT NULL DEFAULT 'agent',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            decided_at TEXT NOT NULL DEFAULT '',
            decided_by TEXT NOT NULL DEFAULT '',
            decision_note TEXT NOT NULL DEFAULT '',
            consumed_at TEXT NOT NULL DEFAULT '',
            announced_at TEXT NOT NULL DEFAULT '',
            wake_task_id TEXT NOT NULL DEFAULT ''
        )
        """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_approvals_owner "
                 "ON agent_approvals(owner_user_id, status, origin_session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_approvals_assignment "
                 "ON agent_approvals(assignment_id, args_digest)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_approval_audit (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT NOT NULL,
            event TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '',
            at TEXT NOT NULL
        )
        """)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _audit(conn: sqlite3.Connection, approval_id: str, event: str, actor: str = "", detail: str = "") -> None:
    conn.execute("INSERT INTO agent_approval_audit (approval_id, event, actor, detail, at) VALUES (?,?,?,?,?)",
                 (approval_id, event, actor, detail[:300], _now_iso()))


def normalize_arguments(arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Kaldets argumenter UDEN serverens egne ``_runtime_*``-felter (de er ikke en del af handlingen)."""
    return {k: v for k, v in (arguments or {}).items() if not str(k).startswith("_")}


def invocation_digest(*, tool_name: str, arguments: dict[str, Any] | None, target: str,
                      assignment_id: str) -> str:
    """Digest af netop dette kald: vaerktoej + normaliserede argumenter + target + assignment."""
    blob = json.dumps({"tool": tool_name, "args": normalize_arguments(arguments), "target": target,
                       "assignment": assignment_id}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def safe_view(tool_name: str, arguments: dict[str, Any] | None) -> str:
    """Hvad et menneske ser i kortet: redigerede (hemmeligheder) og afkortede argumenter."""
    try:
        from core.services.secret_redaction import redact
    except Exception:
        logger.warning("secret_redaction utilgaengelig - sikker visning udelades", exc_info=True)
        return f"{tool_name}(<argumenter skjult>)"
    text = json.dumps(normalize_arguments(arguments), ensure_ascii=False, sort_keys=True, default=str)
    return redact(f"{tool_name}({text})")[:SAFE_VIEW_LIMIT]


def _row_or_none(conn: sqlite3.Connection, approval_id: str) -> dict[str, Any] | None:
    return _row(conn.execute("SELECT * FROM agent_approvals WHERE approval_id=?", (approval_id,)).fetchone())


def get(*, approval_id: str) -> dict[str, Any] | None:
    return _row_or_none(_conn(), approval_id)


def get_for_owner(*, owner_user_id: str, approval_id: str) -> dict[str, Any] | None:
    r = get(approval_id=approval_id)
    return r if r and r["owner_user_id"] == owner_user_id else None


def request(*, owner_user_id: str, origin_session_id: str, assignment_id: str, tool_name: str,
            arguments: dict[str, Any] | None, run_id: str = "", risk_class: str = "write",
            requested_by: str = "agent", kind: str = "tool_call", ttl: timedelta = APPROVAL_TTL,
            now: datetime | None = None) -> dict[str, Any]:
    """Opret (eller genfind) en ventende approval. Idempotent paa (assignment, digest): samme kald giver
    samme post. Et tidligere AFSLAG for samme digest afviser anmodningen (``POLICY_DENIED``)."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    t = now or datetime.now(UTC)
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        a = conn.execute("SELECT agent_id, parent_agent_id, parent_run_id, target, owner_user_id, "
                         "origin_session_id, status FROM agent_assignments WHERE assignment_id=?",
                         (assignment_id,)).fetchone()
        if a is None or a["owner_user_id"] != owner or a["origin_session_id"] != session:
            raise ContractError("INVALID_SCOPE", "assignment tilhoerer ikke ejer/session")
        if a["status"] in ("completed", "failed", "cancelled", "timed_out"):
            raise ContractError("INVALID_TRANSITION", "assignmentet er afsluttet")
        digest = invocation_digest(tool_name=tool_name, arguments=arguments, target=a["target"],
                                   assignment_id=assignment_id)
        prior = conn.execute("SELECT * FROM agent_approvals WHERE assignment_id=? AND args_digest=? "
                             "ORDER BY created_at DESC", (assignment_id, digest)).fetchall()
        for p in prior:
            if p["status"] == DENIED:
                _audit(conn, p["approval_id"], "re-request refused", "system", "samme handling blev afvist")
                conn.commit()
                raise ContractError("POLICY_DENIED", "samme handling er afvist for dette assignment")
        for p in prior:
            if p["status"] in (PENDING, APPROVED) and _parse(p["expires_at"]) > t:
                conn.rollback()
                return dict(p)
        aid = f"appr-{uuid.uuid4().hex[:16]}"
        conn.execute(
            "INSERT INTO agent_approvals (approval_id, kind, owner_user_id, origin_session_id, agent_id, "
            "assignment_id, run_id, parent_agent_id, parent_run_id, target, tool_name, arguments_json, "
            "safe_view, args_digest, risk_class, requested_by, status, created_at, expires_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'pending', ?, ?)",
            (aid, kind, owner, session, a["agent_id"], assignment_id, run_id, a["parent_agent_id"],
             a["parent_run_id"], a["target"], tool_name,
             json.dumps(normalize_arguments(arguments), ensure_ascii=False, default=str),
             safe_view(tool_name, arguments), digest, risk_class, requested_by, _iso(t), _iso(t + ttl)))
        _audit(conn, aid, "requested", requested_by, f"{tool_name} {digest[:12]}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return get(approval_id=aid) or {}


def _authorized(actor_user_id: str, owner_user_id: str) -> bool:
    if actor_user_id and actor_user_id == owner_user_id:
        return True
    try:
        from core.identity.owner_resolver import owner_user_id as platform_owner
        po = str(platform_owner() or "").strip()
        return bool(po) and actor_user_id == po
    except Exception:
        logger.warning("platformens ejer kunne ikke afgoeres - kun assignmentets ejer maa afgoere", exc_info=True)
        return False


def decide(*, approval_id: str, decision: str, actor_user_id: str, actor_kind: str, digest: str,
           note: str = "", now: datetime | None = None) -> dict[str, Any]:
    """Afgoer EN approval. ``approve``/``deny``. Atomisk: to samtidige afgoerelser giver én vinder."""
    if decision not in ("approve", "deny"):
        raise ContractError("INVALID_TRANSITION", decision)
    t = now or datetime.now(UTC)
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        r = _row_or_none(conn, approval_id)
        if r is None:
            raise ContractError("INVALID_SCOPE", "ukendt approval")
        if actor_kind != HUMAN:
            _audit(conn, approval_id, "refused: ikke et menneske", f"{actor_kind}:{actor_user_id}")
            conn.commit()
            raise ContractError("POLICY_DENIED", "kun et menneske kan afgoere en approval")
        if not _authorized(str(actor_user_id or "").strip(), r["owner_user_id"]):
            _audit(conn, approval_id, "refused: uautoriseret", f"{actor_kind}:{actor_user_id}")
            conn.commit()
            raise ContractError("POLICY_DENIED", "aktoeren maa ikke afgoere denne approval")
        if r["status"] == PENDING and _parse(r["expires_at"]) <= t:
            conn.execute("UPDATE agent_approvals SET status='expired' WHERE approval_id=? AND status='pending'",
                         (approval_id,))
            _audit(conn, approval_id, "expired", "system", "udloebet foer afgoerelse")
            conn.commit()
            raise ContractError("EXPIRED", "approval er udloebet")
        if r["status"] != PENDING:
            conn.rollback()
            raise ContractError("INVALID_TRANSITION", f"approval er {r['status']}")
        if not digest or digest != r["args_digest"]:
            _audit(conn, approval_id, "refused: digest passer ikke", f"human:{actor_user_id}")
            conn.commit()
            raise ContractError("INVALID_SCOPE", "digest passer ikke - handlingen er aendret, ny approval kraeves")
        new = APPROVED if decision == "approve" else DENIED
        conn.execute("UPDATE agent_approvals SET status=?, decided_at=?, decided_by=?, decision_note=? "
                     "WHERE approval_id=? AND status='pending'", (new, _iso(t), actor_user_id, note[:300], approval_id))
        _audit(conn, approval_id, new, f"human:{actor_user_id}", note)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return get(approval_id=approval_id) or {}


def consume(*, approval_id: str, digest: str, now: datetime | None = None) -> bool:
    """Brug en godkendt approval. Atomisk ``approved -> consumed`` paa digest og foer udloeb - HOEJST EN
    gang. ``False`` hvis den allerede er brugt, udloebet, afvist eller digesten ikke passer."""
    t = now or datetime.now(UTC)
    conn = _conn()
    cur = conn.execute("UPDATE agent_approvals SET status='consumed', consumed_at=? WHERE approval_id=? "
                       "AND status='approved' AND args_digest=? AND expires_at > ?",
                       (_iso(t), approval_id, digest, _iso(t)))
    won = cur.rowcount == 1
    _audit(conn, approval_id, "consumed" if won else "consume refused", "runtime", digest[:12])
    conn.commit()
    return won


def expire_due(*, now: datetime | None = None) -> list[str]:
    """Udloeb ventende og ubrugte godkendte approvals der har overskredet fristen."""
    t = now or datetime.now(UTC)
    conn = _conn()
    due = [r["approval_id"] for r in conn.execute(
        "SELECT approval_id FROM agent_approvals WHERE status IN ('pending','approved') AND expires_at <= ?",
        (_iso(t),)).fetchall()]
    for aid in due:
        conn.execute("UPDATE agent_approvals SET status='expired' WHERE approval_id=? AND status IN "
                     "('pending','approved')", (aid,))
        _audit(conn, aid, "expired", "system", "frist overskredet")
    conn.commit()
    return due


def cancel_for_assignment(*, assignment_id: str, reason: str) -> list[str]:
    """Annuller ventende/ubrugte approvals for et assignment der er endt."""
    conn = _conn()
    ids = [r["approval_id"] for r in conn.execute(
        "SELECT approval_id FROM agent_approvals WHERE assignment_id=? AND status IN ('pending','approved')",
        (assignment_id,)).fetchall()]
    for aid in ids:
        conn.execute("UPDATE agent_approvals SET status='cancelled' WHERE approval_id=? AND status IN "
                     "('pending','approved')", (aid,))
        _audit(conn, aid, "cancelled", "system", reason)
    conn.commit()
    return ids


def list_for_owner(*, owner_user_id: str, status: str = "", origin_session_id: str = "",
                   limit: int = 50) -> list[dict[str, Any]]:
    """Ejerens approvals (aldrig en andens)."""
    owner = _require(owner_user_id, "owner_user_id")
    q, args = "SELECT * FROM agent_approvals WHERE owner_user_id=?", [owner]
    if status:
        q += " AND status=?"
        args.append(status)
    if origin_session_id:
        q += " AND origin_session_id=?"
        args.append(origin_session_id)
    q += " ORDER BY created_at DESC LIMIT ?"
    args.append(max(1, min(int(limit), 200)))
    return [_row(r) for r in _conn().execute(q, args).fetchall()]


def unannounced_pending(*, owner_user_id: str, origin_session_id: str) -> list[dict[str, Any]]:
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    return [_row(r) for r in _conn().execute(
        "SELECT * FROM agent_approvals WHERE owner_user_id=? AND origin_session_id=? AND status='pending' "
        "AND announced_at='' ORDER BY created_at", (owner, session)).fetchall()]


def claim_announcements(*, owner_user_id: str, origin_session_id: str) -> list[dict[str, Any]]:
    """Atomisk: markér ventende, endnu ikke omtalte approvals som omtalt og returnér dem. Hver approval
    omtales for parenten PRAECIS én gang (ellers ville den fylde hver runde)."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        rows = conn.execute("SELECT * FROM agent_approvals WHERE owner_user_id=? AND origin_session_id=? "
                            "AND status='pending' AND announced_at='' ORDER BY created_at",
                            (owner, session)).fetchall()
        now = _now_iso()
        for r in rows:
            conn.execute("UPDATE agent_approvals SET announced_at=? WHERE approval_id=?", (now, r["approval_id"]))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return [dict(r) for r in rows]


def audit_trail(*, approval_id: str) -> list[dict[str, Any]]:
    return [_row(r) for r in _conn().execute(
        "SELECT event, actor, detail, at FROM agent_approval_audit WHERE approval_id=? ORDER BY audit_id",
        (approval_id,)).fetchall()]
