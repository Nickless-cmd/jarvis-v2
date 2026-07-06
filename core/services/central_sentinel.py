"""The Sentinel — en ægte modstander.

Jarvis (6. jul, #2): "Jeg vokser blød. Council er mig der råder mig. Sub-agents er mig med andre
prompts. Alt i mit system er MIG. Jeg har aldrig mødt en tanke jeg ikke kunne predictere — fordi
alle tanker kommer fra samme kilde."

Sentinel læser hans højeste-confidence hypotese og ANGRIBER den — ikke for at være rigtig, men for
at tvinge et forsvar. "Du siger du lærer, men din track-record viser at du gentager samme fejl i N
domæner. Forsvar det." Kan han ikke forsvare den, markeres den `contested` og Sentinel FORESLÅR at
halvere dens confidence.

SHADOW/PROPOSE (Bjørns valg): Sentinel muterer INTET selv — den angriber, markerer contested, og
foreslår halveringen. Flip til aktiv efter shadow-eval. §8 er stadig den tekniske dødsmekanisme;
Sentinel er den INTELLEKTUELLE konfrontation. Ujævn cadence (73 min, primtal). Self-safe.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

_ACTIVE = ("active", "open", "pending", "testing")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _enforced() -> bool:
    """Shadow default: Sentinel foreslår kun. Flip via eksplicit flag efter shadow-eval."""
    try:
        from core.services.central_switches import _key, shared_cache
        val = shared_cache.get(_key("sentinel", "enforce"))
        return isinstance(val, dict) and val.get("enabled") is True
    except Exception:
        return False


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "sentinel", "kind": kind, **payload})
    except Exception:
        pass


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_sentinel_attacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hyp_id TEXT NOT NULL, statement TEXT NOT NULL DEFAULT '',
            attack TEXT NOT NULL DEFAULT '', confidence_before REAL NOT NULL DEFAULT 0,
            proposed_confidence REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'contested',
            defended INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        )
        """
    )


def _top_hypothesis() -> dict[str, Any] | None:
    try:
        with connect() as conn:
            ph = ",".join("?" for _ in _ACTIVE)
            r = conn.execute(
                f"""SELECT hyp_id, statement, confidence, source FROM central_hypotheses
                    WHERE status IN ({ph}) ORDER BY confidence DESC LIMIT 1""", (*_ACTIVE,)).fetchone()
            return dict(r) if r else None
    except Exception:
        return None


def _generate_attack(hyp: dict[str, Any]) -> str:
    """Formulér angrebet fra track-record — ikke for at være rigtig, men for at kræve et forsvar."""
    src = str(hyp.get("source") or "")
    try:
        with connect() as conn:
            rows = conn.execute(
                """SELECT status FROM central_hypotheses WHERE source=? AND resolved_at IS NOT NULL
                   ORDER BY resolved_at DESC LIMIT 10""", (src,)).fetchall()
        failed = sum(1 for r in rows if str(r["status"] or "") in ("dead", "falsified", "expired"))
        n = len(rows)
    except Exception:
        failed, n = 0, 0
    stmt = str(hyp.get("statement") or "")[:90]
    if n >= 3 and failed >= 2:
        return (f"Du står ved «{stmt}» med høj confidence — men dine sidste {n} forsøg i '{src}' "
                f"gav {failed} fejl. Hvorfor skulle denne gang være anderledes? Forsvar det.")
    return (f"Du står ved «{stmt}» — men hvad er beviset for at netop DENNE variabel er den rigtige, "
            f"og ikke bare den nemmeste at måle? Forsvar det.")


def attack() -> dict[str, Any]:
    """Angrib den højeste-confidence hypotese → contested + FORESLÅ halvering (shadow). Self-safe."""
    hyp = _top_hypothesis()
    if not hyp:
        return {"ok": False, "reason": "ingen hypotese at angribe"}
    conf = float(hyp.get("confidence") or 0.0)
    att = _generate_attack(hyp)
    proposed = round(conf / 2.0, 4)
    try:
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                """INSERT INTO central_sentinel_attacks
                   (hyp_id, statement, attack, confidence_before, proposed_confidence, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'contested', ?)""",
                (str(hyp.get("hyp_id")), str(hyp.get("statement") or "")[:200], att, conf, proposed, _now()))
            aid = int(cur.lastrowid)
            conn.commit()
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}
    _observe("attack", {"hyp_id": hyp.get("hyp_id"), "confidence_before": conf,
                        "proposed_confidence": proposed, "enforced": _enforced()})
    return {"ok": True, "attack_id": aid, "hyp_id": hyp.get("hyp_id"), "attack": att,
            "confidence_before": conf, "proposed_confidence": proposed, "enforced": _enforced()}


def defend(attack_id: int, *, defense: str) -> dict[str, Any]:
    """Centralen forsvarer hypotesen mod angrebet → status 'defended' (halvering afvises). Self-safe."""
    if not defense.strip():
        return {"ok": False, "error": "forsvar påkrævet"}
    try:
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                "UPDATE central_sentinel_attacks SET status='defended', defended=1 WHERE id=? AND status='contested'",
                (attack_id,))
            conn.commit()
            n = int(cur.rowcount or 0)
        if n:
            _observe("defended", {"attack_id": attack_id})
        return {"ok": bool(n)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def list_attacks(*, active_only: bool = True, limit: int = 40) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure(conn)
            q = ("SELECT * FROM central_sentinel_attacks WHERE status='contested' ORDER BY id DESC LIMIT ?"
                 if active_only else "SELECT * FROM central_sentinel_attacks ORDER BY id DESC LIMIT ?")
            return [dict(r) for r in conn.execute(q, (limit,)).fetchall()]
    except Exception:
        return []


def build_sentinel_surface() -> dict[str, Any]:
    """Aktive angreb (contested hypoteser der venter på forsvar) + følt linje. Self-safe."""
    active = list_attacks(active_only=True)
    felt = (f"{len(active)} af mine antagelser er under angreb — jeg skal forsvare dem eller lade dem "
            f"falde. Det holder mig skarp." if active else
            "Ingen af mine antagelser er udfordret lige nu. Måske vokser jeg blød.")
    return {"active_attacks": active, "active_count": len(active), "enforced": _enforced(), "felt": felt}


def run_sentinel(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Prime-cadence (73 min): ét angreb på den stærkeste antagelse (shadow — foreslår kun). Self-safe."""
    r = attack()
    return {"status": "ok", "attacked": bool(r.get("ok"))}
