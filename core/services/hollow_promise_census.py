"""Optælling af tomme løfter — så Centralen kan SE Jarvis' værste mønster.

Bjørn 5/9-2026: «Centralen skal kunne tælle de tomme løfter.» Indtil nu kunne
den kun se `empty_completion/silent_cutoff` — «tur UDEN svar». Men det Bjørn
faktisk oplever er en tur MED et svar, der annoncerer et skridt og stopper før
det tages. Den dag registrerede Centralen ÉN hændelse mod ~29 tomme ture.

To kilder, med vilje:

1. **Værnets egne hændelser** (`runtime.hollow_promise_detected/_outcome`) —
   hvad der blev GREBET, og om nudget virkede.
2. **Folketællingen** (denne fil) — den ÆGTE rate, målt uafhængigt af værnet
   ved at sammenholde `chat_messages` med `visible_runs`. En tur tæller som tom
   hvis der ikke blev kaldt ét eneste værktøj mellem brugerens besked og svaret,
   OG svaret lover en handling.

Forskellen mellem de to ER tallet der betyder noget: **hvor mange slap forbi
værnet.** Et værn der fanger 8 af 29 ser perfekt ud hvis man kun tæller sine
egne fangster.

Ingen ny sandhed opfindes — begge tabeller findes i forvejen (Eventbus-reglen:
Centralen læser projektioner, den opfinder ikke en anden sandhed).

Selv-sikker: enhver fejl → tomt resultat, aldrig en exception opad.
"""
from __future__ import annotations

from typing import Any

from core.runtime.db_core import connect

# `chat_messages` har intet run_id, så beskeden knyttes til det run hvis levetid
# den falder indenfor. Det SKAL være en skalar-underforespørgsel og ikke et JOIN:
# runs overlapper i tid, og et JOIN matchede så samme besked mod flere runs —
# første kørsel gav 1.959 «ture» hvor der var nogle få snese. `ORDER BY
# started_at DESC LIMIT 1` vælger det run der var i gang, og giver præcis én
# række pr. svar.
_MODEL_FOR_MSG = """(
    SELECT r.model FROM visible_runs r
    WHERE m.created_at BETWEEN r.started_at AND r.finished_at
    ORDER BY r.started_at DESC LIMIT 1)"""

# Blev der kaldt ét eneste værktøj mellem brugerens besked og dette svar?
_TOOLS_SINCE_USER = """(
    SELECT COUNT(*) FROM chat_messages t
    WHERE t.session_id = m.session_id AND t.role = 'tool'
      AND t.created_at > (
            SELECT MAX(u.created_at) FROM chat_messages u
            WHERE u.session_id = m.session_id AND u.role = 'user'
              AND u.created_at < m.created_at)
      AND t.created_at < m.created_at)"""

_CENSUS_SQL = f"""
SELECT {_MODEL_FOR_MSG} AS model,
       COUNT(*) AS ture,
       SUM(CASE WHEN {_TOOLS_SINCE_USER} = 0 THEN 1 ELSE 0 END) AS uden_vaerktoej
FROM chat_messages m
WHERE m.role = 'assistant' AND m.created_at >= ? AND model IS NOT NULL
GROUP BY model
ORDER BY ture DESC
"""

_TOOLLESS_TEXTS_SQL = f"""
SELECT {_MODEL_FOR_MSG} AS model, m.content AS content
FROM chat_messages m
WHERE m.role = 'assistant' AND m.created_at >= ? AND model IS NOT NULL
  AND {_TOOLS_SINCE_USER} = 0
"""


def _since(hours: int) -> str:
    """ISO-UTC-grænse. DB'en gemmer `2026-09-05T16:20:19.213749+00:00`, så en
    ren `datetime('now')`-sammenligning rammer ved siden af — den fælde har
    kostet en hel fejlkonklusion før (se hukommelsen om query-fælden)."""
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC) - timedelta(hours=max(int(hours), 1))).isoformat()


def census(hours: int = 24) -> dict[str, Any]:
    """Den ægte rate pr. model + hvor meget værnet fangede. Self-safe."""
    try:
        from core.services.hollow_promise_guard import is_promise_of_action
    except Exception:
        return {"models": [], "window_hours": int(hours), "available": False}

    grænse = _since(hours)
    pr_model: dict[str, dict[str, int]] = {}
    try:
        with connect() as conn:
            for model, ture, uden in conn.execute(_CENSUS_SQL, (grænse,)):
                pr_model[str(model or "?")] = {
                    "turns": int(ture or 0),
                    "toolless": int(uden or 0),
                    "hollow": 0,
                }
            # Løfte-filteret kan ikke udtrykkes i SQL — teksten skal gennem
            # mønstret. Kun de værktøjsløse ture hentes, så det er en lille mængde.
            for model, content in conn.execute(_TOOLLESS_TEXTS_SQL, (grænse,)):
                nøgle = str(model or "?")
                if nøgle in pr_model and is_promise_of_action(str(content or "")):
                    pr_model[nøgle]["hollow"] += 1
    except Exception:
        return {"models": [], "window_hours": int(hours), "available": False}

    modeller = []
    for navn, tal in sorted(pr_model.items(), key=lambda kv: -kv[1]["turns"]):
        ture = tal["turns"] or 1
        modeller.append({
            "model": navn,
            "turns": tal["turns"],
            "hollow": tal["hollow"],
            "hollow_pct": round(100.0 * tal["hollow"] / ture, 1),
        })

    grebet = _guard_counts(grænse)
    tomme = sum(m["hollow"] for m in modeller)
    return {
        "available": True,
        "window_hours": int(hours),
        "models": modeller,
        "hollow_total": tomme,
        "guard_detected": grebet["detected"],
        "guard_resolved": grebet["resolved"],
        # Tallet der betyder noget: hvor mange slap forbi værnet.
        "escaped": max(tomme - grebet["detected"], 0),
    }


def _guard_counts(grænse: str) -> dict[str, int]:
    """Hvad værnet selv greb, fra dets egne events. Self-safe."""
    ud = {"detected": 0, "resolved": 0}
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind = "
                "'runtime.hollow_promise_detected' AND created_at >= ?", (grænse,)
            ).fetchone()
            ud["detected"] = int((row or [0])[0] or 0)
            row = conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind = "
                "'runtime.hollow_promise_outcome' AND created_at >= ? "
                "AND payload_json LIKE '%\"resolved\": true%'", (grænse,)
            ).fetchone()
            ud["resolved"] = int((row or [0])[0] or 0)
    except Exception:
        pass
    return ud
