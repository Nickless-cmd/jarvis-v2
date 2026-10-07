"""Varige bro-invocations for agenter paa et klient-target (agent-contract-v1 E, spec 8 + 8.1).

Hvert kald serveren sender til en klient faar et stabilt ``invocation_id`` og en raekke HER, skrevet
FOER afsendelsen. Raekken er det der goer et tabt kald undersoegbart:

    pending -> sent -> succeeded | failed          (klienten svarede: udfaldet er KENDT)
                  \\-> outcome_unknown              (afsendt, intet svar - ingen blind retry af en skrivning)
    outcome_unknown -> verified_executed | verified_not_executed | human_resolved

``idem_class`` er ``read`` (kan proeves igen efter timeout) eller ``write`` (aldrig). Et muligvis udfoert
skrivende kald uden kvittering bliver ``outcome_unknown``; kun klientens egen status ved reconnect
(``apply_client_report``) eller en menneskelig afgoerelse (``human_resolve``) kan lukke det.

Inde i en BEGIN IMMEDIATE bruges KUN den medgivne conn (``connect()`` ruller en aaben transaktion tilbage).
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from typing import Any

from core.runtime.db_agent_contract import ContractError, _conn, _now_iso

logger = logging.getLogger(__name__)

PENDING, SENT, SUCCEEDED, FAILED, UNKNOWN = "pending", "sent", "succeeded", "failed", "outcome_unknown"
VERIFIED_EXECUTED, VERIFIED_NOT_EXECUTED, HUMAN_RESOLVED = (
    "verified_executed", "verified_not_executed", "human_resolved")
OPEN_STATES = (PENDING, SENT)
RESULT_LIMIT = 8000


def ensure_bridge_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_bridge_invocations (
            invocation_id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            assignment_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            tool TEXT NOT NULL,
            idem_class TEXT NOT NULL,
            args_digest TEXT NOT NULL,
            state TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            result_json TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            resolution TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            sent_at TEXT NOT NULL DEFAULT '',
            resolved_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_bridge_client "
                 "ON agent_bridge_invocations(owner_user_id, client_id, state)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_bridge_assignment "
                 "ON agent_bridge_invocations(assignment_id, state)")


def args_digest(tool: str, args: dict[str, Any]) -> str:
    body = json.dumps({"tool": tool, "args": args}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def get(invocation_id: str) -> dict[str, Any] | None:
    return _row(_conn().execute("SELECT * FROM agent_bridge_invocations WHERE invocation_id=?",
                                (invocation_id,)).fetchone())


def begin(*, invocation_id: str, owner_user_id: str, origin_session_id: str, agent_id: str,
          assignment_id: str, run_id: str, client_id: str, tool: str, idem_class: str,
          args: dict[str, Any]) -> dict[str, Any]:
    """Opret raekken i ``pending``. Samme id med samme argumenter returnerer den eksisterende;
    samme id med andre argumenter afvises (et invocation_id er bundet til netop ET kald)."""
    if idem_class not in ("read", "write"):
        raise ContractError("INVALID_SCOPE", f"ukendt idempotensklasse {idem_class!r}")
    digest = args_digest(tool, args)
    conn = _conn()
    conn.execute(
        "INSERT OR IGNORE INTO agent_bridge_invocations (invocation_id, owner_user_id, origin_session_id, "
        "agent_id, assignment_id, run_id, client_id, tool, idem_class, args_digest, state, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (invocation_id, owner_user_id, origin_session_id, agent_id, assignment_id, run_id, client_id,
         tool, idem_class, digest, PENDING, _now_iso()))
    conn.commit()
    row = get(invocation_id)
    if row is None or row["args_digest"] != digest or row["owner_user_id"] != owner_user_id:
        raise ContractError("IDEMPOTENCY_CONFLICT", f"invocation {invocation_id} hoerer til et andet kald")
    return row


def mark_sent(invocation_id: str) -> None:
    conn = _conn()
    conn.execute("UPDATE agent_bridge_invocations SET state=?, attempts=attempts+1, sent_at=? "
                 "WHERE invocation_id=? AND state IN (?,?)", (SENT, _now_iso(), invocation_id, PENDING, SENT))
    conn.commit()


def unmark_sent(invocation_id: str) -> None:
    """Sendingen lykkedes IKKE (intet forlod serveren): tilbage til ``pending`` og taellerne stemmer igen,
    saa ``abort_unsent`` kan se at intet er afsendt."""
    conn = _conn()
    conn.execute("UPDATE agent_bridge_invocations SET state=?, attempts=MAX(attempts-1, 0), sent_at='' "
                 "WHERE invocation_id=? AND state=?", (PENDING, invocation_id, SENT))
    conn.commit()


def _clip(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text[:RESULT_LIMIT]


def finish(invocation_id: str, *, ok: bool, result: Any = None, error: str = "") -> bool:
    """Klienten SVAREDE: udfaldet er kendt. Kun fra pending/sent/outcome_unknown (et sent svar efter
    en timeout lukker en uafgjort raekke - klientens eget svar er det staerkeste bevis)."""
    conn = _conn()
    cur = conn.execute(
        "UPDATE agent_bridge_invocations SET state=?, result_json=?, error=?, resolved_at=?, "
        "resolution=CASE WHEN state=? THEN 'late_reply' ELSE resolution END "
        "WHERE invocation_id=? AND state IN (?,?,?)",
        (SUCCEEDED if ok else FAILED, _clip(result) if ok else "", "" if ok else error[:500], _now_iso(),
         UNKNOWN, invocation_id, PENDING, SENT, UNKNOWN))
    conn.commit()
    return cur.rowcount == 1


def mark_unknown(invocation_id: str, why: str) -> bool:
    conn = _conn()
    cur = conn.execute("UPDATE agent_bridge_invocations SET state=?, error=? "
                       "WHERE invocation_id=? AND state IN (?,?)",
                       (UNKNOWN, why[:500], invocation_id, PENDING, SENT))
    conn.commit()
    return cur.rowcount == 1


def abort_unsent(invocation_id: str, why: str) -> bool:
    """Intet forlod serveren (klienten var offline foer afsendelse): sikkert at afvise som fejlet."""
    conn = _conn()
    cur = conn.execute("UPDATE agent_bridge_invocations SET state=?, error=?, resolved_at=? "
                       "WHERE invocation_id=? AND state=? AND attempts=0",
                       (FAILED, why[:500], _now_iso(), invocation_id, PENDING))
    conn.commit()
    return cur.rowcount == 1


def unresolved_for_client(owner_user_id: str, client_id: str) -> list[dict[str, Any]]:
    rows = _conn().execute(
        "SELECT * FROM agent_bridge_invocations WHERE owner_user_id=? AND client_id=? AND state IN (?,?,?) "
        "ORDER BY created_at", (owner_user_id, client_id, SENT, UNKNOWN, PENDING)).fetchall()
    return [dict(r) for r in rows]


def unknown_for_assignment(assignment_id: str) -> list[dict[str, Any]]:
    rows = _conn().execute("SELECT * FROM agent_bridge_invocations WHERE assignment_id=? AND state=? "
                           "ORDER BY created_at", (assignment_id, UNKNOWN)).fetchall()
    return [dict(r) for r in rows]


def apply_client_report(*, owner_user_id: str, client_id: str,
                        reports: list[dict[str, Any]]) -> dict[str, str]:
    """Klientens egen status for kendte invocation-id'er ved reconnect. Kun raekker der hoerer til
    DENNE ejer og DENNE klient roeres - en klient kan ikke afgoere en andens kald.

    ``status``: ``completed`` (med resultat) / ``failed`` (med fejl) / ``not_started`` / ``running`` /
    ``unknown``. Kun de tre foerste afgoer noget; ``running``/``unknown`` lader raekken staa."""
    out: dict[str, str] = {}
    conn = _conn()
    for rep in reports:
        iid = str(rep.get("invocation_id") or "")
        row = get(iid)
        if row is None or row["owner_user_id"] != owner_user_id or row["client_id"] != client_id:
            out[iid] = "ignored_unknown_invocation"
            continue
        status = str(rep.get("status") or "")
        if row["state"] in (SUCCEEDED, FAILED, VERIFIED_EXECUTED, VERIFIED_NOT_EXECUTED, HUMAN_RESOLVED):
            out[iid] = f"already_{row['state']}"
        elif status == "completed":
            conn.execute("UPDATE agent_bridge_invocations SET state=?, result_json=?, resolution='client_status', "
                         "resolved_at=? WHERE invocation_id=?",
                         (VERIFIED_EXECUTED, _clip(rep.get("result")), _now_iso(), iid))
            out[iid] = VERIFIED_EXECUTED
        elif status == "failed":
            conn.execute("UPDATE agent_bridge_invocations SET state=?, error=?, resolution='client_status', "
                         "resolved_at=? WHERE invocation_id=?",
                         (VERIFIED_EXECUTED, str(rep.get("error") or "")[:500], _now_iso(), iid))
            out[iid] = VERIFIED_EXECUTED
        elif status == "not_started":
            conn.execute("UPDATE agent_bridge_invocations SET state=?, resolution='client_status', "
                         "resolved_at=? WHERE invocation_id=?", (VERIFIED_NOT_EXECUTED, _now_iso(), iid))
            out[iid] = VERIFIED_NOT_EXECUTED
        else:
            out[iid] = "unchanged"
    conn.commit()
    return out


def human_resolve(*, invocation_id: str, owner_user_id: str, executed: bool, actor_user_id: str) -> dict[str, Any]:
    """Menneskelig afgoerelse af et uafgjort skrivende kald. Kun raekkens ejer."""
    row = get(invocation_id)
    if row is None or row["owner_user_id"] != owner_user_id:
        raise ContractError("INVALID_SCOPE", "ukendt invocation")
    if row["state"] != UNKNOWN:
        raise ContractError("POLICY_DENIED", f"invocation er {row['state']}, ikke uafgjort")
    conn = _conn()
    conn.execute("UPDATE agent_bridge_invocations SET state=?, resolution=?, resolved_at=? WHERE invocation_id=?",
                 (HUMAN_RESOLVED, f"human:{actor_user_id}:{'executed' if executed else 'not_executed'}",
                  _now_iso(), invocation_id))
    conn.commit()
    return get(invocation_id) or {}
