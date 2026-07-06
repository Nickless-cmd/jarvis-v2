"""The Architect — periodisk selv-arkitekt der foreslår ÉT tungt strukturelt snit.

Bjørn+Claude (6. jul, Matrix-tema #5 + gartner-idé #1 "Architect's Pruning Protocol"): "I created
the Matrix. I've been monitoring it ever since." Hvor gartneren (central_excess) MÆRKER vægten
løbende, træder Arkitekten sjældent frem — men når den gør, ser den HELE systemet på én gang og
udtaler ét klart, tungt forslag: den vigtigste strukturelle gæld lige nu, og det konkrete snit der
ville lette den mest. Ikke bred beskæring (det er gartneren) — ét dybt, gennemtænkt snit.

Lav-frekvens (månedlig cadence). Propose-only: Arkitekten SNAKKER, den skærer ikke. Owner (eller
gartner-protokollen) udfører. Kilde: central_excess (oversized filer, vækst). Self-safe.
"""
from __future__ import annotations

from typing import Any

# Under så lav en vægt træder Arkitekten ikke frem — der er intet tungt at udtale.
_SPEAK_MIN_PRESSURE = 40


def assess() -> dict[str, Any]:
    """Se hele systemet → ét prioriteret strukturelt snit-forslag. READ-ONLY. Self-safe.
    Returnerer {pressure, recommendation, rationale, target, felt}."""
    out: dict[str, Any] = {"pressure": 0, "recommendation": "", "rationale": "",
                           "target": "", "felt": "", "worst_files": []}
    try:
        from core.services.central_excess import build_excess_surface
        surf = build_excess_surface()
    except Exception:
        surf = {}
    pressure = int(surf.get("pressure") or 0)
    worst = surf.get("worst_files") or []
    out["pressure"] = pressure
    out["worst_files"] = worst[:5]
    if pressure < _SPEAK_MIN_PRESSURE or not worst:
        out["felt"] = "Strukturen bærer sig selv lige nu — jeg har intet tungt at foreslå."
        return out
    top = worst[0]
    target = top["file"]
    lines = int(top.get("lines") or 0)
    out["target"] = target
    out["recommendation"] = f"Split {target} ({lines:,} linjer) i sin nærmeste naturlige enhed"
    out["rationale"] = (
        f"{target} er den tungeste enkeltfil ({lines:,} linjer) og bærer mest af den strukturelle "
        f"gæld. Ét dybt snit her letter mere end bred beskæring andre steder. Boy Scout-reglen: "
        f"udskil den nærmeste sammenhængende enhed (klasse/daemon/tilstandsmaskine) til egen fil, "
        f"bevar bagudkompatibilitet via re-eksport.")
    out["felt"] = (f"Hvis jeg måtte gøre ÉN strukturel ting: dele {target}. Den bærer {lines:,} "
                   f"linjer alene — det er der min vægt sidder.")
    return out


def record_architect() -> dict[str, Any]:
    """Månedlig cadence: observér Arkitektens forslag til nerve system/architect. Metadata-only.
    Self-safe."""
    a = assess()
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "architect", "kind": "structural_proposal",
                           "pressure": a["pressure"], "target": a.get("target", "")})
    except Exception:
        pass
    return a
