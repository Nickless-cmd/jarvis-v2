"""Integration af en kodeagents arbejde - foerste forbruger af approval-flowet (agent-contract-v1 F4d, spec 8.1/8.2).

Et afsluttet agentrun merger ALDRIG selv sit worktree. Integration er en saerskilt handling der kraever en
menneskelig godkendelse bundet til DIFFENS hash:

1. ``request_integration`` (Jarvis' vaerktoej) opretter en approval ``integrate_worktree`` med worktree, branch,
   base-commit, diff-hash, repo og en forhaandsvisning af de aendrede filer. Jarvis kan ikke godkende den.
2. Et menneske godkender (Desk -> API). Argumenterne kan ikke aendres uden en ny approval, og arbejdet i
   worktree'et kan heller ikke: er diffen en anden nu end ved anmodningen, afvises integrationen.
3. ``execute_approved`` bruger approvalen (hoejst én gang), skriver agentens arbejde som ét commit paa
   ``agent/<assignment>`` og fletter det med ``git merge-tree`` ovenpaa repoets nuvaerende HEAD til en NY gren
   ``integrate/<assignment>``. Intet working tree eller index roeres - hverken Bjoerns eller nogen andens. En
   eksisterende gren overskrives aldrig. Ved konflikt oprettes intet; konfliktfilerne rapporteres. Bjoern
   fast-forwarder selv sin hovedgren: ``git merge --ff-only integrate/<assignment>``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

from core.runtime import db_agent_approvals as appr
from core.runtime.db_agent_contract import ContractError, _conn, _now_iso
from core.services import agent_worktree_git as g
from core.services import agent_worktrees as wtm

logger = logging.getLogger(__name__)

TOOL_NAME = "integrate_worktree"
PREVIEW_FILES = 30


def _retained_worktree(owner_user_id: str, assignment_id: str) -> dict[str, Any]:
    wt = wtm.get_for_assignment(owner_user_id=owner_user_id, assignment_id=assignment_id)
    if wt is None:
        raise ContractError("INVALID_SCOPE", "assignmentet har intet worktree for denne ejer")
    if wt["status"] != "retained":
        raise ContractError("INVALID_TRANSITION", f"worktree'et er {wt['status']}, ikke retained")
    return wt


def _snapshot(wt: dict[str, Any]) -> dict[str, Any]:
    """Hvad der staar i worktree'et NU: diff-hash + filer. Samme beregning ved anmodning og ved udfoerelse."""
    diff = g.diff_against(wt["gitdir"], wt["path"], wt["base_commit"])
    files = g.changed_files(wt["gitdir"], wt["path"], wt["base_commit"])
    return {"worktree_id": wt["worktree_id"], "branch": wt["branch"], "base_commit": wt["base_commit"],
            "repo": wt["repo_path"], "diff_sha256": hashlib.sha256(diff).hexdigest(), "files": len(files),
            "files_preview": [f"{f['status']} {f['path']}" for f in files[:PREVIEW_FILES]]}


def request_integration(*, owner_user_id: str, origin_session_id: str, assignment_id: str) -> dict[str, Any]:
    """Opret (eller genfind) approvalen. Kaster ``ContractError`` ved ukendt/ugyldigt worktree."""
    wt = _retained_worktree(owner_user_id, assignment_id)
    try:
        snap = _snapshot(wt)
    except g.GitError as exc:
        raise ContractError("INVALID_SCOPE", f"aendringerne kunne ikke laeses: {exc.detail}") from exc
    if snap["files"] == 0:
        raise ContractError("INVALID_TRANSITION", "agenten har ikke aendret noget at integrere")
    return appr.request(owner_user_id=owner_user_id, origin_session_id=origin_session_id,
                        assignment_id=assignment_id, tool_name=TOOL_NAME, arguments=snap, kind="integration",
                        requested_by="jarvis", risk_class="integration")


def _result_message(approval: dict[str, Any], payload: dict[str, Any]) -> None:
    """Fortael parenten hvordan det gik, via den samme udbakke som agentresultater (ét svar pr. approval)."""
    conn = _conn()
    a = conn.execute("SELECT agent_id, parent_agent_id, parent_run_id FROM agent_assignments WHERE assignment_id=?",
                     (approval["assignment_id"],)).fetchone()
    body = {"agent_id": a["agent_id"], "assignment_id": approval["assignment_id"], "last_run_id": approval["run_id"],
            "attempt_run_ids": [], "artifact_ref": "", "artifact_error": "", "error_phase": "", **payload}
    now = _now_iso()
    conn.execute(
        "INSERT OR IGNORE INTO agent_result_outbox (message_id, assignment_id, result_type, owner_user_id, "
        "origin_session_id, sender_agent_id, recipient_agent_id, parent_run_id, last_run_id, payload_json, "
        "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (f"msg-{uuid.uuid4().hex[:16]}", approval["assignment_id"], f"integration:{approval['approval_id']}",
         approval["owner_user_id"], approval["origin_session_id"], a["agent_id"], a["parent_agent_id"],
         a["parent_run_id"], approval["run_id"], json.dumps(body, ensure_ascii=False), now, now))
    conn.commit()


def execute_approved(approval: dict[str, Any]) -> dict[str, Any]:
    """Udfoer en GODKENDT integration. Bruger approvalen foerst (hoejst én gang)."""
    aid = approval["approval_id"]
    if approval["kind"] != "integration" or approval["tool_name"] != TOOL_NAME:
        return {"status": "ignored"}
    if not appr.consume(approval_id=aid, digest=approval["args_digest"]):
        return {"status": "not_consumed"}                      # en anden har allerede udfoert den, eller den er udloebet
    args = json.loads(approval["arguments_json"])
    outcome: dict[str, Any] = {"status": "failed", "summary": "", "error_code": "INTEGRATION_FAILED"}
    try:
        wt = _retained_worktree(approval["owner_user_id"], approval["assignment_id"])
        now = _snapshot(wt)
        if now["diff_sha256"] != args["diff_sha256"]:
            outcome.update(error_code="DIFF_CHANGED", summary="arbejdet er aendret siden godkendelsen - anmod igen")
        else:
            outcome = _merge(wt, approval, args)
    except Exception as exc:
        logger.warning("integration %s fejlede", aid, exc_info=True)
        outcome.update(summary=f"{type(exc).__name__}: {exc}"[:300])
    _result_message(approval, outcome)
    if outcome["status"] == "integrated":
        try:
            wtm.decide(owner_user_id=approval["owner_user_id"], worktree_id=args["worktree_id"], decision="integrated")
        except ContractError:
            logger.warning("worktree-beslutning kunne ikke registreres for %s", aid, exc_info=True)
    return outcome


def _merge(wt: dict[str, Any], approval: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    repo = wt["repo_path"]
    assignment = approval["assignment_id"]
    agent_commit = g.commit_worktree_tree(wt["gitdir"], wt["path"], wt["base_commit"],
                                          f"Agent {wt['agent_id']}: {assignment}")
    g.set_ref(repo, f"refs/heads/{wt['branch']}", agent_commit, wt["base_commit"])
    target = g.current_head(repo)
    ref = f"refs/heads/integrate/{g.safe_name(assignment, 'assignment_id')}"
    if g.ref_exists(repo, ref):
        return {"status": "failed", "error_code": "BRANCH_EXISTS", "summary": f"{ref} findes allerede"}
    tree, conflicts = g.merge_tree(repo, target, agent_commit)
    if tree is None:
        return {"status": "conflict", "error_code": "MERGE_CONFLICT", "conflicts": conflicts,
                "summary": f"konflikt i {len(conflicts)} fil(er) ift. repoets nuvaerende HEAD: {', '.join(conflicts[:10])}"}
    merged = g.commit_tree(repo, tree, [target, agent_commit], f"Integrate agent work {assignment}")
    g.create_ref(repo, ref, merged)
    return {"status": "integrated", "integrate_branch": ref.removeprefix("refs/heads/"), "commit": merged,
            "agent_branch": wt["branch"], "agent_commit": agent_commit, "merged_into": target,
            "summary": f"integreret i gren {ref.removeprefix('refs/heads/')} (ovenpaa {target[:12]}); "
                       f"fast-forward din hovedgren selv: git merge --ff-only {ref.removeprefix('refs/heads/')}"}


def run_pending() -> list[str]:
    """Supervisor-tik: godkendte, ubrugte integrationer (f.eks. besluttet lige foer en genstart) udfoeres."""
    conn = _conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM agent_approvals WHERE kind='integration' AND "
                                          "status='approved'").fetchall()]
    done = []
    for r in rows:
        if execute_approved(r).get("status") != "not_consumed":
            done.append(r["approval_id"])
    return done
