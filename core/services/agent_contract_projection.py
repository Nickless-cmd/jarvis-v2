"""Desks projektion af agentkontrakten (agent-contract-v1 G, spec 10).

EN DB-projektion, som AgentInspector, Baggrundsjob-panelet og notifikationsfeedet alle laeser: "liste,
taeller og inspector laeser samme DB-projektion". Intet her kender HTTP; ruten er kun en adapter.

Regler, som koden - ikke en kommentar - haandhaever:

* EJEREN kommer udefra fra den autentificerede bruger, aldrig fra et request-felt. Hver forespoergsel
  filtrerer paa ``owner_user_id`` i SQL; en anden ejers agent, artefakt eller approval er "findes ikke",
  aldrig "forbudt" (ingen orakel). ``legacy_unscoped`` og tom ejer matcher ingen.
* Status afledes af assignment + SENESTE run (``classify``) paa EET sted. Desk udleder aldrig status af
  tekst, og en ukendt status er ``unknown`` + opmaerksomhed - tavshed er ikke succes.
* ``outcome_unknown`` laeses direkte fra run/assignment-status, saa projektionen virker uanset hvordan
  tilstanden skrives.
* Handlinger genbruger de EKSISTERENDE service-funktioner (``agent_contract_service``). Sessionen kommer fra
  agentens gemte oprindelsessession, ikke fra klienten. Kvitteringen siger "accepteret" - ikke "leveret"
  og ikke "stoppet": det afgoeres af den efterfoelgende projektion.
* Kortets resume er begraenset og redigeret; fuldt output kraever ``read_artifact`` (ejer + session).
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime import db_agent_artifacts as art
from core.runtime import db_agent_feed as feed_db
from core.runtime import db_agent_route
from core.runtime.db_agent_contract import (
    ASSIGNMENT_TERMINAL, CONTRACT_VERSION, LEGACY_UNSCOPED, ContractError, _conn,
)

logger = logging.getLogger(__name__)

# --- klassifikation ---------------------------------------------------------------------------

RUN_WAITING = ("waiting_for_client", "waiting_for_approval", "waiting_for_budget")
_RUN_ACTIVE = ("running", "active", "starting", "in_progress")
_RUN_FAILED = ("failed", "timed_out", "cancelled")

#: Buckets i hver gruppe. Taelleren for AKTIVE og antallet der kraever OPMAERKSOMHED er adskilte tal.
ACTIVE_BUCKETS = ("active", "settling", "retry_pending")
WAITING_BUCKETS = RUN_WAITING
TERMINAL_ATTENTION = ("failed", "timed_out", "cancelled")
#: Ventetilstande der kraever at brugeren goer noget (offline klient venter af sig selv, op til 24 t).
ATTENTION_WHEN_OPEN = ("waiting_for_approval", "waiting_for_budget", "outcome_unknown", "unknown")

SUMMARY_LIMIT = 200
GOAL_LIMIT = 200
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def classify(assignment_status: str, run_status: str) -> str:
    """Bucket for ét assignment, afledt af assignment- og seneste run-status. Ren funktion."""
    a, r = str(assignment_status or ""), str(run_status or "")
    if a in ASSIGNMENT_TERMINAL:
        return "done" if a == "completed" else a
    if a == "outcome_unknown" or r == "outcome_unknown":
        return "outcome_unknown"
    if r in RUN_WAITING:
        return r
    if r in _RUN_ACTIVE:
        return "active"
    if r == "queued" or (a == "queued" and not r):
        return "queued"
    if r in _RUN_FAILED:
        return "retry_pending"          # forsoeget fejlede, men assignmentet er aabent (nyt forsoeg afventer)
    if r == "completed":
        return "settling"               # runnet er faerdigt, det samlede udfald er ikke fastlagt endnu
    if a == "active" and not r:
        return "active"
    return "unknown"


def _needs_attention(bucket: str, acknowledged: bool) -> bool:
    if bucket in TERMINAL_ATTENTION:
        return not acknowledged
    return bucket in ATTENTION_WHEN_OPEN


def _clean_owner(owner_user_id: str) -> str:
    owner = str(owner_user_id or "").strip()
    return "" if owner == LEGACY_UNSCOPED else owner


def safe_text(value: Any, limit: int = SUMMARY_LIMIT) -> str:
    """Begraenset og redigeret tekst til et kort: kontroltegn vaek, hemmeligheder maskeret, afkortet."""
    text = _CTRL.sub(" ", str(value or "")).strip()
    try:
        from core.services.secret_redaction import redact
        text = redact(text)
    except Exception:
        logger.warning("secret_redaction utilgaengelig - kort-resume udelades", exc_info=True)
        return ""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        logger.warning("ulaeseligt tidsstempel i en agentraekke: %r", str(value)[:40])
        return None                # ukendt tid er None (vises som «ingen»), aldrig 0


def _seconds(start: str, end: str, now: datetime) -> int | None:
    s = _ts(start)
    if s is None:
        return None
    e = _ts(end) or now
    return max(0, int((e - s).total_seconds()))


def _all(sql: str, args: list[Any] | tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [{k: r[k] for k in r.keys()} for r in _conn().execute(sql, list(args)).fetchall()]


def _outcome(raw: str) -> dict[str, Any]:
    try:
        v = json.loads(raw or "{}")
        return v if isinstance(v, dict) else {}
    except ValueError:
        logger.warning("ulaeselig outcome_json paa et assignment")
        return {}


# --- raekker -----------------------------------------------------------------------------------

def _latest_assignments(owner: str, agent_id: str = "") -> list[dict[str, Any]]:
    """Ejerens SENESTE assignment pr. agent (LEFT JOIN: en agent uden assignment er stadig en raekke)."""
    q = ("SELECT g.agent_id, g.parent_agent_id, g.role, g.goal AS agent_goal, g.status AS agent_status, "
         "g.lifecycle_status, g.owner_session_id, g.council_id, g.provider AS agent_provider, "
         "g.model AS agent_model, g.last_error, g.created_at AS agent_created_at, "
         "a.assignment_id, a.status AS assignment_status, a.target, a.goal, a.origin_session_id, "
         "a.parent_run_id, a.expected_result, a.deadline_at, a.budget_json, a.outcome_json, a.operation, "
         "a.created_at AS assignment_created_at, a.updated_at, a.terminal_at "
         "FROM agent_registry g LEFT JOIN agent_assignments a ON a.assignment_id = "
         "(SELECT assignment_id FROM agent_assignments WHERE agent_id = g.agent_id "
         " ORDER BY created_at DESC, rowid DESC LIMIT 1) WHERE g.owner_user_id = ?")
    args: list[Any] = [owner]
    if agent_id:
        q += " AND g.agent_id = ?"
        args.append(agent_id)
    return _all(q + " ORDER BY COALESCE(a.updated_at, g.updated_at) DESC", args)


def _run_facts(owner: str) -> dict[str, dict[str, Any]]:
    """Seneste runstatus, antal forsoeg, forbrug og seneste fejl pr. assignment - EN forespoergsel."""
    rows = _all("SELECT r.assignment_id, r.run_id, r.attempt_no, r.status, r.started_at, r.finished_at, "
                "r.input_tokens, r.output_tokens, r.cost_usd, r.failure_reason, r.error_phase, r.error_code, "
                "r.updated_at FROM agent_runs r JOIN agent_assignments a ON a.assignment_id = r.assignment_id "
                "WHERE a.owner_user_id = ? AND r.owner_user_id = ? ORDER BY r.attempt_no", [owner, owner])
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        f = out.setdefault(r["assignment_id"], {"attempts": 0, "tokens": 0, "cost": 0.0, "used": False,
                                                "first_started": ""})
        f["attempts"] += 1
        f["tokens"] += int(r["input_tokens"] or 0) + int(r["output_tokens"] or 0)
        f["cost"] += float(r["cost_usd"] or 0)
        f["used"] = f["used"] or bool(r["input_tokens"] or r["output_tokens"] or r["cost_usd"])
        f["first_started"] = f["first_started"] or r["started_at"]
        f["last"] = r                                  # sorteret paa attempt_no: den sidste er den seneste
    return out


def _leases(owner: str) -> dict[str, dict[str, Any]]:
    rows = _all("SELECT l.assignment_id, l.state, l.lease_until, l.renewed_at FROM agent_leases l "
                "JOIN agent_assignments a ON a.assignment_id = l.assignment_id WHERE a.owner_user_id = ?", [owner])
    return {r["assignment_id"]: r for r in rows}


def _routes(owner: str) -> dict[str, dict[str, Any]]:
    rows = _all("SELECT assignment_id, attempt, route_source, provider, model FROM agent_route_decisions "
                "WHERE owner_user_id = ? ORDER BY attempt", [owner])
    return {r["assignment_id"]: r for r in rows}        # seneste forsoeg vinder (sorteret stigende)


def _outbox(owner: str) -> dict[str, str]:
    return {r["assignment_id"]: r["delivery_status"] for r in _all(
        "SELECT assignment_id, delivery_status FROM agent_result_outbox WHERE owner_user_id = ?", [owner])}


def _pending_approvals(owner: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in _all("SELECT assignment_id, COUNT(*) AS n FROM agent_approvals WHERE owner_user_id = ? "
                  "AND status = 'pending' GROUP BY assignment_id", [owner]):
        out[r["assignment_id"]] = int(r["n"])
    return out


def _last_messages(owner: str) -> dict[str, dict[str, Any]]:
    rows = _all("SELECT m.agent_id, m.direction, m.role, m.kind, m.content, m.created_at FROM agent_messages m "
                "JOIN agent_registry g ON g.agent_id = m.agent_id WHERE g.owner_user_id = ? AND m.rowid = "
                "(SELECT x.rowid FROM agent_messages x WHERE x.agent_id = m.agent_id AND x.kind != 'lifecycle' "
                " ORDER BY x.created_at DESC, x.rowid DESC LIMIT 1)", [owner])
    return {r["agent_id"]: r for r in rows}


def _error(run: dict[str, Any] | None, outcome: dict[str, Any], agent_error: str, bucket: str) -> dict[str, str] | None:
    """Fejlaarsagen: runnets praecise fase/kode, ellers det fastlagte udfald. Aldrig opdigtet."""
    if bucket in ("done", "active", "queued", "settling") + RUN_WAITING:
        return None
    code = str(outcome.get("error_code") or (run or {}).get("error_code") or "")
    phase = str(outcome.get("error_phase") or (run or {}).get("error_phase") or "")
    reason = str((run or {}).get("failure_reason") or agent_error or "")
    if not (code or phase or reason):
        return {"phase": "", "code": "", "reason": ""} if bucket != "retry_pending" else None
    return {"phase": phase, "code": code, "reason": safe_text(reason, 300)}


def _reason(bucket: str, pending: int, err: dict[str, str] | None) -> str:
    """Hvorfor staar den her - en fast tekst pr. bucket, aldrig udledt af agentens ord."""
    base = {
        "queued": "Venter i kø",
        "waiting_for_client": "Venter på at klienten kommer online",
        "waiting_for_approval": "Venter på din godkendelse" + (f" ({pending})" if pending > 1 else ""),
        "waiting_for_budget": "Venter på budget – forhøj det eller afslut",
        "outcome_unknown": "Udfaldet er ukendt – kræver afklaring før arbejdet fortsætter",
        "retry_pending": "Forsøget fejlede – nyt forsøg afventer",
        "settling": "Afslutter",
        "failed": "Fejlede", "timed_out": "Tidsfristen udløb", "cancelled": "Afbrudt",
        "unknown": "Ukendt tilstand – ikke tolket som succes",
    }.get(bucket, "")
    if err and err.get("code") and bucket in TERMINAL_ATTENTION + ("outcome_unknown",):
        base += f" ({err['code']}" + (f", fase {err['phase']}" if err.get("phase") else "") + ")"
    return base


def _row(g: dict[str, Any], *, facts: dict, leases: dict, routes: dict, outbox: dict, pend: dict,
         msgs: dict, refs: dict, now: datetime, children: dict[str, int]) -> dict[str, Any]:
    aid = g.get("assignment_id") or ""
    f = facts.get(aid, {})
    last = f.get("last")
    outcome = _outcome(g.get("outcome_json") or "")
    a_status = g.get("assignment_status") or ""
    bucket = classify(a_status, (last or {}).get("status", "")) if aid else "idle"
    ref = refs.get(("agent", aid), {})
    acked = bool(ref.get("acknowledged_at"))
    err = _error(last, outcome, g.get("last_error") or "", bucket)
    lease = leases.get(aid)
    hb = None
    if lease:
        until = _ts(lease["lease_until"])
        hb = {"at": lease["renewed_at"], "state": ("ok" if lease["state"] == "held" and until and until > now
                                                    else "expired")}
    r = routes.get(aid)
    m = msgs.get(g["agent_id"])
    terminal = a_status in ASSIGNMENT_TERMINAL
    pending = pend.get(aid, 0)
    return {
        "agent_id": g["agent_id"], "parent_agent_id": g.get("parent_agent_id") or "",
        "role": g.get("role") or "", "goal": safe_text(g.get("goal") or g.get("agent_goal"), GOAL_LIMIT),
        "council_id": g.get("council_id") or "", "children": children.get(g["agent_id"], 0),
        "lifecycle_status": g.get("lifecycle_status") or "", "target": g.get("target") or "runtime-container",
        "assignment_id": aid, "assignment_status": a_status, "origin_session_id": g.get("origin_session_id")
        or g.get("owner_session_id") or "",
        "run_id": (last or {}).get("run_id", ""), "run_status": (last or {}).get("status", ""),
        "attempts": f.get("attempts", 0), "bucket": bucket, "attention": _needs_attention(bucket, acked),
        "reason": _reason(bucket, pending, err), "error": err,
        "started_at": f.get("first_started", "") or g.get("assignment_created_at") or "",
        "finished_at": (g.get("terminal_at") or "") if terminal else "",
        "duration_s": _seconds(f.get("first_started", "") or g.get("assignment_created_at") or "",
                               (g.get("terminal_at") or "") if terminal else "", now),
        "updated_at": g.get("updated_at") or "", "heartbeat": hb,
        "tokens": f.get("tokens", 0), "cost_usd": round(f["cost"], 6) if f.get("used") else None,
        "route": ({"route_source": r["route_source"], "provider": r["provider"], "model": r["model"]}
                  if r else None),
        "last_message": ({"direction": m["direction"], "kind": m["kind"], "at": m["created_at"],
                          "text": safe_text(m["content"])} if m else None),
        "summary": safe_text(outcome.get("summary")), "pending_approvals": pending, "model_claim": outbox.get(aid, ""),
        "read": bool(ref.get("read_at")), "acknowledged": acked,
    }


def _build_rows(owner: str, agent_id: str = "") -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    refs = feed_db.refs_for_owner(owner)
    kids: dict[str, int] = {}
    for r in _all("SELECT parent_agent_id, COUNT(*) AS n FROM agent_registry WHERE owner_user_id = ? "
                  "AND parent_agent_id != '' GROUP BY parent_agent_id", [owner]):
        kids[r["parent_agent_id"]] = int(r["n"])
    ctx = dict(facts=_run_facts(owner), leases=_leases(owner), routes=_routes(owner), outbox=_outbox(owner),
               pend=_pending_approvals(owner), msgs=_last_messages(owner), refs=refs, now=now, children=kids)
    return [_row(g, **ctx) for g in _latest_assignments(owner, agent_id)]


# --- overblik (liste + taellere) ---------------------------------------------------------------------

def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    b = [r["bucket"] for r in rows]
    return {
        "active": sum(1 for x in b if x in ACTIVE_BUCKETS),
        "queued": sum(1 for x in b if x == "queued"),
        "waiting": sum(1 for x in b if x in WAITING_BUCKETS),
        "blocked": sum(1 for x in b if x == "outcome_unknown"),
        "attention": sum(1 for r in rows if r["attention"]),
        "open": sum(1 for r in rows if r["assignment_status"] in ("queued", "active", "waiting")),
    }


def _groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Et raad er en gruppering af almindelige agentruns - ingen egen sandhed."""
    by: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r["council_id"]:
            by.setdefault(r["council_id"], []).append(r)
    out = []
    for cid, members in sorted(by.items()):
        synth = next((m for m in members if "synth" in (m["role"] or "").lower()), None)
        out.append({"council_id": cid,
                    "members": [{"agent_id": m["agent_id"], "role": m["role"], "bucket": m["bucket"]}
                                for m in members if m is not synth],
                    "synthesis": ({"agent_id": synth["agent_id"], "bucket": synth["bucket"]} if synth else None),
                    "counts": _counts(members)})
    return out


def _capability() -> dict[str, Any]:
    from core.services import agent_contract_service as svc
    st = svc.capability_status()
    return {"enabled": st["enabled"], "reason": st["reason"], "contract_version": st["contract_version"]}


def overview(owner_user_id: str, *, scope: str = "panel", session_id: str = "") -> dict[str, Any]:
    """Liste + taellere. ``panel``: aabne runs + fejl/afbrydelse der ikke er kvitteret (succes forsvinder).
    ``all``: ejerens hele agenttrae."""
    owner = _clean_owner(owner_user_id)
    cap = _capability()
    if not owner:
        return {"status": "error", "code": "INVALID_SCOPE", "error": "ejer mangler",
                "contract_version": CONTRACT_VERSION}
    rows = _build_rows(owner)
    if session_id:
        rows = [r for r in rows if r["origin_session_id"] == session_id]
    if scope != "all":
        rows = [r for r in rows if r["assignment_status"] in ("queued", "active", "waiting") or r["attention"]]
    rows.sort(key=lambda r: r["started_at"] or "", reverse=True)                      # nyeste foerst
    rows.sort(key=lambda r: (not r["attention"], r["bucket"] not in ACTIVE_BUCKETS))  # stabil: opmaerksomhed foerst
    return {"status": "ok", "capability": cap, "agents": rows, "counts": _counts(rows), "groups": _groups(rows),
            "contract_version": CONTRACT_VERSION}


# --- inspector -------------------------------------------------------------------------------------

def agent_detail(owner_user_id: str, agent_id: str) -> dict[str, Any] | None:
    """Alt inspectoren viser om EN agent. ``None`` = findes ikke FOR DENNE EJER (ingen skelnen til 'forbudt')."""
    owner = _clean_owner(owner_user_id)
    if not owner or not str(agent_id or "").strip():
        return None
    rows = _build_rows(owner, agent_id)
    if not rows:
        return None
    head = rows[0]
    asgs = _all("SELECT assignment_id, status, goal, expected_result, target, deadline_at, budget_json, "
                "operation, created_by, created_at, updated_at, terminal_at, outcome_json "
                "FROM agent_assignments WHERE agent_id = ? AND owner_user_id = ? ORDER BY created_at DESC",
                [agent_id, owner])
    assignments = []
    for a in asgs:
        oc = _outcome(a.pop("outcome_json"))
        a["goal"] = safe_text(a["goal"], 500)
        a["budget"] = _outcome(a.pop("budget_json"))
        a["outcome"] = {"status": oc.get("status", ""), "error_code": oc.get("error_code", ""),
                        "error_phase": oc.get("error_phase", ""), "summary": safe_text(oc.get("summary"), 500),
                        "artifact_ref": oc.get("artifact_ref", ""), "artifact_error": oc.get("artifact_error", "")}
        a["routes"] = [{k: x[k] for k in ("attempt", "route_source", "provider", "model", "created_at")}
                       for x in db_agent_route.attempts_for_assignment(a["assignment_id"])
                       if x["owner_user_id"] == owner]
        assignments.append(a)
    runs = _all("SELECT run_id, assignment_id, attempt_no, status, provider, model, started_at, finished_at, "
                "input_tokens, output_tokens, cost_usd, failure_reason, error_phase, error_code "
                "FROM agent_runs WHERE agent_id = ? AND owner_user_id = ? ORDER BY created_at", [agent_id, owner])
    for r in runs:
        r["failure_reason"] = safe_text(r["failure_reason"], 300)
    messages = _all("SELECT message_id, direction, role, kind, content, created_at FROM agent_messages "
                    "WHERE agent_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 30", [agent_id])
    for m in messages:
        m["content"] = safe_text(m["content"], 1500)
    tools = _all("SELECT t.tool_call_id, t.run_id, t.tool_name, t.status, t.started_at, t.finished_at "
                 "FROM agent_tool_calls t JOIN agent_runs r ON r.run_id = t.run_id WHERE t.agent_id = ? "
                 "AND r.owner_user_id = ? ORDER BY t.created_at DESC LIMIT 30", [agent_id, owner])
    approvals = [a for a in _approval_views(owner) if a["agent_id"] == agent_id]
    artifacts = []
    for a in assignments:
        for m in art.manifest(owner_user_id=owner, assignment_id=a["assignment_id"]):
            artifacts.append({"assignment_id": a["assignment_id"], "run_id": m["run_id"], "name": m["name"],
                              "size": m["size"], "status": m["status"], "attempt_no": m["attempt_no"]})
    children = [r["agent_id"] for r in _all(
        "SELECT agent_id FROM agent_registry WHERE parent_agent_id = ? AND owner_user_id = ?", [agent_id, owner])]
    return {"status": "ok", "agent": head, "assignments": assignments, "runs": runs, "messages": messages[::-1],
            "tool_calls": tools, "approvals": approvals, "artifacts": artifacts, "children": children,
            "capability": _capability(), "contract_version": CONTRACT_VERSION}


def _approval_views(owner: str) -> list[dict[str, Any]]:
    from core.services.agent_contract_service import approval_view
    from core.runtime import db_agent_approvals as appr
    return [approval_view(a) for a in appr.list_for_owner(owner_user_id=owner, limit=200)]


# --- artefakter (ejer + session) ---------------------------------------------------------------------

def read_artifact(owner_user_id: str, agent_id: str, run_id: str, name: str, *, offset: int = 0,
                  limit: int = 20000, session_id: str = "") -> dict[str, Any]:
    """Fuldt output. Samme svar for 'findes ikke' og 'tilhoerer en anden' - ingen orakel. Er ``session_id``
    angivet, skal den vaere assignmentets OPRINDELSESsession (den aendres aldrig ved genoptagelse)."""
    owner = _clean_owner(owner_user_id)
    nf = {"status": "NOT_FOUND", "ref": f"{run_id}/{name}"}
    if not owner:
        return nf
    rec = art.get_artifact_record(run_id=run_id, name=name)
    if rec is None or rec["owner_user_id"] != owner or rec["agent_id"] != agent_id:
        return nf
    if session_id:
        a = _conn().execute("SELECT origin_session_id FROM agent_assignments WHERE assignment_id=? "
                            "AND owner_user_id=?", (rec["assignment_id"], owner)).fetchone()
        if a is None or a["origin_session_id"] != session_id:
            return nf
    return art.read_artifact(owner_user_id=owner, ref=f"{run_id}/{name}", offset=offset, limit=limit)


# --- feed ------------------------------------------------------------------------------------------

def _card_title(r: dict[str, Any]) -> str:
    return f"{r['role'] or 'Agent'}: {r['goal']}"[:120]


def _agent_card(r: dict[str, Any]) -> dict[str, Any] | None:
    b = r["bucket"]
    if b == "idle":
        return None
    if b == "done":
        section = "svar"
    elif b in TERMINAL_ATTENTION or b in ATTENTION_WHEN_OPEN or b == "retry_pending":
        section = "venter"
    else:
        section = "aktiv"
    if r["acknowledged"]:
        return None                          # kvitteret: kortet er afsluttet (kvittering er brugerens egen handling)
    summary = r["summary"] if b == "done" else ""
    return {"ref_kind": "agent", "ref_id": r["assignment_id"], "section": section, "bucket": b,
            "agent_id": r["agent_id"], "assignment_id": r["assignment_id"], "origin_session_id": r["origin_session_id"],
            "title": _card_title(r), "reason": r["reason"], "summary": summary, "error": r["error"],
            "updated_at": r["updated_at"], "created_at": r["started_at"],
            "state": {"read": r["read"], "acknowledged": r["acknowledged"], "model_claim": r["model_claim"],
                      "assignment_status": r["assignment_status"]},
            "can_acknowledge": r["assignment_status"] in ASSIGNMENT_TERMINAL}


def feed(owner_user_id: str) -> dict[str, Any]:
    """Kort til notifikationsfeedet: een reference pr. assignment + een pr. ventende approval. Hydreret fra
    assignment/approval; read/ack er brugerens egne tilstande. Aldrig agentindhold ud over et begraenset resume."""
    owner = _clean_owner(owner_user_id)
    if not owner:
        return {"status": "error", "code": "INVALID_SCOPE", "error": "ejer mangler",
                "contract_version": CONTRACT_VERSION}
    cards = [c for c in (_agent_card(r) for r in _build_rows(owner)) if c]
    refs = feed_db.refs_for_owner(owner)
    from core.runtime import db_agent_approvals as appr
    for a in appr.list_for_owner(owner_user_id=owner, status="pending", limit=200):
        ref = refs.get(("approval", a["approval_id"]), {})
        cards.append({"ref_kind": "approval", "ref_id": a["approval_id"], "section": "venter", "bucket": "approval",
                      "agent_id": a["agent_id"], "assignment_id": a["assignment_id"],
                      "origin_session_id": a["origin_session_id"], "title": f"Godkend: {a['tool_name']}",
                      "reason": "Venter på din godkendelse", "summary": safe_text(a["safe_view"], 300),
                      "error": None, "updated_at": a["created_at"], "created_at": a["created_at"],
                      "approval": {"approval_id": a["approval_id"], "digest": a["args_digest"],
                                   "risk_class": a["risk_class"], "expires_at": a["expires_at"],
                                   "tool_name": a["tool_name"], "status": a["status"]},
                      "state": {"read": bool(ref.get("read_at")), "acknowledged": False, "model_claim": "",
                                "assignment_status": ""},
                      "can_acknowledge": False})
    cards.sort(key=lambda c: c["updated_at"] or "", reverse=True)
    sections = {"venter": 0, "svar": 0, "aktiv": 0}
    for c in cards:
        sections[c["section"]] += 1
    unread = sum(1 for c in cards if not c["state"]["read"])
    return {"status": "ok", "cards": cards, "counts": {**sections, "unread": unread},
            "contract_version": CONTRACT_VERSION}


def mark_read(owner_user_id: str, ref_kind: str, ref_id: str) -> bool:
    return feed_db.mark_read(owner_user_id=_clean_owner(owner_user_id), ref_kind=ref_kind, ref_id=ref_id)


def acknowledge(owner_user_id: str, assignment_id: str) -> dict[str, Any]:
    """Kvitter en TERMINAL assignment. En aaben (inkl. ``outcome_unknown``) kan ikke kvitteres vaek - den skal
    afgoeres; ellers kunne en kvittering skjule en uafklaret skrivning."""
    owner = _clean_owner(owner_user_id)
    row = _conn().execute("SELECT status FROM agent_assignments WHERE assignment_id=? AND owner_user_id=?",
                          (assignment_id, owner or "\0")).fetchone() if owner else None
    if row is None:
        return {"status": "error", "code": "INVALID_SCOPE", "error": "ukendt assignment",
                "contract_version": CONTRACT_VERSION}
    if row["status"] not in ASSIGNMENT_TERMINAL:
        return {"status": "error", "code": "INVALID_TRANSITION", "error": "kun et afsluttet assignment kan kvitteres",
                "contract_version": CONTRACT_VERSION}
    ok = feed_db.acknowledge(owner_user_id=owner, ref_kind="agent", ref_id=assignment_id)
    return {"status": "ok" if ok else "error", "acknowledged": ok, "assignment_id": assignment_id,
            "contract_version": CONTRACT_VERSION}


# --- handlinger (genbruger de eksisterende service-funktioner) ------------------------------------------

def _session_of(owner: str, agent_id: str) -> str:
    """Sessionen for en handling - fra DB (agentens oprindelse), ALDRIG fra klienten. '' = ukendt agent."""
    r = _conn().execute("SELECT owner_session_id FROM agent_registry WHERE agent_id=? AND owner_user_id=?",
                        (agent_id, owner)).fetchone() if owner else None
    if r is None:
        return ""
    if r["owner_session_id"]:
        return r["owner_session_id"]
    a = _conn().execute("SELECT origin_session_id FROM agent_assignments WHERE agent_id=? AND owner_user_id=? "
                        "ORDER BY created_at DESC LIMIT 1", (agent_id, owner)).fetchone()
    return a["origin_session_id"] if a else ""


def _unknown(detail: str = "ukendt agent") -> dict[str, Any]:
    return {"status": "error", "code": "INVALID_SCOPE", "phase": "admission", "error": detail,
            "contract_version": CONTRACT_VERSION}


def send_message(owner_user_id: str, agent_id: str, content: str) -> dict[str, Any]:
    """Menneskelig besked til agenten. Maerket som menneske + audit-id (spec 5), aldrig som parent-instruks.
    Kvitteringen er ACCEPT: levering til en igangvaerende tur er ikke bevist."""
    from core.services import agent_contract_service as svc
    owner = _clean_owner(owner_user_id)
    session = _session_of(owner, agent_id)
    if not session:
        return _unknown()
    audit = f"desk-{uuid.uuid4().hex[:12]}"
    out = svc.send_message(owner_user_id=owner, origin_session_id=session, agent_id=agent_id, content=content,
                           sender=f"menneske (Bjørns bruger) via Desk, audit {audit}")
    logger.info("desk-besked til %s: %s audit=%s", agent_id, out.get("status"), audit)
    return {**out, "audit_id": audit, "receipt": _receipt("message", out, delivered=False)}


def followup(owner_user_id: str, agent_id: str, goal: str, *, idempotency_key: str = "") -> dict[str, Any]:
    from core.services import agent_contract_service as svc
    owner = _clean_owner(owner_user_id)
    session = _session_of(owner, agent_id)
    if not session:
        return _unknown()
    out = svc.followup_agent(owner_user_id=owner, origin_session_id=session, agent_id=agent_id, goal=goal,
                             idempotency_key=idempotency_key)
    return {**out, "receipt": _receipt("followup", out)}


def stop(owner_user_id: str, agent_id: str, note: str = "") -> dict[str, Any]:
    """Stop-anmodning. Svaret er ``stop_requested`` - aldrig et lovet ``cancelled``; det afgoeres af projektionen."""
    from core.services import agent_contract_service as svc
    owner = _clean_owner(owner_user_id)
    session = _session_of(owner, agent_id)
    if not session:
        return _unknown()
    out = svc.interrupt_agent(owner_user_id=owner, origin_session_id=session, agent_id=agent_id,
                              note=note or "stop fra Desk")
    return {**out, "receipt": _receipt("stop", out)}


def close(owner_user_id: str, agent_id: str) -> dict[str, Any]:
    from core.services import agent_contract_service as svc
    owner = _clean_owner(owner_user_id)
    session = _session_of(owner, agent_id)
    if not session:
        return _unknown()
    out = svc.close_agent(owner_user_id=owner, origin_session_id=session, agent_id=agent_id)
    return {**out, "receipt": _receipt("close", out)}


def _receipt(kind: str, out: dict[str, Any], *, delivered: bool | None = None) -> dict[str, Any]:
    """Acceptkvittering adskilt fra faktisk effekt. ``confirmed`` er ALTID False her: bekraeftelsen er den
    efterfoelgende projektion (assignment ``cancelled``, agent ``closed``, besked laest af agenten)."""
    ok = out.get("status") in ("accepted", "stop_requested", "noop")
    return {"kind": kind, "accepted": ok, "confirmed": False, "code": out.get("code", ""),
            "state": out.get("status", ""), "delivered": delivered}
