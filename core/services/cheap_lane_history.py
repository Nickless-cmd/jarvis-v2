"""Hvordan klarer cheap lane sig? — historikken bag de 90.000 kald.

## Hvorfor den findes (16/9-2026)

Bjoern: «jeg ander intet om hvordan cheap lane eller load_balanceren klarer
sig». Og han kunne ikke vide det. Hvert eneste kald er bogfoert i
`cheap_provider_invocations` med udfald, fejlkode, latens, tokens og pris —
90.498 raekker siden 26/8 — og INTET endepunkt viste dem. Balancerens egen
flade (`balancer_snapshot`) viser kun NU: hvilke slots er i koeling, hvad er
vaegten lige i dette oejeblik. Den kan ikke svare paa «har den her udbyder
nogensinde virket» eller «hvad fejler mest».

Maalt paa hele bordet foerste gang det blev laest: 61.629 gennemfoerte og
28.869 fejlede kald — 32 % fejl. Det tal har staaet i basen i tre uger.

## Hvorfor aggregeringen sker i SQL

En flade der henter 90.000 raekker og taeller i Python bliver enten langsom
eller klippet med `limit` — og et `limit`-vindue der skjuler halen er en fejl
huset har lavet tre gange. SQL taeller HELE vinduet og returnerer én raekke pr.
udbyder.

## Ordforklaring

* **succesrate** — andel `completed` af alle kald i vinduet. `None` naar der
  ingen kald er; «ingen data» og «nul procent» er to forskellige beskeder.
* **p50/p95 latens** — kun paa gennemfoerte kald. En fejl der fejler hurtigt
  ville ellers pynte paa tallet.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

#: Standardvinduet. Et doegn daekker en nat med hjerteslag og en dag med brug.
STANDARD_TIMER = 24

#: Loft paa raa fejl-lister. Fejlene selv taelles i SQL, saa loftet klipper kun
#: den viste hale, ikke tallene.
FEJL_LOFT = 100


def _siden(timer: float) -> str:
    return (datetime.now(UTC) - timedelta(hours=float(timer))).isoformat()


def _sikr_skema(conn) -> None:
    """Tabellen og dens `auth_profile`-kolonne skal findes, ogsaa foer foerste kald.

    Skriveren (`record_cheap_provider_invocation`) laver begge dele undervejs, saa
    i drift er de der. Men en LAESE-flade maa ikke vaelte paa en frisk database —
    foerste udgave gjorde netop det: «no such column: auth_profile».
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cheap_provider_invocations ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, lane TEXT NOT NULL DEFAULT 'cheap', "
        "provider TEXT NOT NULL, model TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, "
        "error_code TEXT NOT NULL DEFAULT '', error_message TEXT NOT NULL DEFAULT '', "
        "retry_after_seconds INTEGER NOT NULL DEFAULT 0, latency_ms INTEGER NOT NULL DEFAULT 0, "
        "input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0, "
        "cost_usd REAL NOT NULL DEFAULT 0, auth_profile TEXT NOT NULL DEFAULT '', "
        "created_at TEXT NOT NULL)"
    )
    try:
        conn.execute("ALTER TABLE cheap_provider_invocations "
                     "ADD COLUMN auth_profile TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass        # kolonnen er der allerede — det normale


def _rows(sql: str, params: tuple) -> list[dict[str, Any]]:
    from core.runtime.db import connect
    with connect() as conn:
        _sikr_skema(conn)
        raekker = conn.execute(sql, params).fetchall()
    return [dict(r) for r in raekker]


def _percentil(vaerdier: list[int], p: float) -> int:
    """p50/p95 uden numpy. Tom liste → 0."""
    if not vaerdier:
        return 0
    s = sorted(vaerdier)
    i = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return int(s[i])


def udbyder_historik(timer: float = STANDARD_TIMER, lane: str = "cheap") -> dict[str, Any]:
    """Én raekke pr. (udbyder, model) i vinduet: kald, fejl, latens, pris.

    Rækkefoelgen er flest kald foerst — det er dér pengene og fejlene er.
    """
    siden = _siden(timer)
    try:
        raekker = _rows(
            """
            SELECT provider, model, auth_profile,
                   COUNT(*)                                         AS kald,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS ok,
                   SUM(CASE WHEN status <> 'completed' THEN 1 ELSE 0 END) AS fejl,
                   SUM(cost_usd)                                    AS pris,
                   SUM(input_tokens)                                AS ind,
                   SUM(output_tokens)                               AS ud,
                   MAX(created_at)                                  AS sidst,
                   MAX(CASE WHEN status = 'completed' THEN created_at END) AS sidst_ok
            FROM cheap_provider_invocations
            WHERE lane = ? AND created_at >= ?
            GROUP BY provider, model, auth_profile
            ORDER BY kald DESC
            """,
            (lane, siden),
        )
    except Exception as exc:
        logger.warning("cheap_lane_history: opslaget fejlede: %s", exc, exc_info=True)
        return {"aktiv": False, "fejl": str(exc)[:200], "timer": timer, "udbydere": []}

    # Latenser hentes samlet og fordeles — ét opslag frem for ét pr. udbyder.
    lat: dict[tuple[str, str], list[int]] = {}
    try:
        for r in _rows(
            "SELECT provider, model, latency_ms FROM cheap_provider_invocations "
            "WHERE lane = ? AND created_at >= ? AND status = 'completed' AND latency_ms > 0",
            (lane, siden),
        ):
            lat.setdefault((str(r["provider"]), str(r["model"])), []).append(int(r["latency_ms"]))
    except Exception:
        logger.debug("cheap_lane_history: latens-opslag fejlede", exc_info=True)

    fejlkoder = _fejlkoder_pr_udbyder(lane, siden)

    ud: list[dict[str, Any]] = []
    for r in raekker:
        n = int(r["kald"] or 0)
        navn = (str(r["provider"]), str(r["model"]))
        latenser = lat.get(navn, [])
        ud.append({
            "provider": r["provider"],
            "model": r["model"],
            "auth_profile": r["auth_profile"],
            "kald": n,
            "ok": int(r["ok"] or 0),
            "fejl": int(r["fejl"] or 0),
            # «Ingen data» er ikke «nul procent» — samme regel som resten af huset.
            "succesrate": round(int(r["ok"] or 0) / n, 4) if n else None,
            "latens_p50_ms": _percentil(latenser, 50),
            "latens_p95_ms": _percentil(latenser, 95),
            "pris_usd": round(float(r["pris"] or 0.0), 6),
            "input_tokens": int(r["ind"] or 0),
            "output_tokens": int(r["ud"] or 0),
            "sidste_kald": r["sidst"],
            "sidste_ok": r["sidst_ok"],
            "fejlkoder": fejlkoder.get(navn, []),
        })

    samlet_kald = sum(u["kald"] for u in ud)
    samlet_ok = sum(u["ok"] for u in ud)
    return {
        "aktiv": True,
        "timer": timer,
        "lane": lane,
        "siden": siden,
        "udbydere": ud,
        "opsummering": {
            "kald": samlet_kald,
            "ok": samlet_ok,
            "fejl": samlet_kald - samlet_ok,
            "succesrate": round(samlet_ok / samlet_kald, 4) if samlet_kald else None,
            "pris_usd": round(sum(u["pris_usd"] for u in ud), 6),
            "udbydere": len({u["provider"] for u in ud}),
        },
    }


def _fejlkoder_pr_udbyder(lane: str, siden: str) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """De hyppigste fejlkoder pr. (udbyder, model). Tomt ved fejl."""
    try:
        raekker = _rows(
            "SELECT provider, model, error_code, COUNT(*) AS n FROM cheap_provider_invocations "
            "WHERE lane = ? AND created_at >= ? AND status <> 'completed' AND error_code <> '' "
            "GROUP BY provider, model, error_code ORDER BY n DESC",
            (lane, siden),
        )
    except Exception:
        logger.debug("cheap_lane_history: fejlkode-opslag fejlede", exc_info=True)
        return {}
    ud: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in raekker:
        noegle = (str(r["provider"]), str(r["model"]))
        if len(ud.setdefault(noegle, [])) < 5:
            ud[noegle].append({"kode": r["error_code"], "antal": int(r["n"] or 0)})
    return ud


def seneste_fejl(timer: float = STANDARD_TIMER, lane: str = "cheap",
                 loft: int = FEJL_LOFT) -> dict[str, Any]:
    """De nyeste fejl med besked — halen man skal laese naar noget er galt.

    `antal_i_vinduet` taelles SEPARAT i SQL, saa loftet aldrig kan forveksles
    med «saa mange fejl er der» (limit-faelden, tredje gang i huset).
    """
    siden = _siden(timer)
    try:
        raekker = _rows(
            "SELECT provider, model, auth_profile, error_code, error_message, "
            "       retry_after_seconds, latency_ms, created_at "
            "FROM cheap_provider_invocations "
            "WHERE lane = ? AND created_at >= ? AND status <> 'completed' "
            "ORDER BY created_at DESC LIMIT ?",
            (lane, siden, int(loft)),
        )
        i_alt = _rows(
            "SELECT COUNT(*) AS n FROM cheap_provider_invocations "
            "WHERE lane = ? AND created_at >= ? AND status <> 'completed'",
            (lane, siden),
        )
    except Exception as exc:
        logger.warning("cheap_lane_history: fejl-opslag fejlede: %s", exc, exc_info=True)
        return {"aktiv": False, "fejl": str(exc)[:200], "raekker": [], "antal_i_vinduet": 0}
    return {
        "aktiv": True,
        "timer": timer,
        "raekker": raekker,
        "vist": len(raekker),
        "antal_i_vinduet": int(i_alt[0]["n"]) if i_alt else 0,
    }


def tidsserie(timer: float = STANDARD_TIMER, lane: str = "cheap",
              spand_minutter: int = 60) -> dict[str, Any]:
    """Kald og fejl pr. tidsspand — kurven bag «klarer den sig bedre i dag?».

    Spandene laves i SQL med `strftime`, saa hele vinduet taelles. Tomme spand
    udelades; en kurve skal ikke opfinde nuller den ikke har maalt.
    """
    siden = _siden(timer)
    minutter = max(5, int(spand_minutter))
    try:
        raekker = _rows(
            f"""
            SELECT strftime('%Y-%m-%dT%H:%M', created_at,
                            '-' || (CAST(strftime('%M', created_at) AS INTEGER) % {minutter})
                            || ' minutes') AS spand,
                   COUNT(*) AS kald,
                   SUM(CASE WHEN status <> 'completed' THEN 1 ELSE 0 END) AS fejl,
                   AVG(CASE WHEN status = 'completed' AND latency_ms > 0
                            THEN latency_ms END) AS latens
            FROM cheap_provider_invocations
            WHERE lane = ? AND created_at >= ?
            GROUP BY spand
            ORDER BY spand
            """,
            (lane, siden),
        )
    except Exception as exc:
        logger.warning("cheap_lane_history: tidsserie fejlede: %s", exc, exc_info=True)
        return {"aktiv": False, "fejl": str(exc)[:200], "spand": []}
    return {
        "aktiv": True,
        "timer": timer,
        "spand_minutter": minutter,
        "spand": [{
            "tid": r["spand"],
            "kald": int(r["kald"] or 0),
            "fejl": int(r["fejl"] or 0),
            "latens_ms": int(r["latens"]) if r["latens"] else 0,
        } for r in raekker],
    }
