"""Default persistent bash-session ownership for the one-shot ``bash`` tool.

Kept separate from ``simple_tools_web`` so shell lifecycle/state has one
primary responsibility and can evolve without growing the web-tool module.
"""
from __future__ import annotations

import threading as _threading_for_bash


_DEFAULT_BASH_SESSION_ID: str | None = None
_DEFAULT_BASH_SESSION_LOCK = _threading_for_bash.Lock()


def _get_or_open_default_bash_session() -> str | None:
    global _DEFAULT_BASH_SESSION_ID
    # Importeres HER (6/9-2026). De to `_exec_bash_session_*` blev BRUGT uden
    # nogensinde at vaere importeret — en NameError som kalderen fangede med
    # `except Exception` og loggede paa DEBUG. Resultatet: sid blev None, alt
    # faldt til engangs-subprocessen, og den PERSISTENTE shell har aldrig
    # vaeret i brug herfra. Maalt: `cd /tmp` efterfulgt af `pwd` gav
    # repo-roden, selv om kommentaren i _exec_bash lover det modsatte.
    from core.tools.bash_session import (
        _exec_bash_session_list,
        _open_arbejdssession,
    )
    with _DEFAULT_BASH_SESSION_LOCK:
        sid = _DEFAULT_BASH_SESSION_ID
        if sid:
            # Verify the daemon still knows this session.
            listed = _exec_bash_session_list({})
            if listed.get("status") == "ok":
                alive_ids = {
                    str(s.get("session_id"))
                    for s in (listed.get("sessions") or [])
                    if s.get("alive")
                }
                if sid in alive_ids:
                    return sid
            # Otherwise: fall through and re-open below.
            _DEFAULT_BASH_SESSION_ID = None
        # `_open_arbejdssession`, ikke `_exec_bash_session_open`: den delte
        # shell er ikke en opgave, og daemonen skal maerke den som arbejde.
        result = _open_arbejdssession()
        if result.get("status") == "ok" and result.get("session_id"):
            _DEFAULT_BASH_SESSION_ID = str(result["session_id"])
            return _DEFAULT_BASH_SESSION_ID
        return None


def _reset_default_bash_session() -> None:
    global _DEFAULT_BASH_SESSION_ID
    with _DEFAULT_BASH_SESSION_LOCK:
        _DEFAULT_BASH_SESSION_ID = None


__all__ = [
    "_DEFAULT_BASH_SESSION_LOCK",
    "_get_or_open_default_bash_session",
    "_reset_default_bash_session",
    "_threading_for_bash",
]
