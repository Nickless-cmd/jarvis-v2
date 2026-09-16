"""Agent-puljen — en LET liste man kan filtrere i.

## Hvorfor den findes (16/9-2026)

`build_agent_runtime_surface()` henter alle agenter op til `limit` og beriger
HVER af dem med fire ekstra opslag (koersler, beskeder, vaerktoejskald,
planer). Det er den rigtige form naar man kigger paa ÉN agent, og den forkerte
naar man vil se listen: 306 agenter i drift bliver til over tolvhundrede
forespoergsler, og den har hverken filter eller sideinddeling.

Denne flade svarer paa det foerste spoergsmaal — «hvem findes, hvad laver de,
hvad kostede de» — med ét opslag. Detaljen ligger stadig i
`/mc/agents/{id}`, hvor berigelsen hoerer hjemme.

## Hvad en agent «laver» kan man kun se ét sted

`agent_tool_calls` er TOM i drift (0 raekker), saa en «hvilke vaerktoejer
brugte den»-visning ville vaere et tomt loefte. Det naermeste sande er
`agent_runs`: udfald, model, ind/ud-tokens, pris og et resumé pr. koersel.
Derfor er det dem listen samler op.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

#: Statusser der betyder «i gang». Samme saet som `agent_runtime_surfaces`
#: bruger, saa de to flader ikke kan blive uenige om hvad aktiv betyder.
AKTIVE = ("queued", "starting", "active", "waiting", "blocked", "scheduled")

STANDARD_LOFT = 50


def _rows(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    from core.runtime.db import connect
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def agent_liste(*, status: str = "", rolle: str = "", soeg: str = "",
                limit: int = STANDARD_LOFT, offset: int = 0) -> dict[str, Any]:
    """Agenterne med deres koersels-tal. Ét opslag, filtrerbart, sideinddelt.

    `i_alt` taelles SEPARAT fra `limit`. Et loft der ligner et facit har kostet
    huset tre forkerte konklusioner; her staar begge tal ved siden af hinanden.
    """
    hvor: list[str] = []
    p: list[Any] = []
    if status == "aktive":
        hvor.append(f"a.status IN ({','.join('?' * len(AKTIVE))})")
        p.extend(AKTIVE)
    elif status:
        hvor.append("a.status = ?")
        p.append(status)
    if rolle:
        hvor.append("a.role = ?")
        p.append(rolle)
    if soeg:
        hvor.append("(a.goal LIKE ? OR a.agent_id LIKE ? OR a.role LIKE ?)")
        p.extend([f"%{soeg}%"] * 3)
    betingelse = (" WHERE " + " AND ".join(hvor)) if hvor else ""

    try:
        i_alt = _rows(f"SELECT COUNT(*) AS n FROM agent_registry a{betingelse}", tuple(p))
        raekker = _rows(
            f"""
            SELECT a.agent_id, a.parent_agent_id, a.council_id, a.kind, a.role, a.goal,
                   a.status, a.lane, a.provider, a.model, a.persistent,
                   a.tokens_burned, a.failure_count, a.last_error,
                   a.created_at, a.updated_at, a.completed_at,
                   (SELECT COUNT(*) FROM agent_runs r WHERE r.agent_id = a.agent_id) AS koersler,
                   (SELECT SUM(COALESCE(r.cost_usd, 0)) FROM agent_runs r
                     WHERE r.agent_id = a.agent_id) AS pris,
                   (SELECT SUM(COALESCE(r.input_tokens, 0) + COALESCE(r.output_tokens, 0))
                      FROM agent_runs r WHERE r.agent_id = a.agent_id) AS tokens,
                   (SELECT r.status FROM agent_runs r WHERE r.agent_id = a.agent_id
                     ORDER BY r.created_at DESC LIMIT 1) AS seneste_udfald,
                   (SELECT r.output_summary FROM agent_runs r WHERE r.agent_id = a.agent_id
                     ORDER BY r.created_at DESC LIMIT 1) AS seneste_resume,
                   (SELECT r.finished_at FROM agent_runs r WHERE r.agent_id = a.agent_id
                     ORDER BY r.created_at DESC LIMIT 1) AS seneste_slut,
                   (SELECT COUNT(*) FROM agent_messages m WHERE m.agent_id = a.agent_id) AS beskeder
            FROM agent_registry a{betingelse}
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (*p, int(limit), int(offset)),
        )
    except Exception as exc:
        logger.warning("agent_pool_surface: listen fejlede: %s", exc, exc_info=True)
        return {"aktiv": False, "fejl": str(exc)[:200], "agenter": [], "i_alt": 0}

    agenter = []
    for r in raekker:
        agenter.append({
            **r,
            "pris_usd": round(float(r.get("pris") or 0.0), 6),
            "tokens": int(r.get("tokens") or 0),
            "koersler": int(r.get("koersler") or 0),
            "beskeder": int(r.get("beskeder") or 0),
            "varighed_s": _varighed(r.get("created_at"), r.get("completed_at")),
            "er_aktiv": str(r.get("status") or "") in AKTIVE,
        })
    return {
        "aktiv": True,
        "agenter": agenter,
        "vist": len(agenter),
        "i_alt": int(i_alt[0]["n"]) if i_alt else 0,
        "offset": int(offset),
        "limit": int(limit),
        "filtre": {"status": status, "rolle": rolle, "soeg": soeg},
    }


def _varighed(start: Any, slut: Any) -> int:
    """Sekunder mellem to tidsstempler. 0 naar vi ikke kan regne det ud.

    Varigheden findes ikke som felt — den skal regnes, og et gaet er ikke et
    tal. Derfor 0 frem for None: fladen viser «–» paa 0.
    """
    try:
        a = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(slut).replace("Z", "+00:00"))
        return max(0, int((b - a).total_seconds()))
    except Exception:
        return 0


def pool_opsummering(timer: float = 24) -> dict[str, Any]:
    """Puljens tilstand: hvor mange, hvilke roller, hvad koster de, hvor er graenserne."""
    siden = (datetime.now(UTC) - timedelta(hours=float(timer))).isoformat()
    try:
        pr_status = {str(r["status"]): int(r["n"]) for r in _rows(
            "SELECT status, COUNT(*) AS n FROM agent_registry GROUP BY status")}
        pr_rolle = [{"rolle": r["role"], "antal": int(r["n"])} for r in _rows(
            "SELECT role, COUNT(*) AS n FROM agent_registry GROUP BY role ORDER BY n DESC LIMIT 12")]
        vindue = _rows(
            "SELECT COUNT(*) AS koersler, "
            "       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS fejlede, "
            "       SUM(COALESCE(cost_usd, 0)) AS pris, "
            "       SUM(COALESCE(input_tokens,0) + COALESCE(output_tokens,0)) AS tokens "
            "FROM agent_runs WHERE created_at >= ?", (siden,))
        raad = _rows("SELECT status, COUNT(*) AS n FROM council_sessions GROUP BY status")
    except Exception as exc:
        # SAMME FORM, ogsaa naar det gaar galt. Foerste udgave returnerede en
        # kortere dict, og en klient der laeste `vindue` vaeltede paa en frisk
        # database hvor tabellerne ikke findes endnu. En flade maa aendre
        # TALLENE, ikke formen.
        logger.warning("agent_pool_surface: opsummering fejlede: %s", exc, exc_info=True)
        return {"aktiv": False, "fejl": str(exc)[:200], "timer": timer,
                "agenter_i_alt": 0, "pr_status": {}, "aktive_nu": 0, "pr_rolle": [],
                "vindue": {"koersler": 0, "fejlede": 0, "fejlrate": None,
                           "pris_usd": 0.0, "tokens": 0},
                "raad": {}, "graenser": {}}

    v = vindue[0] if vindue else {}
    koersler = int(v.get("koersler") or 0)
    aktive = sum(n for s, n in pr_status.items() if s in AKTIVE)
    try:
        from core.services.agent_runtime_base import MAX_CONCURRENT_AGENTS, MAX_SPAWN_DEPTH
        graenser = {"samtidige": int(MAX_CONCURRENT_AGENTS), "dybde": int(MAX_SPAWN_DEPTH)}
    except Exception:
        graenser = {}

    return {
        "aktiv": True,
        "timer": timer,
        "agenter_i_alt": sum(pr_status.values()),
        "pr_status": pr_status,
        "aktive_nu": aktive,
        "pr_rolle": pr_rolle,
        "vindue": {
            "koersler": koersler,
            "fejlede": int(v.get("fejlede") or 0),
            # «Ingen koersler» og «nul procent fejl» er to forskellige beskeder.
            "fejlrate": round(int(v.get("fejlede") or 0) / koersler, 4) if koersler else None,
            "pris_usd": round(float(v.get("pris") or 0.0), 6),
            "tokens": int(v.get("tokens") or 0),
        },
        "raad": {str(r["status"]): int(r["n"]) for r in raad},
        "graenser": graenser,
    }


def seneste_arbejde(limit: int = 30) -> dict[str, Any]:
    """De nyeste koersler paa tvaers af agenter — «hvad sker der lige nu».

    `agent_runs` er den eneste kilde der faktisk er fyldt: `agent_tool_calls`
    staar tom i drift, saa en vaerktoejs-visning ville vaere et tomt loefte.
    """
    try:
        raekker = _rows(
            """
            SELECT r.run_id, r.agent_id, r.status, r.execution_mode, r.provider, r.model,
                   r.input_summary, r.output_summary, r.failure_reason,
                   r.started_at, r.finished_at, r.input_tokens, r.output_tokens, r.cost_usd,
                   a.role, a.kind, a.goal
            FROM agent_runs r LEFT JOIN agent_registry a ON a.agent_id = r.agent_id
            ORDER BY r.created_at DESC LIMIT ?
            """,
            (int(limit),),
        )
    except Exception as exc:
        logger.warning("agent_pool_surface: seneste arbejde fejlede: %s", exc, exc_info=True)
        return {"aktiv": False, "fejl": str(exc)[:200], "koersler": []}
    for r in raekker:
        r["varighed_s"] = _varighed(r.get("started_at"), r.get("finished_at"))
    return {"aktiv": True, "koersler": raekker}
