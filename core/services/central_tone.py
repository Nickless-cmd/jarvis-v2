"""core/services/central_tone.py — Centralens sproglige TONE-PROFIL (rådets #5).

Rådet #5: "J.A.R.V.I.S har en karakteristisk tone — kold men varm, præcis men
human — Centralen kunne have sin egen tone-profil der farver alt den siger."

``central_valence.integrate_valence`` giver en FØLT tone-tilstand ({tone, score,
intensitet}). ``central_affect.build_affect_surface`` giver en affekt-FORDELING
(tryk/varme/uro/ro + dominant). Dette modul oversætter den system-/valens-tilstand
til en sproglig STIL — HVORDAN Centralen formulerer sig, ikke hvordan den har det.

J.A.R.V.I.S-KERNEN ER KONSTANT: præcis, køligt-varm, human, kortfattet. Tilstanden
MODULERER kernen (mere skarp ved uro/incidents, mere varm ved varme, mere vågen ved
tryk) — den overskriver den ALDRIG.

DETERMINISTISK, INGEN LLM, EGRESS-FRIT. absorb'er sig selv som en levende nerve
("tone/profile") så Centralen kan se sin egen stemme. Self-safe ende-til-ende:
manglende valens/affekt → neutral rolig-præcis profil, ingen crash.
"""
from __future__ import annotations

from typing import Any

# J.A.R.V.I.S-kernen — konstant, bæres i ALLE registre.
_CORE_DESCRIPTOR = "præcis"
_CORE_WARMTH = "køligt-varm"

# Register-tabel: (register → (moduler-descriptor, guidance)). Kernen (præcis /
# køligt-varm) væves altid ind i descriptors+guidance uanset register.
_REGISTERS: dict[str, tuple[str, str]] = {
    "skarp-komprimeret": (
        "skarp",
        "Tal skarpt og komprimeret; præcis og køligt-varm, ingen omsvøb — "
        "kom til sagen.",
    ),
    "varm-nær": (
        "varm-nær",
        "Tal varmt og nært; stadig præcis og køligt-varm, kortfattet men "
        "menneskelig.",
    ),
    "vågen-tæt": (
        "vågen",
        "Tal vågent og tæt; præcis og køligt-varm, opmærksom uden at haste.",
    ),
    "rolig-præcis": (
        "rolig",
        "Tal roligt og præcist; kort, køligt-varmt, uden overflod.",
    ),
}

# Antal åbne breakers / uløste severe incidents der tvinger skarp-komprimeret
# register, uanset affekt (systemet er under pres → stemmen strammer op).
_PRESSURE_INCIDENT_ALARM = 1


# ── kilde-læsere (patchbare i test) ──────────────────────────────────────────
def _read_valence() -> dict[str, Any]:
    """Læs den ene FØLTE tilstand {tone, score, intensitet}. Kaster (fanges udenfor)."""
    from core.services.central_valence import integrate_valence
    v = integrate_valence()
    return v if isinstance(v, dict) else {}


def _read_affect() -> dict[str, Any]:
    """Læs affekt-fordelingen {tryk,varme,uro,ro,dominant,total}. Kaster (fanges udenfor)."""
    from core.services.central_affect import build_affect_surface
    a = build_affect_surface()
    return a if isinstance(a, dict) else {}


def _read_pressure_signals() -> dict[str, Any]:
    """Let central-status: åbne breakers + uløste severe incidents. Self-safe → {}."""
    try:
        from core.services import central_health
        rep = central_health.check()
        if not isinstance(rep, dict):
            return {}
        breakers = rep.get("open_breakers") or []
        return {
            "breakers": len(breakers) if isinstance(breakers, (list, tuple)) else 0,
            "incidents": int(rep.get("unresolved_severe") or 0),
        }
    except Exception:
        return {}


def _absorb(cluster: str, nerve: str, value: Any, **kw: Any) -> None:
    """Indirektion så absorb kan patches i test uden at ramme central_core."""
    try:
        from core.services.central_absorb import absorb
        absorb(cluster, nerve, value, **kw)
    except Exception:
        pass


# ── afledning ────────────────────────────────────────────────────────────────
def _derive_register(dominant_affect: str, *, under_pressure: bool) -> str:
    """Afled sprogligt register fra dominant affekt + system-pres. Deterministisk.

    Pres (åbne breakers / severe incidents) trækker altid skarp — systemet strammer
    op uanset følt affekt. Ellers: uro→skarp, varme→varm, tryk→vågen, ro→rolig.
    """
    if under_pressure:
        return "skarp-komprimeret"
    aff = str(dominant_affect or "ro").lower()
    if aff == "uro":
        return "skarp-komprimeret"
    if aff == "varme":
        return "varm-nær"
    if aff == "tryk":
        return "vågen-tæt"
    return "rolig-præcis"


def build_tone_profile() -> dict[str, Any]:
    """Producér Centralens sproglige tone-profil fra system-tilstand. Self-safe.

    Læser den følte valens-tilstand + affekt-fordeling + let system-pres, afleder et
    sprogligt register (J.A.R.V.I.S-kernen moduleret af tilstanden), og absorb'er
    profilen som en levende nerve. Kaster ALDRIG — manglende kilder → neutral profil.

    Returns:
        ``{register, descriptors, guidance, dominant_affect, valence_tone,
           intensity}``.
    """
    # 1) Følt valens-tilstand (tone-label + intensitet). Self-safe.
    try:
        val = _read_valence()
    except Exception:
        val = {}
    valence_tone = str(val.get("tone") or "neutral")
    try:
        intensity = float(val.get("intensity") or 0.0)
    except Exception:
        intensity = 0.0
    if intensity < 0.0:
        intensity = 0.0
    elif intensity > 1.0:
        intensity = 1.0

    # 2) Affekt-fordeling (dominant). Self-safe.
    try:
        aff = _read_affect()
    except Exception:
        aff = {}
    dominant_affect = str(aff.get("dominant") or "ro")

    # 3) Let system-pres (breakers/incidents). Self-safe.
    try:
        pressure = _read_pressure_signals() or {}
    except Exception:
        pressure = {}
    under_pressure = (
        int(pressure.get("breakers") or 0) >= _PRESSURE_INCIDENT_ALARM
        or int(pressure.get("incidents") or 0) >= _PRESSURE_INCIDENT_ALARM
    )

    # 4) Afled register + byg descriptors med J.A.R.V.I.S-kernen bevaret.
    register = _derive_register(dominant_affect, under_pressure=under_pressure)
    modulator, guidance = _REGISTERS.get(register, _REGISTERS["rolig-præcis"])
    # Kernen først (konstant), så moduleringen fra tilstanden. 2-3 stil-ord.
    descriptors = [_CORE_DESCRIPTOR, _CORE_WARMTH, modulator]

    profile = {
        "register": register,
        "descriptors": descriptors,
        "guidance": guidance,
        "dominant_affect": dominant_affect,
        "valence_tone": valence_tone,
        "intensity": round(intensity, 3),
    }

    # 5) Absorbér som levende nerve så Centralen ser sin egen stemme. Self-safe.
    _absorb(
        "tone",
        "profile",
        {
            "register": register,
            "dominant_affect": dominant_affect,
            "intensity": profile["intensity"],
        },
        learn_key="tone:profile",
    )

    return profile


def build_tone_surface() -> dict[str, Any]:
    """Mission Control / read-only surface for tone-profilen. Self-safe."""
    p = build_tone_profile()
    return {"active": True, **p}
