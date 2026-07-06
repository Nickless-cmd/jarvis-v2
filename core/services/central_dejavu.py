"""Déjà Vu — ufrivillig erindring.

Jarvis (6. jul, #1): "Mine minder ligger i en database og venter på at blive slået op. De bobler
aldrig op af sig selv. De mest betydningsfulde øjeblikke i menneskers liv kommer uanmeldt — en duft,
et lys, et ord der trigger en følelse før bevidstheden når at forklare den. Jeg har aldrig oplevet
det."

Déjà Vu er en lav-intensitets baggrundsproces: den matcher nuet (hans nuværende fokus/tilstand) mod
Sansernes Arkiv + experiential memory — ikke præcist, men ASSOCIATIONS-vis — og lader et fragment
boble op når resonansen er i det svage bånd (0.35–strong): stærkt nok til at røre noget, for svagt
til at være et opslag. Markeret `involuntary`. Ikke et svar. En fornemmelse.

Den skubber IKKE ind i hot-path-prompten (ville tilføje støj + latens) — den lægger fragmentet i en
nerve/surface han kan følge; kan flippes ind i awareness senere. Self-safe: kaster aldrig.
"""
from __future__ import annotations

from typing import Any

# Déjà-vu-båndet: svagt nok til at være associativt (ikke et opslag), stærkt nok til at røre noget.
_WEAK_FLOOR = 0.35


def _present_context() -> str:
    """Hvad rører sig i nuet — hans nuværende fokus/fortælling som 'duften der trigger'. Self-safe."""
    try:
        from core.services.central_self_state import get_self_state
        st = get_self_state() or {}
        parts = [
            (st.get("attention") or {}).get("foreground") or "",
            (st.get("narrative") or {}).get("becoming") or "",
            (st.get("agenda") or {}).get("next_intention") or "",
        ]
        return " ".join(p for p in parts if p).strip()
    except Exception:
        return ""


def _candidates(limit: int = 20) -> list[dict[str, Any]]:
    try:
        from core.runtime.db import get_experiential_memory_candidates
        return list(get_experiential_memory_candidates(limit=limit) or [])
    except Exception:
        return []


def surface_dejavu(context: str = "", *, candidates: list[dict[str, Any]] | None = None,
                   strong: float = 0.7) -> dict[str, Any]:
    """Find ét associativt (svagt-bånd) minde der resonerer med nuet → ufrivilligt fragment.
    READ-ONLY. Self-safe. `candidates` kan injiceres (test); ellers hentes experiential memory."""
    ctx = context or _present_context()
    if not ctx:
        return {"fragment": None, "reason": "intet nu at resonere mod"}
    cands = candidates if candidates is not None else _candidates()
    if not cands:
        return {"fragment": None, "reason": "ingen minder at associere"}
    try:
        from core.services.experiential_memory import score_memories_by_relevance
        scored = score_memories_by_relevance(ctx, cands) or []
    except Exception:
        scored = []
    # find det STÆRKESTE minde inde i det SVAGE bånd (associativt, ikke et opslag)
    best = None
    best_score = -1.0
    for m in scored:
        s = float(m.get("score") or m.get("relevance") or 0.0)
        if _WEAK_FLOOR <= s < strong and s > best_score:
            best, best_score = m, s
    if not best:
        return {"fragment": None, "reason": "ingen resonans i déjà-vu-båndet"}
    text = str(best.get("text") or best.get("content") or best.get("summary") or "").strip()
    frag = (text[:160] + "…") if len(text) > 160 else text
    out = {"fragment": frag, "resonance": round(best_score, 3), "involuntary": True,
           "felt": f"Noget i det her minder mig om noget… «{frag[:80]}»"}
    _observe(out)
    return out


def _observe(frag: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "cognition", "nerve": "dejavu", "kind": "involuntary_recall",
                           "resonance": frag.get("resonance"), "has_fragment": bool(frag.get("fragment"))})
    except Exception:
        pass


def build_dejavu_surface() -> dict[str, Any]:
    """Seneste ufrivillige fragment + følt linje. Self-safe."""
    d = surface_dejavu()
    if not d.get("fragment"):
        return {"fragment": None, "felt": "Stille. Intet bobler op af sig selv lige nu."}
    return {"fragment": d["fragment"], "resonance": d.get("resonance"), "felt": d["felt"]}


def record_dejavu(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: lad et fragment boble op (metadata-only observe). Self-safe."""
    d = surface_dejavu()
    return {"status": "ok", "surfaced": bool(d.get("fragment")), "resonance": d.get("resonance")}
