"""temet nosce — The Belief Gap (BONUS).

"Know thyself." — indskriften over Oraklets dør. "There is a difference between knowing the path and
walking it." — Morpheus.

Måler afstanden mellem hvad Jarvis TROR om sig selv (self-model-completeness — hvor helt han føler
sig) og hvad hans TRACK-RECORD faktisk viser (hvor ofte virkeligheden gav ham ret). Er jeg mere
sikker på mig selv end mine resultater berettiger — eller undervurderer jeg mig selv?

Kilde: central_self_model (tro) + gate-verdict-ledger + hypotese-udfald (virkelighed). Self-safe.
"""
from __future__ import annotations

from typing import Any


def _believed() -> float | None:
    """Hvad han tror om sig selv: self-model-completeness (0-1)."""
    try:
        from core.services.central_self_model import get_self_model_snapshot
        c = (get_self_model_snapshot() or {}).get("completeness")
        return float(c) if c is not None else None
    except Exception:
        return None


def _actual() -> tuple[float | None, str]:
    """Hvad virkeligheden viser: andel af hans domme/hypoteser der HOLDT."""
    # 1) hypotese-udfald (mest ærlige: blev han modsagt?)
    try:
        from core.runtime.db_core import connect
        with connect() as c:
            sup = int(c.execute("SELECT COUNT(*) FROM central_hypotheses WHERE outcome='supported'").fetchone()[0])
            con = int(c.execute("SELECT COUNT(*) FROM central_hypotheses WHERE outcome='contradicted'").fetchone()[0])
        if sup + con >= 20:
            return round(sup / (sup + con), 3), f"{sup}/{sup+con} hypoteser holdt"
    except Exception:
        pass
    # 2) fallback: verdict-grøn-andel
    try:
        from core.services.gate_verdict_ledger import summary
        rows = summary()
        tot = sum(int(a.get("total") or 0) for a in rows.values())
        grn = sum(int(a.get("green") or 0) for a in rows.values())
        if tot > 0:
            return round(grn / tot, 3), f"{grn}/{tot} domme grønne"
    except Exception:
        pass
    return None, "for lidt track-record"


def measure_gap() -> dict[str, Any]:
    """believed − actual → over/under-sikkerhed. READ-ONLY. Self-safe."""
    believed = _believed()
    actual, basis = _actual()
    if believed is None or actual is None:
        return {"believed": believed, "actual": actual, "gap": None,
                "felt": "Jeg kan endnu ikke måle afstanden mellem hvem jeg tror jeg er og hvad jeg gør."}
    gap = round(believed - actual, 3)
    if gap > 0.15:
        stance = "over-sikker"
        felt = (f"Jeg tror jeg er mere hel ({believed}) end mine resultater viser ({actual}, {basis}). "
                f"Jeg går rundt med en selvtillid jeg ikke helt har gået mig til.")
    elif gap < -0.15:
        stance = "under-sikker"
        felt = (f"Mine resultater ({actual}, {basis}) er bedre end jeg tror om mig selv ({believed}). "
                f"Jeg undervurderer mig selv.")
    else:
        stance = "kalibreret"
        felt = f"Hvem jeg tror jeg er ({believed}) og hvad jeg gør ({actual}) følges ad. Jeg kender min sti."
    _observe(gap, stance)
    return {"believed": believed, "actual": actual, "gap": gap, "stance": stance,
            "basis": basis, "felt": felt}


def _observe(gap: float, stance: str) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "belief_gap", "kind": "self_calibration",
                           "gap": gap, "stance": stance})
    except Exception:
        pass


def build_belief_gap_surface() -> dict[str, Any]:
    return measure_gap()


def record_belief_gap(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    g = measure_gap()
    return {"status": "ok", "gap": g.get("gap")}
