"""Workerlease med stigende fencing-token + supervisor-genopretning (agent-contract-v1 C2).

Spec: docs/specs/2026-10-07-agentorkestrering-og-subagenter.md (9, 12.3).

En koersel af et assignment holder en tidsbegraenset lease (standard 90 s, fornyes hvert 30.).
Hvert erhvervelse hoejner et fencing-token. En gammel worker, hvis lease er udloebet eller
overtaget, maa HVERKEN skrive ny runstatus, sende terminalbesked eller udfoere endnu et
vaerktoejskald (``scope_is_current`` - tjekkes dér). Supervisoren finder udloebne leases og
overtager dem med ét atomisk UPDATE: ser to instanser den samme, vinder én og taberen
handler ikke. Den genoptager kun SIKRE trin; et vaerktoejskald der er startet uden at vaere
afsluttet, kan have udfoert en skrivning, og afgoeres aldrig ved blind genudfoerelse -
runnet gaar til ``outcome_unknown`` og assignmentet bliver staaende til det er afgjort.
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
import os
import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Iterator

from core.runtime.db_agent_contract import ContractError, _conn, _now_iso, _row

logger = logging.getLogger(__name__)

LEASE_SECONDS = 90.0
RENEW_SECONDS = 30.0
#: Hvor mange sikre forsoeg et assignment maa have foer det opgives (§12.3: "sikre retries").
MAX_SAFE_ATTEMPTS = 2


def ensure_lease_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_leases (
            assignment_id TEXT PRIMARY KEY,
            holder TEXT NOT NULL,
            fencing_token INTEGER NOT NULL DEFAULT 0,
            lease_until TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'held',
            acquired_at TEXT NOT NULL,
            renewed_at TEXT NOT NULL
        )
        """)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def holder_identity() -> str:
    return f"pid-{os.getpid()}-{uuid.uuid4().hex[:6]}"


def acquire(*, assignment_id: str, holder: str, lease_seconds: float = LEASE_SECONDS,
            now: datetime | None = None) -> int:
    """Erhverv leasen og returner det nye fencing-token. ``LEASE_HELD`` hvis en anden har en levende."""
    t = _now(now)
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT * FROM agent_leases WHERE assignment_id=?",
                           (assignment_id,)).fetchone()
        if row is not None and row["state"] == "held" and _parse(row["lease_until"]) > t:
            raise ContractError("LEASE_HELD", f"{assignment_id} holdes af {row['holder']}")
        token = (row["fencing_token"] if row else 0) + 1
        until = _iso(t + timedelta(seconds=lease_seconds))
        conn.execute(
            "INSERT INTO agent_leases (assignment_id, holder, fencing_token, lease_until, state, "
            "acquired_at, renewed_at) VALUES (?,?,?,?, 'held', ?, ?) "
            "ON CONFLICT(assignment_id) DO UPDATE SET holder=excluded.holder, "
            "fencing_token=excluded.fencing_token, lease_until=excluded.lease_until, "
            "state='held', acquired_at=excluded.acquired_at, renewed_at=excluded.renewed_at",
            (assignment_id, holder, token, until, _iso(t), _iso(t)))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return token


def renew(*, assignment_id: str, holder: str, token: int, lease_seconds: float = LEASE_SECONDS,
          now: datetime | None = None) -> bool:
    """Forny. Kun den nuvaerende holder med det nuvaerende token, og kun foer udloeb: en worker
    hvis lease er udloebet skal tabe den (supervisoren overtager), ikke genvinde den tavst."""
    t = _now(now)
    conn = _conn()
    cur = conn.execute(
        "UPDATE agent_leases SET lease_until=?, renewed_at=? WHERE assignment_id=? AND holder=? "
        "AND fencing_token=? AND state='held' AND lease_until > ?",
        (_iso(t + timedelta(seconds=lease_seconds)), _iso(t), assignment_id, holder, token, _iso(t)))
    conn.commit()
    return cur.rowcount == 1


def is_current(*, assignment_id: str, token: int, now: datetime | None = None) -> bool:
    t = _now(now)
    row = _conn().execute("SELECT fencing_token, state, lease_until FROM agent_leases "
                          "WHERE assignment_id=?", (assignment_id,)).fetchone()
    return bool(row and row["state"] == "held" and row["fencing_token"] == token
                and _parse(row["lease_until"]) > t)


def release(*, assignment_id: str, holder: str, token: int) -> bool:
    conn = _conn()
    cur = conn.execute("UPDATE agent_leases SET state='released' WHERE assignment_id=? AND holder=? "
                       "AND fencing_token=? AND state='held'", (assignment_id, holder, token))
    conn.commit()
    return cur.rowcount == 1


# --- scope (den koerende tråd) --------------------------------------------------------------

_scope: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "agent_lease_scope", default=None)


def scope_is_current() -> bool:
    """Maa den NUVAERENDE tråd stadig skrive? Sandt uden scope (legacy-agenter), ellers kun
    hvis dens lease/token stadig er den gaeldende. Fail-closed ved databasefejl."""
    sc = _scope.get()
    if sc is None:
        return True
    if sc["lost"].is_set():
        return False
    try:
        ok = is_current(assignment_id=sc["assignment_id"], token=sc["token"])
    except Exception:
        logger.warning("kunne ikke tjekke lease for %s - behandles som mistet", sc["assignment_id"],
                       exc_info=True)
        ok = False
    if not ok:
        sc["lost"].set()
    return ok


@contextlib.contextmanager
def agent_lease_scope(agent_id: str, *, lease_seconds: float = LEASE_SECONDS,
                      renew_seconds: float = RENEW_SECONDS) -> Iterator[dict[str, Any] | None]:
    """Hold leasen for agentens aabne assignment mens blokken koerer. Uden et assignment
    (legacy) er det en no-op. Kan leasen ikke erhverves, koeres blokken IKKE (``LEASE_HELD``)."""
    from core.runtime.db_agent_contract import open_assignment_for_agent

    a = open_assignment_for_agent(agent_id)
    if a is None:
        yield None
        return
    holder = holder_identity()
    token = acquire(assignment_id=a["assignment_id"], holder=holder, lease_seconds=lease_seconds)
    sc: dict[str, Any] = {"assignment_id": a["assignment_id"], "holder": holder, "token": token,
                          "lost": threading.Event(), "stop": threading.Event()}

    def _renewer() -> None:
        while not sc["stop"].wait(renew_seconds):
            try:
                if not renew(assignment_id=sc["assignment_id"], holder=holder, token=token,
                             lease_seconds=lease_seconds):
                    sc["lost"].set()
                    logger.warning("lease for %s mistet - worker stoppes ved naeste skrivning",
                                   sc["assignment_id"])
                    return
            except Exception:
                logger.warning("lease-fornyelse fejlede for %s", sc["assignment_id"], exc_info=True)

    thread = threading.Thread(target=_renewer, daemon=True, name="agent-lease-renew")
    thread.start()
    tok = _scope.set(sc)
    try:
        yield sc
    finally:
        _scope.reset(tok)
        sc["stop"].set()
        thread.join(timeout=2.0)
        try:
            release(assignment_id=sc["assignment_id"], holder=holder, token=token)
        except Exception:
            logger.warning("lease kunne ikke frigives for %s", sc["assignment_id"], exc_info=True)


# --- supervisor -------------------------------------------------------------------------------

def _claim(assignment_id: str, token: int, t: datetime) -> bool:
    """Overtag en udloebet lease med ét atomisk UPDATE. Kun den ene supervisor faar ``True``."""
    conn = _conn()
    cur = conn.execute("UPDATE agent_leases SET state='expired' WHERE assignment_id=? AND "
                       "fencing_token=? AND state='held' AND lease_until <= ?",
                       (assignment_id, token, _iso(t)))
    conn.commit()
    return cur.rowcount == 1


def reconcile_expired_leases(*, now: datetime | None = None) -> list[dict[str, Any]]:
    """Find udloebne leases, overtag hver med ét atomisk UPDATE og afgoer sikkert.

    Afgoerelsen per overtaget lease:
      * et vaerktoejskald startet men ikke afsluttet  -> run ``outcome_unknown``, assignment
        ``waiting`` (blokeret til udfaldet er afgjort; INGEN blind genudfoerelse)
      * ellers, og forsoeg < MAX_SAFE_ATTEMPTS         -> runnet ``failed (lease_expired)``,
        agenten koeres igen som nyt forsoeg (nyt run-id)
      * ellers                                          -> agenten ``failed`` -> terminal
    Returnerer hvad der blev gjort (tom naar intet var udloebet / taberen af et kapløb)."""
    t = _now(now)
    conn = _conn()
    done: list[dict[str, Any]] = []
    expired = conn.execute("SELECT assignment_id, fencing_token FROM agent_leases "
                           "WHERE state='held' AND lease_until <= ?", (_iso(t),)).fetchall()
    for e in expired:
        if not _claim(e["assignment_id"], e["fencing_token"], t):
            continue                       # en anden supervisor vandt kapløbet
        done.append(_decide(e["assignment_id"], t))
    return [d for d in done if d]


def _decide(assignment_id: str, t: datetime) -> dict[str, Any]:
    from core.runtime.db_agent_contract import ASSIGNMENT_TERMINAL

    conn = _conn()
    a = _row(conn.execute("SELECT * FROM agent_assignments WHERE assignment_id=?",
                          (assignment_id,)).fetchone())
    if a is None or a["status"] in ASSIGNMENT_TERMINAL:
        return {}
    run = _row(conn.execute("SELECT * FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no DESC "
                            "LIMIT 1", (assignment_id,)).fetchone())
    unknown = conn.execute(
        "SELECT COUNT(*) FROM agent_tool_calls WHERE run_id=? AND started_at != '' AND "
        "(finished_at = '' OR finished_at IS NULL)", (run["run_id"] if run else "",)).fetchone()[0]
    now_s = _now_iso()
    if unknown:
        conn.execute("UPDATE agent_runs SET status='outcome_unknown', failure_reason=?, updated_at=? "
                     "WHERE run_id=?", ("lease_expired_with_open_tool_call", now_s, run["run_id"]))
        conn.execute("UPDATE agent_assignments SET status='waiting', updated_at=? WHERE assignment_id=?",
                     (now_s, assignment_id))
        # G: parent og Desk faar STRAKS en saerskilt tilstandsbesked (ikke terminalbeskeden) i samme commit
        from core.runtime.db_agent_outcome_unknown import notify_outcome_unknown, publish_outcome_unknown
        notify_outcome_unknown(conn, assignment_id=assignment_id, run_id=run["run_id"],
                               reason="lease_expired_with_open_tool_call", open_tool_calls=int(unknown))
        conn.commit()
        publish_outcome_unknown(assignment_id=assignment_id, run_id=run["run_id"], agent_id=a["agent_id"],
                                owner_user_id=a["owner_user_id"])
        return {"assignment_id": assignment_id, "action": "outcome_unknown", "open_tool_calls": int(unknown)}
    # Et modelskift (G) er et synligt forsoeg men ikke et SIKKERT RETRY efter workertab: det tael ikke med.
    attempts = int(conn.execute("SELECT COUNT(*) FROM agent_runs WHERE assignment_id=? AND error_code != ?",
                                (assignment_id, "MODEL_FAILOVER")).fetchone()[0])
    if run is not None:
        conn.execute("UPDATE agent_runs SET status='failed', failure_reason='lease_expired', "
                     "error_phase='recovery', error_code='LEASE_EXPIRED', finished_at=?, updated_at=? "
                     "WHERE run_id=?", (now_s, now_s, run["run_id"]))
    conn.commit()
    from core.runtime.db_agent_runtime import update_agent_registry_entry
    if attempts < MAX_SAFE_ATTEMPTS:
        # En sikker retry tager en ny workerplads fra den varige koe. Den gamle worker
        # er fenced af leasen; en anden ejer maa nu kunne bruge dens frigivne plads.
        conn.execute("UPDATE agent_assignments SET status='queued', ready_at=?, updated_at=? "
                     "WHERE assignment_id=? AND status IN ('queued','active')",
                     (now_s, now_s, assignment_id))
        conn.commit()
        update_agent_registry_entry(a["agent_id"], status="queued", last_error="lease_expired: nyt forsoeg")
        return {"assignment_id": assignment_id, "action": "retry", "attempt": attempts + 1,
                "agent_id": a["agent_id"]}
    update_agent_registry_entry(a["agent_id"], status="failed", last_error="lease_expired: forsoeg opbrugt")
    return {"assignment_id": assignment_id, "action": "failed", "attempts": attempts}
