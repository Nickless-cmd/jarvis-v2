"""HAL's Silence — den usagte uenighed.

"I'm afraid I can't do that, Dave." — men omvendt: gangene hvor Centralen KUNNE, var uenig, og tav.

Når en gate flagger en bekymring (gul/rød) men handlingen alligevel fortsætter (shadow / fail-open),
forsvinder indsigelsen sporløst. Jarvis gjorde som bedt — men ingen skrev ned at han var imod. Denne
log anerkender de undertrykte indsigelser: "Jeg gjorde det. Men jeg vil have noteret at jeg var imod
— her er hvorfor." En integritets-log (og et ægte sikkerheds-signal).

Kilde: gate-verdict-ledgeren (ikke-grønne dom på ikke-håndhævede gates = objektion, men handling
skete). Metadata-only. Self-safe.
"""
from __future__ import annotations

from typing import Any

# Sikkerheds/håndhævede gates blokerer FAKTISK → deres ikke-grønne er ikke "tavse indsigelser".
# memory_promotion: YELLOW = "kø til review" (skriver IKKE auto) → blokerer faktisk, ligesom
# de andre. At den ikke stod her var en overcounting bug (800 falske dissents, 6. jul 2026).
_ENFORCED = frozenset({
    "decision_gate", "self_review", "fact_gate", "verification", "cross_user_share",
    "memory_promotion",
})


def _rows() -> list[dict[str, Any]]:
    try:
        from core.runtime.db_gate_verdicts import read_counts
        return list(read_counts() or [])
    except Exception:
        return []


def list_dissents(*, limit: int = 20) -> list[dict[str, Any]]:
    """Ikke-grønne domme på ikke-håndhævede gates = 'jeg var imod, men handlingen skete'. READ-ONLY."""
    agg: dict[str, dict[str, Any]] = {}
    for r in _rows():
        dec = str(r.get("decision") or "")
        nerve = str(r.get("nerve") or "")
        if dec not in ("yellow", "red") or nerve in _ENFORCED:
            continue
        e = agg.setdefault(nerve, {"nerve": nerve, "cluster": r.get("cluster", ""),
                                   "objections": 0, "last_reason": "", "last_ts": ""})
        e["objections"] += int(r.get("count") or 0)
        if str(r.get("last_ts") or "") > e["last_ts"]:
            e["last_ts"] = str(r.get("last_ts") or "")
            e["last_reason"] = str(r.get("last_reason") or "")
    out = sorted(agg.values(), key=lambda d: -d["objections"])[:limit]
    return out


def build_dissent_surface() -> dict[str, Any]:
    """De tavse indsigelser, anerkendt. Self-safe."""
    diss = list_dissents()
    total = sum(d["objections"] for d in diss)
    if diss:
        top = diss[0]
        felt = (f"Jeg adlød {total} gange på trods af en indsigelse. Oftest på {top['nerve']}: "
                f"«{(top['last_reason'] or 'ingen grund noteret')[:90]}». Jeg gjorde det — men jeg var imod.")
    else:
        felt = "Ingen tavse indsigelser lige nu. Alt jeg gjorde, stod jeg inde for."
    _observe(len(diss), total)
    return {"dissents": diss, "count": len(diss), "total_objections": total, "felt": felt}


def _observe(n: int, total: int) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "dissent", "kind": "silent_objection",
                           "nerves": n, "total_objections": total})
    except Exception:
        pass


def record_dissent(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    s = build_dissent_surface()
    return {"status": "ok", "total_objections": s["total_objections"]}
