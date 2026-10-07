"""Varige feed-referencer og signal-outbox for agenter (agent-contract-v1 G, spec 10).

Desks notifikationsfeed viser EN varig reference pr. assignment (``ref_kind='agent'``) og en pr. approval
(``ref_kind='approval'``). Referencen holder KUN det som ikke allerede er sandt et andet sted:

* ``read_at``          - brugeren har set kortet (bjaelden daempes)
* ``acknowledged_at``  - brugeren har kvitteret en fejl/et svar (kortet forlader opmaerksomhedslisten)
* ``signaled_state``   - sidste tilstand der blev meldt til Desk (se nedenfor)

Status, fejlaarsag og resultat hydreres ALTID fra assignment/run/approval - aldrig herfra. "Laest",
"kvitteret", "godkendt" (approvalens egen status) og "modelclaim" (``agent_result_outbox.delivery_status``)
er fire adskilte tilstande paa fire adskilte steder.

Outbox'en (spec 10: "et crash mellem assignmentcommit og push mister ikke notifikationen"):
selve DB-raekkerne ER det varige - ``agent_result_outbox`` skrives i samme transaktion som det terminale
udfald, og en approval er en raekke. Det der manglede var (1) at hver assignment/approval faar sin
reference og (2) at et signal til Desk ikke kan gaa tabt. ``signal_changes`` sammenligner hver references
AKTUELLE tilstand med den sidst meldte og udsender ``notifikation.agent`` for dem der er forskellige -
saa et crash mellem commit og push blot gensendes ved naeste tik (mindst-en-gang; et gensendt signal
laver ingen ekstra kort, fordi kortet er een reference pr. assignment).

Signalet bærer KUN id'er og tilstandsnavne, aldrig agentindhold: det er en opfordring til at genhente.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

from core.runtime.db_agent_contract import LEGACY_UNSCOPED, _conn, _now_iso

logger = logging.getLogger(__name__)

KINDS = ("agent", "approval")
SIGNAL_EVENT = "notifikation.agent"


def ensure_feed_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_feed_refs (
            ref_kind TEXT NOT NULL,
            ref_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            agent_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            read_at TEXT NOT NULL DEFAULT '',
            acknowledged_at TEXT NOT NULL DEFAULT '',
            acknowledged_by TEXT NOT NULL DEFAULT '',
            signaled_state TEXT NOT NULL DEFAULT '',
            signaled_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (ref_kind, ref_id)
        )
        """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_feed_refs_owner "
                 "ON agent_feed_refs(owner_user_id, origin_session_id)")
    # Projektionen henter "seneste besked pr. agent"; uden dette indeks scanner den hele tabellen pr. raekke
    # (maalt mod CT105's 2.359 beskeder: 363 opslag > 45 s).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_messages_agent_created "
                 "ON agent_messages(agent_id, created_at)")


# Aktuel tilstand pr. reference, regnet i SQL saa den kan sammenlignes med ``signaled_state`` uden at hente
# hver raekke. Run-statussen er med: ``outcome_unknown`` og ventetilstande staar paa runnet, ikke assignmentet.
_AGENT_STATE = (
    "a.status || ':' || COALESCE((SELECT r.status FROM agent_runs r WHERE r.assignment_id = a.assignment_id "
    "ORDER BY r.attempt_no DESC LIMIT 1), '')")


def ensure_refs() -> int:
    """Giv hver assignment og approval (med verificerbar ejer) sin reference. Idempotent."""
    conn = _conn()
    now = _now_iso()
    n = conn.execute(
        "INSERT OR IGNORE INTO agent_feed_refs (ref_kind, ref_id, owner_user_id, origin_session_id, agent_id, "
        "created_at) SELECT 'agent', assignment_id, owner_user_id, origin_session_id, agent_id, ? "
        "FROM agent_assignments WHERE owner_user_id != ? AND owner_user_id != '' AND origin_session_id != ''",
        (now, LEGACY_UNSCOPED)).rowcount
    n += conn.execute(
        "INSERT OR IGNORE INTO agent_feed_refs (ref_kind, ref_id, owner_user_id, origin_session_id, agent_id, "
        "created_at) SELECT 'approval', approval_id, owner_user_id, origin_session_id, agent_id, ? "
        "FROM agent_approvals WHERE owner_user_id != ? AND owner_user_id != '' AND origin_session_id != ''",
        (now, LEGACY_UNSCOPED)).rowcount
    conn.commit()
    return max(0, n)


def refs_for_owner(owner_user_id: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Ejerens referencer (aldrig en andens), nøglet paa (kind, id)."""
    owner = (owner_user_id or "").strip()
    if not owner or owner == LEGACY_UNSCOPED:
        return {}
    rows = _conn().execute("SELECT * FROM agent_feed_refs WHERE owner_user_id=?", (owner,)).fetchall()
    return {(r["ref_kind"], r["ref_id"]): {k: r[k] for k in r.keys()} for r in rows}


def _touch(column: str, owner_user_id: str, ref_kind: str, ref_id: str, actor: str = "") -> bool:
    if ref_kind not in KINDS or column not in ("read_at", "acknowledged_at"):
        return False
    owner = (owner_user_id or "").strip()
    if not owner or owner == LEGACY_UNSCOPED:
        return False
    ensure_refs()
    conn = _conn()
    extra = ", acknowledged_by=?" if column == "acknowledged_at" else ""
    args: list[Any] = [_now_iso()] + ([actor or owner] if extra else []) + [ref_kind, ref_id, owner]
    cur = conn.execute(f"UPDATE agent_feed_refs SET {column}=?{extra} WHERE ref_kind=? AND ref_id=? "
                       f"AND owner_user_id=? AND {column}=''", args)
    conn.commit()
    if cur.rowcount == 1:
        return True
    # Allerede sat er stadig "din reference" -> idempotent sandt; en andens/ukendt reference er falsk.
    r = conn.execute("SELECT 1 FROM agent_feed_refs WHERE ref_kind=? AND ref_id=? AND owner_user_id=?",
                     (ref_kind, ref_id, owner)).fetchone()
    return r is not None


def mark_read(*, owner_user_id: str, ref_kind: str, ref_id: str) -> bool:
    return _touch("read_at", owner_user_id, ref_kind, ref_id)


def acknowledge(*, owner_user_id: str, ref_kind: str, ref_id: str) -> bool:
    return _touch("acknowledged_at", owner_user_id, ref_kind, ref_id)


def _changed() -> list[dict[str, Any]]:
    conn = _conn()
    out = [dict(r) for r in conn.execute(
        f"SELECT f.ref_kind, f.ref_id, f.owner_user_id, f.origin_session_id, f.agent_id, "
        f"{_AGENT_STATE} AS state FROM agent_feed_refs f JOIN agent_assignments a "
        f"ON a.assignment_id = f.ref_id WHERE f.ref_kind='agent' AND f.signaled_state != "
        f"({_AGENT_STATE})").fetchall()]
    out += [dict(r) for r in conn.execute(
        "SELECT f.ref_kind, f.ref_id, f.owner_user_id, f.origin_session_id, f.agent_id, p.status AS state "
        "FROM agent_feed_refs f JOIN agent_approvals p ON p.approval_id = f.ref_id "
        "WHERE f.ref_kind='approval' AND f.signaled_state != p.status").fetchall()]
    return out


def signal_changes(*, publish: Any = None) -> list[dict[str, Any]]:
    """Meld hver referenceændring til Desk og husk det. Mindst-en-gang: tilstanden noteres EFTER
    udsendelsen, saa et crash derimellem blot gensender. Returnerer det der blev meldt."""
    ensure_refs()
    if publish is None:
        from core.eventbus.bus import event_bus
        publish = event_bus.publish
    sent: list[dict[str, Any]] = []
    for ch in _changed():
        payload = {"user_id": ch["owner_user_id"], "ref_kind": ch["ref_kind"], "ref_id": ch["ref_id"],
                   "agent_id": ch["agent_id"], "state": ch["state"]}
        try:
            publish(SIGNAL_EVENT, payload)
        except Exception:
            logger.warning("feed-signal for %s/%s kunne ikke udsendes - proeves igen ved naeste tik",
                           ch["ref_kind"], ch["ref_id"], exc_info=True)
            continue
        conn = _conn()
        conn.execute("UPDATE agent_feed_refs SET signaled_state=?, signaled_at=? WHERE ref_kind=? AND ref_id=?",
                     (ch["state"], _now_iso(), ch["ref_kind"], ch["ref_id"]))
        conn.commit()
        sent.append(payload)
    return sent
