"""Default persistent bash-session ownership for the one-shot ``bash`` tool.

Kept separate from ``simple_tools_web`` so shell lifecycle/state has one
primary responsibility and can evolve without growing the web-tool module.
"""
from __future__ import annotations

import threading as _threading_for_bash
from typing import Any


# Daemonens loft er otte sessioner. Seks reserveres til almindelige `bash`-
# arbejds-shells, så to eksplicitte bash_session_open-kald stadig har plads.
_MAX_DEFAULT_BASH_SESSIONS = 6
_DEFAULT_BASH_SESSION_IDS: dict[str, str] = {}
_DEFAULT_BASH_SESSION_LOCK = _threading_for_bash.Lock()


def _default_bash_session_scope(args: dict[str, Any] | None = None) -> str:
    """Return a stable owner/session scope for the ordinary ``bash`` tool."""
    data = args or {}
    user_id = str(
        data.get("_runtime_user_id") or data.get("_user_id") or ""
    ).strip()
    session_id = str(
        data.get("_runtime_session_id") or data.get("_session_id") or ""
    ).strip()
    turn_id = str(data.get("_runtime_turn_id") or "").strip()

    if session_id:
        return f"session:{user_id or '_unknown'}:{session_id}"
    if turn_id:
        return f"turn:{user_id or '_unknown'}:{turn_id}"
    if user_id:
        return f"user:{user_id}"
    return "_default"


def _get_or_open_default_bash_session(scope: str | None = None) -> str | None:
    key = str(scope or "_default")
    # Importeres HER (6/9-2026). De to `_exec_bash_session_*` blev BRUGT uden
    # nogensinde at vaere importeret — en NameError som kalderen fangede med
    # `except Exception` og loggede paa DEBUG. Resultatet: sid blev None, alt
    # faldt til engangs-subprocessen, og den PERSISTENTE shell har aldrig
    # vaeret i brug herfra. Maalt: `cd /tmp` efterfulgt af `pwd` gav
    # repo-roden, selv om kommentaren i _exec_bash lover det modsatte.
    from core.tools.bash_session import (
        _exec_bash_session_close,
        _exec_bash_session_list,
        _open_arbejdssession,
    )
    with _DEFAULT_BASH_SESSION_LOCK:
        listed = _exec_bash_session_list({})
        rows = list(listed.get("sessions") or []) if listed.get("status") == "ok" else []
        alive = {
            str(row.get("session_id")): row
            for row in rows
            if row.get("alive") and row.get("session_id")
        }

        # Daemonen kan overleve API-processen. Fjern proceslokale pegere til
        # shells daemonen ikke længere kender, før der vælges/genåbnes.
        for stale_scope, stale_sid in list(_DEFAULT_BASH_SESSION_IDS.items()):
            if stale_sid not in alive:
                _DEFAULT_BASH_SESSION_IDS.pop(stale_scope, None)

        sid = _DEFAULT_BASH_SESSION_IDS.get(key)
        if sid and sid in alive:
            return sid

        # API-processen kan være genstartet mens daemonen fortsatte. Genadoptér
        # den scope-mærkede shell i stedet for at åbne en ny og fylde loftet.
        adopted = next(
            (
                candidate_sid
                for candidate_sid, row in alive.items()
                if row.get("arbejde") and str(row.get("arbejde_scope") or "") == key
            ),
            None,
        )
        if adopted:
            _DEFAULT_BASH_SESSION_IDS[key] = adopted
            return adopted

        # Undgå at den sessionspecifikke pool selv bliver en ny kø. Når loftet
        # er nået, returneres None, og kalderen bruger engangs-subprocess.
        # Vi lukker ikke en eksisterende shell ud fra et øjebliksbillede af
        # `busy`: mellem list og close kunne dens ejer nå at starte et kald.
        if len(_DEFAULT_BASH_SESSION_IDS) >= _MAX_DEFAULT_BASH_SESSIONS:
            return None

        # `_open_arbejdssession`, ikke `_exec_bash_session_open`: den delte
        # shell er ikke en opgave, og daemonen skal maerke den som arbejde.
        # Forskellen er nu at "delt" betyder inden for samme chat-session —
        # aldrig på tværs af samtidige visible runs.
        result = _open_arbejdssession(key)
        if result.get("status") == "error" and "max " in str(result.get("error") or ""):
            # Rollout-kompatibilitet: daemoner fra før scope-fixet kan stå med
            # op til otte anonyme, ledige arbejds-shells. Luk kun én sådan
            # legacy-shell efter et bekræftet kapacitetsafslag og prøv igen.
            # Scope-mærkede eller optagede shells røres aldrig her.
            legacy = next(
                (
                    row
                    for row in rows
                    if row.get("arbejde")
                    and not row.get("busy")
                    and not str(row.get("arbejde_scope") or "")
                ),
                None,
            )
            if legacy and legacy.get("session_id"):
                _exec_bash_session_close({"session_id": str(legacy["session_id"])})
                result = _open_arbejdssession(key)
        if result.get("status") == "ok" and result.get("session_id"):
            sid = str(result["session_id"])
            _DEFAULT_BASH_SESSION_IDS[key] = sid
            return sid
        return None


def _reset_default_bash_session(scope: str | None = None) -> None:
    key = str(scope or "_default")
    with _DEFAULT_BASH_SESSION_LOCK:
        _DEFAULT_BASH_SESSION_IDS.pop(key, None)


__all__ = [
    "_DEFAULT_BASH_SESSION_LOCK",
    "_default_bash_session_scope",
    "_get_or_open_default_bash_session",
    "_reset_default_bash_session",
    "_threading_for_bash",
]
