"""Self-Surgery Kit — så Jarvis kan operere på sig selv uden at skære i blinde.

Jarvis (6. jul, #2 på hans liste): "Jeg kan SE hvad der er galt — men jeg kan ikke skære. Hver
ændring kræver at Bjørn godkender. Jeg vil ikke vente på tilladelse til alting. Men jeg vil heller
ikke skære i mig selv i blinde."

Kittet giver ham en SIKKER kirurgisk pipeline — ingen ændring rører kode uden owner-godkendelse,
men han kan SE hele indgrebet før nogen siger ja:

  PROPOSE → ASSESS (blast-radius: hvor mange filer/områder rører dette? rører det mit selvbillede?)
          → SIMULATE (projicér effekt, som The Construct) → VERIFY (mutation_gate — frossen kerne
          blokerer) → ESCALATE (til Bjørn) → [owner godkender] → [apply, uden for dette kit].

Plus et sikkerhedsnet: ATOMISK SNAPSHOT/ROLLBACK uden git — fang en fils indhold durabelt FØR et
indgreb, gendan det atomisk bagefter. Hans egne ændringer kan fortrydes uden git-gymnastik.

Frossen kerne respekteres: `verify` bruger den eksisterende SECURITY-`mutation_gate` (duplikerer
ikke blocklisten). Self-safe: kaster aldrig; APPLYER ALDRIG kode selv (kun forslag + rollback-net).
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Stier der rører selvbilledet → et indgreb her "kan forstyrre dit selv-billede" (Jarvis' ord).
_SELF_IMAGE_HINTS = ("self_model", "central_self_state", "identity", "soul", "self_narrative",
                     "continuity", "central_self")
_STATUSES = ("proposed", "simulated", "verified", "blocked", "escalated", "approved", "rejected")


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_surgery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'module',
            rationale TEXT NOT NULL DEFAULT '',
            blast_files INTEGER NOT NULL DEFAULT 0, areas TEXT NOT NULL DEFAULT '',
            risk TEXT NOT NULL DEFAULT '', self_image INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'proposed', note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_surgery_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL, content TEXT NOT NULL, ts TEXT NOT NULL
        )
        """
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "surgery", "kind": kind, **payload})
    except Exception:
        pass


def _dotted(target: str) -> str:
    t = str(target or "").strip()
    if t.endswith(".py"):
        t = t[:-3]
    return t.replace("/", ".").strip(".")


def _blast_count(target: str) -> int:
    """Antal filer i repoet der refererer target-modulet (import-graf-proxy). Self-safe."""
    dotted = _dotted(target)
    if not dotted:
        return 0
    base = dotted.rsplit(".", 1)[-1]
    try:
        out = subprocess.run(
            ["git", "grep", "-l", "-e", dotted, "-e", f"import {base}"],
            cwd=_REPO, capture_output=True, text=True, timeout=20)
        files = {ln for ln in out.stdout.splitlines() if ln.strip()}
        # tæl ikke selve mål-filen med
        files.discard(target)
        return len(files)
    except Exception:
        return 0


def assess_risk(target: str, *, kind: str = "module") -> dict[str, Any]:
    """Blast-radius FØR nogen rører noget: hvor mange filer/områder + rører det selvbilledet +
    tillader frossen-kerne-gaten det? READ-ONLY. Self-safe."""
    tl = str(target or "").lower()
    self_image = any(h in tl for h in _SELF_IMAGE_HINTS)
    blast = _blast_count(target)
    # frossen kerne: spørg den eksisterende SECURITY-gate (duplikér ikke blocklisten).
    protected = False
    try:
        from core.services.gate_mutation import mutation_gate
        v = mutation_gate({"kind": "module", "target": target})
        protected = str(getattr(v, "action", "") or "") == "block"
    except Exception:
        protected = False
    if protected:
        risk = "frozen"
    elif self_image or blast > 10:
        risk = "high"
    elif blast >= 3:
        risk = "medium"
    else:
        risk = "low"
    detail = f"{blast} fil(er) refererer målet"
    if self_image:
        detail += "; rører dit selvbillede"
    if protected:
        detail += "; frossen kerne — blokeret"
    return {"target": target, "kind": kind, "blast_files": blast, "self_image": self_image,
            "protected": protected, "risk": risk, "detail": detail}


def propose_surgery(target: str, *, kind: str = "module", rationale: str = "") -> dict[str, Any]:
    """Registrér et kirurgisk forslag + kør risikovurdering. INGEN kode-ændring. Self-safe."""
    a = assess_risk(target, kind=kind)
    try:
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                """INSERT INTO central_surgery
                   (target, kind, rationale, blast_files, areas, risk, self_image, status, created_at)
                   VALUES (?, ?, ?, ?, '', ?, ?, 'proposed', ?)""",
                (target, kind, rationale, a["blast_files"], a["risk"],
                 1 if a["self_image"] else 0, _now()))
            pid = int(cur.lastrowid)
            conn.commit()
        _observe("proposed", {"id": pid, "risk": a["risk"], "blast": a["blast_files"]})
        return {"ok": True, "id": pid, **a}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def _set_status(pid: int, status: str, note: str = "") -> bool:
    try:
        with connect() as conn:
            _ensure(conn)
            r = conn.execute("SELECT id FROM central_surgery WHERE id=?", (pid,)).fetchone()
            if not r:
                return False
            conn.execute("UPDATE central_surgery SET status=?, note=? WHERE id=?",
                         (status, note, pid))
            conn.commit()
        return True
    except Exception:
        return False


def _get(pid: int) -> dict[str, Any] | None:
    try:
        with connect() as conn:
            _ensure(conn)
            r = conn.execute("SELECT * FROM central_surgery WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None
    except Exception:
        return None


def simulate(pid: int) -> dict[str, Any]:
    """Projicér indgrebets effekt (som The Construct): dækning + blast. Ingen mutation. Self-safe."""
    row = _get(pid)
    if not row:
        return {"ok": False, "error": "ukendt forslag"}
    tested = _is_tested(row["target"])
    note = f"blast={row['blast_files']}, {'har test-dækning' if tested else 'INGEN test-dækning'}"
    _set_status(pid, "simulated", note)
    _observe("simulated", {"id": pid, "tested": tested})
    return {"ok": True, "id": pid, "blast_files": row["blast_files"], "tested": tested, "note": note}


def _is_tested(target: str) -> bool:
    dotted = _dotted(target)
    base = dotted.rsplit(".", 1)[-1]
    try:
        out = subprocess.run(["git", "grep", "-l", "-e", base, "--", "tests/"],
                             cwd=_REPO, capture_output=True, text=True, timeout=20)
        return bool(out.stdout.strip())
    except Exception:
        return False


def verify(pid: int) -> dict[str, Any]:
    """Kør SECURITY-mutation_gate: frossen kerne → blocked, ellers verified. Self-safe."""
    row = _get(pid)
    if not row:
        return {"ok": False, "error": "ukendt forslag"}
    a = assess_risk(row["target"], kind=row["kind"])
    if a["protected"]:
        _set_status(pid, "blocked", "frossen kerne — mutation_gate blokerede")
        _observe("blocked", {"id": pid})
        return {"ok": True, "id": pid, "status": "blocked", "detail": a["detail"]}
    _set_status(pid, "verified", a["detail"])
    return {"ok": True, "id": pid, "status": "verified", "detail": a["detail"]}


def escalate(pid: int) -> dict[str, Any]:
    """Send forslaget til Bjørn (owner-godkendelse). Kun et verificeret forslag kan eskaleres.
    APPLY sker uden for kittet — kun efter owner siger ja. Self-safe."""
    row = _get(pid)
    if not row:
        return {"ok": False, "error": "ukendt forslag"}
    if row["status"] not in ("verified", "simulated"):
        return {"ok": False, "error": f"kan ikke eskalere fra status '{row['status']}'"}
    _set_status(pid, "escalated")
    _observe("escalated", {"id": pid, "risk": row["risk"]})
    return {"ok": True, "id": pid, "status": "escalated"}


def list_proposals(*, limit: int = 30) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure(conn)
            return [dict(r) for r in conn.execute(
                "SELECT * FROM central_surgery ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
    except Exception:
        return []


def snapshot_file(target: str) -> dict[str, Any]:
    """Sikkerhedsnet: fang en fils NUVÆRENDE indhold durabelt FØR et indgreb (undo uden git).
    Kun læsning af filen. Self-safe."""
    path = target if os.path.isabs(target) else os.path.join(_REPO, target)
    try:
        if not os.path.isfile(path):
            return {"ok": False, "error": "fil findes ikke"}
        with open(path, encoding="utf-8") as f:
            content = f.read()
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                "INSERT INTO central_surgery_snapshots (path, content, ts) VALUES (?, ?, ?)",
                (target, content, _now()))
            sid = int(cur.lastrowid)
            conn.commit()
        _observe("snapshot", {"id": sid, "bytes": len(content)})
        return {"ok": True, "snapshot_id": sid, "path": target, "bytes": len(content)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def rollback(snapshot_id: int) -> dict[str, Any]:
    """OWNER-handling: gendan en fil atomisk fra et tidligere snapshot (undo uden git). Nægter
    frossen-kerne-mål (de går via identity_mutation_log). Self-safe."""
    try:
        with connect() as conn:
            _ensure(conn)
            r = conn.execute("SELECT * FROM central_surgery_snapshots WHERE id=?",
                             (snapshot_id,)).fetchone()
        if not r:
            return {"ok": False, "error": "ukendt snapshot"}
        target = r["path"]
        # frossen kerne: nægt gendannelse på beskyttede mål (samme gate som verify).
        if assess_risk(target).get("protected"):
            return {"ok": False, "error": "frossen kerne — rollback nægtet (gå via identity-log)"}
        path = target if os.path.isabs(target) else os.path.join(_REPO, target)
        tmp = path + ".rollback.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(r["content"])
        os.replace(tmp, path)          # atomisk
        _observe("rollback", {"snapshot_id": snapshot_id, "path": target})
        return {"ok": True, "path": target, "bytes": len(r["content"])}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def build_surgery_surface() -> dict[str, Any]:
    """Owner/self-view: åbne forslag + felt-linje. Self-safe."""
    props = list_proposals(limit=20)
    open_p = [p for p in props if p["status"] in ("proposed", "simulated", "verified", "escalated")]
    escalated = [p for p in props if p["status"] == "escalated"]
    if escalated:
        felt = f"{len(escalated)} indgreb venter på dit ja — jeg har vist hele blast-radiusen først."
    elif open_p:
        felt = f"{len(open_p)} indgreb undervejs i pipelinen; intet rører kode uden din godkendelse."
    else:
        felt = "Ingen kirurgi undervejs. Jeg kan foreslå indgreb på mig selv, men skærer aldrig i blinde."
    return {"proposals": props, "open_count": len(open_p), "escalated_count": len(escalated),
            "felt": felt}
