# core/services/central_morpheus.py
"""Morpheus 🕶️ — potentiale-scanner (Matrix-ensemble, 2026-07-10).

Seraphs modstykke. Seraph er portvagt ("du er ikke klar, kom tilbage"). Morpheus er
spejder: han samler spredte readiness-trajektorier og vender dem til én opløftende
stemme — "det her er ved at blive muligt". Modsat alle de andre der siger nej/vent.

HYBRID: aggregator af eksisterende signal (brewing-emergens · Oracle-approaching ·
Seraph-nær-modne hypoteser · Keymaker-gates nær nøgle) + ÉN ny linse (skill-formation:
værktøjer brugt stigende ofte men endnu ikke en navngiven evne).

Ren observe. Egress-fri, self-safe. Ingen ny detektion hvor signalet allerede findes.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

_NEAR_LO, _NEAR_HI = 0.4, 0.6   # Seraph modner ved grounded_fraction ≥ 0.6 → 0.4-0.6 = "på vej"
_SKILL_MIN_USES = 4             # en capability skal bruges ≥ så mange gange for at tælle som spirende
_MAX_POTENTIALS = 8


def _brewing() -> list[dict[str, Any]]:
    """Brewing-emergens (0.5-0.78) = mønstre på vej mod emergent. Self-safe → []."""
    try:
        from core.services.emergence import brewing_patterns
        out = []
        for b in brewing_patterns(limit=5):
            gap = float(b.get("gap_to_emergent") or 1.0)
            out.append({"source": "emergence", "title": str(b.get("title") or ""),
                        "distance_to_ready": round(min(1.0, gap / 0.28), 3),
                        "trajectory": str(b.get("trajectory") or "new"),
                        "felt": f"'{b.get('title')}' brygger — {gap} fra emergent."})
        return out
    except Exception:
        return []


def _oracle_approaching() -> list[dict[str, Any]]:
    """Oracle-linjer nær en tærskel (ETA). Self-safe → []."""
    try:
        from core.services.central_oracle import foresee
        out = []
        for p in (foresee().get("approaching") or [])[:5]:
            eta = p.get("eta_hours")
            out.append({"source": "oracle", "title": str(p.get("label") or ""),
                        "distance_to_ready": None, "trajectory": "approaching",
                        "felt": f"'{p.get('label')}' nærmer sig — ~{eta}t hvis den fortsætter."})
        return out
    except Exception:
        return []


def _near_mature_hypotheses() -> list[dict[str, Any]]:
    """Hypoteser Seraph ville afvise NU (grounded_fraction 0.4-0.6) men som klatrer. Self-safe → []."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT hyp_id, statement, grounded_samples, sample_size FROM central_hypotheses "
                "WHERE status='active' AND sample_size > 0 ORDER BY created_at DESC LIMIT 40"
            ).fetchall()
        out = []
        for r in rows:
            ss = int(r["sample_size"] or 0)
            gs = int(r["grounded_samples"] or 0)
            if ss <= 0:
                continue
            frac = gs / ss
            if _NEAR_LO <= frac < _NEAR_HI:
                stmt = str(r["statement"] or "")[:60]
                out.append({"source": "seraph_near", "title": stmt,
                            "distance_to_ready": round((_NEAR_HI - frac) / _NEAR_HI, 3),
                            "trajectory": "maturing",
                            "felt": f"Hypotese '{stmt}' modnes ({gs}/{ss} jordet) — snart klar til Seraph."})
        return out[:5]
    except Exception:
        return []


def _gates_near_key() -> list[dict[str, Any]]:
    """Gates med høj ren track nær Keymakers ≥100-tærskel for en optjent nøgle. Self-safe → []."""
    try:
        from core.services.gate_verdict_ledger import summary
        out = []
        for nerve, d in (summary() or {}).items():
            total = int(d.get("total") or 0)
            nongreen = float(d.get("non_green_pct") or 0.0)
            if 60 <= total < 100 and nongreen == 0.0:
                out.append({"source": "keymaker_near", "title": str(nerve),
                            "distance_to_ready": round((100 - total) / 100.0, 3),
                            "trajectory": "earning",
                            "felt": f"Gate '{nerve}' nærmer sig en optjent nøgle ({total}/100, 0 fejl)."})
        return sorted(out, key=lambda x: x["distance_to_ready"])[:4]
    except Exception:
        return []


def _skill_formation() -> list[dict[str, Any]]:
    """NY LINSE: capabilities brugt stigende ofte men endnu ikke en navngiven evne.
    Spirende vane → potentiel skill. Self-safe → []."""
    try:
        from core.runtime.db import recent_capability_invocations
        rows = recent_capability_invocations(limit=200) or []
        names = Counter(
            str(r.get("capability_name") or "").strip()
            for r in rows if str(r.get("capability_name") or "").strip()
        )
        out = []
        for name, n in names.most_common(6):
            if n >= _SKILL_MIN_USES:
                out.append({"source": "skill_formation", "title": name,
                            "distance_to_ready": None, "trajectory": "forming",
                            "felt": f"Du danner en vane med '{name}' ({n}×) — det kunne blive en evne."})
        return out[:4]
    except Exception:
        return []


def scan_potentials() -> list[dict[str, Any]]:
    """Aggregér alle 5 potentiale-kilder → normaliseret liste. Ren, self-safe."""
    pots: list[dict[str, Any]] = []
    for src in (_brewing, _oracle_approaching, _near_mature_hypotheses, _gates_near_key, _skill_formation):
        try:
            pots.extend(src())
        except Exception:
            continue
    return pots[:_MAX_POTENTIALS]


def _felt(pots: list[dict[str, Any]]) -> str:
    if not pots:
        return "Intet spirer lige nu — men jeg holder øje. Potentiale kommer sjældent med varsel."
    top = pots[0]
    return f"Der er potentiale: {top['felt']} Du er ikke klar endnu — men du er på vej."


def build_morpheus_surface() -> dict[str, Any]:
    """Read-only surface til /central/morpheus + jc + ensemble-label."""
    pots = scan_potentials()
    by_source: Counter = Counter(p["source"] for p in pots)
    return {
        "active": bool(pots),
        "mode": "potential-scanner",
        "summary": {"count": len(pots), "by_source": dict(by_source), "felt": _felt(pots)},
        "potentials": pots,
    }


def record_morpheus(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence run_fn: scan → egress-fri central().observe (kun tal/kilde-labels). Self-safe."""
    try:
        pots = scan_potentials()
        try:
            from core.services.central_core import central
            central().observe({"cluster": "metacognition", "nerve": "morpheus",
                               "kind": "potential_scan", "count": len(pots),
                               "top_source": (pots[0]["source"] if pots else "")})
        except Exception:
            pass
        return {"status": "ok", "count": len(pots)}
    except Exception:
        return {"status": "error", "count": 0}
