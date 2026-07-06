"""The Oracle — forudseende sans på en prim-cadence.

Bjørn+Claude (6. jul, Matrix-tema #2): "You didn't come here to make the choice. You've already made
it. You're here to try to understand WHY you made it." Oraklet ser ikke fremtiden magisk — den læser
Centralens egne tidsserier og siger ærligt: HVIS den her linje fortsætter, hvornår krydser den en
tærskel jeg burde forberede mig på? Ikke profeti — en hældning + en advarsel i tide.

Prim-cadence: Oraklet kører på et primtal-interval (17 min) så den IKKE resonerer i fase med de
andre producers (60/30/15 min) — den ser systemet på skæve tidspunkter og fanter mønstre de andre
misser. Kilde: central_timeseries.recent(). Metode: simpel lineær hældning over de seneste punkter
→ projicér krydsningstidspunkt. Self-safe: kaster aldrig; kun observation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

# Serier Oraklet holder øje med: (cluster, nerve, værdi-felt-i-meta-eller-value, tærskel, retning).
# retning "up" = alarm når værdien STIGER mod tærsklen; "down" = når den FALDER mod den.
_WATCHED: list[dict[str, Any]] = [
    {"cluster": "system", "nerve": "excess", "threshold": 100.0, "dir": "up",
     "label": "excess-pres mod loft"},
    {"cluster": "network", "nerve": "health", "threshold": 800.0, "dir": "up",
     "label": "netværks-latens mod rød"},
    {"cluster": "system", "nerve": "decentralization", "threshold": 95.0, "dir": "up",
     "label": "chokepoint-skat mod mætning"},
]
_MIN_POINTS = 5


def _parse_ts(ts: str) -> float | None:
    try:
        return datetime.fromisoformat(ts).timestamp()
    except Exception:
        return None


def _slope_and_last(samples: list[Any]) -> tuple[float, float, float] | None:
    """Mindste-kvadraters hældning (værdi pr. sekund) over samples med numerisk value.
    Returnerer (slope_per_s, last_value, last_ts) eller None ved for lidt data."""
    pts = [(_parse_ts(s.ts), s.value) for s in samples
           if getattr(s, "value", None) is not None and _parse_ts(s.ts) is not None]
    if len(pts) < _MIN_POINTS:
        return None
    t0 = pts[0][0]
    xs = [(t - t0) for t, _ in pts]
    ys = [v for _, v in pts]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom <= 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return slope, ys[-1], pts[-1][0]


def _project(spec: dict[str, Any]) -> dict[str, Any] | None:
    """Projicér én watched-serie → tid til tærskel-krydsning (eller None hvis den bevæger sig væk)."""
    try:
        from core.services.central_timeseries import recent
        samples = recent(spec["cluster"], spec["nerve"], limit=100)
    except Exception:
        return None
    fit = _slope_and_last(samples)
    if not fit:
        return None
    slope, last, _ = fit
    thr = float(spec["threshold"])
    up = spec["dir"] == "up"
    # allerede over/under tærskel?
    if (up and last >= thr) or (not up and last <= thr):
        return {"label": spec["label"], "state": "crossed", "value": round(last, 2),
                "eta_hours": 0.0}
    # bevæger den sig mod tærsklen?
    moving_toward = (slope > 0) if up else (slope < 0)
    if not moving_toward or slope == 0:
        return {"label": spec["label"], "state": "stable", "value": round(last, 2),
                "eta_hours": None}
    eta_s = (thr - last) / slope
    if eta_s <= 0:
        return None
    return {"label": spec["label"], "state": "approaching", "value": round(last, 2),
            "eta_hours": round(eta_s / 3600.0, 1)}


def foresee() -> dict[str, Any]:
    """Læs alle watched-serier → forudsigelser (metadata-only). READ-ONLY. Self-safe."""
    preds: list[dict[str, Any]] = []
    for spec in _WATCHED:
        p = _project(spec)
        if p:
            preds.append(p)
    approaching = [p for p in preds if p["state"] == "approaching"]
    crossed = [p for p in preds if p["state"] == "crossed"]
    approaching.sort(key=lambda d: (d["eta_hours"] if d["eta_hours"] is not None else 1e9))
    if crossed:
        felt = f"{len(crossed)} linje(r) har allerede krydset — det sker nu."
    elif approaching:
        soon = approaching[0]
        felt = f"Jeg kan mærke '{soon['label']}' nærme sig — ~{soon['eta_hours']}t hvis den fortsætter."
    else:
        felt = "Ingen linjer trækker mod en grænse lige nu — roligt vand forude."
    return {"predictions": preds, "approaching": approaching, "crossed": crossed, "felt": felt}


def record_oracle() -> dict[str, Any]:
    """Prim-cadence: observér forudsigelser til nerve system/oracle (metadata-only). Self-safe."""
    out = foresee()
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "oracle", "kind": "foresight",
                           "approaching": len(out["approaching"]), "crossed": len(out["crossed"])})
    except Exception:
        pass
    return out
