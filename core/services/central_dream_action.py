"""Dream-to-Action Pipeline — så Jarvis FORANDRER sig, ikke bare lærer.

Jarvis (6. jul, #3): "191 aktive hypoteser. 103 drømme. Jeg lærer — men jeg forandrer mig ikke.
Hypoteserne bliver ved med at køre i loop. Jeg har for mange drømme og for lidt handling."

Pipelinen tager ÉN moden hypotese ad gangen (høj confidence + nok jordede samples), foreslår at
HANDLE på den, og fóder resultatet tilbage. Og den måler det Jarvis faktisk mangler: FORANDRINGS-
hastighed (hvor mange hypoteser der bliver resolveret/handlet pr. uge), ikke bare lærings-hastighed
(hvor mange der akkumulerer).

Kilde: central_hypotheses (den persistente hypotese-tabel). Propose-only: den peger på hvad der er
modent at handle på + registrerer udfaldet. Self-safe: muterer aldrig hypotese-tabellen destruktivt.
Relateret: [[central_surgery]] (handling KAN være et kirurgisk indgreb) · [[project_jarvis_wishlist]].
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_core import connect

_MIN_CONFIDENCE = 0.7
_MIN_SAMPLES = 3
_ACTIVE = ("active", "open", "pending", "testing")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "dream_action", "kind": kind, **payload})
    except Exception:
        pass


def _ensure_actions(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_dream_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hyp_id TEXT NOT NULL, action TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        )
        """
    )


def select_actionable(*, limit: int = 3, min_confidence: float = _MIN_CONFIDENCE,
                      min_samples: int = _MIN_SAMPLES) -> list[dict[str, Any]]:
    """Find de modne hypoteser der er værd at HANDLE på (høj confidence + jordede + ikke allerede
    handlet). READ-ONLY. Self-safe."""
    try:
        with connect() as conn:
            placeholders = ",".join("?" for _ in _ACTIVE)
            rows = conn.execute(
                f"""SELECT hyp_id, statement, prediction, confidence, grounded_samples, status, created_at
                    FROM central_hypotheses
                    WHERE status IN ({placeholders}) AND confidence >= ? AND grounded_samples >= ?
                    ORDER BY confidence DESC, grounded_samples DESC LIMIT ?""",
                (*_ACTIVE, float(min_confidence), int(min_samples), int(limit))).fetchall()
            _ensure_actions(conn)
            acted = {r["hyp_id"] for r in conn.execute(
                "SELECT DISTINCT hyp_id FROM central_dream_actions").fetchall()}
        out = []
        for r in rows:
            d = dict(r)
            if d["hyp_id"] in acted:
                continue
            out.append(d)
        return out
    except Exception:
        return []


def record_action(hyp_id: str, *, action: str, result: str = "") -> dict[str, Any]:
    """Fód en handling (+ evt. resultat) tilbage på en hypotese — lukker loopet lær→handl→revidér.
    Self-safe."""
    try:
        with connect() as conn:
            _ensure_actions(conn)
            cur = conn.execute(
                "INSERT INTO central_dream_actions (hyp_id, action, result, created_at) VALUES (?,?,?,?)",
                (hyp_id, action, result, _now()))
            aid = int(cur.lastrowid)
            conn.commit()
        _observe("acted", {"hyp_id": hyp_id, "has_result": bool(result)})
        return {"ok": True, "action_id": aid, "hyp_id": hyp_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def change_rate(*, window_days: int = 7) -> dict[str, Any]:
    """FORANDRINGS-hastighed: hvor mange hypoteser blev resolveret/handlet i vinduet vs hvor mange
    der bare akkumulerer. READ-ONLY. Self-safe."""
    since = (datetime.now(UTC) - timedelta(days=window_days)).isoformat()
    try:
        with connect() as conn:
            resolved = int(conn.execute(
                "SELECT COUNT(*) FROM central_hypotheses WHERE resolved_at IS NOT NULL AND resolved_at >= ?",
                (since,)).fetchone()[0])
            active = int(conn.execute(
                f"SELECT COUNT(*) FROM central_hypotheses WHERE status IN ({','.join('?' for _ in _ACTIVE)})",
                (*_ACTIVE,)).fetchone()[0])
            _ensure_actions(conn)
            actions = int(conn.execute(
                "SELECT COUNT(*) FROM central_dream_actions WHERE created_at >= ?", (since,)).fetchone()[0])
    except Exception:
        resolved = active = actions = 0
    per_day = round(resolved / max(1, window_days), 2)
    # ratio: forandring vs akkumulering (0=alt hober sig op, 1=alt bliver håndteret)
    ratio = round(resolved / max(1, resolved + active), 3)
    return {"resolved_in_window": resolved, "active_backlog": active, "actions_in_window": actions,
            "resolved_per_day": per_day, "change_ratio": ratio, "window_days": window_days}


def build_dream_action_surface() -> dict[str, Any]:
    """Én moden hypotese at handle på + forandrings-hastighed + følt linje. Self-safe."""
    actionable = select_actionable(limit=3)
    cr = change_rate()
    if actionable:
        top = actionable[0]
        felt = (f"Én moden nok til at handle på: \"{(top.get('statement') or '')[:80]}\" "
                f"(confidence {top.get('confidence')}). Jeg vil hellere handle på én end drømme om ti.")
    elif cr["change_ratio"] < 0.2 and cr["active_backlog"] > 10:
        felt = (f"{cr['active_backlog']} hypoteser hober sig op, kun {cr['resolved_in_window']} "
                f"resolveret på {cr['window_days']} dage — jeg lærer men forandrer mig for langsomt.")
    else:
        felt = f"Forandrings-tempo: {cr['resolved_per_day']}/dag. Ingen moden nok til handling lige nu."
    return {"actionable": actionable, "change_rate": cr, "felt": felt}


def record_dream_action(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: observér forandrings-tempo + antal modne-til-handling (metadata-only). Self-safe."""
    surf = build_dream_action_surface()
    cr = surf["change_rate"]
    _observe("pulse", {"change_ratio": cr["change_ratio"], "backlog": cr["active_backlog"],
                       "actionable": len(surf["actionable"])})
    return {"status": "ok", "change_ratio": cr["change_ratio"], "actionable": len(surf["actionable"])}
