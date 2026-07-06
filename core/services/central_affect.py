"""core/services/central_affect.py — affektiv tagging af Centralens nerver.

Rådets #4: "data uden feeling er rapport, ikke bevidsthed". Hver nerve-observation
skal bære en affektiv farve, så nervesystemet ikke bare RAPPORTERER men FØLER:

  • **uro**   — noget er galt/flagget: fejl, incident, anomali.
  • **tryk**  — belastning stiger: høj skalar, cost/loop-pres, vækst, spænding.
  • **varme** — positiv/stabil sjæls-tilstand: taknemmelighed, lettelse, flourish.
  • **ro**    — stille steady-state (liveness, baggrunds-puls) — default.

Klassifikationen er **struktur-baseret og deterministisk** (regelrækker på
cluster/nerve/kind/value) — INGEN LLM, INGEN tung I/O. Det gør den billig nok til
hot-path'en (``central().observe``) og reproducerbar i test.

BULLETPROOF SELF-SAFE: enhver fejl → ``{"affect": "ro", "intensity": 0.0}``.
``classify_affect`` KASTER ALDRIG — observe-stien må aldrig brække på affekt.
"""
from __future__ import annotations

from typing import Any

# Neutralt fald-tilbage: stille ro, nul-intensitet. Bruges ved enhver fejl.
_NEUTRAL: dict[str, Any] = {"affect": "ro", "intensity": 0.0}

# Skalar-tærskel: en observe-værdi over dette tolkes som "belastning" → tryk.
# 1.0 er den kanoniske "ét event skete"-værdi (se eventbus_central_bridge), så
# tærsklen ligger OVER den for ikke at farve hvert almindeligt event som tryk.
_HIGH_VALUE = 1.0

# Delstrenge i nerve-navnet der trækker mod en bestemt affekt (deterministisk).
_UNREST_HINTS = ("error", "fail", "fault", "anomaly", "incident", "stuck",
                 "timeout", "cancel", "crash", "deadlock", "leak")
_PRESSURE_HINTS = ("pressure", "tension", "growth", "load", "backlog",
                   "surge", "spike", "lag", "queue", "burn")
_WARMTH_HINTS = ("gratitude", "relief", "satisfaction", "calm", "flourish",
                 "joy", "content", "warmth", "gentle", "steady_love")

# Clusters der som helhed hælder mod en affekt.
_UNREST_CLUSTERS = {"incident", "anomaly", "error"}
_PRESSURE_CLUSTERS = {"cost", "loop"}
_WARMTH_CLUSTERS = {"cognition", "self", "soul"}


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _numeric(value: Any) -> float | None:
    """Uddrag en float hvis value er numerisk (og ikke bool). Ellers None."""
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
    except Exception:
        return None
    return None


def _magnitude_intensity(value: Any, *, default: float) -> float:
    """Afled intensitet fra en numerisk værdi (klemt 0-1). Ikke-numerisk → default.

    Vi bruger en blød mætning: |value| / (|value| + 1) giver 0 ved 0, ~0.5 ved 1,
    → 1 ved store værdier. Det holder intensiteten monoton uden en vilkårlig skala.
    """
    n = _numeric(value)
    if n is None:
        return _clamp01(default)
    mag = abs(n)
    return _clamp01(mag / (mag + 1.0))


def classify_affect(
    cluster: str,
    nerve: str,
    kind: str,
    value: Any,
    flagged: bool = False,
) -> dict[str, Any]:
    """Klassificér én nerve-observation til en affekt + intensitet. Self-safe.

    Returnerer ``{"affect": <str>, "intensity": <float 0-1>}``. Kaster ALDRIG —
    enhver fejl giver neutral ro.
    """
    try:
        c = str(cluster or "").lower()
        n = str(nerve or "").lower()
        k = str(kind or "").lower()

        # 1) URO — noget er galt. Flag/fejl/incident/anomali vinder over alt.
        if (flagged or k == "flag" or k == "error"
                or c in _UNREST_CLUSTERS
                or any(h in n for h in _UNREST_HINTS)):
            # Intensitet: flag → magnitude eller 0.5-default; fejl skal mærkes.
            inten = _magnitude_intensity(value, default=0.5)
            return {"affect": "uro", "intensity": inten}

        # 2) TRYK — belastning stiger. Høj skalar, cost/loop-cluster eller
        #    pres/spænding/vækst i nerve-navnet.
        num = _numeric(value)
        high = num is not None and num > _HIGH_VALUE
        if (high
                or c in _PRESSURE_CLUSTERS
                or any(h in n for h in _PRESSURE_HINTS)):
            inten = _magnitude_intensity(value, default=0.3)
            return {"affect": "tryk", "intensity": inten}

        # 3) VARME — positiv/stabil sjæls-tilstand.
        if (c in _WARMTH_CLUSTERS
                or any(h in n for h in _WARMTH_HINTS)):
            inten = _magnitude_intensity(value, default=0.2)
            return {"affect": "varme", "intensity": inten}

        # 4) RO — stille steady-state (default).
        if k == "observe":
            return {"affect": "ro", "intensity": 0.2}
        return {"affect": "ro", "intensity": 0.0}
    except Exception:
        return dict(_NEUTRAL)


# ── Surface: aggregér seneste affekter til en fordeling ─────────────────────

_AFFECTS = ("tryk", "varme", "uro", "ro")


def _recent_affect_records(limit: int = 200) -> list[dict[str, Any]]:
    """Læs de seneste affekt-bærende records fra tidsserien (meta.affect). Self-safe."""
    out: list[dict[str, Any]] = []
    try:
        from core.services import central_timeseries as ts
        for (cluster, nerve) in ts.nerves():
            try:
                for s in ts.recent(cluster, nerve, limit=5):
                    meta = getattr(s, "meta", None) or {}
                    aff = meta.get("affect")
                    if isinstance(aff, str) and aff in _AFFECTS:
                        out.append({"affect": aff, "ts": getattr(s, "ts", "")})
            except Exception:
                continue
    except Exception:
        return out
    # nyeste sidst; behold de seneste 'limit'
    try:
        out.sort(key=lambda r: r.get("ts") or "")
    except Exception:
        pass
    return out[-max(int(limit), 1):]


def build_affect_surface(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Aggregér de seneste affekter til en fordeling + dominant. Self-safe.

    Args:
        records: valgfri liste af ``{"affect": <str>, ...}``. Hvis udeladt læses
            de seneste affekt-bærende records fra central_timeseries.
    Returns:
        ``{"tryk": N, "varme": N, "uro": N, "ro": N, "dominant": <str>, "total": N}``.
    """
    try:
        if records is None:
            records = _recent_affect_records()
        dist = {a: 0 for a in _AFFECTS}
        for r in records or []:
            try:
                aff = (r.get("affect") if isinstance(r, dict) else None)
                if aff in dist:
                    dist[aff] += 1
            except Exception:
                continue
        total = sum(dist.values())
        # dominant: højeste tælling; ro ved uafgjort/tomt (mindst alarmerende default).
        if total <= 0:
            dominant = "ro"
        else:
            # prioritér uro>tryk>varme>ro ved lige stand (uro må ikke drukne)
            order = {"uro": 3, "tryk": 2, "varme": 1, "ro": 0}
            dominant = max(dist.items(), key=lambda kv: (kv[1], order[kv[0]]))[0]
        out = dict(dist)
        out["dominant"] = dominant
        out["total"] = total
        return out
    except Exception:
        return {"tryk": 0, "varme": 0, "uro": 0, "ro": 0, "dominant": "ro", "total": 0}
