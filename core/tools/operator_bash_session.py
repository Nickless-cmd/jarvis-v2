"""operator_bash_session — vedvarende-FØLELSE bash-session på operatorens maskine.

Samme open/run/close-UX som det lokale `bash_session`, men shellen lever IKKE som en
ægte daemon på operatoren (det kræver bro-ændringer). I stedet **server-emuleres**
sessionen: `cwd` spores server-side via en markør, og exporteret env/venv persisteres
i en `.env`-fil PÅ operatoren der source'es ved hver run. Ét bro-hop pr. run → samme
stabilitet som `operator_bash`, men `cd`/venv/env-vars overlever på tværs af kald.

NB (Bjørn 2026-06-21): bevidst minimal — del af tool-systemet der skal konsolideres
under unified-gate-arbejdet. Tilføjet nu som quick-fix.
"""
from __future__ import annotations

import shlex
import threading
import time
import uuid
from typing import Any

_SESSIONS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_IDLE_TTL = 1800.0  # 30 min idle, som bash_session
_CWD_MARKER = "__OBS_CWD__:"


def _now() -> float:
    return time.time()


def _q(s: str) -> str:
    return shlex.quote(s or "")


def _reap() -> None:
    cutoff = _now() - _IDLE_TTL
    with _LOCK:
        for sid in [s for s, v in _SESSIONS.items() if v.get("last", 0.0) < cutoff]:
            _SESSIONS.pop(sid, None)


def _extract_cwd(out: str) -> tuple[str, str]:
    """Pluk cwd-markøren ud af stdout og fjern den fra det Jarvis ser."""
    cwd, keep = "", []
    for ln in (out or "").splitlines():
        if ln.startswith(_CWD_MARKER):
            cwd = ln[len(_CWD_MARKER):].strip()
        else:
            keep.append(ln)
    return cwd, "\n".join(keep)


def _exec_operator_bash_session_open(args: dict[str, Any]) -> dict[str, Any]:
    _reap()
    uid = str(args.get("_user_id") or "").strip()
    sid = "opsess-" + uuid.uuid4().hex[:12]
    with _LOCK:
        _SESSIONS[sid] = {"cwd": "", "user_id": uid, "last": _now()}
    return {
        "status": "ok", "session_id": sid,
        "note": ("Vedvarende operator-shell-session. Genbrug session_id i "
                 "operator_bash_session_run — cd, env-vars og virtualenvs persisterer."),
    }


def _exec_operator_bash_session_run(args: dict[str, Any]) -> dict[str, Any]:
    sid = str(args.get("session_id") or "").strip()
    cmd = str(args.get("command") or "")
    if not sid:
        return {"status": "error", "error": "session_id is required"}
    if not cmd:
        return {"status": "error", "error": "command is required"}
    with _LOCK:
        sess = _SESSIONS.get(sid)
    if sess is None:
        return {"status": "error",
                "error": "unknown session_id (udløbet?) — kald operator_bash_session_open"}
    uid = sess.get("user_id") or str(args.get("_user_id") or "")
    cwd = sess.get("cwd") or ""
    envf = f"/tmp/.jarvis_opsess_{sid}.env"
    cd_line = f"cd {_q(cwd)} 2>/dev/null\n" if cwd else ""
    wrapped = (
        f"{cd_line}"
        f"[ -f {_q(envf)} ] && . {_q(envf)} 2>/dev/null\n"
        f"{cmd}\n"
        f"__obs_rc=$?\n"
        f"export -p > {_q(envf)} 2>/dev/null\n"
        f'printf "\\n{_CWD_MARKER}%s\\n" "$(pwd)"\n'
        f"exit $__obs_rc\n"
    )
    timeout = args.get("timeout") or 30.0
    try:
        timeout = max(1.0, min(float(timeout), 300.0))
    except Exception:
        timeout = 30.0

    from core.tools.simple_tools import _exec_operator_bash
    res = _exec_operator_bash({"command": wrapped, "_user_id": uid, "timeout_s": timeout})

    inner = (res or {}).get("result") if isinstance(res, dict) else None
    if isinstance(inner, dict):
        new_cwd, cleaned = _extract_cwd(str(inner.get("stdout") or ""))
        inner["stdout"] = cleaned
        if new_cwd:
            with _LOCK:
                if sid in _SESSIONS:
                    _SESSIONS[sid]["cwd"] = new_cwd
                    _SESSIONS[sid]["last"] = _now()
    return res


def _exec_operator_bash_session_close(args: dict[str, Any]) -> dict[str, Any]:
    sid = str(args.get("session_id") or "").strip()
    if not sid:
        return {"status": "error", "error": "session_id is required"}
    with _LOCK:
        sess = _SESSIONS.pop(sid, None)
    uid = (sess or {}).get("user_id") or str(args.get("_user_id") or "")
    try:  # ryd operator-side env-fil (best-effort)
        from core.tools.simple_tools import _exec_operator_bash
        _exec_operator_bash({"command": f"rm -f /tmp/.jarvis_opsess_{sid}.env",
                             "_user_id": uid, "timeout_s": 10.0})
    except Exception:
        pass
    return {"status": "ok", "closed": bool(sess)}


def _exec_operator_bash_session_list(_args: dict[str, Any]) -> dict[str, Any]:
    _reap()
    now = _now()
    with _LOCK:
        sessions = [
            {"session_id": s, "cwd": v.get("cwd") or "~", "idle_s": round(now - v.get("last", now), 1)}
            for s, v in _SESSIONS.items()
        ]
    return {"status": "ok", "sessions": sessions}


OPERATOR_BASH_SESSION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "operator_bash_session_open",
        "description": (
            "Åbn en vedvarende shell-session på brugerens egen maskine (operatoren). "
            "Returnerer et session_id du genbruger på tværs af kald, så cd, env-vars og "
            "virtualenvs persisterer — samme stabilitet som operator_bash (ét bro-hop pr. "
            "run), men med vedvarende tilstand. Idle-sessioner dør efter 30 min."),
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "operator_bash_session_run",
        "description": (
            "Kør en kommando i en åben operator-session. Samme shell-tilstand som forrige "
            "kald (cd, env, venv). Returnerer exit_code + output. Default timeout 30s, max 300s."),
        "parameters": {"type": "object", "properties": {
            "session_id": {"type": "string", "description": "Returneret af operator_bash_session_open."},
            "command": {"type": "string", "description": "Shell-kommando."},
            "timeout": {"type": "number", "description": "Sekunder før timeout (default 30, max 300)."}},
            "required": ["session_id", "command"]}}},
    {"type": "function", "function": {
        "name": "operator_bash_session_close",
        "description": "Luk en operator-session og ryd dens env-fil på maskinen.",
        "parameters": {"type": "object", "properties": {
            "session_id": {"type": "string"}}, "required": ["session_id"]}}},
    {"type": "function", "function": {
        "name": "operator_bash_session_list",
        "description": "List åbne operator-sessioner + deres cwd og idle-tid.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
]
