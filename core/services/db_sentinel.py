"""DB-cluster — observabilitet + flag for jarvis.db's helbred. IKKE en blokerende gate og
ALDRIG destruktiv: Centralen ser DB'ens struktur + vækst og flagger uregelmæssigheder, men
dropper/ændrer ALDRIG noget selv.

KRITISK SIKKERHEDS-INVARIANT (autoclean = FORESLÅ-til-review, aldrig auto-drop): liveness-
lektien viste at "døde" cognitive_*-tabeller var AFLØST af nyere runtime_*, IKKE døde — en
stille DROP TABLE ville have destrueret levende/genbrugt data. Derfor: tom tabel = KANDIDAT
til menneskelig review, ikke en handling. Intet i dette modul kører DDL/DML.

Phase 1: table-census (row-counts) + vækst-delta vs forrige snapshot + flag EGREGIOUS vækst
(både fordobling OG stor absolut tilvækst → lav false-positive) som incident + kandidat-død-
liste (0 rækker). Self-safe; kaster aldrig.
"""
from __future__ import annotations

from typing import Any

_SNAPSHOT_KEY = "db_sentinel:last_census"
_SNAPSHOT_TTL = 30 * 24 * 3600.0  # 30 dage — overlever lange ophold mellem scans

# Egregious-vækst: en tabel skal BÅDE være vokset stort absolut OG mindst fordoblet, før
# den flagges — så normal organisk vækst ikke spammer incidents. Tærsklerne er bevidst høje.
_GROWTH_ABS = 20000
_GROWTH_FACTOR = 2.0


def _list_tables() -> list[str]:
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        return [str(r[0]) for r in rows]
    except Exception:
        return []


def census() -> dict[str, int]:
    """Row-count pr. tabel. Best-effort; en fejlende tabel udelades."""
    out: dict[str, int] = {}
    try:
        from core.runtime.db import connect
        with connect() as conn:
            for name in _list_tables():
                try:
                    n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()
                    out[name] = int(n[0] or 0)
                except Exception:
                    continue
    except Exception:
        pass
    return out


def dead_table_candidates() -> list[str]:
    """Tabeller med 0 rækker = KANDIDATER til oprydning. KUN til menneskelig review —
    ALDRIG auto-drop (cognitive_*-lektien: tom ≠ død; kan være afløst-men-genbrugt eller
    periodisk-fyldt). Dette er en read-only liste; intet droppes."""
    return sorted(name for name, n in census().items() if n == 0)


def _load_prev() -> dict[str, int]:
    try:
        from core.services import shared_cache
        v = shared_cache.get(_SNAPSHOT_KEY)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _save(c: dict[str, int]) -> None:
    try:
        from core.services import shared_cache
        shared_cache.set(_SNAPSHOT_KEY, c, ttl_seconds=_SNAPSHOT_TTL)
    except Exception:
        pass


def scan() -> dict[str, Any]:
    """Census + vækst-delta vs forrige snapshot + flag egregious vækst. Returnér rapport.
    Første scan etablerer baseline (ingen flags). Self-safe."""
    cur = census()
    prev = _load_prev()
    flagged: list[dict[str, Any]] = []
    for name, n in cur.items():
        p = prev.get(name)
        if p is None:
            continue  # ny tabel siden sidste snapshot → ingen baseline endnu
        grew = n - p
        if grew >= _GROWTH_ABS and (p == 0 or n >= p * _GROWTH_FACTOR):
            flagged.append({"table": name, "from": p, "to": n, "grew": grew})
    empty = sorted(name for name, n in cur.items() if n == 0)
    report = {
        "tables": len(cur),
        "total_rows": sum(cur.values()),
        "empty": empty,
        "flagged_growth": flagged,
    }
    _save(cur)
    return report


def observe() -> dict[str, Any]:
    """Kør scan + central.observe(summary) + flag egregious vækst som incident (review).
    ALDRIG destruktiv. Bør kaldes på en lav-frekvent kadence (fx dagligt)."""
    report = scan()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "db", "nerve": "census",
            "tables": report["tables"], "total_rows": report["total_rows"],
            "empty_count": len(report["empty"]),
            "flagged_growth": report["flagged_growth"][:20],
        })
    except Exception:
        pass
    for f in report["flagged_growth"]:
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="db", nerve="table_growth", kind="growth", severity="error",
                message=f"tabel {f['table']} voksede {f['from']}→{f['to']} (+{f['grew']} rækker)",
            )
        except Exception:
            pass
    return report


def build_db_health_surface() -> dict[str, object]:
    """MC-surface — read-only meta-projektion af DB-helbred + kandidat-død-liste til review."""
    try:
        cur = census()
        empty = sorted(name for name, n in cur.items() if n == 0)
        return {
            "active": True, "mode": "db_sentinel",
            "tables": len(cur), "total_rows": sum(cur.values()),
            "dead_candidates_for_review": empty,
            "authority": "derived-read-only — foreslår, dropper ALDRIG",
        }
    except Exception:
        return {"active": False, "mode": "db_sentinel"}
