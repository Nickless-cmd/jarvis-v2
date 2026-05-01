"""Tool wrappers for the process supervisor."""
from __future__ import annotations

from typing import Any

from core.services.process_supervisor import (
    list_processes,
    remove_process,
    spawn_process,
    stop_process,
    tail_process_log,
)


def _exec_process_spawn(args: dict[str, Any]) -> dict[str, Any]:
    return spawn_process(
        name=str(args.get("name") or "").strip(),
        command=str(args.get("command") or "").strip(),
        cwd=str(args.get("cwd") or "").strip() or None,
        env=args.get("env") if isinstance(args.get("env"), dict) else None,
        replace_if_running=bool(args.get("replace_if_running", False)),
    )


def _exec_process_list(args: dict[str, Any]) -> dict[str, Any]:
    return list_processes(include_stopped=bool(args.get("include_stopped", True)))


def _exec_process_stop(args: dict[str, Any]) -> dict[str, Any]:
    return stop_process(
        str(args.get("name") or "").strip(),
        grace=int(args.get("grace") or 5),
    )


def _exec_process_tail(args: dict[str, Any]) -> dict[str, Any]:
    return tail_process_log(
        str(args.get("name") or "").strip(),
        lines=int(args.get("lines") or 40),
    )


def _exec_process_remove(args: dict[str, Any]) -> dict[str, Any]:
    return remove_process(str(args.get("name") or "").strip())


PROCESS_SUPERVISOR_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "process_spawn",
            "description": (
                "Spawn a long-running background process under JarvisX supervision. "
                "Use this INSTEAD of `nohup foo &` via bash — supervised processes "
                "have their pid tracked, stdout+stderr captured to a per-name log, "
                "and remain visible to process_list/process_tail/process_stop. "
                "Examples: a poller daemon, a watcher, a dev server. Each process "
                "is keyed by `name` (sanitized to alphanum + - _ .). If a process "
                "with the same name is already running, this errors unless you pass "
                "replace_if_running=true."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Identifier (e.g. 'toku-poller')"},
                    "command": {"type": "string", "description": "Shell command to run"},
                    "cwd": {"type": "string", "description": "Working directory (optional)"},
                    "env": {
                        "type": "object",
                        "description": "Extra env vars (optional, merged onto current env)",
                    },
                    "replace_if_running": {
                        "type": "boolean",
                        "description": "Stop existing same-name process and respawn (default false)",
                    },
                },
                "required": ["name", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_list",
            "description": (
                "List supervised processes with status (running/exited/lost), "
                "uptime, command, cwd, log path. 'lost' = pid no longer exists "
                "but no exit code captured (e.g. parent runtime restarted while "
                "the process was alive)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "include_stopped": {
                        "type": "boolean",
                        "description": "Include exited/lost entries (default true)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_stop",
            "description": (
                "Gracefully stop a supervised process: SIGTERM, wait `grace` seconds, "
                "SIGKILL if still alive. Default grace 5s. The registry entry remains "
                "(use process_remove to clean up after stop)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "grace": {"type": "integer", "description": "Seconds before SIGKILL (default 5)"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_tail",
            "description": (
                "Read the last N lines of a supervised process's combined "
                "stdout+stderr log. Default 40, max 500."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "lines": {"type": "integer", "description": "Number of lines (default 40, max 500)"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_remove",
            "description": (
                "Remove a stopped process from the registry. Refuses if still "
                "running — call process_stop first."
            ),
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
]


PROCESS_SUPERVISOR_TOOL_HANDLERS: dict[str, Any] = {
    "process_spawn": _exec_process_spawn,
    "process_list": _exec_process_list,
    "process_stop": _exec_process_stop,
    "process_tail": _exec_process_tail,
    "process_remove": _exec_process_remove,
}
