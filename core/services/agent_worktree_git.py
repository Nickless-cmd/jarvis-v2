"""Git-operationer for agent-worktrees (agent-contract-v1 C5a, spec 8.1).

Rene subprocess-hjaelpere uden DB. To principper:

* Intet i et worktree stoles paa. Agenten skriver i det; dets ``.git``-FIL kan pege hvorhen som helst.
  Serveren koerer derfor ALTID git med eksplicit ``GIT_DIR`` (hovedrepoets ``worktrees/<navn>``) og
  ``GIT_WORK_TREE``, aldrig ved at lade git opdage repoet fra worktree'et.
* Ingen hooks, ingen fsmonitor, ingen system-/brugerconfig, ingen prompts.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/\-]{0,200}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,127}$")
GIT_TIMEOUT_S = 120


class GitError(RuntimeError):
    def __init__(self, detail: str, *, returncode: int = 1) -> None:
        super().__init__(detail)
        self.detail, self.returncode = detail, returncode


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/nonexistent",
           "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0"}
    env.update(extra or {})
    return env


def run_git(args: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None,
            timeout: int = GIT_TIMEOUT_S, check: bool = True, input_bytes: bytes | None = None
            ) -> subprocess.CompletedProcess:
    cmd = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
           "-c", "protocol.ext.allow=never", "-c", "safe.directory=*", *args]
    proc = subprocess.run(cmd, cwd=cwd, env=_env(env), capture_output=True, timeout=timeout,
                          input=input_bytes)
    if check and proc.returncode != 0:
        raise GitError((proc.stderr or proc.stdout).decode("utf-8", "replace")[:500],
                       returncode=proc.returncode)
    return proc


def safe_ref(ref: str) -> str:
    ref = str(ref or "HEAD")
    if ref != "HEAD" and (not _REF.match(ref) or ".." in ref or ref.endswith(".lock")):
        raise GitError(f"ugyldig ref {ref!r}")
    return ref


def safe_name(name: str, what: str = "navn") -> str:
    if not _NAME.match(str(name or "")) or ".." in str(name):
        raise GitError(f"ugyldigt {what} {name!r}")
    return str(name)


def validate_repo(path: str, allowed_roots: list[str]) -> str:
    """Returner repoets toplevel (realpath) hvis det ligger under en tilladt rod og er et almindeligt
    git-repo; ellers ``GitError``. Et symlink ud af roden er ikke et tilladt repo."""
    real = os.path.realpath(str(path or ""))
    roots = [os.path.realpath(r) for r in allowed_roots]
    if not any(real == r or real.startswith(r + os.sep) for r in roots):
        raise GitError(f"{real} ligger ikke under en tilladt workspace-rod")
    if not os.path.isdir(real):
        raise GitError(f"{real} er ikke en mappe")
    top = run_git(["rev-parse", "--show-toplevel"], cwd=real).stdout.decode().strip()
    if os.path.realpath(top) != real:
        raise GitError("stien er ikke repoets toplevel")
    if run_git(["rev-parse", "--is-bare-repository"], cwd=real).stdout.decode().strip() != "false":
        raise GitError("bare repos er ikke tilladt")
    return real


def resolve_commit(repo: str, ref: str = "HEAD") -> str:
    out = run_git(["rev-parse", "--verify", "--quiet", f"{safe_ref(ref)}^{{commit}}"], cwd=repo)
    return out.stdout.decode().strip()


def read_gitdir(repo: str, path: str) -> str:
    """Hovedrepoets administrationsmappe for et NYOPRETTET worktree, laest fra dets ``.git``-fil
    OMGAAENDE efter oprettelsen (foer agenten har roert noget) og kontrolleret mod hovedrepoet."""
    first = Path(path, ".git").read_text(encoding="utf-8").strip()
    if not first.startswith("gitdir:"):
        raise GitError("worktree'ets .git-fil har uventet form")
    gitdir = os.path.realpath(first.split(":", 1)[1].strip())
    expected = os.path.realpath(os.path.join(repo, ".git", "worktrees")) + os.sep
    if not gitdir.startswith(expected):
        raise GitError("worktree'ets gitdir ligger uden for hovedrepoets worktrees-mappe")
    return gitdir


def add_worktree(repo: str, path: str, branch: str, base_commit: str) -> None:
    safe_name(branch.replace("/", "-"), "branch")
    run_git(["worktree", "add", "-b", branch, path, base_commit], cwd=repo)


def _wt_env(gitdir: str, path: str) -> dict[str, str]:
    return {"GIT_DIR": gitdir, "GIT_WORK_TREE": path}


def stage_all(gitdir: str, path: str) -> None:
    run_git(["add", "-A", "--", "."], cwd=path, env=_wt_env(gitdir, path))


def diff_against(gitdir: str, path: str, base_commit: str) -> bytes:
    """Hele agentens aendring ift. basen - ogsaa nye og slettede filer og commits (binaer-sikker)."""
    stage_all(gitdir, path)
    return run_git(["diff", "--cached", "--binary", "--no-ext-diff", base_commit], cwd=path,
                   env=_wt_env(gitdir, path)).stdout


def changed_files(gitdir: str, path: str, base_commit: str) -> list[dict[str, str]]:
    stage_all(gitdir, path)
    out = run_git(["diff", "--cached", "--name-status", "--no-renames", "-z", base_commit], cwd=path,
                  env=_wt_env(gitdir, path)).stdout.decode("utf-8", "replace")
    parts = [p for p in out.split("\0") if p]
    return [{"status": parts[i], "path": parts[i + 1]} for i in range(0, len(parts) - 1, 2)]


def commits_since(gitdir: str, path: str, base_commit: str) -> list[str]:
    out = run_git(["rev-list", f"{base_commit}..HEAD"], cwd=path, env=_wt_env(gitdir, path))
    return out.stdout.decode().split()


def make_bundle(repo: str, branch: str, base_commit: str, dest: str) -> bool:
    """Bundle af agentens commits (``base..branch``). ``False`` naar der ingen commits er."""
    probe = run_git(["rev-list", "--count", f"{base_commit}..{branch}"], cwd=repo).stdout.decode().strip()
    if probe == "0":
        return False
    run_git(["bundle", "create", dest, f"{base_commit}..{branch}"], cwd=repo)
    return True


def remove_worktree(repo: str, path: str, branch: str) -> None:
    """Fjern worktree + branch. Idempotent: et allerede fjernet worktree er ikke en fejl."""
    run_git(["worktree", "remove", "--force", path], cwd=repo, check=False)
    if os.path.lexists(path):
        # Agenten ejer worktree'ets indhold - ogsaa dets ``.git``-fil. Er den roeret, afviser git at fjerne
        # mappen. Kalderne har allerede verificeret at ``path`` er ``<rod>/<agent>/<assignment>``, saa
        # mappen slettes direkte (rmtree foelger ikke symlinks) og git-registreringen ryddes bagefter.
        shutil.rmtree(path, ignore_errors=True)
    run_git(["worktree", "prune"], cwd=repo, check=False)
    if os.path.exists(path):
        raise GitError(f"{path} findes stadig efter remove")
    run_git(["branch", "-D", branch], cwd=repo, check=False)


def tree_size(path: str) -> int:
    """Samlet filstoerrelse (bytes) uden at foelge symlinks ud af traeet."""
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                logger.debug("kunne ikke maale %s", f, exc_info=True)
    return total


def path_is_inside(path: str, root: str) -> bool:
    real, base = os.path.realpath(path), os.path.realpath(root)
    return real != base and real.startswith(base + os.sep)


def ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- integration (F4d): flet til en NY gren uden at roere nogens working tree ------------------------------

_IDENT = {"GIT_AUTHOR_NAME": "Jarvis agent", "GIT_AUTHOR_EMAIL": "agent@jarvis.local",
          "GIT_COMMITTER_NAME": "Jarvis agent", "GIT_COMMITTER_EMAIL": "agent@jarvis.local"}


def current_head(repo: str) -> str:
    return run_git(["rev-parse", "--verify", "HEAD^{commit}"], cwd=repo).stdout.decode().strip()


def ref_exists(repo: str, ref: str) -> bool:
    return run_git(["show-ref", "--verify", "--quiet", ref], cwd=repo, check=False).returncode == 0


def commit_worktree_tree(gitdir: str, path: str, base_commit: str, message: str) -> str:
    """Skriv agentens samlede arbejdstilstand som ÉT commit ovenpaa basen (server-side, med det gemte gitdir)."""
    stage_all(gitdir, path)
    env = {**_wt_env(gitdir, path), **_IDENT}
    tree = run_git(["write-tree"], cwd=path, env=env).stdout.decode().strip()
    return run_git(["commit-tree", tree, "-p", base_commit, "-m", message], cwd=path,
                   env=env).stdout.decode().strip()


def merge_tree(repo: str, ours: str, theirs: str) -> tuple[str | None, list[str]]:
    """``git merge-tree --write-tree``: (tree-oid, []) ved ren fletning, (None, konfliktfiler) ved konflikt.
    Roerer hverken index eller working tree."""
    proc = run_git(["merge-tree", "--write-tree", "--name-only", "--no-messages", ours, theirs], cwd=repo,
                   check=False)
    lines = proc.stdout.decode("utf-8", "replace").splitlines()
    if proc.returncode == 0 and lines:
        return lines[0].strip(), []
    if proc.returncode == 1:
        return None, [ln for ln in lines[1:] if ln.strip()]
    raise GitError((proc.stderr or proc.stdout).decode("utf-8", "replace")[:300], returncode=proc.returncode)


def commit_tree(repo: str, tree: str, parents: list[str], message: str) -> str:
    args = ["commit-tree", tree]
    for p in parents:
        args += ["-p", p]
    return run_git([*args, "-m", message], cwd=repo, env=_IDENT).stdout.decode().strip()


def create_ref(repo: str, ref: str, oid: str) -> None:
    """Opret ``ref`` -> ``oid`` KUN hvis den ikke findes (old-value = nul): en eksisterende gren overskrives aldrig."""
    run_git(["update-ref", ref, oid, "0" * 40], cwd=repo)


def set_ref(repo: str, ref: str, new: str, old: str) -> None:
    run_git(["update-ref", ref, new, old], cwd=repo)
