"""Verification gate — advisory check on destructive/mutation actions.

R2 of the reasoning-layer rollout. Pure observational: reads the eventbus,
classifies recent tool.completed events, and reports two kinds of signals:

1. **Unverified mutations** — files written/edited or commands run, with no
   matching verify_* call afterward. Suggests a verify_* the model could
   make next.
2. **Failed verifications** — recent verify_* calls that returned status
   "failed". Hard evidence the model claimed something that wasn't true.

Does NOT block. Does NOT auto-call verify_* (that would surprise the user
and cost tokens). It surfaces awareness only — the model decides what to
do with it.

Reads eventbus on demand. No daemon, no persistence. Cheap to call.

Promotion path: if telemetry shows the model ignores the warnings while
mutations slip through, R2.5 can flip the gate to blocking for tier=deep
actions. That's a separate decision after we have data.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── Shell-kommando-klassifikator (R2 noise-reduktion, 2026-06-13) ────────
# Problem: hver bash-kald talte som mutation — også read-only (grep/cat/ls/
# git status). Det gav ~45 advarsler/dag → banner blindness → 15% heed-rate.
# Fix: tæl KUN shell-kald der reelt ændrer state. Konservativ: ukendt
# kommando → mutation (misser aldrig reel risiko; skærer kun kendt støj).

# Kommandoer der ALDRIG ændrer state (hele kommandoen er read-only).
_RO_CMDS: frozenset[str] = frozenset({
    "cat", "less", "more", "head", "tail", "bat", "tac", "nl", "zcat",
    "ls", "ll", "dir", "tree", "find", "fd", "stat", "file", "du", "df", "wc",
    "realpath", "readlink", "basename", "dirname", "lsblk", "lsof", "blkid",
    "grep", "rg", "ag", "ack", "egrep", "fgrep", "zgrep",
    "ps", "pgrep", "pidof", "top", "free", "uptime", "whoami", "id", "hostname",
    "uname", "env", "printenv", "which", "type", "pwd", "date", "cal", "nproc",
    "lscpu", "echo", "printf", "jq", "yq", "sort", "uniq", "cut", "tr", "column",
    "comm", "join", "paste", "fold", "diff", "cmp", "md5sum", "sha256sum",
    "sha1sum", "cksum", "test", "true", "false", "seq", "nvidia-smi", "netstat",
    "ss", "ping", "dig", "host", "man", "history", "tldr", "hexdump", "xxd",
    "strings", "od", "tac", "rev", "expr", "bc", "wc",
})
# Kontekst-følsomme: KUN read-only for disse subkommandoer (None = altid RO).
_RO_SUBCMD: dict[str, frozenset[str] | None] = {
    "git": frozenset({
        "status", "log", "diff", "show", "branch", "rev-parse", "ls-files",
        "blame", "describe", "config", "remote", "shortlog", "reflog",
        "cat-file", "rev-list", "name-rev", "whatchanged", "grep", "ls-tree",
        "var", "help", "tag", "stash",  # tag/stash uden args = list (RO nok)
    }),
    "systemctl": frozenset({
        "status", "is-active", "is-enabled", "is-failed", "list-units",
        "list-unit-files", "show", "cat", "get-default", "list-dependencies",
    }),
    "journalctl": None,
    "docker": frozenset({"ps", "images", "logs", "inspect", "stats", "top",
                         "version", "info", "port", "diff", "history"}),
    "kubectl": frozenset({"get", "describe", "logs", "top", "explain",
                          "api-resources", "version", "config"}),
    "ollama": frozenset({"list", "show", "ps"}),
    "npm": frozenset({"list", "ls", "view", "outdated", "audit"}),
    "pip": frozenset({"list", "show", "freeze"}),
    "pip3": frozenset({"list", "show", "freeze"}),
    "conda": frozenset({"list", "info", "env"}),
}
# Write-redirect til en rigtig fil (ikke /dev/null eller fd-dup) → mutation.
_WRITE_REDIRECT = re.compile(r">>?\s*(?!/dev/null|&)\S")
_SEG_SPLIT = re.compile(r"&&|\|\||;|\|")


def shell_command_is_mutating(command: str) -> bool:
    """True hvis et shell-kald reelt ændrer state; False for read-only.

    Konservativ: ukendt kommando → True (mutation). Skærer kun kendt read-only
    støj (grep/cat/ls/git status/...) fra R2-gatens mutations-tælling."""
    c = (command or "").strip()
    if not c:
        return False
    if _WRITE_REDIRECT.search(c):
        return True
    for seg in _SEG_SPLIT.split(c):
        toks = seg.split()
        i = 0
        # spring env-assignments + wrappere over (FOO=bar sudo nohup time exec)
        while i < len(toks) and (
            ("=" in toks[i] and not toks[i].startswith("-"))
            or toks[i] in ("sudo", "nohup", "time", "exec", "env", "command", "stdbuf")
        ):
            i += 1
        if i >= len(toks):
            continue
        cmd = toks[i].rsplit("/", 1)[-1]
        sub = toks[i + 1] if i + 1 < len(toks) else ""
        if cmd in _RO_SUBCMD:
            allowed = _RO_SUBCMD[cmd]
            if allowed is None or sub in allowed:
                continue
            return True
        if cmd == "sed":
            if "-i" in toks:
                return True
            continue
        if cmd in _RO_CMDS:
            continue
        return True  # ukendt kommando → konservativt en mutation
    return False

# Tools that *change state* (file/repo/system/config/memory/comms) and should
# ideally be paired with a verify before the model claims success.
_MUTATION_TOOLS_FILE: frozenset[str] = frozenset({
    "write_file", "edit_file", "publish_file", "stage_edit_file",
})
_MUTATION_TOOLS_SHELL: frozenset[str] = frozenset({
    "bash", "bash_session_run",
})
_MUTATION_TOOLS_SERVICE: frozenset[str] = frozenset({
    "control_daemon", "restart_overdue_daemons",
})
_MUTATION_TOOLS_CONFIG: frozenset[str] = frozenset({
    "update_setting", "approve_proposal", "approve_plan",
    "propose_git_commit",
})
# Phase 1 expansion (2026-05-14): memory writes and outbound communication
# are mutations too — Jarvis was treating these as "free" because they
# weren't in the gate's awareness.
_MUTATION_TOOLS_MEMORY: frozenset[str] = frozenset({
    "memory_upsert_section",
})
_MUTATION_TOOLS_COMMS: frozenset[str] = frozenset({
    "send_discord_dm",
})
_MUTATION_TOOLS_TODO: frozenset[str] = frozenset({
    "todo_set", "todo_update_status",
})

_MUTATION_TOOLS: frozenset[str] = (
    _MUTATION_TOOLS_FILE
    | _MUTATION_TOOLS_SHELL
    | _MUTATION_TOOLS_SERVICE
    | _MUTATION_TOOLS_CONFIG
    | _MUTATION_TOOLS_MEMORY
    | _MUTATION_TOOLS_COMMS
    | _MUTATION_TOOLS_TODO
)

# Strict verifies — explicit verify_* tools designed for the purpose.
# When Jarvis calls one of these, it's a strong signal of "I checked".
_VERIFY_TOOLS: frozenset[str] = frozenset({
    "verify_file_contains", "verify_service_active", "verify_endpoint_responds",
})

# Light verifies (Phase 1 addition, 2026-05-14) — tools that read back
# state without claiming it. When Jarvis reads a file he just edited, or
# queries db_query / process_list / git_log right after a mutation,
# that's evidence he at least glanced back. Weaker signal than a strict
# verify_*, but a much better proxy for "did you look?" than nothing.
#
# Counted toward "effective heeding" in telemetry; reported separately
# from strict_heeded so the difference is visible.
_LIGHT_VERIFY_TOOLS: frozenset[str] = frozenset({
    "read_file",
    "db_query",
    "process_list", "process_tail",
    "git_log",
    "find_files",
    "smart_outline",
    "search", "search_memory", "search_sessions", "search_chat_history",
    "semantic_search_code",
    "verification_status",
})

ALL_VERIFY_TOOLS: frozenset[str] = _VERIFY_TOOLS | _LIGHT_VERIFY_TOOLS

_LOOKBACK_MINUTES = 10
_LOOKBACK_EVENTS = 200
_MAX_WARNINGS_SURFACED = 4


def _suggested_verify(tool: str) -> str | None:
    if tool in _MUTATION_TOOLS_FILE:
        return "verify_file_contains"
    if tool in _MUTATION_TOOLS_SERVICE:
        return "verify_service_active"
    return None  # bash / config: no automatic suggestion


def _recent_events(minutes: int = _LOOKBACK_MINUTES) -> list[dict[str, Any]]:
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=_LOOKBACK_EVENTS)
    except Exception:
        return []
    cutoff = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()
    out: list[dict[str, Any]] = []
    for e in events:
        if str(e.get("created_at", "")) >= cutoff:
            out.append(e)
    return out


def _scan(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify events into mutations / strict-verifies / light-verifies.

    Strict verifies = explicit verify_* tools.
    Light verifies = read-back tools (read_file, db_query, process_list, ...).
    Both count toward "effective" heeding; only strict counts as a strong signal.
    """
    mutations: list[dict[str, Any]] = []
    strict_verifies: list[dict[str, Any]] = []
    light_verifies: list[dict[str, Any]] = []
    failed_verifies: list[dict[str, Any]] = []

    for e in events:
        if str(e.get("kind", "")) != "tool.completed":
            continue
        payload = e.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        tool = str(payload.get("tool", ""))
        status = str(payload.get("status", ""))
        ts = str(e.get("created_at", ""))
        item = {"tool": tool, "status": status, "ts": ts, "payload": payload}
        if tool in _VERIFY_TOOLS:
            strict_verifies.append(item)
            if status == "failed":
                failed_verifies.append(item)
        elif tool in _LIGHT_VERIFY_TOOLS and status == "ok":
            light_verifies.append(item)
        elif tool in _MUTATION_TOOLS and status == "ok":
            # Shell-kald: tæl kun hvis det reelt ændrer state. Emit-siden
            # sætter "mutating" på payloaden; default True (gamle events +
            # sikkerhed). Skærer read-only støj (grep/cat/git status/...).
            if tool in _MUTATION_TOOLS_SHELL and not payload.get("mutating", True):
                continue
            mutations.append(item)

    return {
        "mutations": mutations,
        "verifies": strict_verifies,           # back-compat key
        "strict_verifies": strict_verifies,
        "light_verifies": light_verifies,
        "failed_verifies": failed_verifies,
    }


def evaluate_verification_gate(*, minutes: int = _LOOKBACK_MINUTES) -> dict[str, Any]:
    """Return verification-gate signals for the recent window."""
    events = _recent_events(minutes=minutes)
    scan = _scan(events)
    mutations = scan["mutations"]
    strict_verifies = scan["strict_verifies"]
    light_verifies = scan["light_verifies"]
    failed = scan["failed_verifies"]

    by_tool: dict[str, int] = {}
    for m in mutations:
        by_tool[m["tool"]] = by_tool.get(m["tool"], 0) + 1

    # Strict-only count: mutations without an explicit verify_* call
    unverified_strict = max(0, len(mutations) - len(strict_verifies))
    # Effective count: mutations without ANY readback (strict OR light)
    unverified_effective = max(
        0, len(mutations) - len(strict_verifies) - len(light_verifies)
    )

    suggestions: list[str] = []
    for tool, count in sorted(by_tool.items(), key=lambda kv: -kv[1]):
        verify = _suggested_verify(tool)
        if verify and count > 0:
            suggestions.append(f"{count}× {tool} → overvej {verify}")

    return {
        "status": "ok",
        "window_minutes": minutes,
        "mutation_count": len(mutations),
        "verify_count": len(strict_verifies),               # back-compat
        "strict_verify_count": len(strict_verifies),
        "light_verify_count": len(light_verifies),
        "failed_verify_count": len(failed),
        "unverified_count": unverified_strict,              # back-compat
        "unverified_strict": unverified_strict,
        "unverified_effective": unverified_effective,
        "by_tool": by_tool,
        "suggestions": suggestions,
        "failed_verifies": [
            {
                "tool": f["tool"],
                "reason": str((f.get("payload") or {}).get("result", {}).get("reason"))
                if isinstance((f.get("payload") or {}).get("result"), dict)
                else "",
                "ts": f["ts"],
            }
            for f in failed[:_MAX_WARNINGS_SURFACED]
        ],
    }


def verification_gate_section() -> str | None:
    """Format gate signals as a prompt-awareness section, or None.

    Uses "effective" unverified count (no strict verify AND no light readback)
    to decide whether to surface. This avoids nagging when Jarvis has already
    glanced back at what he mutated.
    """
    result = evaluate_verification_gate()
    failed = result.get("failed_verifies") or []
    unverified_effective = int(result.get("unverified_effective") or 0)
    unverified_strict = int(result.get("unverified_strict") or 0)
    suggestions = result.get("suggestions") or []

    if not failed and unverified_effective <= 0:
        return None

    # Record this surface for R2 telemetry — we want to know whether this
    # warning gets heeded (followed by a strict OR light readback).
    try:
        from core.services.verification_gate_telemetry import record_surface
        record_surface(
            failed_verify_count=int(result.get("failed_verify_count") or 0),
            unverified_count=unverified_effective,
            mutation_count=int(result.get("mutation_count") or 0),
            verify_count=int(result.get("strict_verify_count") or 0),
        )
    except Exception:
        pass

    lines: list[str] = []
    if failed:
        lines.append(
            f"❌ {len(failed)} verify_* fejlede i sidste {result['window_minutes']} min "
            f"— hård evidens for at du har påstået noget der ikke holder:"
        )
        for f in failed:
            reason = f.get("reason") or "se eventbus for detaljer"
            lines.append(f"  - {f['tool']}: {reason}")
    if unverified_effective > 0:
        strict = int(result.get("strict_verify_count") or 0)
        light = int(result.get("light_verify_count") or 0)
        lines.append(
            f"⚠ {result['mutation_count']} mutations / {strict} strict-verifies "
            f"/ {light} read-backs i sidste {result['window_minutes']} min — "
            f"{unverified_effective} mutation(er) uden nogen form for kig tilbage:"
        )
        if suggestions:
            for s in suggestions[:_MAX_WARNINGS_SURFACED]:
                lines.append(f"  - {s}")
        else:
            # No suggested verify_* for these mutation kinds, but still
            # surface the count by tool — Jarvis can decide if a readback
            # (read_file / db_query / process_list / ...) is warranted.
            by_tool = result.get("by_tool") or {}
            top_tools = sorted(by_tool.items(), key=lambda kv: -kv[1])[:_MAX_WARNINGS_SURFACED]
            for tool, count in top_tools:
                lines.append(f"  - {count}× {tool}")

    return "Verification gate:\n" + "\n".join(lines)


def _exec_verification_status(args: dict[str, Any]) -> dict[str, Any]:
    minutes = int(args.get("minutes") or _LOOKBACK_MINUTES)
    minutes = max(1, min(120, minutes))
    return evaluate_verification_gate(minutes=minutes)


VERIFICATION_GATE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "verification_status",
            "description": (
                "Read the verification gate: how many mutations vs verifies "
                "in the recent window, plus any failed verify_* calls. "
                "Returns suggestions for which verify_* to run next. "
                "Advisory only — does not block or auto-call anything."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {
                        "type": "integer",
                        "description": "Lookback window (default 10, max 120).",
                    },
                },
                "required": [],
            },
        },
    },
]


def build_verification_gate_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "verification_gate",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_verification_gate_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"verification_gate.{kind}",
            payload or {},
        )
    except Exception:
        pass

