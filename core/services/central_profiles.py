"""Profil-overfladen til Centralen — Fase 9.

Exit-kriteriet i spec'en siger «Mission Control explains model, tools,
approval, retry, compaction, memory, private layers, and subagent policy».
Mission Control findes ikke laengere; den blev revet ud, og fladerne er i dag
`central_cli` og desk. Kriteriet oversaettes derfor til: **den flade der
findes** skal kunne forklare det.

## Hvad «forklare» betyder her

Ikke at vise et profilnavn. Et navn er netop det man ikke kan efterproeve —
profiler aendrer sig, og en koersel fra i gaar koerte under gaarsdagens udgave.
Overfladen viser derfor tre ting sammen:

  * de syv profiler som de ser ud NU, med hver akse udskrevet
  * hvad de seneste koersler FAKTISK koerte under (navn + hash fra raekken)
  * om de to stemmer overens

Det sidste er pointen. Staar der en hash paa en koersel som ingen nulevende
profil har, er profilen aendret siden — og det er praecis det man vil vide, naar
man undersoeger hvorfor noget gik galt i forgaars.
"""
from __future__ import annotations

from typing import Any

#: De felter kriteriet naevner. Model haandteres for sig: den hoerer til
#: koerslen, ikke til profilen — samme profil kan koere paa flere modeller.
FORKLAREDE_FELTER: tuple[str, ...] = (
    "tool_scope", "approval_mode", "sandbox",
    "cross_session_context", "telemetry_sharing",
    "retry", "compaction", "memory", "private_layers", "subagents",
)


def _profil_rækker() -> list[dict[str, Any]]:
    from core.runtime.profiles import byg, kendte
    ud: list[dict[str, Any]] = []
    for navn in kendte():
        p = byg(navn)
        ud.append({
            "navn": navn,
            "hash": p.hash,
            "skema_version": p.skema_version,
            **{f: p.felter.get(f) for f in FORKLAREDE_FELTER},
            # Kriterium 7. Uden disse to viser fladen kun hvad profilen
            # OENSKER — og fire af de syv oensker en kryds-session-begraensning
            # som (maalt 13/9-2026) ingen haandhaever. En flade der kun viser
            # oensket ville tegne en graense der ikke findes.
            "haandhaevelse": p.haandhaevelse(),
            "afvigelser": p.afvigelser(),
        })
    return ud


def _seneste_kørsler(graense: int = 20) -> list[dict[str, Any]]:
    """Hvad koerslerne FAKTISK koerte under. Tom liste hvis kolonnerne ikke
    findes endnu — en database der ikke har naaet migrationen er ikke en fejl."""
    try:
        from core.runtime.db import connect
    except Exception:
        return []
    try:
        with connect() as conn:
            rækker = conn.execute(
                """
                SELECT run_id, lane, model, status, started_at,
                       profile_name, profile_hash, profile_schema_version
                FROM visible_runs
                WHERE profile_name != ''
                ORDER BY started_at DESC LIMIT ?
                """,
                (int(graense),),
            ).fetchall()
    except Exception:
        return []
    return [
        {
            "run_id": r[0], "lane": r[1], "model": r[2], "status": r[3],
            "started_at": r[4], "profil": r[5], "hash": r[6],
            "skema_version": r[7],
        }
        for r in rækker
    ]


def build_profiles_surface() -> dict[str, Any]:
    """Alt Centralen skal bruge for at kunne forklare en koersels regler."""
    profiler = _profil_rækker()
    kendte_hashes = {p["hash"] for p in profiler}
    kørsler = _seneste_kørsler()
    ukendte = sorted({
        k["hash"] for k in kørsler
        if k.get("hash") and k["hash"] not in kendte_hashes
    })
    return {
        "active": True,
        "skema_version": profiler[0]["skema_version"] if profiler else 0,
        "profiler": profiler,
        "seneste_kørsler": kørsler,
        # Koersler hvis profil ikke laengere findes i den form de koerte under.
        # Ikke en fejl — en oplysning. Den fortaeller at profilen er aendret
        # siden, og at en undersoegelse skal tage hoejde for det.
        "hashes_uden_nulevende_profil": ukendte,
        "forklarede_felter": list(FORKLAREDE_FELTER),
        # Samlet, saa en operatoer ikke skal aabne syv profiler for at se at
        # et loefte ikke holdes nogen steder.
        "uhaandhaevede_akser": sorted({
            a for p in profiler
            for a, v in (p.get("haandhaevelse") or {}).items()
            if not v.get("haandhaevet")
        }),
        "afvigelser_i_alt": sum(len(p.get("afvigelser") or []) for p in profiler),
    }
