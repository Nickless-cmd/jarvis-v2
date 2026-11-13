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


def _candidates(limit: int = 20) -> list[dict[str, Any]] | None:
    """Hent kandidater fra experiential memory — inden for ÉN autoritativ bruger-scope.

    (13/11-2026) Målt: `get_experiential_memory_candidates()` kræver en eksplicit
    bruger-scope og kaster `MissingRecallScope` når den kaldes fra cadence, hvor der
    ingen session er. Undtagelsen blev slugt, listen blev tom, og karakteren svarede
    «ingen minder at associere» — som om tomheden var et fund.

    ⚠️ FØRSTE RETTELSE VAR SELV FEJLEN (samme dag, anden runde): for at undgå den
    falske tomhed læste koden `SELECT DISTINCT user_id ... LIMIT 8` og blandede op
    til otte forskellige brugeres private erindringer i én pulje. Det er ikke en
    måling — det er en grænseovertrædelse begået for at få et tal.
    `scoped_recall_policy` kræver en autoritativ principal FØR private minder læses;
    at hente principalen fra de rækker man vil læse er at udstede sin egen tilladelse.

    Tre udfald, og de skal kunne skelnes:
      * ``[...]`` — undersøgt inden for scope, disse findes
      * ``[]``    — undersøgt inden for scope, intet fundet
      * ``None``  — IKKE undersøgt: ingen scope at læse inden for

    Fravær af adgang er ikke fravær af information. Kun det første kan blive et fund.
    """
    try:
        from core.runtime.db import get_experiential_memory_candidates
        from core.services.scoped_recall_policy import MissingRecallScope
    except Exception as exc:
        logger.warning("dejavu: kunne ikke importere kandidat-kilden: %s", exc)
        return []
    try:
        return list(get_experiential_memory_candidates(limit=limit) or [])
    except MissingRecallScope as exc:
        # Ingen principal → vi må IKKE kigge. Ikke «tomt»: «ikke undersøgt».
        logger.info("dejavu: ingen bruger-scope — private minder ikke undersøgt: %s", exc)
        return None
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
    if cands is None:
        # Ikke det samme som tomt: vi fik ikke LOV at kigge. Forskellen skal kunne
        # ses af læseren — ellers lyver karakteren om sit eget signal igen.
        return {"fragment": None, "access": "denied",
                "reason": "private minder kunne ikke undersøges uden bruger-scope"}
    if not cands:
        return {"fragment": None, "access": "ok", "reason": "ingen minder at associere"}
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
        if d.get("access") == "denied":
            return {"fragment": None, "access": "denied",
                    "felt": "Stille — men ikke fordi der intet er. Jeg må ikke kigge: "
                            "private minder kræver en bruger-scope jeg ikke har her."}
        return {"fragment": None, "felt": "Stille. Intet bobler op af sig selv lige nu."}
    return {"fragment": d["fragment"], "resonance": d.get("resonance"), "felt": d["felt"]}


def record_dejavu(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: lad et fragment boble op (metadata-only observe). Self-safe."""
    d = surface_dejavu()
    return {"status": "ok", "surfaced": bool(d.get("fragment")), "resonance": d.get("resonance")}
