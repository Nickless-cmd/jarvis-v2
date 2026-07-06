"""Autonome sessioner — rotér pr. oprindelse+dag, og gør historien synlig.

FØR: alle autonome runs (drømme, råd, arbejde, outreach, recurring, heartbeat …)
funnelede via ``start_autonomous_run(session_id=None)`` ind i ÉN udødelig session med
titlen "Autonomous". Den voksede 100-175 beskeder/dag, roterede aldrig, og ramte
kontekst-vinduet (25 ægte API-fejl) fordi hver run genindlæste hele historikken. Ingen
— hverken Bjørn, Jarvis i sine aktive sessioner, eller Centralen — så den historie.

NU: hver autonom run får en session bestemt af (oprindelse, dag) med et deterministisk id
``auto-{origin}-{YYYYMMDD}``. Konteksten forbliver afgrænset (én dags aktivitet pr.
oprindelse) → kontekst-fejlene forsvinder, OG historien bliver læsbar + kategoriseret.
``build_autonomous_history_surface`` projicerer strømmen så Centralen (og Central-CLI)
kan vise den — egress-frit: tællere + titler + fejl-antal, aldrig råt privat indhold.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# Kanoniske oprindelser. Ny oprindelse? Tilføj her (fallback = "autonomous").
ORIGINS: tuple[str, ...] = (
    "dream", "council", "work", "outreach",
    "recurring", "heartbeat", "scheduled", "wakeup", "autonomous",
)

_LABELS = {
    "dream": "Drømme", "council": "Råd", "work": "Arbejde", "outreach": "Outreach",
    "recurring": "Tilbagevendende", "heartbeat": "Hjerteslag", "scheduled": "Planlagt",
    "wakeup": "Vækning", "autonomous": "Autonom",
}

_SESSION_PREFIX = "auto-"


def normalize_origin(origin: str | None) -> str:
    o = (origin or "").strip().lower()
    return o if o in ORIGINS else "autonomous"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y%m%d")


def resolve_autonomous_session(origin: str | None) -> str:
    """Returnér (opret idempotent) sessionen for (oprindelse, i dag).

    Deterministisk id ``auto-{origin}-{YYYYMMDD}`` → race-fri på tværs af processer,
    ingen O(n)-scan af alle sessioner. Self-safe.
    """
    o = normalize_origin(origin)
    day = _today()
    session_id = f"{_SESSION_PREFIX}{o}-{day}"
    label = _LABELS.get(o, o.capitalize())
    iso_day = f"{day[:4]}-{day[4:6]}-{day[6:]}"
    title = f"Autonom · {label} · {iso_day}"
    try:
        from core.services.chat_sessions import get_or_create_named_session
        return get_or_create_named_session(session_id, title)
    except Exception:
        return session_id


def _origin_of_session(session_id: str) -> str:
    """Udled oprindelse fra et ``auto-{origin}-{dato}``-id."""
    if not session_id.startswith(_SESSION_PREFIX):
        return "autonomous"
    rest = session_id[len(_SESSION_PREFIX):]
    # split fra højre: sidste segment = dato, resten = origin (origin har ingen '-')
    parts = rest.rsplit("-", 1)
    return normalize_origin(parts[0] if parts else "")


def build_autonomous_history_surface(*, days: int = 7, per_origin_limit: int = 5) -> dict[str, Any]:
    """Projicér den autonome historie for owner-visning (§24.4-sikker).

    Grupperer roterende autonome sessioner pr. oprindelse med: antal sessioner, samlet
    besked-antal, seneste aktivitet, og ANTAL kontekst-vindue-fejl (liveness-signal — at
    en oprindelse rammer væggen). Returnerer titler + tællere, ALDRIG råt beskedindhold.
    Self-safe → tom struktur ved fejl.
    """
    out: dict[str, Any] = {"origins": {}, "total_sessions": 0, "total_messages": 0,
                           "total_context_errors": 0}
    try:
        from core.runtime.db_core import connect
        cutoff = datetime.now(UTC).timestamp() - days * 86400
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT cs.session_id, cs.title, cs.updated_at,
                       COUNT(cm.id) AS msgs,
                       SUM(CASE WHEN cm.role='assistant' AND (
                            cm.content LIKE '%prompt is too long%'
                         OR cm.content LIKE '%maximum context%'
                         OR cm.content LIKE '%context_length_exceeded%'
                         OR cm.content LIKE '%exceeds%context%') THEN 1 ELSE 0 END) AS ctx_err
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cm.session_id = cs.session_id
                WHERE cs.session_id LIKE ?
                GROUP BY cs.session_id
                ORDER BY cs.updated_at DESC
                """,
                (f"{_SESSION_PREFIX}%",),
            ).fetchall()
    except Exception:
        return out

    for r in rows:
        sid = r["session_id"]
        # dato-suffix filtrering til seneste `days`
        try:
            day = sid.rsplit("-", 1)[-1]
            ts = datetime.strptime(day, "%Y%m%d").replace(tzinfo=UTC).timestamp()
            if ts < cutoff - 86400:
                continue
        except Exception:
            pass
        origin = _origin_of_session(sid)
        bucket = out["origins"].setdefault(
            origin, {"label": _LABELS.get(origin, origin), "sessions": 0,
                     "messages": 0, "context_errors": 0, "last_active": "", "recent": []}
        )
        msgs = int(r["msgs"] or 0)
        errs = int(r["ctx_err"] or 0)
        bucket["sessions"] += 1
        bucket["messages"] += msgs
        bucket["context_errors"] += errs
        if (r["updated_at"] or "") > bucket["last_active"]:
            bucket["last_active"] = r["updated_at"] or ""
        if len(bucket["recent"]) < per_origin_limit:
            bucket["recent"].append(
                {"session_id": sid, "title": r["title"], "messages": msgs,
                 "context_errors": errs, "updated_at": r["updated_at"]}
            )
        out["total_sessions"] += 1
        out["total_messages"] += msgs
        out["total_context_errors"] += errs
    return out
