"""Agentens EGEN git-administrationsmappe (agent-contract-v1 leverance C, hul 1; spec 8.1).

Problemet: en kodeagent skal kunne ``git add``/``git commit`` i sit worktree, men sandboxen maa ikke se
hovedrepoets ``.git`` (refs, hooks, config, andre worktrees). Loesningen er at give agenten en PRIVAT
gitdir ved siden af worktree'et (``<worktree>.gitdir``) og lade serveren IMPORTERE dens commits bagefter:

* ``objects/``  skrivbar (agentens nye objekter), med ``alternates`` til hovedrepoets objekter som
  SKRIVEBESKYTTET mount - agenten kan laese basen, aldrig skrive i hovedrepoet.
* ``refs/``     skrivbar (agentens egen gren).
* ``idx/``      skrivbar (agentens index; git omdoeber ``index.lock`` -> ``index``, det kan ikke ske paa en
                  bind-mountet fil).
* ``config``, ``HEAD``, ``packed-refs``  skrivebeskyttede mounts: ingen ``core.hooksPath``/filter/alias-
                  aendring, intet skift af gren, ingen ``pack-refs`` der pruner loese refs.
* alt andet i ``/gitdir`` er en privat tmpfs der forsvinder med sandboxen - saa agenten kan ikke plante
  ``commondir``, ``info/attributes`` eller lignende paa vaerten.

Serveren stoler IKKE paa noget i mappen ud over objekter og gren-ref'en: dens egen config er
skrivebeskyttet for agenten, og commits hentes ind i hovedrepoet med ``git fetch`` (fsck paa) til et
separat ref-navnerum ``refs/agent-work/<assignment>`` - aldrig til agentens ``refs/heads/agent/..``
(det bruges af integrationen) og aldrig til andre refs.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from core.services import agent_worktree_git as g

logger = logging.getLogger(__name__)

SANDBOX_GITDIR = "/gitdir"
SANDBOX_IDXDIR = "/gitidx"
WORK_REF_PREFIX = "refs/agent-work/"
_IDENT_NAME, _IDENT_EMAIL = "Jarvis agent", "agent@jarvis.local"

_CONFIG = f"""[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = false
\tlogallrefupdates = false
\thooksPath = /dev/null
\tfsmonitor = false
[gc]
\tauto = 0
[maintenance]
\tauto = false
[user]
\tname = {_IDENT_NAME}
\temail = {_IDENT_EMAIL}
[commit]
\tgpgsign = false
"""


def gitdir_path(worktree_path: str) -> str:
    """Den private gitdir ligger ved siden af worktree'et (altsaa UDEN for det der mountes som /work)."""
    return str(worktree_path).rstrip("/") + ".gitdir"


def work_ref(assignment_id: str) -> str:
    return WORK_REF_PREFIX + g.safe_name(assignment_id, "assignment_id")


def _objects_chain(repo: str) -> list[str]:
    """Hovedrepoets objektmappe + dens egne alternates (kaeden), som absolutte stier der findes."""
    common = g.run_git(["rev-parse", "--git-common-dir"], cwd=repo).stdout.decode().strip()
    objects = os.path.realpath(os.path.join(repo, common, "objects"))
    chain, todo = [], [objects]
    while todo and len(chain) < 8:
        cur = todo.pop(0)
        if cur in chain or not os.path.isdir(cur):
            continue
        chain.append(cur)
        alt = Path(cur, "info", "alternates")
        if alt.is_file():
            for line in alt.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    todo.append(os.path.realpath(os.path.join(cur, line)))
    return chain


def create(repo: str, path: str, branch: str, base_commit: str) -> str:
    """Opret den private gitdir for et NYT worktree (foer agenten har roert noget). Returnerer stien."""
    gd = gitdir_path(path)
    chain = _objects_chain(repo)
    if not chain:
        raise g.GitError("hovedrepoets objektmappe blev ikke fundet")
    for sub in ("objects/info", "objects/pack", "refs/heads", "refs/tags", "idx"):
        os.makedirs(os.path.join(gd, sub), exist_ok=True)
    Path(gd, "HEAD").write_text(f"ref: refs/heads/{branch}\n", encoding="utf-8")
    Path(gd, "config").write_text(_CONFIG, encoding="utf-8")
    Path(gd, "packed-refs").write_text("", encoding="utf-8")
    Path(gd, "objects", "info", "alternates").write_text("\n".join(chain) + "\n", encoding="utf-8")
    env = {"GIT_DIR": gd, "GIT_WORK_TREE": path, "GIT_INDEX_FILE": os.path.join(gd, "idx", "index")}
    g.run_git(["update-ref", f"refs/heads/{branch}", base_commit], cwd=path, env=env)
    g.run_git(["read-tree", base_commit], cwd=path, env=env)
    return gd


def sandbox_mounts(repo: str, path: str) -> list[tuple[str, str, str]] | None:
    """Mounts til ``agent_sandbox`` der giver agenten git i sin egen gitdir. ``None`` hvis worktree'et
    ikke har en (aeldre worktree) - saa har agenten ingen git, men shell og filskrivning virker."""
    gd = gitdir_path(path)
    if not os.path.isdir(gd):
        return None
    mounts: list[tuple[str, str, str]] = [("tmpfs", "", SANDBOX_GITDIR)]
    for name in ("HEAD", "config", "packed-refs"):
        mounts.append(("ro", os.path.join(gd, name), f"{SANDBOX_GITDIR}/{name}"))
    mounts.append(("rw", os.path.join(gd, "objects"), f"{SANDBOX_GITDIR}/objects"))
    mounts.append(("rw", os.path.join(gd, "refs"), f"{SANDBOX_GITDIR}/refs"))
    mounts.append(("rw", os.path.join(gd, "idx"), SANDBOX_IDXDIR))
    for objdir in _objects_chain(repo):
        mounts.append(("ro", objdir, objdir))
    return mounts


def sandbox_env() -> dict[str, str]:
    return {"GIT_DIR": SANDBOX_GITDIR, "GIT_WORK_TREE": "/work", "GIT_INDEX_FILE": f"{SANDBOX_IDXDIR}/index",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "safe.directory", "GIT_CONFIG_VALUE_0": "*",
            "GIT_AUTHOR_NAME": _IDENT_NAME, "GIT_AUTHOR_EMAIL": _IDENT_EMAIL,
            "GIT_COMMITTER_NAME": _IDENT_NAME, "GIT_COMMITTER_EMAIL": _IDENT_EMAIL}


def import_agent_work(repo: str, path: str, branch: str, assignment_id: str) -> str | None:
    """Hent agentens commits ind i hovedrepoet som ``refs/agent-work/<assignment>`` og returner tippen
    (``None`` hvis agenten ingen gren har eller der ingen privat gitdir er). ``fetch`` med fsck paa:
    objekterne verificeres, og kun DEN ene ref kopieres. Kaster ``GitError`` ved en uventet fejl."""
    gd = gitdir_path(path)
    if not os.path.isdir(gd):
        return None
    dest = work_ref(assignment_id)
    proc = g.run_git(["-c", "fetch.fsckObjects=true", "-c", "transfer.fsckObjects=true", "fetch", "--quiet",
                      "--no-tags", "--no-write-fetch-head", "--no-recurse-submodules", gd,
                      f"+refs/heads/{branch}:{dest}"], cwd=repo, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).decode("utf-8", "replace")
        if "couldn't find remote ref" in err:
            g.run_git(["update-ref", "-d", dest], cwd=repo, check=False)
            return None
        raise g.GitError(err[:300], returncode=proc.returncode)
    return g.run_git(["rev-parse", "--verify", f"{dest}^{{commit}}"], cwd=repo).stdout.decode().strip()


def commits_since(repo: str, base_commit: str, assignment_id: str) -> list[str]:
    """Agentens importerede commits ``base..refs/agent-work/<id>`` (tom hvis intet er importeret)."""
    dest = work_ref(assignment_id)
    if not g.ref_exists(repo, dest):
        return []
    return g.run_git(["rev-list", f"{base_commit}..{dest}"], cwd=repo).stdout.decode().split()


def remove(repo: str, path: str) -> None:
    """Fjern den private gitdir og det importerede ref. Idempotent."""
    gd = gitdir_path(path)
    root = os.path.dirname(os.path.dirname(os.path.realpath(path)))
    if g.path_is_inside(gd, root) and os.path.lexists(gd):
        shutil.rmtree(gd, ignore_errors=True)
    g.run_git(["update-ref", "-d", work_ref(os.path.basename(path.rstrip("/")))], cwd=repo, check=False)
