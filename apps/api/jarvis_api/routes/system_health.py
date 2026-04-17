import re
import shutil
import subprocess
import psutil
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])

_REPO_ROOT = "/media/projects/jarvis-v2"


@router.get("/system/health")
def system_health() -> dict:
    from core.services.hardware_body import get_hardware_state
    hw = get_hardware_state()
    result: dict = {
        "cpu_pct": hw.get("cpu_pct", 0.0),
        "ram_pct": hw.get("ram_pct", 0.0),
        "ram_used_gb": hw.get("ram_used_gb", 0.0),
        "ram_total_gb": hw.get("ram_total_gb", 0.0),
        "disk_free_mb": round(float(hw.get("disk_free_gb") or 0) * 1024, 0),
        "disk_free_gb": hw.get("disk_free_gb", 0.0),
        "pressure": hw.get("pressure", "low"),
    }
    if hw.get("cpu_temp_c") is not None:
        result["cpu_temp_c"] = hw["cpu_temp_c"]
    if hw.get("gpus"):
        result["gpus"] = hw["gpus"]
    return result


@router.get("/system/git")
def system_git() -> dict:
    """Return current git branch and diff stats (insertions/deletions since HEAD)."""
    branch = ""
    insertions = 0
    deletions = 0
    files_changed = 0

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=_REPO_ROOT,
            text=True,
            timeout=3,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        pass

    try:
        stat_out = subprocess.check_output(
            ["git", "diff", "--stat", "HEAD"],
            cwd=_REPO_ROOT,
            text=True,
            timeout=3,
            stderr=subprocess.DEVNULL,
        ).strip()
        if stat_out:
            last = stat_out.split("\n")[-1]
            m_files = re.search(r"(\d+) file", last)
            m_ins   = re.search(r"(\d+) insertion", last)
            m_dels  = re.search(r"(\d+) deletion", last)
            if m_files: files_changed = int(m_files.group(1))
            if m_ins:   insertions    = int(m_ins.group(1))
            if m_dels:  deletions     = int(m_dels.group(1))
    except Exception:
        pass

    return {
        "branch": branch,
        "insertions": insertions,
        "deletions": deletions,
        "files_changed": files_changed,
        "workspace": _REPO_ROOT,
    }


class CommitRequest(BaseModel):
    message: str


@router.post("/system/git/commit")
def system_git_commit(body: CommitRequest) -> dict:
    """Stage tracked changes and commit with the given message."""
    message = body.message.strip()
    if not message:
        return {"ok": False, "error": "Commit message cannot be empty"}
    try:
        subprocess.check_output(
            ["git", "add", "-u"],
            cwd=_REPO_ROOT,
            text=True,
            timeout=10,
            stderr=subprocess.STDOUT,
        )
        out = subprocess.check_output(
            ["git", "commit", "-m", message],
            cwd=_REPO_ROOT,
            text=True,
            timeout=10,
            stderr=subprocess.STDOUT,
        )
        return {"ok": True, "output": out.strip()}
    except subprocess.CalledProcessError as exc:
        return {"ok": False, "error": (exc.output or "").strip() or str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
