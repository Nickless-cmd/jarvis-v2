"""Git-checkpoint pr. redigeringsrunde — en dårlig runde kan rulles tilbage samlet.

Porteret fra jarvis-code 2026-09-06.

Runtime havde `agentic_checkpoints`, men det er RUN-tilstand (hvilke runs er i
luften), ikke filer. Der fandtes intet der kunne fortryde en redigeringsrunde
som helhed — kun værktøjernes egne enkeltrettelser.

## Hvorfor `git stash create` og ikke noget andet

`git stash create` laver et commit-OBJEKT for arbejdstræet uden at røre HEAD,
index, arbejdstræet eller stash-listen. Det dukker ikke op i `git log`,
`git branch` eller `git stash list`. Så et checkpoint kan aldrig flytte
Bjørns gren eller forurene hans historik — hvilket er hele grunden til at det
er forsvarligt at tage et automatisk.

Tilbagerulning er `git checkout <sha> -- .`, som kun rører arbejdstræ og
index. Aldrig HEAD. Det her er bevidst IKKE `reset --hard`: den kommando åd
491 journal-linjer på CT105 en gang, og den lektie står ved magt.

## Forskel fra jarvis-code

Stakken ligger i runtime_state pr. session, ikke i hukommelsen. Runtime er to
processer, og et checkpoint taget i api'et skal kunne rulles tilbage fra
runtimen.

Det har en pris værd at kende: et stash-objekt er løst og kan bortsamles af
`git gc` hvis det bliver gammelt nok. Derfor tjekker `rollback_last` at
objektet stadig findes, frem for at love en tilbagerulning den ikke kan
holde.
"""
from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

logger = logging.getLogger(__name__)

_KEY = "edit_checkpoints_by_session"
_MAX_PR_SESSION = 20


def _load() -> dict[str, Any]:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_KEY, {})
        return dict(v) if isinstance(v, dict) else {}
    except Exception:
        return {}


def _save(state: dict[str, Any]) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_KEY, state)
    except Exception:
        logger.warning("edit_checkpoint: kunne ikke gemme", exc_info=True)


def _git(cwd: str, *args: str, timeout: int = 15) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout or "").strip()
    except Exception:
        return 1, ""


def is_git_repo(cwd: str) -> bool:
    kode, ud = _git(cwd, "rev-parse", "--is-inside-work-tree", timeout=5)
    return kode == 0 and ud == "true"


def _objekt_findes(cwd: str, sha: str) -> bool:
    """Er stash-objektet der endnu, eller har `git gc` taget det?"""
    kode, _ = _git(cwd, "cat-file", "-e", f"{sha}^{{commit}}", timeout=5)
    return kode == 0


def checkpoint(cwd: str, session_id: str, *, note: str = "") -> str | None:
    """Fotografér arbejdstræet. None hvis ikke et git-repo eller træet er rent."""
    sti = str(cwd or "").strip()
    sid = str(session_id or "").strip() or "_default"
    if not sti or not is_git_repo(sti):
        return None
    kode, sha = _git(sti, "stash", "create")
    if kode != 0 or not sha:
        return None  # rent træ — intet at fotografere
    st = _load()
    stak = [p for p in (st.get(sid) or []) if isinstance(p, dict)]
    stak.append({"cwd": sti, "sha": sha, "tid": time.time(), "note": str(note)[:200]})
    st[sid] = stak[-_MAX_PR_SESSION:]
    _save(st)
    logger.info("edit_checkpoint: %s @ %s (%s)", sha[:10], sti, note or "runde")
    return sha


def list_checkpoints(session_id: str) -> list[dict[str, Any]]:
    sid = str(session_id or "").strip() or "_default"
    return list(_load().get(sid) or [])


def rollback_last(session_id: str) -> dict[str, Any]:
    """Gendan filerne fra seneste checkpoint. Popper stakken."""
    sid = str(session_id or "").strip() or "_default"
    st = _load()
    stak = [p for p in (st.get(sid) or []) if isinstance(p, dict)]
    if not stak:
        return {"status": "error", "error": "ingen checkpoints i denne session"}
    post = stak.pop()
    st[sid] = stak
    _save(st)
    cwd, sha = str(post.get("cwd") or ""), str(post.get("sha") or "")
    if not _objekt_findes(cwd, sha):
        return {"status": "error",
                "error": f"checkpointet {sha[:10]} findes ikke længere "
                         "(bortsamlet af git gc) — der er intet at rulle tilbage til"}
    kode, _ = _git(cwd, "checkout", sha, "--", ".")
    if kode != 0:
        return {"status": "error", "error": f"kunne ikke gendanne {sha[:10]}"}
    return {"status": "ok", "gendannet": sha[:10], "cwd": cwd,
            "note": post.get("note"), "tilbage": len(stak)}


def clear(session_id: str) -> None:
    sid = str(session_id or "").strip() or "_default"
    st = _load()
    if sid in st:
        st.pop(sid, None)
        _save(st)
