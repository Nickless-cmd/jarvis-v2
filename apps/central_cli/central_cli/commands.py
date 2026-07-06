from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    method: str
    path: str
    body: dict | None
    write: bool


# Direkte GET-endpoints (realtime/observabilitet).
_GET_ENDPOINTS = {
    "status": "/central/realtime",
    "realtime": "/central/realtime",
    "series": "/central/timeseries",
    "diag": "/central/diagnostics",
    "providers": "/central/providers",
    "mind": "/central/mind",
    "feel": "/central/feel",
    "overview": "/mc/overview",
    "costs": "/mc/costs",
    "runs": "/mc/runs",
    "approvals": "/mc/approvals",
    "autonomous": "/central/autonomous",
    "connections": "/central/connections",
    "users": "/central/users",
    "excess": "/central/excess",
    "decentral": "/central/decentralization",
    "keys": "/central/keys",
    "construct": "/central/construct",
    "oracle": "/central/oracle",
    "architect": "/central/architect",
    "echo": "/central/echo-breaker",
    "glitch": "/central/glitch",
    "continuity": "/central/continuity",
}

# Verber der routes til central_terminal-parseren via POST /central/command
# (genbrug af eksisterende vokabular — ingen duplikeret logik).
_TERMINAL_VERBS = {
    "incidents", "trace", "scan", "instrument", "daemons", "model",
    "learning", "drift", "breakers", "autonomy", "clusters", "resolve",
}


def resolve_command(verb: str, args: list[str]) -> CommandSpec:
    """Map (verb, args) → CommandSpec. Writes markeres write=True (til confirm-guard)."""
    if verb in _GET_ENDPOINTS:
        return CommandSpec("GET", _GET_ENDPOINTS[verb], None, False)

    if verb == "nerve" and args:
        return CommandSpec("GET", f"/central/nerve/{args[0]}", None, False)

    if verb == "toggle" and len(args) >= 1:
        nerve = args[0]
        enabled = not (len(args) >= 2 and args[1].lower() in ("off", "false", "0"))
        return CommandSpec("POST", f"/central/nerve/{nerve}/toggle", {"enabled": enabled}, True)

    if verb == "approve" and len(args) >= 2:
        kind, ident = args[0], args[1]
        path = {
            "tool": "/mc/tool-intent/approve",
            "autonomy": f"/mc/autonomy/proposals/{ident}/approve",
            "initiative": f"/mc/initiatives/{ident}/approve",
        }.get(kind, "/mc/tool-intent/approve")
        body = {"id": ident} if kind == "tool" else {}
        return CommandSpec("POST", path, body, True)

    if verb == "deny" and len(args) >= 2:
        kind, ident = args[0], args[1]
        path = {
            "tool": "/mc/tool-intent/deny",
            "autonomy": f"/mc/autonomy/proposals/{ident}/reject",
            "initiative": f"/mc/initiatives/{ident}/reject",
        }.get(kind, "/mc/tool-intent/deny")
        body = {"id": ident} if kind == "tool" else {}
        return CommandSpec("POST", path, body, True)

    # The Keymaker: godkend en optjent nøgle → flip flag ON i TTL (owner-write).
    if verb == "unlock" and len(args) >= 1:
        return CommandSpec("POST", f"/central/keys/{args[0]}/approve", {}, True)

    # Alt andet → central_terminal-parser via /central/command.
    line = " ".join([verb, *args]).strip()
    is_write = verb in ("resolve",)
    return CommandSpec("POST", "/central/command", {"line": line}, is_write)
