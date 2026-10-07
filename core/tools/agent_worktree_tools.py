"""Agent-kun-vaerktoejer til at skrive i agentens EGET worktree (agent-contract-v1 C5b).

Navngivet ``wt_*`` (ikke ``worktree_*``): `worktree_tools.py` er Jarvis' egne worktree-primitiver
(worktree_create/merge/discard), og de to maa aldrig forveksles.

Findes IKKE i Jarvis' vaerktoejskatalog: kun en agent med policyen ``worktree-write`` faar dem i sit
skema (``agent_runtime_base._build_agent_tools_payload``). Hvilket worktree der er tale om afgoeres af
SERVEREN ud fra agentens identitet (``_runtime_agent_id`` saettes af agent-dispatchen og overskrives
altid) og dens aabne assignment - aldrig af et argument modellen skriver. Selve skrivningen sker i en
sandbox (``agent_worktree_exec``).
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

WORKTREE_TOOL_NAMES = ("wt_bash", "wt_write_file")

WT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "wt_bash",
        "description": (
            "Run a shell command in YOUR private worktree (mounted at /work, the only writable place). "
            "No network, no git against the main repository, no access outside /work. Use it to run "
            "tests, build, inspect and edit files. The server records your changes as a diff when you "
            "finish; nothing is merged without approval."),
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "Shell command, run with bash -c in /work."},
            "timeout_seconds": {"type": "number", "description": "Max 600, default 120."}},
            "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "wt_write_file",
        "description": "Write a text file inside YOUR worktree. `path` is relative to /work; paths that leave "
                       "the worktree are refused.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
]


def _worktree_for(args: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """(worktree, fejl). Agenten og dens assignment slaas op af serveren."""
    agent_id = str(args.get("_runtime_agent_id") or "").strip()
    if not agent_id:
        return None, {"status": "error", "code": "NO_WORKTREE", "error": "kaldet har ingen agent-identitet"}
    from core.runtime import db_agent_contract as c
    from core.services import agent_worktrees as wtm

    a = c.open_assignment_for_agent(agent_id)
    if a is None:
        return None, {"status": "error", "code": "NO_WORKTREE", "error": "agenten har ingen aaben opgave"}
    wt = wtm.get_for_assignment(owner_user_id=a["owner_user_id"], assignment_id=a["assignment_id"])
    if wt is None:
        return None, {"status": "error", "code": "NO_WORKTREE", "error": "opgaven har intet worktree"}
    return wt, None


def _fail(exc: Exception) -> dict[str, Any]:
    code = getattr(exc, "code", type(exc).__name__)
    logger.info("worktree-vaerktoej afvist: %s", exc)
    return {"status": "error", "code": code, "error": str(getattr(exc, "detail", "") or exc)[:300]}


def _exec_wt_bash(args: dict[str, Any]) -> dict[str, Any]:
    wt, err = _worktree_for(args)
    if err:
        return err
    from core.services import agent_worktree_exec as ex
    try:
        res = ex.run_in_worktree(worktree_id=wt["worktree_id"], command=str(args.get("command") or ""),
                                 timeout_s=float(args.get("timeout_seconds") or ex.DEFAULT_TIMEOUT_S))
    except Exception as exc:                     # ExecError, SandboxUnavailable ... - altid et svar, aldrig et crash
        return _fail(exc)
    return {"status": "ok", "text": json.dumps(res, ensure_ascii=False), **res}


def _exec_wt_write_file(args: dict[str, Any]) -> dict[str, Any]:
    wt, err = _worktree_for(args)
    if err:
        return err
    from core.services import agent_worktree_exec as ex
    try:
        res = ex.write_file_in_worktree(worktree_id=wt["worktree_id"], path=str(args.get("path") or ""),
                                        content=str(args.get("content") or ""))
    except Exception as exc:  # afvisning bliver et fejlresultat til modellen; _fail logger den
        return _fail(exc)
    return {"status": "ok", "text": f"skrev {res['bytes']} bytes til {res['path']}", **res}
