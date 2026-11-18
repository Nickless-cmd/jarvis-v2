"""Leverance A af agent-contract-v1: assignment, run-binding og terminal outbox.

Spec: docs/specs/2026-10-07-agentorkestrering-og-subagenter.md §4, §6 og §12.2.

Ansvar: varig sandhed for HVEM der ejer en agent, HVILKEN opgave den fik, og at
ét assignment giver PRÆCIS én terminal `agent_result` til den direkte parent.
Intet her kører en model; modulet er kun DB-kontrakten.

Additiv migration: `agent_registry` og `agent_runs` beholdes, og får nye
kolonner. Eksisterende rækker har INGEN verificerbar ejer og mærkes
`legacy_unscoped` — de backfilles aldrig med Bjørns id (§12.2).
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from typing import Any

from core.runtime.db_core import _now_iso, connect

logger = logging.getLogger(__name__)

LEGACY_UNSCOPED = "legacy_unscoped"
CONTRACT_VERSION = "agent-contract-v1"

ASSIGNMENT_OPEN = frozenset({"queued", "active", "waiting"})
ASSIGNMENT_TERMINAL = frozenset({"completed", "failed", "cancelled", "timed_out"})
RESULT_TYPE = "agent_result"
DELIVERY_STATES = ("accepted", "delivered", "claimed_by_model_step", "acknowledged")


class ContractError(Exception):
    """Afvist kald med stabil kode, så adaptere kan svare entydigt."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _add_columns(conn: sqlite3.Connection, table: str, columns: list[tuple[str, str]]) -> None:
    have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, decl in columns:
        if name not in have:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
            except sqlite3.OperationalError as exc:  # begge units migrerer samme DB
                if "duplicate column" not in str(exc).lower():
                    raise


def ensure_agent_contract_tables(conn: sqlite3.Connection) -> None:
    """Idempotent skema. Kalder `_ensure_agent_runtime_tables` først, så de
    tabeller der udvides findes (hos en frisk DB såvel som den levende)."""
    from core.runtime.db_agent_runtime import _ensure_agent_runtime_tables

    _ensure_agent_runtime_tables(conn)
    _add_columns(conn, "agent_registry", [
        ("owner_user_id", f"TEXT NOT NULL DEFAULT '{LEGACY_UNSCOPED}'"),
        ("owner_session_id", "TEXT NOT NULL DEFAULT ''"),
        ("lifecycle_status", "TEXT NOT NULL DEFAULT 'available'"),
        ("closed_at", "TEXT NOT NULL DEFAULT ''"),     # retention (12.1): 90 dages uret efter lukning
    ])
    _add_columns(conn, "agent_runs", [
        ("assignment_id", "TEXT NOT NULL DEFAULT ''"),
        ("owner_user_id", f"TEXT NOT NULL DEFAULT '{LEGACY_UNSCOPED}'"),
        ("attempt_no", "INTEGER NOT NULL DEFAULT 0"),
        ("error_phase", "TEXT NOT NULL DEFAULT ''"),
        ("error_code", "TEXT NOT NULL DEFAULT ''"),
        ("artifact_path", "TEXT NOT NULL DEFAULT ''"),
    ])
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_assignments (
            assignment_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            parent_agent_id TEXT NOT NULL DEFAULT '',
            parent_run_id TEXT NOT NULL DEFAULT '',
            goal TEXT NOT NULL,
            input_refs_json TEXT NOT NULL DEFAULT '[]',
            expected_result TEXT NOT NULL DEFAULT '',
            target TEXT NOT NULL DEFAULT 'runtime-container',
            deadline_at TEXT NOT NULL DEFAULT '',
            budget_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT NOT NULL DEFAULT '',
            operation TEXT NOT NULL DEFAULT 'dispatch',
            idempotency_key TEXT NOT NULL DEFAULT '',
            request_digest TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'queued',
            outcome_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            terminal_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_assignments_idem
        ON agent_assignments(owner_user_id, origin_session_id, operation, idempotency_key)
        WHERE idempotency_key != ''
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_assignments_agent "
        "ON agent_assignments(agent_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_runs_assignment "
        "ON agent_runs(assignment_id, attempt_no)"
    )
    from core.runtime.db_agent_capacity import ensure_capacity_columns
    ensure_capacity_columns(conn)
    from core.runtime.db_agent_deadlines import ensure_deadline_columns
    ensure_deadline_columns(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_result_outbox (
            message_id TEXT PRIMARY KEY,
            assignment_id TEXT NOT NULL,
            result_type TEXT NOT NULL DEFAULT 'agent_result',
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            sender_agent_id TEXT NOT NULL,
            recipient_agent_id TEXT NOT NULL,
            parent_run_id TEXT NOT NULL DEFAULT '',
            last_run_id TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL,
            delivery_status TEXT NOT NULL DEFAULT 'accepted',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (assignment_id, result_type)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_result_outbox_recipient "
        "ON agent_result_outbox(owner_user_id, origin_session_id, delivery_status)"
    )
    from core.runtime.db_agent_wait import ensure_wait_tables

    ensure_wait_tables(conn)
    from core.runtime.db_agent_artifacts import ensure_artifact_tables

    ensure_artifact_tables(conn)
    from core.runtime.db_agent_lease import ensure_lease_tables

    ensure_lease_tables(conn)
    from core.services.agent_prompt_layers import ensure_prompt_tables

    ensure_prompt_tables(conn)
    from core.runtime.db_agent_memory import ensure_memory_tables

    ensure_memory_tables(conn)
    from core.services.agent_worktrees import ensure_worktree_tables

    ensure_worktree_tables(conn)
    from core.runtime.db_agent_approvals import ensure_approval_tables

    ensure_approval_tables(conn)
    from core.runtime.db_agent_route import ensure_route_tables

    ensure_route_tables(conn)
    from core.runtime.db_agent_bridge import ensure_bridge_tables

    ensure_bridge_tables(conn)
    from core.runtime.db_agent_council import ensure_council_tables

    ensure_council_tables(conn)

    from core.runtime.db_agent_fork import ensure_fork_tables

    ensure_fork_tables(conn)
    from core.runtime.db_agent_outcome_unknown import ensure_outcome_unknown_columns

    ensure_outcome_unknown_columns(conn)
    from core.runtime.db_agent_mandate import ensure_mandate_tables

    ensure_mandate_tables(conn)

    from core.runtime.db_agent_feed import ensure_feed_tables

    ensure_feed_tables(conn)


_ENSURED: set[str] = set()


def _conn() -> sqlite3.Connection:
    """Ensure-én-gang-per-proces-og-DB: ellers koster hvert statusskifte 8 DDL-kald."""
    from core.runtime import db_core

    conn = connect()
    key = str(db_core.DB_PATH)
    if key not in _ENSURED:
        ensure_agent_contract_tables(conn)
        conn.commit()
        _ENSURED.add(key)
    return conn


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return None if r is None else {k: r[k] for k in r.keys()}


def _require(value: str, name: str) -> str:
    value = (value or "").strip()
    if not value or value == LEGACY_UNSCOPED:
        raise ContractError("INVALID_SCOPE", f"{name} mangler eller er ikke verificerbar")
    return value


def _digest(*parts: Any) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def mark_legacy_unscoped() -> dict[str, int]:
    """Gamle rækker uden ejer er allerede mærket via kolonne-default; denne
    tæller dem, så en administrativ læseflade kan vise dem (§12.2)."""
    conn = _conn()
    agents = conn.execute(
        "SELECT COUNT(*) FROM agent_registry WHERE owner_user_id = ?", (LEGACY_UNSCOPED,)
    ).fetchone()[0]
    runs = conn.execute(
        "SELECT COUNT(*) FROM agent_runs WHERE owner_user_id = ?", (LEGACY_UNSCOPED,)
    ).fetchone()[0]
    return {"agents": int(agents), "runs": int(runs)}


def accept_assignment(
    *,
    agent_id: str,
    owner_user_id: str,
    origin_session_id: str,
    goal: str,
    parent_agent_id: str = "",
    parent_run_id: str = "",
    input_refs: list[str] | None = None,
    expected_result: str = "",
    target: str = "runtime-container",
    deadline_at: str = "",
    budget: dict[str, Any] | None = None,
    created_by: str = "",
    operation: str = "dispatch",
    idempotency_key: str = "",
    request_digest: str = "",
) -> dict[str, Any]:
    """Accepter ét assignment atomisk sammen med dets første run.

    Samme idempotens-nøgle inden for (ejer, session, operation) returnerer
    SAMME accept; samme nøgle med andre argumenter afvises. Et afvist kald
    efterlader intet halvt assignment og intet run.
    """
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    if not (goal or "").strip():
        raise ContractError("INVALID_SCOPE", "goal mangler")
    # Kalderen kan angive sin egen digest (service-laget regner den paa ANMODNINGEN,
    # fordi agent_id foedes foerst efter idempotens-opslaget).
    digest = request_digest or _digest(
        agent_id, goal, parent_agent_id, parent_run_id, input_refs or [],
        expected_result, target, deadline_at, budget or {})
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        if idempotency_key:
            hit = conn.execute(
                "SELECT * FROM agent_assignments WHERE owner_user_id=? AND "
                "origin_session_id=? AND operation=? AND idempotency_key=?",
                (owner, session, operation, idempotency_key),
            ).fetchone()
            if hit is not None:
                if hit["request_digest"] != digest:
                    raise ContractError("IDEMPOTENCY_CONFLICT", idempotency_key)
                run = conn.execute(
                    "SELECT run_id FROM agent_runs WHERE assignment_id=? "
                    "ORDER BY attempt_no LIMIT 1", (hit["assignment_id"],),
                ).fetchone()
                conn.rollback()
                return {"agent_id": hit["agent_id"], "assignment_id": hit["assignment_id"],
                        "run_id": run["run_id"] if run else "", "status": hit["status"],
                        "replayed": True, "contract_version": CONTRACT_VERSION}
        agent = conn.execute(
            "SELECT owner_user_id, lifecycle_status FROM agent_registry WHERE agent_id=?",
            (agent_id,),
        ).fetchone()
        if agent is None:
            raise ContractError("INVALID_SCOPE", "ukendt agent")
        if agent["owner_user_id"] not in (owner, LEGACY_UNSCOPED):
            raise ContractError("POLICY_DENIED", "agenten tilhører en anden ejer")
        if agent["owner_user_id"] == LEGACY_UNSCOPED:
            raise ContractError("POLICY_DENIED", "legacy_unscoped agent kan ikke dispatches")
        if agent["lifecycle_status"] in ("closing", "closed"):
            raise ContractError("POLICY_DENIED", f"agenten er {agent['lifecycle_status']}")
        busy = conn.execute(
            "SELECT 1 FROM agent_assignments WHERE agent_id=? AND status IN "
            "('queued','active','waiting') LIMIT 1", (agent_id,),
        ).fetchone()
        if busy is not None:
            raise ContractError("CAPACITY", "agenten har allerede et aktivt assignment")
        from core.runtime.db_agent_capacity import assert_queue_capacity
        assert_queue_capacity(conn, parent_agent_id=parent_agent_id)
        now = _now_iso()
        from core.runtime.db_agent_deadlines import initial_queue_deadline
        queue_deadline = initial_queue_deadline()
        assignment_id = f"asg-{uuid.uuid4().hex[:16]}"
        run_id = f"run-{uuid.uuid4().hex[:16]}"
        conn.execute(
            "INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id, "
            "origin_session_id, parent_agent_id, parent_run_id, goal, input_refs_json, "
            "expected_result, target, deadline_at, budget_json, created_by, operation, "
            "idempotency_key, request_digest, status, created_at, updated_at, queue_deadline_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'queued', ?, ?, ?)",
            (assignment_id, agent_id, owner, session, parent_agent_id, parent_run_id,
             goal, json.dumps(input_refs or []), expected_result, target, deadline_at,
             json.dumps(budget or {}), created_by, operation, idempotency_key, digest,
             now, now, queue_deadline),
        )
        conn.execute(
            "INSERT INTO agent_runs (run_id, agent_id, status, assignment_id, "
            "owner_user_id, attempt_no, created_at, updated_at) "
            "VALUES (?,?, 'queued', ?, ?, 1, ?, ?)",
            (run_id, agent_id, assignment_id, owner, now, now),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return {"agent_id": agent_id, "assignment_id": assignment_id, "run_id": run_id,
            "status": "queued", "replayed": False, "contract_version": CONTRACT_VERSION}


def commit_terminal_outcome(
    *,
    assignment_id: str,
    status: str,
    summary: str = "",
    error_code: str = "",
    error_phase: str = "",
    artifact_ref: str = "",
    last_run_id: str = "",
    artifact_error: str = "",
    only_from: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Fastlæg assignmentets samlede udfald OG dets ene terminalbesked i SAMME
    transaktion. Et gentaget kald returnerer den eksisterende besked uden at
    ændre noget: terminale statusser er uforanderlige (§4, §6)."""
    if status not in ASSIGNMENT_TERMINAL:
        raise ContractError("INVALID_TRANSITION", f"{status} er ikke terminal")
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        a = conn.execute(
            "SELECT * FROM agent_assignments WHERE assignment_id=?", (assignment_id,)
        ).fetchone()
        if a is None:
            raise ContractError("INVALID_SCOPE", "ukendt assignment")
        existing = conn.execute(
            "SELECT * FROM agent_result_outbox WHERE assignment_id=? AND result_type=?",
            (assignment_id, RESULT_TYPE),
        ).fetchone()
        if a["status"] in ASSIGNMENT_TERMINAL:
            conn.rollback()
            return {"committed": False, "assignment_status": a["status"],
                    "message": _row(existing)}
        if only_from is not None and a["status"] not in only_from:
            conn.rollback()
            return {"committed": False, "assignment_status": a["status"], "message": None}
        last = last_run_id or (conn.execute(
            "SELECT run_id FROM agent_runs WHERE assignment_id=? "
            "ORDER BY attempt_no DESC LIMIT 1", (assignment_id,)).fetchone() or {"run_id": ""}
        )["run_id"]
        attempts = [r["run_id"] for r in conn.execute(
            "SELECT run_id FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no",
            (assignment_id,))]
        now = _now_iso()
        payload = {
            "status": status, "error_code": error_code, "error_phase": error_phase,
            "summary": summary, "agent_id": a["agent_id"], "assignment_id": assignment_id,
            "last_run_id": last, "attempt_run_ids": attempts, "artifact_ref": artifact_ref,
            "artifact_error": artifact_error,
        }
        conn.execute(
            "UPDATE agent_assignments SET status=?, outcome_json=?, terminal_at=?, "
            "updated_at=? WHERE assignment_id=?",
            (status, json.dumps(payload), now, now, assignment_id),
        )
        if status == "timed_out" and only_from == ("queued",):
            conn.execute("UPDATE agent_runs SET status='timed_out', error_phase=?, error_code=?, "
                         "failure_reason=?, finished_at=?, updated_at=? "
                         "WHERE run_id=? AND status='queued'",
                         (error_phase, error_code, summary, now, now, last))
            conn.execute("UPDATE agent_registry SET status='expired', expired_at=?, updated_at=? "
                         "WHERE agent_id=?", (now, now, a["agent_id"]))
        message_id = f"msg-{uuid.uuid4().hex[:16]}"
        conn.execute(
            "INSERT INTO agent_result_outbox (message_id, assignment_id, result_type, "
            "owner_user_id, origin_session_id, sender_agent_id, recipient_agent_id, "
            "parent_run_id, last_run_id, payload_json, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (message_id, assignment_id, RESULT_TYPE, a["owner_user_id"],
             a["origin_session_id"], a["agent_id"], a["parent_agent_id"],
             a["parent_run_id"], last, json.dumps(payload), now, now),
        )
        from core.runtime.db_agent_wait import evaluate_in_tx
        fired = evaluate_in_tx(conn, assignment_id)  # ventekontrakter, samme transaktion
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    # Beslutningsgrundlaget fryses EFTER udfalds-committet, men før forælderen
    # kan have handlet på det: ventekontrakten er netop fyret, og vækningen sker
    # i et senere tick. Rækken bærer assignment_id i `refs`, så eksperimentet
    # «beslutningskvalitet vs. udfald» kan koble valg til udfald mekanisk i
    # stedet for at rekonstruere begrundelsen bagefter (16/11-2026).
    try:
        from core.runtime.db_credit_assignment import record_agent_outcome_choice
        record_agent_outcome_choice(
            assignment_id=assignment_id,
            agent_id=a["agent_id"],
            parent_run_id=a["parent_run_id"],
            status=status,
            summary=summary,
            error_code=error_code,
            error_phase=error_phase,
            attempt_run_ids=attempts,
        )
    except Exception:
        logger.warning("beslutningsgrundlag kunne ikke fryses for %s", assignment_id,
                       exc_info=True)
    # Agentens egen erindring: deterministisk resume af DETTE assignment, efter committet. En fejl
    # her registreres som hukommelsesfejl og aendrer aldrig udfaldet (§7.2).
    from core.runtime.db_agent_memory import project_summary
    project_summary(assignment_id)
    # Et afsluttet assignment har ingen aabne approvals og intet at genoptage (F4b).
    try:
        from core.runtime.db_agent_approvals import cancel_for_assignment
        cancel_for_assignment(assignment_id=assignment_id, reason=f"assignmentet blev {status}")
        ck = _conn()          # ÉN forbindelse: et nyt _conn()-kald ruller en aaben transaktion tilbage
        ck.execute("UPDATE agent_checkpoints SET status='discarded' WHERE assignment_id=? AND status='parked'",
                   (assignment_id,))
        # Run-raekken maa ikke blive staaende i waiting_for_approval naar
        # assignmentet er terminalt. Det er den samme zombie som
        # ``agent_parking.py`` beskriver og loeser for sin vej — men ad DENNE
        # vej blev checkpointet discarded uden at runnet blev lukket.
        #
        # Maalt 22/10-2026: asg-4bea67d6cc004dd4 var 'cancelled', agenten var
        # 'cancelled', checkpointet var 'discarded' — og runnet stod stadig
        # 'waiting_for_approval'. Fordi ``decided_parked()`` kun ser checkpoints
        # der ER 'parked', faldt raekken ud af oprydningen og blev aldrig samlet
        # op: den holdt kortet i «venter» for evigt. Et run i waiting_for_approval
        # kan ikke vaere afsluttet paa anden vis, saa 'cancelled' er den aerlige
        # status her — det er hvad der skete med det.
        _nu = _now_iso()
        ck.execute("UPDATE agent_runs SET status='cancelled', finished_at=?, updated_at=? "
                   "WHERE assignment_id=? AND status='waiting_for_approval'",
                   (_nu, _nu, assignment_id))
        ck.commit()
    except Exception:
        logger.warning("kunne ikke rydde approvals for %s", assignment_id, exc_info=True)
    _signal_feed(assignment_id)
    if fired:
        from core.runtime.db_agent_wait import materialize_pending_wakes
        try:
            materialize_pending_wakes()
        except Exception:
            logger.warning("vaekning kunne ikke skrives nu; tages op af dispatcheren",
                           exc_info=True)
    return {"committed": True, "assignment_status": status,
            "message": _row(conn.execute(
                "SELECT * FROM agent_result_outbox WHERE message_id=?", (message_id,)
            ).fetchone())}


def _signal_feed(assignment_id: str) -> None:
    """Meld terminaludfaldet til Desks feed straks (G). Fejler det, tager supervisor-tikket det op -
    udfaldet og dets outbox-besked er allerede committet, saa intet kan gaa tabt."""
    try:
        from core.runtime.db_agent_feed import signal_changes
        signal_changes()
    except Exception:
        logger.warning("feed-signal for %s kunne ikke udsendes nu; tages op af supervisor-tikket",
                       assignment_id, exc_info=True)


def advance_delivery(*, message_id: str, owner_user_id: str, to_status: str) -> dict[str, Any]:
    """Flyt en terminalbesked fremad i leveringskæden. Kun fremad, kun ejeren."""
    if to_status not in DELIVERY_STATES:
        raise ContractError("INVALID_TRANSITION", to_status)
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        m = conn.execute(
            "SELECT * FROM agent_result_outbox WHERE message_id=? AND owner_user_id=?",
            (message_id, owner_user_id),
        ).fetchone()
        if m is None:
            raise ContractError("INVALID_SCOPE", "ukendt besked for denne ejer")
        if DELIVERY_STATES.index(to_status) <= DELIVERY_STATES.index(m["delivery_status"]):
            conn.rollback()
            return _row(m)  # idempotent: aldrig baglæns, aldrig dobbelt claim
        conn.execute(
            "UPDATE agent_result_outbox SET delivery_status=?, updated_at=? "
            "WHERE message_id=?", (to_status, _now_iso(), message_id),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return _row(_conn().execute(
        "SELECT * FROM agent_result_outbox WHERE message_id=?", (message_id,)).fetchone())


def list_pending_results(*, owner_user_id: str, origin_session_id: str) -> list[dict[str, Any]]:
    """Ubehandlede terminalbeskeder for NETOP denne ejer og session."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    rows = _conn().execute(
        "SELECT * FROM agent_result_outbox WHERE owner_user_id=? AND origin_session_id=? "
        "AND delivery_status != 'acknowledged' ORDER BY created_at", (owner, session),
    ).fetchall()
    return [_row(r) for r in rows]


def get_assignment(*, assignment_id: str, owner_user_id: str) -> dict[str, Any] | None:
    """Ejerfiltreret opslag; en anden ejers assignment er `None`, ikke 403."""
    return _row(_conn().execute(
        "SELECT * FROM agent_assignments WHERE assignment_id=? AND owner_user_id=?",
        (assignment_id, owner_user_id),
    ).fetchone())


# --- A2: kobling til den eksisterende agent-livscyklus -----------------------

# Registry-status -> assignmentets terminale status. `failed` for en
# PERSISTENT agent er et forsoeg, der genplanlaegges med backoff, ikke et
# slutresultat (§6), og saettes derfor ikke her.
_SETTLING = {"completed": "completed", "failed": "failed",
             "cancelled": "cancelled", "expired": "timed_out",
             # en persistent agent gaar til `scheduled` naar en aktivering er faerdig (G, §12.1)
             "scheduled": "completed"}
_ERROR_PHASE = {"failed": "model", "cancelled": "recovery", "expired": "budget",
                # 18/11-2026: `timed_out` er en TERMINAL status (`_SETTLING` mapper
                # `expired` hertil), men manglede som noegle — saa et opslag paa den
                # terminale status gav ("", "") i stedet for en fase. Maalt: en
                # QUEUE_DEADLINE-raekke stod med en tom etikette.
                "timed_out": "budget"}
_ERROR_CODE = {"failed": "AGENT_FAILED", "cancelled": "CANCELLED", "expired": "TIMED_OUT",
               "timed_out": "TIMED_OUT"}

#: Koder der beskriver at ASSIGNMENTET blev lukket — ikke hvorfor det fejlede.
#: `RUN_ORPHANED` skrives af `close_orphan_runs` naar assignmentet var terminalt foer
#: leasen udloeb; `RUN_STALE` af `close_stale_runs` naar ingen ejede raekken laengere.
#: De er observationer af en LUKNING, og en fase bygget paa dem ville paastaa en aarsag
#: vi ikke har. Maalt 18/11-2026: 16 runs baerer en af dem, og 9 af 19 faseskift var
#: en meta-kode der blev laest som en aarsag.
_META_KODER = frozenset({"RUN_ORPHANED", "RUN_STALE"})

#: Den ene fase der er GAETTET af tabellen frem for observeret. Kun den maa en
#: senere, bedre kilde rette bagud — en specifik fase (`execution`, `budget`) kan
#: vaere skrevet af en kilde der vidste mere end leasing-stien goer.
_GAETTET_FASE = frozenset({"model"})


#: Workerens egne koder (``agent_worker_runner.WorkerError``) -> (kode, fase).
#:
#: 18/11-2026: fejlhandleren i ``agent_runtime_spawn`` laeste
#: ``getattr(exc, "error_code", "")`` — men ``WorkerError`` gemmer koden i
#: ``.code``. Feltet fandtes ikke, saa hver worker-fejl faldt til tabellen og
#: paastod at MODELLEN fejlede. Maalt i den levende DB: 5 af 5 runs med
#: ``CANCELLED: agenten blev annulleret`` stod som ``AGENT_FAILED``/``model``,
#: og de 5 var 5 af de 8 ``AGENT_FAILED`` der findes.
#:
#: Fasen er familien, koden er praecisionen — samme moenster som
#: ``LEASE_EXPIRED``/``recovery`` og ``CLI_BACKEND_FAILED``/``execution``.
#: ``cancelled`` og ``approval`` er nye faser, fordi de to ellers ville blive
#: rapporteret som fejl i noget der ikke fejlede: en annullering er et tilsigtet
#: stop, og en afventende godkendelse er en pause — ikke et sammenbrud.
_WORKER_FEJL: dict[str, tuple[str, str]] = {
    "PROTOCOL": ("WORKER_PROTOCOL", "execution"),
    "TOOL_NOT_ALLOWED": ("TOOL_NOT_ALLOWED", "execution"),
    "CAPACITY": ("WORKER_CAPACITY", "budget"),
    "APPROVAL_PENDING": ("APPROVAL_PENDING", "approval"),
    "OUTCOME_UNKNOWN": ("OUTCOME_UNKNOWN", "recovery"),
    "LEASE_LOST": ("LEASE_LOST", "recovery"),
    "TIMEOUT": ("WORKER_TIMEOUT", "execution"),
    "CANCELLED": ("CANCELLED", "cancelled"),
    "WORKER_DIED": ("WORKER_DIED", "execution"),
    "WORKER_ERROR": ("WORKER_ERROR", "execution"),
}


def worker_error_kode(code: str) -> tuple[str, str]:
    """(error_code, error_phase) for en ``WorkerError``-kode — ellers ("", "").

    Eksakt match, ikke ``.upper()``: ``CheapProviderError`` baerer ogsaa en
    ``.code``, men i smaa bogstaver (``timeout``, ``unreachable``). En
    normalisering ville goere en provider-timeout til en worker-fejl.
    """
    return _WORKER_FEJL.get(str(code or ""), ("", ""))


def bind_agent_owner(*, agent_id: str, owner_user_id: str, owner_session_id: str) -> None:
    """Stempl den autentificerede ejer paa agenten. Skriver kun naar agenten
    endnu er `legacy_unscoped`; en eksisterende ejer ændres aldrig (§4)."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(owner_session_id, "owner_session_id")
    conn = _conn()
    conn.execute(
        "UPDATE agent_registry SET owner_user_id=?, owner_session_id=? "
        "WHERE agent_id=? AND owner_user_id=?", (owner, session, agent_id, LEGACY_UNSCOPED))
    conn.commit()


def queued_contract_run(agent_id: str) -> str:
    """Id på det run accept_assignment forudoprettede og som endnu ikke er startet."""
    r = _conn().execute(
        "SELECT run_id FROM agent_runs WHERE agent_id=? AND assignment_id != '' "
        "AND status='queued' AND started_at='' ORDER BY attempt_no LIMIT 1", (agent_id,),
    ).fetchone()
    return r["run_id"] if r else ""


def adopt_run(*, agent_id: str, run_id: str) -> str:
    """Bind et nyoprettet run til agentens åbne assignment som næste forsøg.
    Returnerer assignment_id, eller "" når agenten ikke har et (legacy-vej)."""
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        run = conn.execute("SELECT assignment_id FROM agent_runs WHERE run_id=?",
                           (run_id,)).fetchone()
        if run is None:
            conn.rollback()
            return ""
        if run["assignment_id"]:
            conn.execute("UPDATE agent_assignments SET status='active', updated_at=? "
                         "WHERE assignment_id=? AND status='queued'",
                         (_now_iso(), run["assignment_id"]))
            conn.commit()
            return run["assignment_id"]
        a = conn.execute(
            "SELECT assignment_id, owner_user_id FROM agent_assignments WHERE agent_id=? "
            "AND status IN ('queued','active','waiting') ORDER BY created_at DESC LIMIT 1",
            (agent_id,)).fetchone()
        if a is None:
            conn.rollback()
            return ""
        n = conn.execute("SELECT COALESCE(MAX(attempt_no),0)+1 FROM agent_runs "
                         "WHERE assignment_id=?", (a["assignment_id"],)).fetchone()[0]
        conn.execute("UPDATE agent_runs SET assignment_id=?, owner_user_id=?, attempt_no=? "
                     "WHERE run_id=?", (a["assignment_id"], a["owner_user_id"], n, run_id))
        conn.execute("UPDATE agent_assignments SET status='active', updated_at=? "
                     "WHERE assignment_id=? AND status='queued'",
                     (_now_iso(), a["assignment_id"]))
        conn.commit()
        return a["assignment_id"]
    except BaseException:
        conn.rollback()
        raise


#: Kendte infrastruktur-aarsager i `agent_registry.last_error` -> (kode, fase).
#: Teksterne skrives af `agent_runtime_spawn` selv (`_auto_cleanup` og
#: `recover_crashed_agents`), saa de er et lukket, kendt saet — ikke fri tekst
#: der skal tolkes. Uden denne tabel faldt begge tilbage paa `model`.
_INFRA_LAST_ERROR = (
    ("auto_cleanup_stale_failed_after_", "AGENT_RECLAIMED", "recovery"),
    ("process restarted while agent was active", "AGENT_RESTARTED", "recovery"),
)


def _infra_aarsag(last_error: str) -> tuple[str, str]:
    """(kode, fase) for en kendt infrastruktur-aarsag — ellers ("", "")."""
    tekst = str(last_error or "")
    for praefiks, kode, fase in _INFRA_LAST_ERROR:
        if praefiks in tekst:
            return kode, fase
    return "", ""


def _run_fejlkode(conn: Any, assignment_id: str) -> tuple[str, str]:
    """(error_code, error_phase) fra det seneste run under assignmentet der HAR en kode.

    En orphan-marker kan vaere skrevet EFTER assignmentet blev terminalt og er tom
    paa settle-tidspunktet — men det underliggende run har koden. Derfor: nyeste
    run med en ikke-tom kode, ikke blot det nyeste run.

    17/11-2026: funktionen findes fordi `settle_agent_status` faldt tilbage paa en
    fast tabel (`AGENT_FAILED`/`model`) naar agentens tekst var tom. Maalt paa de
    65 fejlede assignments: runnet bar `LEASE_EXPIRED`, `CLI_QUOTA_EXHAUSTED`,
    `RUN_STALE` eller `CLI_BACKEND_FAILED` — kun 2 af 26 var aegte model-fejl.
    """
    row = conn.execute(
        "SELECT error_code, error_phase FROM agent_runs WHERE assignment_id=? "
        "AND COALESCE(error_code,'') != '' "
        # `RUN_ORPHANED` beskriver at ASSIGNMENTET blev lukket, ikke hvad der gik
        # galt — og den skrives typisk EFTER det ægte run. Maalt paa
        # `asg-d96dabe04904478c`: LEASE_EXPIRED kl. 21:00:03, orphan-markeren kl.
        # 21:05:38. Uden denne sortering arvede vi meta-koden og skjulte aarsagen.
        # Begge meta-koder nedprioriteres: `RUN_STALE` skrives af den periodiske
        # fanger og kan lande efter den aegte kode praecis som `RUN_ORPHANED`.
        "ORDER BY (error_code IN ('RUN_ORPHANED','RUN_STALE')), "
        "finished_at DESC, attempt_no DESC LIMIT 1",
        (assignment_id,)).fetchone()
    if row is None:
        return "", ""
    return str(row["error_code"] or ""), str(row["error_phase"] or "")


def reclassify_terminal_outcome(conn: Any, assignment_id: str) -> bool:
    """Ret en GAETTET fase paa et allerede terminalt assignment.

    18/11-2026 (defekt 1, vej b): koden kan ankomme EFTER settle.
    ``close_orphan_runs`` kaldes netop fordi assignmentet blev terminalt foer leasen
    udloeb — saa ``settle_agent_status`` skrev ``AGENT_FAILED``/``model`` (tabellens
    gaet), og bagefter skrev leasing-stien ``RUN_ORPHANED`` paa runnet. Ingen rettede
    assignmentets ``outcome_json`` bagud.

    Maalt paa 288 gemte assignments: 26 stod med fase ``model``, 19 blev modsagt af
    runnets egen kode — og **14 af de 19 fik koden efter** assignmentets terminale
    tid. Vej (a) (settle slaar koden op igen) kan ikke loese dem: koden fandtes ikke.

    Kun ``_GAETTET_FASE`` rettes. En fase der allerede er specifik roeres ikke — den
    kan vaere skrevet af en kilde der vidste mere end leasing-stien goer. Returnerer
    True naar rækken blev rettet.
    """
    row = conn.execute("SELECT outcome_json FROM agent_assignments WHERE assignment_id=?",
                       (assignment_id,)).fetchone()
    if row is None or not row["outcome_json"]:
        return False
    try:
        outcome = json.loads(row["outcome_json"])
    except Exception:
        logger.warning("outcome_json kunne ikke læses for %s", assignment_id)
        return False
    if str(outcome.get("error_phase") or "") not in _GAETTET_FASE:
        return False
    kode, fase = _run_fejlkode(conn, assignment_id)
    if not kode:
        return False
    if kode in _META_KODER:
        fase = "unknown"
    if kode == str(outcome.get("error_code") or "") and fase == str(outcome.get("error_phase") or ""):
        return False
    outcome["error_code"] = kode
    outcome["error_phase"] = fase
    conn.execute("UPDATE agent_assignments SET outcome_json=? WHERE assignment_id=?",
                 (json.dumps(outcome, ensure_ascii=False), assignment_id))
    return True


def partial_delivery_error(
    *,
    full: str,
    registry_status: str,
    run_error_code: str = "",
    run_error_phase: str = "",
    last_error: str = "",
) -> tuple[str, str]:
    """(error_code, error_phase) for et terminalt udfald.

    26/10-2026: en DELVIS leverance er ikke en model-fejl.

    Maalt paa `asg-4a79ab1ca3094db2`: agenten svarede paa 1 af 3 spoergsmaal, og
    markeringen "UFULDSTÆNDIG (N ubesvarede spoergsmaal)" stod i resultatet.
    Alligevel blev udfaldet stemplet `AGENT_FAILED` med `error_phase: "model"` —
    det paastaar at MODELLEN fejlede, naar den faktisk arbejdede (6 vaerktoejskald)
    og leverede et korrekt svar paa det foerste spoergsmaal. En agent der stoppede
    midt i, fejlede i LEVERANCEN, ikke i modelkaldet. Fasen skal sige det den ved,
    ellers leder den naeste mig efter den forkerte aarsag.

    17/11-2026: tabellen var FOERSTE udvej, ikke sidste.

    Maalt paa de 65 fejlede assignments: 26 blev stemplet `AGENT_FAILED`/`model`,
    men runnet under dem bar `LEASE_EXPIRED`, `CLI_QUOTA_EXHAUSTED`, `RUN_STALE`
    eller `CLI_BACKEND_FAILED` — kun 2 af de 26 var aegte model-fejl. Tabellen
    blev brugt hver gang teksten var tom (17 af 26), og den paastod dermed
    "modellen fejlede" om infrastruktur. Konsekvensen var ikke kosmetisk: 23 af
    de 26 fik intet nyt forsoeg, fordi assignmentet blev terminalt foer leasen
    udloeb — et arbejde der blev draebt af en genstart og bagefter bebrejdet
    modellen.

    Raekkefoelgen er derfor: markeringen (den mest specifikke) -> runnets egen
    kode (den observerede aarsag) -> kendt infrastruktur-tekst -> tabellen.
    """
    text = str(full or "")
    if text.strip() and "UFULDSTÆNDIG" in text:
        return _incomplete_kode(text)
    kode = str(run_error_code or "").strip()
    if kode:
        if kode in _META_KODER:
            # Koden bevares — den er observeret. Men fasen maa ikke paastaa en aarsag:
            # `recovery` siger "vi genoprettede", og det er ikke det samme som
            # "vi ved ikke hvorfor". `unknown` er den aerlige etikette.
            return kode, "unknown"
        fase = str(run_error_phase or "").strip() or _ERROR_PHASE.get(registry_status, "")
        return kode, fase
    kode, fase = _infra_aarsag(last_error)
    if kode:
        return kode, fase
    return _ERROR_CODE.get(registry_status, ""), _ERROR_PHASE.get(registry_status, "")


def error_fra_exception(
    exc: BaseException,
    *,
    registry_status: str = "failed",
    full: str = "",
    last_error: str = "",
) -> tuple[str, str]:
    """(error_code, error_phase) for en vilkaarlig undtagelse fra agent-koerslen.

    18/11-2026: raekkefoelgen er markeringen -> undtagelsens egne felter ->
    workerens kode -> den eksisterende kaede i :func:`partial_delivery_error`.

    Undtagelsens ``code`` gates paa TYPEN og ikke paa feltnavnet, fordi flere
    undtagelser baerer et ``.code`` med hver sin betydning (``ContractError``,
    ``CheapProviderError``, ``WorkerError``).
    """
    text = str(full or "")
    if text.strip() and "UFULDSTÆNDIG" in text:
        return _incomplete_kode(text)
    kode = str(getattr(exc, "error_code", "") or "").strip()
    if kode:
        fase = str(getattr(exc, "error_phase", "") or "").strip()
        return kode, fase or _ERROR_PHASE.get(registry_status, "")
    try:
        from core.services.agent_worker_runner import WorkerError
    except Exception:  # pragma: no cover — worker-modulet er altid der
        WorkerError = ()  # type: ignore[assignment]
    if isinstance(exc, WorkerError):
        kode, fase = worker_error_kode(str(getattr(exc, "code", "") or ""))
        if kode:
            return kode, fase
    return partial_delivery_error(
        full=full, registry_status=registry_status, last_error=last_error)


def _markering_grund(text: str) -> str:
    """Årsagen inde i markeringen: ``UFULDSTÆNDIG (<grund>) — agentens tekst:``.

    ``agent_runtime_base._loop_result`` skriver allerede den ægte grund ind i
    parentesen (``stop_reason``, antal ubesvarede spørgsmål, eller
    ``"rundebudgettet løb ud efter N runder"``). Indtil 11/11-2026 blev den
    kastet væk: klassifikationen læste kun ordet ``UFULDSTÆNDIG`` og kaldte
    alt for det samme. Grunden er den eneste kilde der kan skelne dem.
    """
    m = re.search(r"UFULDSTÆNDIG\s*\(([^\n]*?)\)", str(text or ""))
    return m.group(1).strip() if m else ""


#: Grunde der betyder at agenten blev STOPPET af en ressource — ikke at dens
#: leverance var mangelfuld. Det er to forskellige jagter: kapacitet peger på
#: budgettet, leverance peger på agentens arbejde.
_KAPACITETS_GRUND = ("rundebudgettet", "deadline")


def _incomplete_kode(text: str) -> tuple[str, str]:
    """(error_code, error_phase) for en ``UFULDSTÆNDIG``-markering — splittet på grunden.

    11/11-2026: én etiket skjulte mindst tre ægte årsager. Målt i drift på de 38
    agentfejl: de blev alle stemplet ``AGENT_INCOMPLETE``/``delivery``, uanset om
    agenten (a) blev klippet af rundebudgettet, (b) kunne skrive men skrev intet,
    eller (c) sluttede med et løfte om næste skridt i stedet for et resultat.
    Etiketten var derfor ikke forkert — den var ubrugelig: den sendte den næste
    mig efter "leverancen" i alle tre tilfælde, også når den ægte årsag var at
    ressourcegrænsen ramte midt i arbejdet.

    ``AGENT_INCOMPLETE``/``delivery`` bevares som fallback for grunde der ikke
    kendes (fx "N spørgsmål uden nummereret svar"), så eksisterende læsere og
    test ikke brækker. De nye koder er mere specifikke, ikke en anden familie.
    """
    grund = _markering_grund(text)
    if any(n in grund for n in _KAPACITETS_GRUND):
        return "AGENT_BUDGET_EXHAUSTED", "capacity"
    # 18/11-2026: en blokeret agent skrev heller intet — men det var miljøet der
    # stoppede den, ikke dens leverance. Teksten sættes i `agent_loop_core`
    # (`_blokerings_grund`); den må ikke forveksles med den nedenstående, for de
    # sender den næste jagt to forskellige steder hen.
    if "blev blokeret af miljøet" in grund:
        return "AGENT_BLOCKED_BY_ENVIRONMENT", "environment"
    if "kunne skrive men skrev intet" in grund:
        return "AGENT_NO_WRITE", "delivery"
    if "løfte" in grund:
        return "AGENT_PROMISED_NOT_DONE", "delivery"
    return "AGENT_INCOMPLETE", "delivery"


# Hvor tidligt i svaret en erklaering skal staa for at taelle. En agent der
# RAPPORTERER om en anden agents erklaering midt i en lang tekst er ikke selv
# declined — derfor et vindue og ikke en soegning i hele teksten.
_DECLINE_VINDUE = 250

# Erklaeringen skal naevne OPGAVEN. Det er det ord der giver praecision:
# «jeg kunne ikke loese det med vaerktoej X, men fandt en anden vej» rammes
# ikke, og det er netop den saetning en for bred markoer ville oede.
_DECLINE_MOENSTRE = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"jeg\s+kan\s+ikke\s+l[øo]se\s+opgaven",
    r"jeg\s+kunne\s+ikke\s+l[øo]se\s+opgaven",
    r"jeg\s+kan\s+ikke\s+udf[øo]re\s+opgaven",
    r"jeg\s+kunne\s+ikke\s+udf[øo]re\s+opgaven",
    r"jeg\s+kan\s+ikke\s+gennemf[øo]re\s+opgaven",
    r"jeg\s+er\s+ikke\s+i\s+stand\s+til\s+at\s+l[øo]se\s+opgaven",
    r"opgaven\s+kan\s+ikke\s+l[øo]ses",
))


def decline_error(*, text: str) -> tuple[str, str]:
    """(error_code, error_phase) naar agenten SELV melder at opgaven ikke kunne loeses.

    MAALT 4/11-2026 i `agent_runs` (7 dage, status='completed', n=4): alle fire
    havde et svar der erklaerede at opgaven ikke kunne loeses, og alle fire stod
    som `completed` med `error_code=''` og `error_phase=''`.

    Skarpest: `agent-71b2452a7d0e42e79395f4a38d3109e7` svarede ordret «Jeg kan
    ikke loese opgaven: mit vaerktoejssaet i denne sandbox indeholder ikke …» —
    og blev stemplet `completed`, `provider_status=completed`, `tool_calls=1`.
    Den HAVDE `wt_bash` og `wt_write_file`. Der findes derfor INTET strukturelt
    signal at laese paa den anden side: agent-loekken rapporterede selv succes,
    og der blev kaldt et vaerktoej. Markoeren maa vaere en erklaering.

    HVORFOR EN EGEN KODE OG EN EGEN STATUS
    `AGENT_INCOMPLETE`/`delivery` (26/10) betyder «agenten blev afbrudt midt i».
    Det er en anden jagt end «agenten vurderede at den ikke kunne» — slaas de
    sammen, kan den naeste mig ikke se forskel. Status er `declined`, ikke
    `failed`: agenten LEVEREDE et svar, og leverancen skal bevares. En
    `failed`-status ville kaste arbejdet vaek for at faa signalet.

    GROENSEN — og den er aegte: en agent der skriver «jeg kan ikke loese opgaven
    med X, MEN jeg loeste den med Y» inden for de foerste 250 tegn bliver
    fejlagtigt stemplet. Prisen er lav netop fordi `declined` bevarer
    leverancen: intet arbejde gaar tabt, kun signalet bliver forkaert. Det er
    den bevidste afvejning, ikke en forglemmelse.
    """
    hoved = str(text or "").strip()[:_DECLINE_VINDUE]
    if not hoved:
        return "", ""
    for m in _DECLINE_MOENSTRE:
        if m.search(hoved):
            return "AGENT_DECLINED", "capability"
    return "", ""


def latest_agent_reply(conn: Any, agent_id: str) -> str:
    """Agentens seneste leverance til Jarvis — markeringen foretraekkes (26/10-2026).

    MAALT 26/10-2026 paa `asg-bcbee979ef364037`: spawn bevarede den delvise
    leverance som `kind='result'` (22:21:50.931) og skrev 1 ms senere
    `kind='failure'` (22:21:50.932). Det gamle opslag tog den NYESTE besked inden
    for `('result','')`, ramte `failure`-beskeden — som laa uden for filteret — og
    fik `None`. `full` blev tom, `partial_delivery_error` faldt tilbage paa
    `AGENT_FAILED`/`model`, og markeringen blev aldrig laest.

    `failure` foretraekkes: den baerer markeringen OG hele agentens tekst
    ("UFULDSTÆNDIG (N …) — agentens tekst: …"), mens `result` kun baerer den raa
    tekst uden markering.
    """
    # 27/10-2026: `failure` er KORTET NED til 350 tegn i spawn (agent_runtime_spawn.py),
    # saa agentens afsluttende linje — `DAEKNING: 1,2` — blev skaaret af. Maalt paa
    # `asg-8c08c689239f4ff8`: den fulde `result`-besked gav 2 ubesvarede (det sande tal),
    # mens den trunkerede `failure` gav 3 og slet ingen erklaering. Kontrakten blev derfor
    # laest paa en tekst hvor dens egen noegle var fjernet.
    #
    # Raekkefoelgen er nu: den FULDE tekst foerst. `failure` bruges kun naar den baerer
    # markeringen OG `result` ikke findes — ellers ville den trunkerede kopi vinde igen.
    rows = conn.execute(
        "SELECT kind, content FROM agent_messages WHERE agent_id=? AND direction='agent->jarvis' "
        "AND kind IN ('result','failure','') ORDER BY created_at DESC",
        (agent_id,)).fetchall()
    if not rows:
        return ""
    full_result = ""
    failure = ""
    for r in rows:
        body = str(r["content"] or "")
        if r["kind"] == "result" and not full_result:
            full_result = body
        elif r["kind"] == "failure" and not failure:
            failure = body
    # 27/10-2026: BEGGE halvdele skal med. `failure` baerer markeringen, `result` baerer
    # den fulde tekst — og spawn klipper `failure` ved 350 tegn, saa den alene mister
    # agentens afsluttende linje (maalt: `DAEKNING: 3` blev skaaret af).
    #
    # Maalt paa `asg-8c08c689239f4ff8`: `result` alene gav 2 ubesvarede men INGEN
    # markering; `failure` alene gav markeringen men en trunkeret tekst. Foerst den ene,
    # saa den anden = begge fejl tilbage. Derfor: markeringen FORAN den fulde tekst.
    if full_result.strip() and failure.strip() and "UFULDSTÆNDIG" in failure:
        if "UFULDSTÆNDIG" in full_result:
            return full_result
        # `failure` er "… UFULDSTÆNDIG (N …) — agentens tekst:\n<trunkeret>".
        # Behold markeringen, kast den trunkerede kopi, saet den fulde tekst ind.
        hoved = failure.split("— agentens tekst:", 1)[0].strip()
        return f"{hoved} — agentens tekst:\n{full_result}"
    if full_result.strip():
        return full_result
    return failure


def settle_agent_status(*, agent_id: str, registry_status: str) -> dict[str, Any] | None:
    """Kaldes når agentens registry-status bliver terminal. Fastlægger det åbne
    assignments udfald og den ene terminalbesked. `None` når intet skal ske."""
    target = _SETTLING.get(registry_status)
    if target is None:
        return None
    from core.runtime.db_agent_lease import scope_is_current
    if not scope_is_current():
        # En worker med udloebet/overtaget lease maa ikke skrive terminal status (§9).
        logger.warning("settle_agent_status afvist for %s: workerens lease er ikke laengere gaeldende",
                       agent_id)
        return None
    conn = _conn()
    agent = conn.execute("SELECT persistent, last_error FROM agent_registry WHERE agent_id=?",
                         (agent_id,)).fetchone()
    if agent is None or (registry_status == "failed" and agent["persistent"]):
        return None
    from core.runtime.db_agent_outcome_unknown import is_blocked
    if is_blocked(agent_id):
        # et uafklaret udfald afsluttes ALDRIG af en registry-status (timeout, annullering, sen succes): kun en
        # verificering eller en menneskelig afgoerelse (``resolve_outcome_unknown``) kan (§9, §12.2)
        logger.warning("settle_agent_status afvist for %s: uafklaret udfald", agent_id)
        return None
    if registry_status == "scheduled":
        # `scheduled` afslutter KUN en persistent aktivering hvis dens seneste run faktisk blev faerdigt;
        # efter en fejlet koersel er det et retry med backoff, ikke et udfald (§6).
        last = conn.execute("SELECT r.status FROM agent_runs r JOIN agent_assignments a "
                            "ON a.assignment_id = r.assignment_id WHERE a.agent_id=? AND a.status IN "
                            "('queued','active','waiting') ORDER BY r.attempt_no DESC LIMIT 1",
                            (agent_id,)).fetchone()
        if not agent["persistent"] or last is None or last["status"] != "completed":
            return None
    a = conn.execute("SELECT assignment_id FROM agent_assignments WHERE agent_id=? AND "
                     "status IN ('queued','active','waiting') ORDER BY created_at DESC LIMIT 1",
                     (agent_id,)).fetchone()
    if a is None:
        return None
    full = latest_agent_reply(conn, agent_id)
    # 17/11-2026: dommen skal laese runnets EGEN kode foer den falder tilbage paa
    # tabellen. Maalt paa de 65 fejlede assignments: runnet bar `LEASE_EXPIRED`,
    # `CLI_QUOTA_EXHAUSTED`, `RUN_STALE` eller `CLI_BACKEND_FAILED`, mens
    # assignmentet blev stemplet `AGENT_FAILED`/`model`.
    _run_kode, _run_fase = _run_fejlkode(conn, a["assignment_id"])
    # 26/10-2026: en DELVIS leverance er ikke en model-fejl.
    #
    # Maalt paa `asg-4a79ab1ca3094db2`: agenten svarede paa 1 af 3 spoergsmaal, og
    # markeringen "UFULDSTÆNDIG (N ubesvarede spoergsmaal)" stod i resultatet.
    # Alligevel blev udfaldet stemplet `AGENT_FAILED` med `error_phase: "model"` —
    # det paastaar at MODELLEN fejlede, naar den faktisk arbejdede (6 vaerktoejskald)
    # og leverede et korrekt svar paa det foerste spoergsmaal. En agent der stoppede
    # midt i, fejlede i LEVERANCEN, ikke i modelkaldet. Fasen skal sige det den ved,
    # ellers leder den naeste mig efter den forkerte aarsag.
    _error_code, _error_phase = partial_delivery_error(
        full=full, registry_status=registry_status,
        run_error_code=_run_kode, run_error_phase=_run_fase,
        last_error=str(agent["last_error"] or ""))
    owner = conn.execute("SELECT owner_user_id FROM agent_assignments WHERE assignment_id=?",
                         (a["assignment_id"],)).fetchone()["owner_user_id"]
    # Resultatfilen faerdiggoeres FOER den terminale DB-transaktion (§9).
    from core.runtime.db_agent_artifacts import write_terminal_artifacts
    # Skrivende kodeagent: aendringerne (diff, filer, commits) afleveres som artefakter og worktree'et
    # BEVARES - det merges aldrig herfra (§8.1).
    wt_summary = None
    try:
        from core.services.agent_worktrees import snapshot_for_assignment
        wt_summary = snapshot_for_assignment(assignment_id=a["assignment_id"])
    except Exception:
        logger.warning("worktree-aflevering fejlede for %s", a["assignment_id"], exc_info=True)
    art = write_terminal_artifacts(
        agent_id=agent_id, assignment_id=a["assignment_id"], owner_user_id=owner, status=target,
        reply=full, summary=full[:500], error_code=_error_code,
        error_phase=_error_phase, worktree=wt_summary)
    return commit_terminal_outcome(
        assignment_id=a["assignment_id"], status=target, summary=full[:500],
        error_code=_error_code,
        error_phase=_error_phase,
        artifact_ref=art["artifact_ref"], artifact_error=art["artifact_error"],
    )


def claim_pending_results(*, owner_user_id: str, origin_session_id: str) -> list[dict[str, Any]]:
    """Atomisk claim: alle ubehandlede (accepted/delivered) terminalbeskeder for
    netop denne ejer og session flyttes til `claimed_by_model_step` i ÉN
    transaktion og returneres. To samtidige kaldere deler dem aldrig."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        rows = conn.execute(
            "SELECT * FROM agent_result_outbox WHERE owner_user_id=? AND "
            "origin_session_id=? AND delivery_status IN ('accepted','delivered') "
            "ORDER BY created_at, message_id", (owner, session)).fetchall()
        now = _now_iso()
        for r in rows:
            conn.execute("UPDATE agent_result_outbox SET delivery_status="
                         "'claimed_by_model_step', updated_at=? WHERE message_id=?",
                         (now, r["message_id"]))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    out = []
    for r in rows:
        d = _row(r)
        d["delivery_status"] = "claimed_by_model_step"
        out.append(d)
    return out


# --- F1: opslag til service-laget --------------------------------------------

def find_assignment_by_key(*, owner_user_id: str, origin_session_id: str, operation: str,
                           idempotency_key: str) -> dict[str, Any] | None:
    """Findes der allerede et assignment for netop denne ejer/session/operation/noegle?"""
    if not idempotency_key:
        return None
    return _row(_conn().execute(
        "SELECT * FROM agent_assignments WHERE owner_user_id=? AND origin_session_id=? "
        "AND operation=? AND idempotency_key=?",
        (owner_user_id, origin_session_id, operation, idempotency_key)).fetchone())


def open_assignment_for_agent(agent_id: str) -> dict[str, Any] | None:
    return _row(_conn().execute(
        "SELECT * FROM agent_assignments WHERE agent_id=? AND status IN "
        "('queued','active','waiting') ORDER BY created_at DESC LIMIT 1", (agent_id,)).fetchone())


def count_open_assignments(*, owner_user_id: str = "", parent_agent_id: str = "") -> int:
    """Aabne assignments, globalt eller afgraenset til en ejer / en direkte parent."""
    q = "SELECT COUNT(*) FROM agent_assignments WHERE status IN ('queued','active','waiting')"
    args: list[Any] = []
    if owner_user_id:
        q += " AND owner_user_id=?"
        args.append(owner_user_id)
    if parent_agent_id:
        q += " AND parent_agent_id=?"
        args.append(parent_agent_id)
    return int(_conn().execute(q, args).fetchone()[0])


def set_lifecycle(*, agent_id: str, owner_user_id: str, lifecycle_status: str) -> bool:
    """Agentens livstidsstatus (available/active/suspended/closing/closed). Kun ejeren,
    og `closed` kan aldrig aabnes igen af et almindeligt kald (§4, §12.2)."""
    if lifecycle_status not in ("available", "active", "suspended", "closing", "closed"):
        raise ContractError("INVALID_TRANSITION", lifecycle_status)
    conn = _conn()
    cur = conn.execute(
        "UPDATE agent_registry SET lifecycle_status=?, closed_at=CASE WHEN ?='closed' THEN ? ELSE closed_at END "
        "WHERE agent_id=? AND owner_user_id=? AND lifecycle_status != 'closed'",
        (lifecycle_status, lifecycle_status, _now_iso(), agent_id, owner_user_id))
    conn.commit()
    return cur.rowcount == 1


def discard_unstarted_assignment(*, agent_id: str, owner_user_id: str) -> bool:
    """Fjern et assignment (og dets agent) der ALDRIG er startet: ingen terminalbesked,
    intet run med ``started_at``. Bruges naar en admission fejler EFTER accept (f.eks. et worktree der ikke
    kan reserveres), saa et afvist kald ikke efterlader et halvt barn (§11.1). Alt andet afvises.

    ## Hvorfor `queued` ikke laengere er betingelsen (8/10-2026)

    Vagten stod foer paa ``status='queued'`` som en proxy for «ikke startet».
    Den proxy holdt op med at vaere sand da den varige scheduler kom til: en ny
    assignment claimer en workerplads MED DET SAMME og staar derfor ``active``
    allerede i det oejeblik dispatch returnerer. Maalt ved integrationen af de
    fire produktionspunkter — status lige efter dispatch er ``active``, ikke
    ``queued``.

    Konsekvensen var at §11.1's oprydning aldrig kunne naa sit eget maal: en
    admission der fejler efter accept efterlod praecis det halve barn den er
    skrevet for at fjerne.

    De to betingelser der FAKTISK betyder «ingen effekt endnu» — intet run med
    ``started_at`` og ingen afsendt terminalbesked — blev tjekket hele tiden og
    tjekkes stadig, inde i den samme ``BEGIN IMMEDIATE``. Har en worker naaet at
    saette ``started_at``, afvises kaldet som foer. Workerpladsen frigives af sig
    selv: kapaciteten taelles paa ``status='active'``, og raekken slettes."""
    import shutil

    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        a = conn.execute("SELECT assignment_id FROM agent_assignments WHERE agent_id=? AND owner_user_id=? "
                         "AND status IN ('queued','active')", (agent_id, owner_user_id)).fetchall()
        if len(a) != 1:
            conn.rollback()
            return False
        aid = a[0]["assignment_id"]
        started = conn.execute("SELECT 1 FROM agent_runs WHERE assignment_id=? AND started_at != ''",
                               (aid,)).fetchone()
        sent = conn.execute("SELECT 1 FROM agent_result_outbox WHERE assignment_id=?", (aid,)).fetchone()
        others = conn.execute("SELECT 1 FROM agent_assignments WHERE agent_id=? AND assignment_id != ?",
                              (agent_id, aid)).fetchone()
        if started or sent or others:
            conn.rollback()
            return False
        run_ids = [r["run_id"] for r in conn.execute("SELECT run_id FROM agent_runs WHERE assignment_id=?",
                                                     (aid,)).fetchall()]
        for rid in run_ids:
            conn.execute("DELETE FROM agent_artifacts WHERE run_id=?", (rid,))
        conn.execute("DELETE FROM agent_assignment_mandates WHERE assignment_id=?", (aid,))
        conn.execute("DELETE FROM agent_runs WHERE assignment_id=?", (aid,))
        conn.execute("DELETE FROM agent_leases WHERE assignment_id=?", (aid,))
        conn.execute("DELETE FROM agent_assignments WHERE assignment_id=?", (aid,))
        conn.execute("DELETE FROM agent_messages WHERE agent_id=?", (agent_id,))
        conn.execute("DELETE FROM agent_registry WHERE agent_id=? AND owner_user_id=?", (agent_id, owner_user_id))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    from core.runtime.db_agent_artifacts import artifact_root
    shutil.rmtree(artifact_root() / agent_id, ignore_errors=True)
    return True
