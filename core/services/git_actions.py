"""Rolle-aware git-eksekvering for code mode.

container/'repo'  → server-side subprocess (KUN owner; gate i route-laget).
workstation       → git via operator_bash på brugerens egen bro.

PR-oprettelse: GitHub-OAuth-connector (API) primært, gh CLI som fallback.
"""
from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

from core.services.attributed_git_commit import (
    AttributedCommitResult,
    commit_with_attribution,
)
from core.services.commit_attribution import CommitAttribution, new_manual_run_id


# ── Container (server-repo) ────────────────────────────────────────────────

def _git_container(repo: str, *a: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, timeout=timeout)


def _human_attribution() -> CommitAttribution:
    return CommitAttribution(
        actor="bjorn",
        actor_type="human",
        run_id=new_manual_run_id(),
        session_id="none",
        origin="interactive",
        approved_by="bjorn",
    )


def _commit_container(repo: str, message: str) -> AttributedCommitResult:
    return commit_with_attribution(
        repo=Path(repo),
        message=message,
        attribution=_human_attribution(),
    )


def commit_all_container(repo: str, message: str) -> dict:
    msg = (message or "").strip() or "WIP: ændringer fra code mode"
    add = _git_container(repo, "add", "-A")
    if add.returncode != 0:
        return {"status": "error", "detail": f"git add: {add.stderr[:200]}"}
    cm = _commit_container(repo, msg)
    if cm.returncode != 0:
        out = (cm.stdout or "") + (cm.stderr or "")
        if "nothing to commit" in out or "working tree clean" in out:
            return {"status": "nochange", "message": msg}
        return {"status": "error", "detail": out[:200]}
    sha = (cm.sha or "")[:12]
    branch = _git_container(repo, "branch", "--show-current").stdout.strip()
    return {"status": "ok", "sha": sha, "branch": branch, "message": msg}


def _agent_attribution() -> CommitAttribution:
    """Jarvis' egen attribution: actor=jarvis, origin=interactive.

    Bevidst adskilt fra `_human_attribution`. Actor-feltet afgør hvem
    commit'en tilskrives, og et agent-commit må ikke stå som Bjørns.
    """
    return CommitAttribution(
        actor="jarvis",
        actor_type="agent",
        run_id=new_manual_run_id(),
        session_id="none",
        origin="interactive",
        approved_by="bjorn",
    )


#: Hvor meget af en fejlbesked der vises. Halen, ikke hovedet — se `_uddrag`.
_FEJL_UDDRAG = 1200


def _uddrag(blob: str, graense: int = _FEJL_UDDRAG) -> str:
    """Behold HALEN af en fejlbesked: aarsagen staar sidst, ikke foerst.

    MAALT 10/11-2026: ``blob[:400]`` paa en pre-commit-kaede der printer 30
    «Passed»-linjer og fejler paa den sidste gav agenten de foerste seks linjer
    og skar aarsagen vaek. Agenten fik et «error» uden grund og kunne ikke
    afgoere om den skulle proeve igen — den eneste vej til svaret var at koere
    git gennem bash og se hele outputtet.

    Reproduceret i et testrepo: 30 «Passed»-linjer + én fejl gav
    ``len(detail) == 400`` der sluttede midt i linje 6, og fejl-strengen var
    ikke til stede i det agenten saa.
    """
    tekst = (blob or "").strip()
    if len(tekst) <= graense:
        return tekst
    udeladt = len(tekst) - graense
    return f"[{udeladt} tegn udeladt — viser halen] …\n" + tekst[-graense:]


def commit_paths_as_jarvis(
    repo: str,
    message: str,
    paths: tuple[str, ...] = (),
) -> dict:
    """Commit uden shell — argv hele vejen, beskeden gennem en temp-fil.

    Derfor findes denne funktion: ``bash "git commit -m '<besked>'"`` sender
    beskeden gennem en shell FØR git ser den. Backticks bliver
    kommando-substitution og ``$variabel`` bliver ekspanderet, så det der
    lander i repoet er skåret — permanent, fordi `main` ikke kan amenderes.

    Målt 30/10-2026: ordet ``running`` forsvandt ud af en commit-besked,
    med reglen om præcis dette stående i prompten den tur.

    Her er beskeden et JSON-argument. Der er ingen shell imellem.
    """
    root = str(repo or "").strip()
    if not root:
        return {"status": "error", "detail": "repo mangler"}
    if not str(message or "").strip():
        return {"status": "error", "detail": "message mangler"}

    selected = tuple(str(p) for p in paths if str(p))
    add_cmd = ["git", "-C", root, "add"]
    if selected:
        add_cmd.extend(["--", *selected])
    else:
        add_cmd.append("-A")
    add = subprocess.run(add_cmd, capture_output=True, text=True, timeout=60)
    if add.returncode != 0:
        return {"status": "error", "detail": f"git add: {(add.stderr or '').strip()[:200]}"}

    head_before = _git_container(root, "rev-parse", "HEAD").stdout.strip()
    result = commit_with_attribution(
        repo=Path(root),
        message=message,
        attribution=_agent_attribution(),
        paths=selected,
    )
    if result.returncode != 0:
        blob = ((result.stdout or "") + (result.stderr or "")).strip()
        if "nothing to commit" in blob or "working tree clean" in blob:
            return {"status": "nochange", "detail": _uddrag(blob, 200)}
        # SPØRG REPOET, IKKE EXIT-KODEN — ogsaa her, hvor
        # `commit_with_attribution` allerede har spurgt én gang. Kalderens eget
        # svar gør at et fejl-resultat ALDRIG kan mangle svaret paa «landede
        # den?»: et «error» uden den oplysning efterlader agenten uden grund
        # til at tro andet end «prøv igen», og det giver en dublet-commit.
        head_after = _git_container(root, "rev-parse", "HEAD").stdout.strip()
        if head_after and head_after != head_before:
            return {
                "status": "ok",
                "sha": head_after[:12],
                "full_sha": head_after,
                "branch": _git_container(root, "branch", "--show-current").stdout.strip(),
                "message": message,
                "note": (
                    f"HEAD flyttede sig til {head_after[:12]} selv om git meldte "
                    f"exit={result.returncode}. Der ER committet — kør IKKE igen."
                ),
            }
        return {
            "status": "error",
            "detail": _uddrag(blob),
            "head_before": head_before[:12],
            "head_after": head_after[:12],
            "head_moved": False,
        }

    sha = (result.sha or "").strip()
    branch = subprocess.run(
        ["git", "-C", root, "branch", "--show-current"],
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    svar = {
        "status": "ok",
        "sha": sha[:12],
        "full_sha": sha,
        "branch": branch,
        "message": message,
    }
    # Naar `commit_with_attribution` selv reddede en commit som git meldte fejl
    # paa, staar begrundelsen i `result.note`. Uden den ser agenten kun
    # «Committed» og ved ikke at git protesterede undervejs.
    if result.note:
        svar["note"] = result.note
    return svar


# ── Workstation (brugerens egen bro) ───────────────────────────────────────

def _operator_exec(name: str, args: dict) -> dict:
    from core.tools.simple_tools import execute_tool
    return execute_tool(name, args) or {}


def _ws_git(root: str, uid: str, gitargs: str, timeout: int = 60) -> tuple[int, str, str]:
    """Kør `git -C <root> <gitargs>` på brugerens bro. Returnér (rc, stdout, stderr)."""
    cmd = f"git -C {root!r} {gitargs}"
    res = _operator_exec("operator_bash", {"command": cmd, "_user_id": uid, "timeout_s": timeout})
    if res.get("status") != "ok":
        return (1, "", res.get("error") or "bridge_not_connected")
    r = res.get("result") or {}
    return (int(r.get("exit_code") or 0), str(r.get("stdout") or ""), str(r.get("stderr") or ""))


def _ws_attributed_commit(
    root: str,
    uid: str,
    message: str,
    *,
    timeout: int = 120,
) -> tuple[int, str, str]:
    command = shlex.join([
        "python3",
        str(Path(root) / "scripts" / "commit_with_attribution.py"),
        "--repo", root,
        "--message", message,
        "--actor", "bjorn",
        "--origin", "interactive",
        "--approved-by", "bjorn",
    ])
    res = _operator_exec(
        "operator_bash",
        {"command": command, "_user_id": uid, "timeout_s": timeout},
    )
    if res.get("status") != "ok":
        return (1, "", str(res.get("error") or "bridge_not_connected"))
    result = res.get("result") or {}
    return (
        int(result.get("exit_code") or 0),
        str(result.get("stdout") or ""),
        str(result.get("stderr") or ""),
    )


def commit_all_workstation(root: str, uid: str, message: str) -> dict:
    msg = (message or "").strip() or "WIP: ændringer fra code mode"
    rc, _, err = _ws_git(root, uid, "add -A")
    if rc != 0:
        return {"status": "error", "detail": f"git add: {err[:200]}"}
    rc, out, err = _ws_attributed_commit(root, uid, msg)
    if rc != 0:
        blob = out + err
        if "nothing to commit" in blob or "working tree clean" in blob:
            return {"status": "nochange", "message": msg}
        return {"status": "error", "detail": blob[:200]}
    sha = _ws_git(root, uid, "rev-parse --short HEAD")[1].strip()
    branch = _ws_git(root, uid, "branch --show-current")[1].strip()
    return {"status": "ok", "sha": sha, "branch": branch, "message": msg}


# ── Dispatch + remote-parsing ──────────────────────────────────────────────

def commit_all(target: dict, container_repo: str, uid: str, message: str) -> dict:
    kind = (target or {}).get("kind")
    if kind == "container":
        return commit_all_container(container_repo, message)
    if kind == "workstation":
        root = str((target or {}).get("root") or "")
        if not root:
            return {"status": "no_repo"}
        return commit_all_workstation(root, uid, message)
    return {"status": "error", "detail": "ukendt target"}


def parse_owner_repo(remote_url: str) -> str:
    u = (remote_url or "").strip()
    if not u:
        return ""
    u = re.sub(r"\.git$", "", u)
    m = re.search(r"github\.com[:/]([^/]+/[^/]+)$", u)
    return m.group(1) if m else ""


# ── PR-orkestrering (commit → branch → push → PR: API primær, gh fallback) ──

def _ws_git_raw(root: str, uid: str, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    """Kør vilkårlig kommando i `root` på brugerens bro (til gh)."""
    full = f"cd {root!r} && {cmd}"
    res = _operator_exec("operator_bash", {"command": full, "_user_id": uid, "timeout_s": timeout})
    if res.get("status") != "ok":
        return (1, "", res.get("error") or "bridge_not_connected")
    r = res.get("result") or {}
    return (int(r.get("exit_code") or 0), str(r.get("stdout") or ""), str(r.get("stderr") or ""))


def create_pr(target: dict, container_repo: str, uid: str, title: str, body: str) -> dict:
    """Commit → branch hvis på default → push → PR (API, ellers gh-fallback)."""
    kind = (target or {}).get("kind")
    ws = kind == "workstation"
    root = str((target or {}).get("root") or "") if ws else container_repo
    if not root:
        return {"status": "no_repo"}

    def g(args: str):
        if ws:
            return _ws_git(root, uid, args)
        cp = _git_container(root, *_split_gh(args))
        return (cp.returncode, cp.stdout, cp.stderr)

    rc, out, _ = g("symbolic-ref --quiet refs/remotes/origin/HEAD")
    base = out.strip().rsplit("/", 1)[-1] if rc == 0 and out.strip() else "main"
    branch = g("branch --show-current")[1].strip()
    if not branch or branch == base:
        short = g("rev-parse --short HEAD")[1].strip() or "work"
        branch = f"jarvis/work-{short}"
        if g(f"switch -c {branch}")[0] != 0:
            return {"status": "error", "detail": "kunne ikke oprette branch"}
    g("add -A")
    commit_message = title or "Ændringer fra code mode"
    if ws:
        _ws_attributed_commit(root, uid, commit_message)
    else:
        _commit_container(root, commit_message)
    if g(f"push -u origin {branch}")[0] != 0:
        return {"status": "error", "detail": "git push fejlede (creds?)"}

    from core.services import github_connector
    repo = parse_owner_repo(g("remote get-url origin")[1].strip())
    if repo:
        api = github_connector.create_pr(uid, repo, head=branch, base=base, title=title, body=body)
        if api.get("status") == "ok":
            return {"status": "ok", "url": api.get("url"), "branch": branch, "via": "api"}
    return _create_pr_gh(ws, root, uid, base, branch, title, body)


def _create_pr_gh(ws: bool, root: str, uid: str, base: str, branch: str, title: str, body: str) -> dict:
    args = f"pr create --base {base} --head {branch}"
    args += f" --title {title!r} --body {(body or title)!r}" if (title or "").strip() else " --fill"
    if ws:
        rc, out, err = _ws_git_raw(root, uid, f"gh {args}")
    else:
        cp = subprocess.run(["gh", *_split_gh(args)], cwd=root, capture_output=True, text=True, timeout=120)
        rc, out, err = cp.returncode, cp.stdout, cp.stderr
    if rc != 0:
        return {"status": "error", "detail": (err or out)[:250] or "gh utilgængelig"}
    url = next((w for w in (out or "").split() if w.startswith("http")), "")
    return {"status": "ok", "url": url, "branch": branch, "via": "gh"}


def _split_gh(args: str) -> list[str]:
    import shlex
    return shlex.split(args)
