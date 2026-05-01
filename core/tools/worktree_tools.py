"""Git worktree primitive — let Jarvis experiment in isolation.

Pattern: `dispatch_to_claude_code` already does this for spawned
subagents. These tools give Jarvis HIMSELF a way to spin up a
worktree, work in it (via existing edit_file/bash/etc), then either
merge back or discard. Useful for risky refactors and exploratory
work where he doesn't want to touch main.

Worktrees live under <project_root>/.jarvisx-worktrees/<branch_name>
so they're naturally scoped to the project (and excluded by the
project tree skiplist via the .jarvisx prefix).

After creating a worktree, Jarvis is responsible for:
  1. cd'ing his bash session into it
  2. Doing his edits there (relative paths now point to the worktree)
  3. Merging or discarding when done

The tools don't enforce these — they're primitives.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from core.identity.project_context import current_project_root

logger = logging.getLogger(__name__)

_WORKTREE_DIR = ".jarvisx-worktrees"


def _project_root() -> Path | None:
    root = current_project_root().strip()
    if not root:
        return None
    p = Path(root).expanduser().resolve()
    return p if p.is_dir() else None


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists() or _git(path, ["rev-parse", "--git-dir"]).returncode == 0


def _git(cwd: Path, argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *argv],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )


def _safe_branch_name(name: str) -> str:
    # Allow letters, digits, and a few separators; reject any path-y stuff
    cleaned = "".join(c for c in (name or "").strip() if c.isalnum() or c in "-_./")
    return cleaned[:80]


def _exec_worktree_create(args: dict[str, Any]) -> dict[str, Any]:
    name = _safe_branch_name(str(args.get("branch_name") or ""))
    base = str(args.get("base_branch") or "").strip() or None
    if not name:
        return {"status": "error", "error": "branch_name required (alphanum/-_./, max 80)"}
    root = _project_root()
    if root is None:
        return {"status": "error", "error": "no project anchored"}
    if not _is_git_repo(root):
        return {"status": "error", "error": f"not a git repo: {root}"}

    wt_root = root / _WORKTREE_DIR
    wt_root.mkdir(exist_ok=True)
    wt_path = wt_root / name.replace("/", "_")
    if wt_path.exists():
        return {
            "status": "error",
            "error": f"worktree already exists at {wt_path}. Use worktree_discard first or pick another name.",
        }

    # Build the git worktree add command.
    branch_argv = ["worktree", "add"]
    if base:
        # Create new branch from base
        branch_argv += ["-b", name, str(wt_path), base]
    else:
        # Create new branch from current HEAD
        branch_argv += ["-b", name, str(wt_path)]

    res = _git(root, branch_argv)
    if res.returncode != 0:
        return {
            "status": "error",
            "error": f"git worktree add failed: {res.stderr.strip() or res.stdout.strip()}",
        }
    return {
        "status": "ok",
        "branch": name,
        "path": str(wt_path),
        "base_branch": base or "HEAD",
        "message": (
            f"Worktree ready at {wt_path}. "
            f"`cd {wt_path}` in your bash session to start working there."
        ),
    }


def _exec_worktree_list(_args: dict[str, Any]) -> dict[str, Any]:
    root = _project_root()
    if root is None:
        return {"status": "error", "error": "no project anchored"}
    if not _is_git_repo(root):
        return {"status": "error", "error": "not a git repo"}
    res = _git(root, ["worktree", "list", "--porcelain"])
    if res.returncode != 0:
        return {"status": "error", "error": res.stderr.strip()}
    items: list[dict[str, str]] = []
    cur: dict[str, str] = {}
    for line in res.stdout.splitlines():
        if not line:
            if cur:
                items.append(cur)
                cur = {}
            continue
        if line.startswith("worktree "):
            cur["path"] = line[len("worktree ") :]
        elif line.startswith("branch "):
            cur["branch"] = line[len("branch ") :].replace("refs/heads/", "")
        elif line.startswith("HEAD "):
            cur["head"] = line[len("HEAD ") :]
        elif line == "bare":
            cur["bare"] = "true"
        elif line == "detached":
            cur["detached"] = "true"
    if cur:
        items.append(cur)
    # Mark the JarvisX-managed ones
    wt_root_str = str(root / _WORKTREE_DIR)
    for it in items:
        it["managed_by_jarvisx"] = it.get("path", "").startswith(wt_root_str)
    return {"status": "ok", "count": len(items), "worktrees": items}


def _exec_worktree_merge(args: dict[str, Any]) -> dict[str, Any]:
    name = _safe_branch_name(str(args.get("branch_name") or ""))
    target = str(args.get("target_branch") or "").strip() or None
    no_ff = bool(args.get("no_ff", True))
    if not name:
        return {"status": "error", "error": "branch_name required"}
    root = _project_root()
    if root is None:
        return {"status": "error", "error": "no project anchored"}
    if not _is_git_repo(root):
        return {"status": "error", "error": "not a git repo"}

    # Resolve target — default to current HEAD branch in main repo
    if target is None:
        head_res = _git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
        if head_res.returncode != 0:
            return {"status": "error", "error": f"could not resolve HEAD: {head_res.stderr}"}
        target = head_res.stdout.strip()

    # Switch main repo to target branch (caller may already be there)
    co = _git(root, ["checkout", target])
    if co.returncode != 0:
        return {
            "status": "error",
            "error": f"checkout {target} failed: {co.stderr.strip()}",
        }

    merge_argv = ["merge"]
    if no_ff:
        merge_argv.append("--no-ff")
    merge_argv += [name, "-m", f"Merge JarvisX worktree branch '{name}'"]
    mr = _git(root, merge_argv)
    if mr.returncode != 0:
        return {
            "status": "error",
            "error": f"merge failed: {mr.stderr.strip() or mr.stdout.strip()}",
            "hint": "Resolve conflicts manually in main repo, or worktree_discard to abandon.",
        }
    return {
        "status": "ok",
        "branch": name,
        "target": target,
        "message": f"Merged '{name}' into '{target}'. Worktree is still on disk — call worktree_discard to clean up.",
    }


def _exec_worktree_discard(args: dict[str, Any]) -> dict[str, Any]:
    name = _safe_branch_name(str(args.get("branch_name") or ""))
    delete_branch = bool(args.get("delete_branch", True))
    force = bool(args.get("force", False))
    if not name:
        return {"status": "error", "error": "branch_name required"}
    root = _project_root()
    if root is None:
        return {"status": "error", "error": "no project anchored"}
    wt_path = root / _WORKTREE_DIR / name.replace("/", "_")
    if not wt_path.exists():
        # Maybe it's a branch with no on-disk worktree
        if delete_branch:
            del_res = _git(root, ["branch", "-D" if force else "-d", name])
            if del_res.returncode != 0:
                return {"status": "error", "error": del_res.stderr.strip()}
        return {"status": "ok", "message": f"branch {name} deleted (no worktree on disk)"}

    # Remove the worktree
    rm_argv = ["worktree", "remove", str(wt_path)]
    if force:
        rm_argv.append("--force")
    res = _git(root, rm_argv)
    if res.returncode != 0:
        # Try the harder path — direct rm + git prune
        if force:
            try:
                shutil.rmtree(wt_path)
                _git(root, ["worktree", "prune"])
            except Exception as exc:
                return {"status": "error", "error": f"force-remove failed: {exc}"}
        else:
            return {
                "status": "error",
                "error": f"git worktree remove failed: {res.stderr.strip()}. Pass force=true to force.",
            }

    if delete_branch:
        del_res = _git(root, ["branch", "-D" if force else "-d", name])
        if del_res.returncode != 0:
            return {
                "status": "ok",
                "warning": f"worktree removed, but branch delete failed: {del_res.stderr.strip()}",
            }

    return {"status": "ok", "branch": name, "path": str(wt_path), "deleted": True}


WORKTREE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "worktree_create",
            "description": (
                "Create an isolated git worktree under <project>/.jarvisx-worktrees/ "
                "for risky/exploratory work without touching main. Returns the path; "
                "cd into it from bash to work there. When done: worktree_merge to "
                "merge changes back, or worktree_discard to throw away. Requires "
                "an anchored project that's a git repo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "branch_name": {
                        "type": "string",
                        "description": "New branch name (alphanum/-_./, max 80)",
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "Branch/ref to base on (default current HEAD)",
                    },
                },
                "required": ["branch_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_list",
            "description": (
                "List all worktrees on the current project. Each entry includes "
                "path, branch, HEAD sha, and managed_by_jarvisx flag (true if "
                "under .jarvisx-worktrees/)."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_merge",
            "description": (
                "Merge a worktree branch back into a target (default: current HEAD "
                "in main repo). Uses --no-ff by default for clear merge history. "
                "On conflict, returns error and you must resolve manually. "
                "After successful merge, worktree files remain — call "
                "worktree_discard to clean up."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "branch_name": {"type": "string"},
                    "target_branch": {
                        "type": "string",
                        "description": "Defaults to current HEAD branch in main repo",
                    },
                    "no_ff": {
                        "type": "boolean",
                        "description": "Use --no-ff (default true)",
                    },
                },
                "required": ["branch_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_discard",
            "description": (
                "Remove a worktree directory and (by default) delete its branch. "
                "Refuses if branch has unmerged changes; pass force=true to "
                "override (uses git branch -D)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "branch_name": {"type": "string"},
                    "delete_branch": {
                        "type": "boolean",
                        "description": "Also delete the branch (default true)",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force-remove worktree + force-delete branch (default false)",
                    },
                },
                "required": ["branch_name"],
            },
        },
    },
]


WORKTREE_TOOL_HANDLERS: dict[str, Any] = {
    "worktree_create": _exec_worktree_create,
    "worktree_list": _exec_worktree_list,
    "worktree_merge": _exec_worktree_merge,
    "worktree_discard": _exec_worktree_discard,
}
