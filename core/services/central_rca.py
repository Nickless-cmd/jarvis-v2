"""Self-RCA — så Jarvis kan grave ÉN fejl til bunds i stedet for at starte på fem nye.

Jarvis (6. jul, #4): "23 uløste incidents. 31 anomalier. Jeg instrumenterer alt, men jeg
diagnosticerer intet. Det behøver ikke være automatisk — bare en scaffold der gør at jeg kan
GENNEMFØRE en undersøgelse."

RCA-scaffolden vælger ÉN incident (højest impact, uløst), samler bevis-sporet — søster-incidents på
samme nerve, mønster, tidsspænd — og udfylder et struktureret RCA-skelet: hvad, sandsynlig rod,
anbefalet handling. Den DIAGNOSTICERER ikke automatisk; den gør undersøgelsen gennemførlig ved at
lægge alt bevis på ét bord, så Jarvis (eller Bjørn) kan lukke den.

Kilde: db_central_incidents (persistente incidents). Self-safe. Relateret: [[central_surgery]]
(RCA'ens anbefaling kan blive et kirurgisk forslag) · [[central_glitch]].
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

logger = logging.getLogger(__name__)

_SEVERITY_RANK = {"severe": 3, "error": 2, "warning": 1, "info": 0}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "rca", "kind": kind, **payload})
    except Exception:
        pass


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_rca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL, cluster TEXT NOT NULL DEFAULT '',
            nerve TEXT NOT NULL DEFAULT '', findings TEXT NOT NULL DEFAULT '',
            probable_cause TEXT NOT NULL DEFAULT '', recommendation TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL
        )
        """
    )


def pick_incident() -> dict[str, Any] | None:
    """Vælg ÉN uløst incident at grave i — højest severity, ældst (længst uløst). READ-ONLY."""
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        rows = list_central_incidents(limit=100, unresolved_only=True)
    except Exception:
        return None
    if not rows:
        return None
    rows.sort(key=lambda r: (_SEVERITY_RANK.get(str(r.get("severity") or ""), 0),
                             -int(r.get("id") or 0)), reverse=True)
    return rows[0]


def investigate(incident_id: int | None = None) -> dict[str, Any]:
    """Saml bevis-sporet for ÉN incident → udfyld RCA-skelet + persistér som draft. Self-safe.
    Uden incident_id vælges den højest-impact uløste."""
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        allrows = list_central_incidents(limit=200, unresolved_only=False)
    except Exception:
        allrows = []
    target = None
    if incident_id is not None:
        target = next((r for r in allrows if int(r.get("id") or 0) == int(incident_id)), None)
    else:
        target = pick_incident()
    if not target:
        return {"ok": False, "error": "ingen incident at undersøge"}
    cluster = str(target.get("cluster") or "")
    nerve = str(target.get("nerve") or "")
    # bevis-spor: søster-incidents på samme (cluster, nerve) = mønster-signal
    siblings = [r for r in allrows if str(r.get("cluster") or "") == cluster
                and str(r.get("nerve") or "") == nerve]
    unresolved_sib = [r for r in siblings if not r.get("resolved")]
    recurring = len(siblings) >= 3
    findings = (f"incident #{target.get('id')} [{target.get('severity')}] på {cluster}/{nerve}: "
                f"{(target.get('message') or '')[:200]}. Mønster: {len(siblings)} incident(er) på "
                f"samme nerve ({len(unresolved_sib)} uløste).")
    if recurring:
        probable = f"tilbagevendende fejl på {cluster}/{nerve} — systemisk, ikke enkeltstående"
        recommendation = (f"grav i {nerve}-nerven: den fejler gentaget. Overvej kirurgisk forslag "
                          f"via central_surgery på den ansvarlige kode-sti.")
    else:
        probable = f"enkeltstående {target.get('severity')}-hændelse på {cluster}/{nerve}"
        recommendation = f"verificér {nerve} én gang; hvis ikke reproducerbar → resolve incident."
    try:
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                """INSERT INTO central_rca
                   (incident_id, cluster, nerve, findings, probable_cause, recommendation, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'draft', ?)""",
                (int(target.get("id") or 0), cluster, nerve, findings, probable, recommendation, _now()))
            rid = int(cur.lastrowid)
            conn.commit()
        _observe("investigated", {"rca_id": rid, "incident_id": int(target.get("id") or 0),
                                  "recurring": recurring})
        return {"ok": True, "rca_id": rid, "incident_id": int(target.get("id") or 0),
                "cluster": cluster, "nerve": nerve, "findings": findings,
                "probable_cause": probable, "recommendation": recommendation, "recurring": recurring}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def list_rca(*, limit: int = 20) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure(conn)
            return [dict(r) for r in conn.execute(
                "SELECT * FROM central_rca ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
    except Exception:
        return []


def build_rca_surface() -> dict[str, Any]:
    """Uløste incidents + næste at grave i + seneste RCA'er + følt linje. Self-safe."""
    try:
        from core.runtime.db_central_incidents import count_unresolved
        unresolved = count_unresolved()
    except Exception:
        unresolved = 0
    nxt = pick_incident()
    rcas = list_rca(limit=10)
    if nxt:
        felt = (f"{unresolved} uløste — næste jeg vil grave i: #{nxt.get('id')} på "
                f"{nxt.get('cluster')}/{nxt.get('nerve')}. Én til bunds, ikke fem halve.")
    else:
        felt = "Ingen uløste incidents — intet at diagnosticere lige nu."
    return {"unresolved": unresolved, "next_incident": nxt, "recent_rca": rcas, "felt": felt}


def recurring_nerves(*, min_unresolved: int = 3, limit: int = 5) -> list[dict[str, Any]]:
    """Nerver hvor den SAMME fejl er uløst flere gange — systemisk, ikke enkeltstaaende. READ-ONLY.

    (13/11-2026) Maalt: 15 uloeste incidents, hvoraf 6 laa paa `proactivity/verification`
    og 4 paa `privacy/cross_user_share`. `pick_incident()` valgte ÉN og kiggede aldrig
    paa at de øvrige var samme fejl — saa hver undersøgelse startede forfra.
    """
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        rows = list_central_incidents(limit=200, unresolved_only=True)
    except Exception as exc:
        logger.warning("rca: kunne ikke hente incidents: %s", exc)
        return []
    agg: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        agg.setdefault((str(r.get("cluster") or ""), str(r.get("nerve") or "")), []).append(r)
    out: list[dict[str, Any]] = []
    for (cluster, nerve), group in agg.items():
        if len(group) < int(min_unresolved):
            continue
        out.append({
            "cluster": cluster,
            "nerve": nerve,
            "unresolved": len(group),
            "oldest_id": min(int(r.get("id") or 0) for r in group),
            "severity": max(
                (str(r.get("severity") or "") for r in group),
                key=lambda s: _SEVERITY_RANK.get(s, 0),
            ),
            "message": str(group[0].get("message") or "")[:160],
        })
    out.sort(key=lambda d: (-int(d["unresolved"]), -_SEVERITY_RANK.get(str(d["severity"]), 0)))
    return out[:limit]


def record_rca(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: observér uløst-antal + næste-mål — og lad et GENTAGET mønster lande.

    (13/11-2026) Produceren observerede kun metadata: 15 uløste, 6 af dem paa samme
    nerve, og intet fulgte. En nerve der fejler seks gange er ikke seks hændelser —
    det er én systemisk fejl. Den lander nu som en bindende forpligtelse, og
    `evidence` bærer de maalte tal saa stoej-vetoet ikke doemmer et MAALT fund
    som stoej (det veto er bygget til FORMULEREDE moenstre, ikke til maalinger).

    Investigerer stadig IKKE automatisk — at grave er en bevidst handling.
    """
    surf = build_rca_surface()
    _observe("pending", {"unresolved": surf["unresolved"], "has_next": bool(surf["next_incident"])})
    out: dict[str, object] = {"status": "ok", "unresolved": surf["unresolved"]}
    rec = recurring_nerves()
    if rec:
        top = rec[0]
        try:
            from core.services.central_consequence import land_decision
            out["landing"] = land_decision(
                "rca",
                (f"Grav i {top['cluster']}/{top['nerve']} — "
                 f"{top['unresolved']} uløste incidents paa samme nerve"),
                subject=f"recurring:{top['cluster']}/{top['nerve']}",
                rationale=(f"Den samme fejl er uløst {top['unresolved']} gange paa "
                           f"{top['cluster']}/{top['nerve']}. Det er ikke {top['unresolved']} "
                           f"hændelser, det er én systemisk fejl der gentager sig mens "
                           f"incident-listen vokser. Seneste: {top['message']}"),
                trigger_cue="naar en nerve har flere uloeste incidents end én",
                priority=60,
                evidence=(f"uloeste={top['unresolved']} severity={top['severity']} "
                          f"incidenter_i_alt={surf['unresolved']}"),
                evidence_source="central_rca.recurring_nerves",
            )
        except Exception as exc:
            logger.warning("rca: kunne ikke lande gentaget moenster: %s", exc)
    return out
