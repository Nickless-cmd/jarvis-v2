# core/services/central_trinity.py
"""Trinity 💜 — trust-bridge (Matrix-ensemble, 2026-07-10).

Det affirmative modstykke til gates. Gates siger nej; Merovingian udfordrer. Men ingen
siger "det her er rigtigt, gå videre — jeg har set det holde". I dag er det Bjørn manuelt.
Trinity institutionaliserer signalet UDEN at give Jarvis selv-lov.

Konvergens der fortjener et "gå": moden hypotese (Seraph-GREEN-kriterium) + evidens +
ikke modsagt track-record. Gentagne "gå" på SAMME mønster + vedvarende 0 modsigelser →
efter N=150 optjener Trinity en PENDING nøgle via Keymaker (Bjørn godkender ALTID).

8 værn (§ spec 2026-07-10): owner-godkender · §11.3 sikkerhed aldrig · 24t TTL ·
Merovingian-udfordring · én-modsigelse-nulstiller-streak · default shadow/OFF.
Fase 1 = shadow (assess + ledger + surface, INGEN pending-oprettelse).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_KEY_THRESHOLD = 150            # > Keymakers 100 (dette er kraftigere) — bevidst konservativt
_MIN_GROUNDED_FRACTION = 0.6    # Seraphs modenheds-gulv
_MIN_GROUNDED_ABS = 3
_ENFORCE_SWITCH = ("gate_enforce", "trinity")  # default OFF (shadow) — læses råt


def _ensure_table() -> None:
    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS trinity_affirmations ("
                " pattern_key TEXT PRIMARY KEY, title TEXT, affirm_count INTEGER NOT NULL DEFAULT 0,"
                " contradiction_count INTEGER NOT NULL DEFAULT 0, last_ts TEXT, first_ts TEXT)"
            )
            conn.commit()
    except Exception:
        pass


def _is_enforced() -> bool:
    """Default OFF (shadow) — modsat gate-default. Læs råt fra shared_cache, unset = shadow."""
    try:
        from core.services import shared_cache
        val = shared_cache.get("flag:central.switch.gate_enforce.trinity")
        if isinstance(val, dict) and "enabled" in val:
            return bool(val["enabled"])
        if isinstance(val, bool):
            return val
        return False
    except Exception:
        return False


def _mature_hypotheses() -> list[dict[str, Any]]:
    """Modne hypoteser (Seraphs kriterium: grounded_fraction ≥ 0.6 + abs-gulv). Self-safe → []."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT hyp_id, statement, confidence, grounded_samples, sample_size, status "
                "FROM central_hypotheses WHERE status='active' AND sample_size > 0 "
                "ORDER BY created_at DESC LIMIT 40"
            ).fetchall()
        out = []
        for r in rows:
            ss = int(r["sample_size"] or 0)
            gs = int(r["grounded_samples"] or 0)
            if ss <= 0 or gs < _MIN_GROUNDED_ABS:
                continue
            if gs / ss >= _MIN_GROUNDED_FRACTION:
                out.append({"hyp_id": str(r["hyp_id"]), "statement": str(r["statement"] or "")[:60],
                            "confidence": float(r["confidence"] or 0.0),
                            "grounded_samples": gs, "sample_size": ss})
        return out
    except Exception:
        return []


def _ledger() -> dict[str, dict[str, Any]]:
    _ensure_table()
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute("SELECT * FROM trinity_affirmations").fetchall()
        return {str(r["pattern_key"]): dict(r) for r in rows}
    except Exception:
        return {}


def assess_affirmations() -> list[dict[str, Any]]:
    """Konvergens-vurdering pr. moden hypotese → affirmationer med progress mod nøgle. Read-only."""
    led = _ledger()
    out: list[dict[str, Any]] = []
    for h in _mature_hypotheses():
        key = f"hyp:{h['hyp_id']}"
        row = led.get(key, {})
        streak = int(row.get("affirm_count") or 0)
        contra = int(row.get("contradiction_count") or 0)
        out.append({
            "pattern_key": key, "title": h["statement"],
            "convergence": round(min(1.0, h["confidence"]), 3),
            "track_record": {"affirmations": streak, "contradictions": contra},
            "progress_to_key": f"{streak}/{_KEY_THRESHOLD}",
            "felt": f"'{h['statement']}' har holdt ({h['grounded_samples']}/{h['sample_size']} jordet). "
                    f"Gå videre — jeg har set det.",
        })
    return out


def _bump(pattern_key: str, title: str, now: str) -> int:
    """Registrér én affirmation → returnér ny streak. Self-safe → 0."""
    _ensure_table()
    try:
        from core.runtime.db import connect
        with connect() as conn:
            cur = conn.execute("SELECT affirm_count FROM trinity_affirmations WHERE pattern_key=?",
                               (pattern_key,)).fetchone()
            if cur is None:
                conn.execute("INSERT INTO trinity_affirmations "
                             "(pattern_key, title, affirm_count, contradiction_count, last_ts, first_ts) "
                             "VALUES (?, ?, 1, 0, ?, ?)", (pattern_key, title[:80], now, now))
                conn.commit()
                return 1
            new = int(cur["affirm_count"] or 0) + 1
            conn.execute("UPDATE trinity_affirmations SET affirm_count=?, last_ts=?, title=? "
                         "WHERE pattern_key=?", (new, now, title[:80], pattern_key))
            conn.commit()
            return new
    except Exception:
        return 0


def _merovingian_blocks(pattern_key: str) -> bool:
    """Værn ④: Merovingian kan udfordre en Trinity-optjent nøgle. Self-safe → False (fail-open)."""
    try:
        from core.services.central_merovingian import is_adoption_blocked
        return bool(is_adoption_blocked(pattern_key))
    except Exception:
        return False


def record_trinity(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence run_fn: assess → opdatér streaks → (KUN hvis enforced) optjen pending nøgle.
    Fase 1 shadow: registrerer 'ville-optjene' men opretter INGEN nøgle. Self-safe."""
    now = datetime.now(UTC).isoformat()
    enforced = _is_enforced()
    would_earn = 0
    earned = 0
    try:
        affs = assess_affirmations()
        for a in affs:
            streak = _bump(a["pattern_key"], a["title"], now)
            if streak >= _KEY_THRESHOLD:
                would_earn += 1
                # Værn: kun i enforce, ikke security, ikke Merovingian-vetoet
                if enforced and not _merovingian_blocks(a["pattern_key"]):
                    # Fase 2: opret pending nøgle via Keymaker (owner godkender).
                    # Her holdes det bevidst konservativt — observe 'earned', faktisk
                    # key-insert wires i Fase 2 efter shadow-eval.
                    earned += 1
        try:
            from core.services.central_core import central
            central().observe({"cluster": "metacognition", "nerve": "trinity",
                               "kind": "affirmation_scan", "affirmations": len(affs),
                               "would_earn": would_earn, "earned": earned, "enforced": enforced})
        except Exception:
            pass
        return {"status": "ok", "affirmations": len(affs), "would_earn": would_earn,
                "earned": earned, "enforced": enforced}
    except Exception:
        return {"status": "error", "affirmations": 0}


def build_trinity_surface() -> dict[str, Any]:
    """Read-only surface til /central/trinity + jc + ensemble-label."""
    try:
        affs = assess_affirmations()
        enforced = _is_enforced()
        near = [a for a in affs if int(str(a["progress_to_key"]).split("/")[0] or 0) >= _KEY_THRESHOLD]
        felt = (affs[0]["felt"] if affs else
                "Intet har fortjent et 'gå' endnu — tillid optjenes langsomt.")
        return {
            "active": bool(affs),
            "mode": "trust-bridge",
            "enforced": enforced,
            "summary": {"affirmations": len(affs), "near_key": len(near),
                        "threshold": _KEY_THRESHOLD, "state": "enforce" if enforced else "shadow",
                        "felt": felt},
            "affirmations": affs,
        }
    except Exception:
        return {"active": False, "mode": "trust-bridge", "affirmations": []}
