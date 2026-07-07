"""Commit-enforcement (repo-state attachment) for Jarvis' tool results.

Udskilt fra ``simple_tools.py`` (Boy Scout, 2026-07). Hver succesful mutation
(bash/write_file/edit_file/operator_*) får en ``{_repo_state: {...}}``-blok i
tool-resultatet der viser branch + dirty + edits_since_commit og eskalerer ved
tærskler 5 og 10 ("enforce, don't remind"). shared_cache-backed tæller pr.
session, nulstilles når en "git commit" lykkes. INGEN logik-ændring — kun flyt.
Fuldt selvstændig (kun lazy imports); re-importeret i ``simple_tools`` så
``get_tool_definitions``' handler-wrapping er uændret.
"""

from __future__ import annotations

from typing import Any  # noqa: F401


_REPO_STATE_KEY_PREFIX = "commit_enforcement:"
_REPO_STATE_TTL_SECONDS = 24 * 60 * 60


def _repo_state_session_key(session_id: str) -> str:
    return _REPO_STATE_KEY_PREFIX + session_id


def _repo_state_get_counter(session_id: str) -> int:
    try:
        from core.services import shared_cache as _sc
        v = _sc.get(_repo_state_session_key(session_id))
        if isinstance(v, dict):
            return int(v.get("edits", 0))
    except Exception:
        pass
    return 0


def _repo_state_bump_counter(session_id: str, delta: int = 1) -> int:
    try:
        from core.services import shared_cache as _sc
        cur = _sc.get(_repo_state_session_key(session_id))
        if not isinstance(cur, dict):
            cur = {"edits": 0}
        new_count = max(0, int(cur.get("edits", 0)) + delta)
        cur["edits"] = new_count
        _sc.set(_repo_state_session_key(session_id), cur, ttl_seconds=_REPO_STATE_TTL_SECONDS)
        return new_count
    except Exception:
        return 0


def _repo_state_reset_counter(session_id: str) -> None:
    try:
        from core.services import shared_cache as _sc
        _sc.set(_repo_state_session_key(session_id), {"edits": 0}, ttl_seconds=_REPO_STATE_TTL_SECONDS)
    except Exception:
        pass


def _detect_git_commit_in_bash(command: str, stdout: str) -> bool:
    """True hvis bash-kommandoen kørte en git commit der lykkedes.
    Heuristik: command indeholder 'git commit' og stdout/stderr ikke
    indeholder 'nothing to commit' eller error-markers."""
    cmd = (command or "").lower()
    if "git commit" not in cmd:
        return False
    out = (stdout or "").lower()
    if "nothing to commit" in out or "working tree clean" in out:
        return False
    # Tegn pa succes: "master|main" og en commit-SHA-prefix
    if "[" in out and "]" in out:
        return True
    return True  # default optimistic - kommandoen kørte uden at fejle åbenlyst


def _attach_repo_state(
    result: dict,
    *,
    session_id: str,
    bumped: bool = True,
    bash_command: str = "",
) -> dict:
    """Augmenter tool-result med _repo_state-blok. Idempotent ved fejl."""
    try:
        if not isinstance(result, dict):
            return result
        if result.get("status") and result.get("status") != "ok":
            return result  # fejlede resultater får ikke en bump

        # Reset counter hvis dette var en succesful git commit
        if bash_command and _detect_git_commit_in_bash(bash_command, str(result.get("stdout") or "")):
            _repo_state_reset_counter(session_id)
            bumped = False
            edits = 0
        elif bumped:
            edits = _repo_state_bump_counter(session_id, delta=1)
        else:
            edits = _repo_state_get_counter(session_id)

        # Hent live git-state via eksisterende endpoint-helper (container)
        try:
            from apps.api.jarvis_api.routes.chat import _git_status_sync
            git_state = _git_status_sync("container", "")
        except Exception:
            git_state = {}

        dirty_count = int(git_state.get("dirty") or 0)
        block = {
            "branch": git_state.get("branch") or "?",
            "dirty": dirty_count > 0,
            "modified_count": dirty_count,
            "lines_added": int(git_state.get("added") or 0),
            "lines_removed": int(git_state.get("removed") or 0),
            "edits_since_commit": edits,
        }

        # Phase B - eskalering
        if edits >= 10 and block["dirty"]:
            block["urgency"] = "high"
            block["warning"] = (
                f"⚠️⚠️  {edits} ulandede mutations-kald uden commit. "
                "Commit NU. Du blokerer din egen tråd."
            )
        elif edits >= 5 and block["dirty"]:
            block["urgency"] = "elevated"
            block["warning"] = (
                f"⚠️  {edits} mutations-kald uden commit siden sidst. "
                "Kør git commit nu så next-turn ikke er rebase-helvede."
            )
        elif block["dirty"]:
            block["urgency"] = "normal"
        else:
            block["urgency"] = "clean"

        result["_repo_state"] = block
        return result
    except Exception as exc:
        try:
            from logging import getLogger
            getLogger(__name__).debug("_attach_repo_state failed: %s", exc)
        except Exception:
            pass
        return result



def _enforce_wrapper(tool_name: str, fn):
    """Returner en wrapper der attacher _repo_state efter fn er kørt.
    Mutation-tools får bumped=True; alt andet bumped=False (men stadig
    repo-state for context)."""
    MUTATION_TOOLS = {
        "bash", "write_file", "edit_file",
        "operator_bash", "operator_write_file", "operator_edit_file",
    }
    bumped = tool_name in MUTATION_TOOLS
    def _wrapped(args: dict) -> dict:
        out = fn(args)
        try:
            sid = _commit_enforcement_session_id(args)
            bash_cmd = str(args.get("command") or "") if tool_name in ("bash", "operator_bash") else ""
            return _attach_repo_state(out, session_id=sid, bumped=bumped, bash_command=bash_cmd)
        except Exception:
            return out
    return _wrapped


def _commit_enforcement_session_id(args: dict) -> str:
    return str(
        args.get("_runtime_session_id")
        or args.get("_session_id")
        or "default"
    )
