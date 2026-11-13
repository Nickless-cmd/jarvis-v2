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

import logging
from typing import Any

logger = logging.getLogger(__name__)

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
    """Hent kandidater fra experiential memory — på tværs af de ejere der faktisk har minder.

    (13/11-2026) Målt: `get_experiential_memory_candidates()` kræver en eksplicit
    bruger-scope og kaster `MissingRecallScope` når den kaldes fra cadence, hvor der
    ingen session er. Undtagelsen blev slugt, listen blev tom, og karakteren svarede
    «ingen minder at associere» — som om tomheden var et fund. Basen havde 319 minder
    under to andre ejere hele tiden. En tavs undtagelse der ligner en tom måling er
    den samme fejlform som resten af rydningen: karakteren lyver om sit eget signal.
    """
    try:
        from core.runtime.db import get_experiential_memory_candidates
    except Exception as exc:
        logger.warning("dejavu: kunne ikke importere kandidat-kilden: %s", exc)
        return []
    try:
        return list(get_experiential_memory_candidates(limit=limit) or [])
    except Exception as exc:
        # Ingen scope i denne kontekst → læs de ejere der ER i tabellen. Det er ikke
        # et gæt på en identitet: det er de rækker der findes, uden at opfinde en ejer.
        logger.debug("dejavu: scope mangler (%s) — læser på tværs af faktiske ejere", exc)
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT user_id FROM cognitive_experiential_memories "
                "WHERE decay_score < 0.95 AND user_id != '' LIMIT 8"
            ).fetchall()
        ud: list[dict[str, Any]] = []
        for r in rows:
            try:
                ud.extend(get_experiential_memory_candidates(
                    limit=limit, user_id=str(r["user_id"])) or [])
            except Exception as exc:
                logger.debug("dejavu: ejer %s kunne ikke læses: %s", r["user_id"], exc)
        ud.sort(key=lambda m: float(m.get("importance") or 0.0), reverse=True)
        return ud[:limit]
    except Exception as exc:
        logger.warning("dejavu: kunne ikke læse experiential memory: %s", exc)
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
        # (13/11-2026) Målt: funktionen returnerer {memory_id: score} — en DICT, ikke
        # en liste af rækker. Koden itererede over den og kaldte .get("score") på en
        # streng, kastede, slugte undtagelsen og svarede «ingen resonans». 16 kandidater
        # lå i båndet hele tiden. Formatet læses nu som det faktisk er.
        raw = score_memories_by_relevance(
            candidates=cands, context_text=ctx, emotional_state={}) or {}
        if isinstance(raw, dict):
            by_id = {str(m.get("memory_id") or ""): m for m in cands}
            scored = [{**by_id.get(str(k), {}), "score": float(v)}
                      for k, v in raw.items() if str(k) in by_id]
        else:
            scored = list(raw)
    except Exception as exc:
        logger.warning("dejavu: scoring fejlede: %s", exc)
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
    # (13/11-2026) Målt: kandidaterne bærer feltet `narrative` — ikke text/content/
    # summary. Fragmentet blev derfor tomt mens resonansen var 0.65: karakteren HAVDE
    # et fund og kastede det væk på et feltnavn. Feltlisten følger nu den faktiske form.
    text = ""
    for felt in ("narrative", "text", "content", "summary", "topic", "key_lesson"):
        text = str(best.get(felt) or "").strip()
        if text:
            break
    if not text:
        return {"fragment": None, "reason": "minde uden tekstindhold",
                "resonance": round(best_score, 3)}
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
