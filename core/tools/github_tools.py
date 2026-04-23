"""Git introspection tools — operates on the Jarvis v2 repo."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

JARVIS_REPO = Path("/media/projects/jarvis-v2")


def _git(args: list[str], cwd: Path = JARVIS_REPO) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _exec_git_log(args: dict[str, Any]) -> dict[str, Any]:
    n = min(int(args.get("n") or 20), 100)
    oneline = bool(args.get("oneline", True))
    fmt = "%h %as %an %s" if oneline else "%H%n%an <%ae>%n%ai%n%s%n%b%n---"
    code, out, err = _git(["log", f"-{n}", f"--format={fmt}"])
    if code != 0:
        return {"status": "error", "error": err or "git log failed"}
    return {"status": "ok", "log": out, "n": n}


def _exec_git_diff(args: dict[str, Any]) -> dict[str, Any]:
    target = str(args.get("target") or "").strip()
    staged = bool(args.get("staged", False))
    git_args = ["diff"]
    if staged:
        git_args.append("--staged")
    if target:
        git_args.extend(["--", target])
    code, out, err = _git(git_args)
    if code != 0:
        return {"status": "error", "error": err or "git diff failed"}
    return {"status": "ok", "diff": out or "(no changes)"}


def _exec_git_status(args: dict[str, Any]) -> dict[str, Any]:
    code, out, err = _git(["status", "--short"])
    if code != 0:
        return {"status": "error", "error": err or "git status failed"}
    _, branch_out, _ = _git(["branch", "--show-current"])
    return {"status": "ok", "branch": branch_out, "changes": out or "(clean)"}


def _exec_git_branch(args: dict[str, Any]) -> dict[str, Any]:
    all_branches = bool(args.get("all", False))
    git_args = ["branch", "-v"]
    if all_branches:
        git_args.append("-a")
    code, out, err = _git(git_args)
    if code != 0:
        return {"status": "error", "error": err or "git branch failed"}
    return {"status": "ok", "branches": out}


def _exec_git_blame(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    if not path:
        return {"status": "error", "error": "path is required"}
    line_start = args.get("line_start")
    line_end = args.get("line_end")
    git_args = ["blame", "--date=short"]
    if line_start and line_end:
        git_args += [f"-L{line_start},{line_end}"]
    git_args.append(path)
    code, out, err = _git(git_args)
    if code != 0:
        return {"status": "error", "error": err or "git blame failed"}
    return {"status": "ok", "blame": out}


GITHUB_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Show recent git commit history for the Jarvis v2 repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "description": "Number of commits to show (default 20, max 100)."},
                    "oneline": {"type": "boolean", "description": "Compact one-line format (default true)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show unstaged (or staged) changes in the Jarvis v2 repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Optional file path to limit diff to."},
                    "staged": {"type": "boolean", "description": "Show staged changes instead of unstaged (default false)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Show current branch and working tree status for the Jarvis v2 repo.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_branch",
            "description": "List branches in the Jarvis v2 repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "all": {"type": "boolean", "description": "Include remote branches (default false)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_blame",
            "description": "Show who last modified each line of a file in the Jarvis v2 repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to repo root."},
                    "line_start": {"type": "integer", "description": "Start line for range blame."},
                    "line_end": {"type": "integer", "description": "End line for range blame."},
                },
                "required": ["path"],
            },
        },
    },
]
