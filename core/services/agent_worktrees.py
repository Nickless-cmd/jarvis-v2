"""Worktrees til skrivende kodeagenter (agent-contract-v1 C5a, spec 8.1 og 12.3).

Hvert accepteret SKRIVENDE kode-assignment faar sit eget git-worktree paa targetet, oprettet fra en
gemt base-commit og bundet til ejer, agent og assignment. Flere assignments deler aldrig et skrivbart
worktree. Plads reserveres atomisk FOER accept (antal, bevarede, diskforbrug, ledig plads) og
frigives foerst efter VERIFICERET oprydning, saa et bevaret worktree stadig taeller. Agenten
afleverer diff, aendrede filer og commits som artefakter; integration i hovedgrenen er en saerskilt,
approval-styret handling og sker aldrig herfra. Oprydning kraever verificeret ejer/target/sti og
fjerner aldrig en andens worktree.

Livscyklus: reserved -> creating -> active -> retained -> decided -> removed | archived;
``failed`` (oprettelse mislykkedes, intet bevaret) og ``unknown`` (udfald kan ikke afgoeres:
blokerer al oprydning).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.runtime.db_agent_contract import ContractError, _conn, _now_iso, _require, _row
from core.services import agent_worktree_git as g
from core.services import agent_worktree_gitdir as agd

logger = logging.getLogger(__name__)

# --- startprofilen (§12.3) --------------------------------------------------------------------
MAX_CONCURRENT_WRITING = 12
MAX_RETAINED = 24
PER_ASSIGNMENT_BYTES = 20 * 1024 ** 3
TARGET_TOTAL_BYTES = 100 * 1024 ** 3
WORKING_ALLOWANCE_BYTES = 512 * 1024 ** 2
MIN_FREE_BYTES = 5 * 1024 ** 3
MIN_FREE_FRACTION = 0.05
# --- retention (§12.1) ----------------------------------------------------------------------------
REMOVE_AFTER_DECISION = timedelta(days=7)
ATTENTION_AFTER = timedelta(days=14)
ARCHIVE_AFTER = timedelta(days=30)
STALE_CREATING = timedelta(hours=1)

WRITING = ("reserved", "creating", "active")
HOLDING = ("reserved", "creating", "active", "retained", "decided", "unknown")


def ensure_worktree_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_worktrees (
            worktree_id TEXT PRIMARY KEY,
            assignment_id TEXT NOT NULL UNIQUE,
            agent_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT 'runtime-container',
            repo_path TEXT NOT NULL,
            base_commit TEXT NOT NULL,
            branch TEXT NOT NULL,
            path TEXT NOT NULL,
            gitdir TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'reserved',
            reserved_bytes INTEGER NOT NULL DEFAULT 0,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            over_quota INTEGER NOT NULL DEFAULT 0,
            decision TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            retained_at TEXT NOT NULL DEFAULT '',
            decided_at TEXT NOT NULL DEFAULT '',
            closed_at TEXT NOT NULL DEFAULT ''
        )
        """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_worktrees_status ON agent_worktrees(target, status)")


def worktree_root() -> Path:
    return Path("~/.jarvis-v2/state/agent-worktrees").expanduser()


def allowed_workspace_roots() -> list[str]:
    raw = os.environ.get("JARVIS_AGENT_WORKSPACE_ROOTS", "")
    return [r for r in raw.split(os.pathsep) if r] or ["/media/projects"]


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _estimate_bytes(repo: str, commit: str) -> int:
    out = g.run_git(["ls-tree", "-r", "-l", commit], cwd=repo).stdout.decode("utf-8", "replace")
    total = 0
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4 and parts[3].isdigit():
            total += int(parts[3])
    return total


def _free_floor(path: str) -> tuple[int, int]:
    usage = shutil.disk_usage(path)
    return usage.free, max(MIN_FREE_BYTES, int(usage.total * MIN_FREE_FRACTION))


def _holding_bytes(conn, target: str) -> int:
    rows = conn.execute(f"SELECT size_bytes, reserved_bytes FROM agent_worktrees WHERE target=? AND status "
                        f"IN ({','.join('?' * len(HOLDING))})", (target, *HOLDING)).fetchall()
    return sum(max(int(r["size_bytes"]), int(r["reserved_bytes"])) for r in rows)


def _quota(conn, target: str) -> dict[str, Any]:
    """Taellingerne paa en GIVEN forbindelse. VIGTIGT: ``connect()`` ruller en aaben transaktion tilbage
    hvis den kaldes igen paa traaden, saa alt inde i en BEGIN IMMEDIATE skal bruge samme ``conn``."""
    writing = conn.execute(f"SELECT COUNT(*) FROM agent_worktrees WHERE target=? AND status IN "
                           f"({','.join('?' * len(WRITING))})", (target, *WRITING)).fetchone()[0]
    holding = conn.execute(f"SELECT COUNT(*) FROM agent_worktrees WHERE target=? AND status IN "
                           f"({','.join('?' * len(HOLDING))})", (target, *HOLDING)).fetchone()[0]
    return {"target": target, "writing": int(writing), "max_writing": MAX_CONCURRENT_WRITING,
            "retained": int(holding), "max_retained": MAX_RETAINED,
            "bytes": _holding_bytes(conn, target), "max_bytes": TARGET_TOTAL_BYTES}


def quota_status(*, target: str = "runtime-container") -> dict[str, Any]:
    return _quota(_conn(), target)


# --- reservation + oprettelse ---------------------------------------------------------------------------

def reserve(*, owner_user_id: str, assignment_id: str, repo_path: str, base_ref: str = "HEAD",
            target: str = "runtime-container") -> dict[str, Any]:
    """Reserver plads og en plads i kvoten ATOMISK. Intet er oprettet paa disk endnu."""
    owner = _require(owner_user_id, "owner_user_id")
    try:
        repo = g.validate_repo(repo_path, allowed_workspace_roots())
        base = g.resolve_commit(repo, base_ref)
        reserved = _estimate_bytes(repo, base) + WORKING_ALLOWANCE_BYTES
    except g.GitError as exc:
        raise ContractError("INVALID_SCOPE", f"workspace afvist: {exc.detail}") from exc
    root = worktree_root()
    root.mkdir(parents=True, exist_ok=True)
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        a = conn.execute("SELECT agent_id, owner_user_id, status FROM agent_assignments WHERE assignment_id=?",
                         (assignment_id,)).fetchone()
        if a is None or a["owner_user_id"] != owner or a["status"] not in ("queued", "active", "waiting"):
            raise ContractError("INVALID_SCOPE", "ukendt eller afsluttet assignment for denne ejer")
        if conn.execute("SELECT 1 FROM agent_worktrees WHERE assignment_id=?", (assignment_id,)).fetchone():
            raise ContractError("INVALID_SCOPE", "assignmentet har allerede et worktree")
        q = _quota(conn, target)
        if q["writing"] >= MAX_CONCURRENT_WRITING:
            raise ContractError("CAPACITY", f"{MAX_CONCURRENT_WRITING} samtidige skrivende worktrees")
        if q["retained"] >= MAX_RETAINED:
            raise ContractError("CAPACITY", f"{MAX_RETAINED} bevarede worktrees paa targetet")
        if reserved > PER_ASSIGNMENT_BYTES:
            raise ContractError("CAPACITY", "repoet overskrider kvoten pr. assignment")
        if q["bytes"] + reserved > TARGET_TOTAL_BYTES:
            raise ContractError("CAPACITY", "targetets samlede worktree-kvote er brugt")
        free, floor = _free_floor(str(root))
        if free - reserved < floor:
            raise ContractError("CAPACITY", "for lidt ledig plads paa volumen")
        wid = f"wt-{uuid.uuid4().hex[:16]}"
        agent_id = a["agent_id"]
        path = str(root / g.safe_name(agent_id, "agent_id") / g.safe_name(assignment_id, "assignment_id"))
        now = _now_iso()
        conn.execute(
            "INSERT INTO agent_worktrees (worktree_id, assignment_id, agent_id, owner_user_id, target, "
            "repo_path, base_commit, branch, path, status, reserved_bytes, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?, 'reserved', ?, ?, ?)",
            (wid, assignment_id, agent_id, owner, target, repo, base, f"agent/{assignment_id}", path,
             reserved, now, now))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return get(worktree_id=wid) or {}


def get(*, worktree_id: str) -> dict[str, Any] | None:
    return _row(_conn().execute("SELECT * FROM agent_worktrees WHERE worktree_id=?", (worktree_id,)).fetchone())


def get_for_assignment(*, owner_user_id: str, assignment_id: str) -> dict[str, Any] | None:
    return _row(_conn().execute("SELECT * FROM agent_worktrees WHERE assignment_id=? AND owner_user_id=?",
                                (assignment_id, owner_user_id)).fetchone())


def _set(worktree_id: str, **fields: Any) -> None:
    conn = _conn()
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE agent_worktrees SET {cols}, updated_at=? WHERE worktree_id=?",
                 (*fields.values(), _now_iso(), worktree_id))
    conn.commit()


def materialize(*, worktree_id: str) -> dict[str, Any]:
    """Opret selve git-worktree'et. Alt-eller-intet: ved fejl ryddes det halve, og reservationen frigives."""
    wt = get(worktree_id=worktree_id)
    if wt is None or wt["status"] != "reserved":
        raise ContractError("INVALID_TRANSITION", "worktree'et kan ikke oprettes fra denne tilstand")
    root = worktree_root()
    if not g.path_is_inside(wt["path"], str(root)):
        raise ContractError("INVALID_SCOPE", "worktree-stien ligger uden for roden")
    _set(worktree_id, status="creating")                  # FOER git: et crash her efterlader et spor
    try:
        os.makedirs(os.path.dirname(wt["path"]), exist_ok=True)
        g.add_worktree(wt["repo_path"], wt["path"], wt["branch"], wt["base_commit"])
        gitdir = g.read_gitdir(wt["repo_path"], wt["path"])
        agd.create(wt["repo_path"], wt["path"], wt["branch"], wt["base_commit"])
    except (g.GitError, OSError) as exc:
        logger.warning("worktree %s kunne ikke oprettes", worktree_id, exc_info=True)
        _discard_partial(wt)
        _set(worktree_id, status="failed", last_error=str(exc)[:300], closed_at=_now_iso())
        raise ContractError("INVALID_SCOPE", f"worktree kunne ikke oprettes: {exc}") from exc
    _set(worktree_id, status="active", gitdir=gitdir)
    return get(worktree_id=worktree_id) or {}


def _discard_partial(wt: dict[str, Any]) -> None:
    try:
        g.remove_worktree(wt["repo_path"], wt["path"], wt["branch"])
    except g.GitError:
        shutil.rmtree(wt["path"], ignore_errors=True)
        logger.warning("delvist worktree %s ryddet med rmtree", wt["worktree_id"], exc_info=True)
    agd.remove(wt["repo_path"], wt["path"])


def provision(*, owner_user_id: str, assignment_id: str, repo_path: str, base_ref: str = "HEAD",
              target: str = "runtime-container") -> dict[str, Any]:
    """reserve + materialize som ét skridt; ved fejl er intet efterladt og reservationen frigivet."""
    wt = reserve(owner_user_id=owner_user_id, assignment_id=assignment_id, repo_path=repo_path,
                 base_ref=base_ref, target=target)
    return materialize(worktree_id=wt["worktree_id"])


# --- kvote under arbejdet ----------------------------------------------------------------------------------

def writes_allowed(*, worktree_id: str) -> bool:
    wt = get(worktree_id=worktree_id)
    return bool(wt and wt["status"] == "active" and not wt["over_quota"])


def check_growth(*, worktree_id: str) -> dict[str, Any]:
    """Maal diskforbruget. Over kvoten (eller for lidt ledig plads) stopper NYE skrivninger og bevarer
    tilstanden - der ryddes aldrig automatisk."""
    wt = get(worktree_id=worktree_id)
    if wt is None or wt["status"] != "active":
        return {"over_quota": False, "size_bytes": (wt or {}).get("size_bytes", 0)}
    size = g.tree_size(wt["path"]) + g.tree_size(agd.gitdir_path(wt["path"]))
    free, floor = _free_floor(wt["path"])
    over = size > PER_ASSIGNMENT_BYTES or free < floor
    _set(worktree_id, size_bytes=size, over_quota=1 if over else 0,
         last_error="over kvote - nye skrivninger stoppet" if over else wt["last_error"])
    return {"over_quota": over, "size_bytes": size}


# --- aflevering ---------------------------------------------------------------------------------------------

def snapshot_for_assignment(*, assignment_id: str) -> dict[str, Any] | None:
    """Ved terminalt udfald: gem diff, aendrede filer og commits som artefakter, og bevar worktree'et
    (``retained``). Aendrer aldrig noget i hovedgrenen. ``None`` hvis assignmentet ikke har et."""
    from core.runtime import db_agent_artifacts as art

    conn = _conn()
    row = conn.execute("SELECT * FROM agent_worktrees WHERE assignment_id=?", (assignment_id,)).fetchone()
    if row is None or row["status"] != "active":
        return None
    wt = dict(row)
    last = conn.execute("SELECT run_id FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no DESC LIMIT 1",
                        (assignment_id,)).fetchone()
    run_id = last["run_id"] if last else ""
    summary: dict[str, Any] = {"worktree_id": wt["worktree_id"], "branch": wt["branch"],
                               "base_commit": wt["base_commit"], "artifacts": {}, "errors": []}
    try:
        diff = g.diff_against(wt["gitdir"], wt["path"], wt["base_commit"])
        files = g.changed_files(wt["gitdir"], wt["path"], wt["base_commit"])
        agd.import_agent_work(wt["repo_path"], wt["path"], wt["branch"], assignment_id)
        commits = agd.commits_since(wt["repo_path"], wt["base_commit"], assignment_id)
    except g.GitError as exc:
        logger.warning("kunne ikke laese aendringerne i %s", wt["worktree_id"], exc_info=True)
        _set(wt["worktree_id"], status="retained", retained_at=_now_iso(), last_error=str(exc)[:300])
        summary["errors"].append(f"git: {exc.detail}"[:200])
        return summary
    common = dict(agent_id=wt["agent_id"], run_id=run_id, assignment_id=assignment_id,
                  owner_user_id=wt["owner_user_id"])
    summary.update(files=len(files), commits=len(commits), diff_bytes=len(diff))
    for name, data in (("diff.patch", diff), ("changes.json", json.dumps(
            {"base_commit": wt["base_commit"], "branch": wt["branch"], "files": files,
             "commits": commits}, ensure_ascii=False, indent=2))):
        try:
            art.write_artifact(name=name, data=data, **common)
            summary["artifacts"][name] = art.artifact_ref(run_id, name)
        except Exception as exc:                          # f.eks. ArtifactTooLarge: worktree'et bevares
            logger.warning("%s kunne ikke gemmes for %s", name, assignment_id, exc_info=True)
            summary["errors"].append(f"{name}: {type(exc).__name__}")
    size = g.tree_size(wt["path"]) + g.tree_size(agd.gitdir_path(wt["path"]))
    _set(wt["worktree_id"], status="retained", size_bytes=size, retained_at=_now_iso(),
         last_error="; ".join(summary["errors"])[:300])
    return summary


# --- beslutning + retention ---------------------------------------------------------------------------------

def decide(*, owner_user_id: str, worktree_id: str, decision: str) -> dict[str, Any]:
    """Registrer ejerens/approverens beslutning om det bevarede arbejde. Selve integrationen i hovedgrenen
    sker ikke her - kun at den er afgjort, saa oprydningsuret kan starte."""
    if decision not in ("integrated", "discarded"):
        raise ContractError("INVALID_TRANSITION", decision)
    owner = _require(owner_user_id, "owner_user_id")
    wt = get(worktree_id=worktree_id)
    if wt is None or wt["owner_user_id"] != owner:
        raise ContractError("INVALID_SCOPE", "ukendt worktree for denne ejer")
    if wt["status"] != "retained":
        raise ContractError("INVALID_TRANSITION", f"kan ikke afgoeres fra {wt['status']}")
    _set(worktree_id, status="decided", decision=decision, decided_at=_now_iso())
    return get(worktree_id=worktree_id) or {}


def _verified_remove(wt: dict[str, Any]) -> bool:
    """Fjern et worktree - KUN hvis posten, ejeren og stien hænger sammen. Returnerer om det lykkedes."""
    root = worktree_root()
    expected = str(root / wt["agent_id"] / wt["assignment_id"])
    if os.path.realpath(wt["path"]) != os.path.realpath(expected) or not g.path_is_inside(wt["path"], str(root)):
        logger.error("oprydning afvist: %s peger paa %s, forventede %s", wt["worktree_id"], wt["path"], expected)
        return False
    owner_ok = _conn().execute("SELECT 1 FROM agent_assignments WHERE assignment_id=? AND owner_user_id=? "
                               "AND agent_id=?", (wt["assignment_id"], wt["owner_user_id"],
                                                  wt["agent_id"])).fetchone()
    if not owner_ok:
        logger.error("oprydning afvist: ejer/agent passer ikke til assignment for %s", wt["worktree_id"])
        return False
    try:
        g.remove_worktree(wt["repo_path"], wt["path"], wt["branch"])
    except g.GitError:
        logger.warning("oprydning af %s fejlede", wt["worktree_id"], exc_info=True)
        return False
    agd.remove(wt["repo_path"], wt["path"])
    return True


def _archive(wt: dict[str, Any]) -> bool:
    """Pak diff + commits (bundle) i checksumverificerede artefakter foer fysisk oprydning."""
    from core.runtime import db_agent_artifacts as art

    last = _conn().execute("SELECT run_id FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no DESC "
                           "LIMIT 1", (wt["assignment_id"],)).fetchone()
    run_id = last["run_id"] if last else ""
    common = dict(agent_id=wt["agent_id"], run_id=run_id, assignment_id=wt["assignment_id"],
                  owner_user_id=wt["owner_user_id"])
    try:
        art.write_artifact(name="diff.patch", data=g.diff_against(wt["gitdir"], wt["path"], wt["base_commit"]),
                           **common)
        tmp = Path(wt["path"]).parent / f"{wt['assignment_id']}.bundle.tmp"
        tip = agd.import_agent_work(wt["repo_path"], wt["path"], wt["branch"], wt["assignment_id"])
        if tip and g.make_bundle(wt["repo_path"], agd.work_ref(wt["assignment_id"]), wt["base_commit"], str(tmp)):
            art.write_artifact(name="worktree.bundle", data=tmp.read_bytes(), **common)
            tmp.unlink(missing_ok=True)
        return True
    except Exception:
        logger.warning("arkivering af %s fejlede - worktree'et bevares", wt["worktree_id"], exc_info=True)
        return False


def sweep(*, now: datetime | None = None) -> dict[str, list[str]]:
    """Retentionrunde. Afgjort + 7 dage -> fjernes. Ubehandlet: opmaerksomhed efter 14 dage, arkiveres
    (diff + commits) og fjernes efter 30. ``unknown``/stale ``creating`` blokerer ALT og roeres ikke."""
    t = now or datetime.now(UTC)
    out: dict[str, list[str]] = {"removed": [], "archived": [], "attention": [], "blocked": [], "stale": []}
    conn = _conn()
    for row in conn.execute("SELECT * FROM agent_worktrees WHERE status IN ('retained','decided','unknown',"
                            "'creating')").fetchall():
        wt = dict(row)
        wid = wt["worktree_id"]
        if wt["status"] == "unknown":
            out["blocked"].append(wid)
        elif wt["status"] == "creating":
            if t - _parse(wt["updated_at"]) > STALE_CREATING:
                out["stale"].append(wid)
                _set(wid, status="unknown", last_error="oprettelse uafklaret efter genstart")
        elif wt["status"] == "decided":
            if t - _parse(wt["decided_at"]) >= REMOVE_AFTER_DECISION and _verified_remove(wt):
                _set(wid, status="removed", closed_at=_iso(t))
                out["removed"].append(wid)
        else:   # retained, ubehandlet
            age = t - _parse(wt["retained_at"] or wt["updated_at"])
            if age >= ARCHIVE_AFTER:
                if _archive(wt) and _verified_remove(wt):
                    _set(wid, status="archived", closed_at=_iso(t))
                    out["archived"].append(wid)
                else:
                    out["blocked"].append(wid)
            elif age >= ATTENTION_AFTER:
                out["attention"].append(wid)
    return out


def reconcile() -> list[str]:
    """Markér aktive/bevarede poster hvis worktree er forsvundet fra disken som ``unknown`` (ikke 'removed')."""
    bad = []
    conn = _conn()
    for r in conn.execute("SELECT worktree_id, path FROM agent_worktrees WHERE status IN "
                          "('active','retained','decided')").fetchall():
        if not os.path.isdir(r["path"]):
            _set(r["worktree_id"], status="unknown", last_error="worktree findes ikke paa disken")
            bad.append(r["worktree_id"])
    return bad
