"""Simple, general-purpose tools for Jarvis visible lane.

Eight tools that cover everything Jarvis needs. Permission logic lives
here in the runtime, not in the prompt. Models call tools via native
function calling; the runtime decides what to approve.
"""

from __future__ import annotations

import html
import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from core.eventbus.bus import event_bus
from core.runtime.config import JARVIS_HOME, PROJECT_ROOT

MAX_READ_CHARS = 32000
MAX_SEARCH_RESULTS = 60
MAX_SEARCH_LINE_CHARS = 200
MAX_FIND_RESULTS = 100
MAX_BASH_OUTPUT_CHARS = 16000
MAX_BASH_SECONDS = 15
MAX_WEB_FETCH_CHARS = 24000
WORKSPACE_DIR = Path(JARVIS_HOME) / "workspaces" / "default"

# Paths that can be written without user approval.
_AUTO_APPROVE_WRITE_PATHS = {
    str(WORKSPACE_DIR / "MEMORY.md"),
    str(WORKSPACE_DIR / "USER.md"),
}
_AUTO_APPROVE_WRITE_PREFIXES = [
    str(WORKSPACE_DIR) + "/",                          # all runtime workspace files
    str(Path(PROJECT_ROOT) / "workspace" / "default") + "/",  # repo workspace template
]
_BLOCKED_WRITE_PATTERNS = [
    "/.git/",
    "/.env",
    "/credentials",
    "/.ssh/",
    "/node_modules/",
    "/__pycache__/",
]

# ── Tool definitions (Ollama-compatible JSON schemas) ──────────────────

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read any file on the system by absolute path. Use for code, config, logs, workspace files — anything.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute file path to read",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates file if it doesn't exist. Workspace files (MEMORY.md, USER.md) are auto-approved; other files require user approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute file path to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Make a surgical find-and-replace edit in a file. Workspace files are auto-approved; other files require user approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute file path to edit",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to find (must match exactly)",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search file contents with regex. Returns matching lines with file paths and line numbers. Searches project root by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex search pattern",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in (default: project root)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files by glob pattern. Returns matching file paths with sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g. '*.py', 'test_*.py', '**/*.md')",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: project root)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command. Read-only commands (ls, cat, git status, grep, lscpu, etc) are auto-approved. Mutations (git commit, pip install, mkdir) require user approval. Destructive commands (rm, git reset --hard) require explicit approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the text content of a web page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information. Returns search result summaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ── Permission classification ──────────────────────────────────────────

_READ_ONLY_COMMAND_PREFIXES = [
    "cat ", "head ", "tail ", "less ", "more ",
    "ls", "ll ", "la ", "dir ",
    "find ", "locate ",
    "grep ", "rg ", "ag ", "ack ",
    "wc ", "sort ", "uniq ", "diff ", "comm ",
    "file ", "stat ", "du ", "df ",
    "git status", "git log", "git diff", "git show", "git branch",
    "git remote", "git tag", "git stash list", "git rev-parse",
    "git blame", "git shortlog", "git describe",
    "pwd", "whoami", "hostname", "uname", "id ",
    "lscpu", "lshw", "lsblk", "lspci", "lsusb", "lsmod",
    "free ", "uptime", "nproc", "hostnamectl",
    "nvidia-smi", "sensors",
    "ps ", "top -bn1", "pgrep ", "ss ", "netstat ",
    "ip addr", "ip route", "ifconfig",
    "systemctl status", "journalctl",
    "which ", "whereis ", "type ",
    "python -c ", "python3 -c ",
    "echo ", "date", "cal ",
    "env", "printenv",
    "tree ",
]

_DESTRUCTIVE_PATTERNS = [
    r"\brm\b", r"\brm\s+-rf\b",
    r"git\s+reset\s+--hard", r"git\s+clean",
    r"git\s+push\s+--force", r"git\s+push\s+-f\b",
    r"\bdrop\s+table\b", r"\bdrop\s+database\b",
    r"\btruncate\b",
    r"mkfs\b", r"dd\s+if=",
    r":(){ :\|:& };:",
    r"\bshutdown\b", r"\breboot\b", r"\bpoweroff\b",
]

_BLOCKED_COMMANDS = [
    r"\bcurl\b.*\|\s*bash",
    r"\bwget\b.*\|\s*bash",
    r"\bsudo\s+rm\b",
]


_READ_ONLY_GIT_SUBCOMMANDS = {
    "status", "log", "diff", "show", "branch", "remote", "tag",
    "stash list", "rev-parse", "blame", "shortlog", "describe",
    "ls-files", "ls-tree", "cat-file", "reflog",
}


def classify_command(command: str) -> str:
    """Classify a shell command: 'auto', 'approval', 'destructive', or 'blocked'."""
    normalized = command.strip().lower()

    for pattern in _BLOCKED_COMMANDS:
        if re.search(pattern, normalized):
            return "blocked"

    for pattern in _DESTRUCTIVE_PATTERNS:
        if re.search(pattern, normalized):
            return "destructive"

    for prefix in _READ_ONLY_COMMAND_PREFIXES:
        if normalized.startswith(prefix) or normalized == prefix.strip():
            return "auto"

    # Git with flags before subcommand (e.g. git -C /path log)
    git_match = re.match(r"git\s+(?:-\S+\s+\S+\s+)*(\S+(?:\s+\S+)?)", normalized)
    if git_match:
        subcmd = git_match.group(1)
        if any(subcmd.startswith(s) for s in _READ_ONLY_GIT_SUBCOMMANDS):
            return "auto"

    # Piped commands: check if all segments are read-only
    if "|" in normalized:
        segments = [s.strip() for s in normalized.split("|")]
        if all(
            any(seg.startswith(p) or seg == p.strip() for p in _READ_ONLY_COMMAND_PREFIXES)
            for seg in segments
            if seg
        ):
            return "auto"

    return "approval"


def classify_file_write(path: str) -> str:
    """Classify a file write: 'auto', 'approval', or 'blocked'."""
    resolved = str(Path(path).resolve())

    for blocked in _BLOCKED_WRITE_PATTERNS:
        if blocked in resolved:
            return "blocked"

    if resolved in _AUTO_APPROVE_WRITE_PATHS:
        return "auto"

    for prefix in _AUTO_APPROVE_WRITE_PREFIXES:
        if resolved.startswith(prefix):
            return "auto"

    return "approval"


# ── Tool execution handlers ────────────────────────────────────────────

def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool call and return the result."""
    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}", "status": "error"}

    event_bus.publish("tool.invoked", {
        "tool": name,
        "arguments": {k: str(v)[:100] for k, v in arguments.items()},
    })

    try:
        result = handler(arguments)
    except Exception as exc:
        result = {"error": str(exc), "status": "error"}

    event_bus.publish("tool.completed", {
        "tool": name,
        "status": result.get("status", "ok"),
    })

    return result


def execute_tool_force(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute tool bypassing approval checks. Only call for user-approved requests."""
    handler = _FORCE_HANDLERS.get(name) or _TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}", "status": "error"}

    event_bus.publish("tool.force_invoked", {
        "tool": name,
        "arguments": {k: str(v)[:100] for k, v in arguments.items()},
    })

    try:
        result = handler(arguments)
    except Exception as exc:
        result = {"error": str(exc), "status": "error"}

    event_bus.publish("tool.completed", {
        "tool": name,
        "status": result.get("status", "ok"),
    })
    return result


def _exec_read_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}

    target = Path(path).expanduser().resolve()
    if not target.exists():
        return {"error": f"File not found: {path}", "status": "error"}
    if not target.is_file():
        return {"error": f"Not a file: {path}", "status": "error"}

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        return {"error": f"Permission denied: {path}", "status": "error"}

    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS - 1] + "…"

    return {"text": text, "path": str(target), "size": len(text), "status": "ok"}


def _exec_write_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    if not path:
        return {"error": "path is required", "status": "error"}

    target = Path(path).expanduser().resolve()
    classification = classify_file_write(str(target))

    if classification == "blocked":
        return {"error": f"Write blocked for safety: {path}", "status": "blocked"}

    if classification == "approval":
        return {
            "status": "approval_needed",
            "message": f"Writing to {path} requires your approval. Please confirm in chat.",
            "path": str(target),
            "content_preview": content[:200] + ("…" if len(content) > 200 else ""),
        }

    # Auto-approved (workspace files)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"status": "ok", "path": str(target), "bytes_written": len(content.encode("utf-8"))}


def _exec_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    if not path or not old_text:
        return {"error": "path and old_text are required", "status": "error"}

    target = Path(path).expanduser().resolve()
    classification = classify_file_write(str(target))

    if classification == "blocked":
        return {"error": f"Edit blocked for safety: {path}", "status": "blocked"}

    if classification == "approval":
        return {
            "status": "approval_needed",
            "message": f"Editing {path} requires your approval. Please confirm in chat.",
            "path": str(target),
            "old_text_preview": old_text[:100],
            "new_text_preview": new_text[:100],
        }

    if not target.exists():
        return {"error": f"File not found: {path}", "status": "error"}

    content = target.read_text(encoding="utf-8", errors="replace")
    if old_text not in content:
        return {"error": "old_text not found in file", "status": "error"}

    count = content.count(old_text)
    if count > 1:
        return {"error": f"old_text matches {count} locations — be more specific", "status": "error"}

    new_content = content.replace(old_text, new_text, 1)
    target.write_text(new_content, encoding="utf-8")
    return {"status": "ok", "path": str(target), "replacements": 1}


def _exec_search(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    search_path = str(args.get("path") or "").strip() or str(PROJECT_ROOT)
    if not pattern:
        return {"error": "pattern is required", "status": "error"}

    argv = [
        "grep", "-rn", "--color=never",
        "--include=*.py", "--include=*.md", "--include=*.json",
        "--include=*.yaml", "--include=*.yml", "--include=*.toml",
        "--include=*.ts", "--include=*.tsx", "--include=*.js",
        "--include=*.css", "--include=*.html",
        "--exclude-dir=.git", "--exclude-dir=node_modules",
        "--exclude-dir=__pycache__", "--exclude-dir=.claude",
        "--exclude-dir=dist", "--exclude-dir=build",
        "-m", str(MAX_SEARCH_RESULTS),
        pattern,
        ".",
    ]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
            cwd=search_path,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out", "status": "error"}

    lines = result.stdout.strip().splitlines()[:MAX_SEARCH_RESULTS]
    bounded = [
        line if len(line) <= MAX_SEARCH_LINE_CHARS else line[:MAX_SEARCH_LINE_CHARS - 1] + "…"
        for line in lines
    ]
    text = "\n".join(bounded) if bounded else "[no matches]"
    return {"text": text, "match_count": len(bounded), "status": "ok"}


def _exec_find_files(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    search_path = str(args.get("path") or "").strip() or str(PROJECT_ROOT)
    if not pattern:
        return {"error": "pattern is required", "status": "error"}

    argv = [
        "find", search_path,
        "-type", "f",
        "-name", pattern,
        "-not", "-path", "*/.git/*",
        "-not", "-path", "*/node_modules/*",
        "-not", "-path", "*/__pycache__/*",
        "-not", "-path", "*/.claude/*",
    ]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Find timed out", "status": "error"}

    paths = result.stdout.strip().splitlines()[:MAX_FIND_RESULTS]
    entries: list[str] = []
    for fp in paths:
        try:
            size = Path(fp).stat().st_size
            entries.append(f"{fp}  ({size} bytes)")
        except OSError:
            entries.append(fp)

    text = "\n".join(entries) if entries else "[no files found]"
    return {"text": text, "file_count": len(entries), "status": "ok"}


def _exec_bash(args: dict[str, Any]) -> dict[str, Any]:
    command = str(args.get("command") or "").strip()
    if not command:
        return {"error": "command is required", "status": "error"}

    classification = classify_command(command)

    if classification == "blocked":
        return {"error": f"Command blocked for safety: {command}", "status": "blocked"}

    if classification == "destructive":
        return {
            "status": "approval_needed",
            "message": f"Destructive command requires explicit approval: {command}",
            "command": command,
            "classification": "destructive",
        }

    if classification == "approval":
        return {
            "status": "approval_needed",
            "message": f"This command may modify the system. Please confirm: {command}",
            "command": command,
            "classification": "mutation",
        }

    # Auto-approved (read-only)
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {MAX_BASH_SECONDS}s", "status": "error"}

    output = result.stdout.strip()
    if result.stderr.strip():
        output += "\n[stderr] " + result.stderr.strip()

    if len(output) > MAX_BASH_OUTPUT_CHARS:
        output = output[:MAX_BASH_OUTPUT_CHARS - 1] + "…"

    return {
        "text": output or "[no output]",
        "exit_code": result.returncode,
        "status": "ok",
    }


def _exec_web_fetch(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    req = urllib_request.Request(
        url,
        headers={"User-Agent": "Jarvis/2.0 (personal assistant)"},
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Fetch failed: {exc}", "status": "error"}

    # Strip HTML tags for a rough text extraction
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > MAX_WEB_FETCH_CHARS:
        text = text[:MAX_WEB_FETCH_CHARS - 1] + "…"

    return {"text": text, "url": url, "chars": len(text), "status": "ok"}


def _exec_web_search(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}

    # Web search requires an external API (Google, Bing, SearXNG, etc).
    # For now, fall back to a DuckDuckGo HTML fetch.
    search_url = f"https://html.duckduckgo.com/html/?q={urllib_request.quote(query)}"
    req = urllib_request.Request(
        search_url,
        headers={"User-Agent": "Jarvis/2.0 (personal assistant)"},
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Search failed: {exc}", "status": "error"}

    # Extract result snippets from DuckDuckGo HTML
    results: list[str] = []
    for match in re.finditer(
        r'class="result__snippet"[^>]*>(.*?)</[^>]+>', raw, re.DOTALL
    ):
        snippet = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        snippet = html.unescape(snippet)
        if snippet:
            results.append(snippet)
        if len(results) >= 8:
            break

    text = "\n\n".join(f"{i+1}. {r}" for i, r in enumerate(results)) if results else "[no results]"
    return {"text": text, "result_count": len(results), "query": query, "status": "ok"}


# ── Handler registry ───────────────────────────────────────────────────

_TOOL_HANDLERS: dict[str, Any] = {
    "read_file": _exec_read_file,
    "write_file": _exec_write_file,
    "edit_file": _exec_edit_file,
    "search": _exec_search,
    "find_files": _exec_find_files,
    "bash": _exec_bash,
    "web_fetch": _exec_web_fetch,
    "web_search": _exec_web_search,
}


def _force_write_file(args: dict[str, Any]) -> dict[str, Any]:
    """Write file bypassing approval (blocked paths still blocked)."""
    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    if not path:
        return {"error": "path is required", "status": "error"}
    target = Path(path).expanduser().resolve()
    if classify_file_write(str(target)) == "blocked":
        return {"error": f"Write blocked for safety: {path}", "status": "blocked"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"status": "ok", "path": str(target), "size": len(content)}


def _force_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    """Edit file bypassing approval (blocked paths still blocked)."""
    path = str(args.get("path") or "").strip()
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    if not path or not old_text:
        return {"error": "path and old_text are required", "status": "error"}
    target = Path(path).expanduser().resolve()
    if classify_file_write(str(target)) == "blocked":
        return {"error": f"Edit blocked for safety: {path}", "status": "blocked"}
    if not target.exists():
        return {"error": f"File not found: {path}", "status": "error"}
    content = target.read_text(encoding="utf-8", errors="replace")
    if old_text not in content:
        return {"error": "old_text not found in file", "status": "error"}
    new_content = content.replace(old_text, new_text, 1)
    target.write_text(new_content, encoding="utf-8")
    return {"status": "ok", "path": str(target), "replacements": 1}


def _force_bash(args: dict[str, Any]) -> dict[str, Any]:
    """Run bash command bypassing approval (blocked still blocked)."""
    command = str(args.get("command") or "").strip()
    if not command:
        return {"error": "command is required", "status": "error"}
    if classify_command(command) == "blocked":
        return {"error": f"Command blocked: {command}", "status": "blocked"}
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {MAX_BASH_SECONDS}s", "status": "error"}
    output = result.stdout.strip()
    if result.stderr.strip():
        output = (output + "\n" + result.stderr.strip()).strip()
    if len(output) > MAX_BASH_OUTPUT_CHARS:
        output = output[:MAX_BASH_OUTPUT_CHARS - 1] + "…"
    return {"text": output or "[no output]", "exit_code": result.returncode, "status": "ok"}


_FORCE_HANDLERS: dict[str, Any] = {
    "write_file": _force_write_file,
    "edit_file": _force_edit_file,
    "bash": _force_bash,
}


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return Ollama-compatible tool definitions."""
    return TOOL_DEFINITIONS


def format_tool_result_for_model(name: str, result: dict[str, Any]) -> str:
    """Format a tool result as text for the model's context."""
    status = result.get("status", "unknown")

    if status == "error":
        return f"[Tool {name} error: {result.get('error', 'unknown error')}]"

    if status == "blocked":
        return f"[Tool {name} blocked: {result.get('error', 'blocked for safety')}]"

    if status == "approval_needed":
        return f"[Tool {name}: {result.get('message', 'requires user approval')}]"

    text = result.get("text", "")
    if text:
        return text

    # Human-friendly summaries for common tool results
    path = result.get("path", "")
    if name == "write_file" and path:
        size = result.get("size", "")
        return f"Wrote {path}" + (f" ({size} bytes)" if size else "")
    if name == "edit_file" and path:
        n = result.get("replacements", 0)
        return f"Edited {path} ({n} replacement{'s' if n != 1 else ''})"

    return json.dumps(
        {k: v for k, v in result.items() if k != "status"},
        ensure_ascii=False,
        indent=2,
    )
