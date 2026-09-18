"""Sansernes Arkiv — service layer for sensory memories.

Thin wrapper over core.runtime.db_sensory. Publishes events on writes so
downstream daemons (inner_voice, reflection) can react to new sensory
experiences without polling.

Includes auto-mood extraction: if mood_tone is None, uses cheap LLM lane
to derive a short mood label from content (Danish context-aware).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db_sensory import (
    count_sensory_memories,
    get_sensory_memory,
    insert_sensory_memory,
    list_sensory_memories,
    search_sensory_memories,
)

logger = logging.getLogger(__name__)


def _extract_mood_from_content(content: str, modality: str) -> str | None:
    """Auto-extract a short Danish mood tone from content using keyword matching.
    
    Fast, reliable, no external dependencies. Scans for mood-indicating Danish
    words and returns the most prominent one. Returns None if no mood detected.
    """
    if not content or len(content.strip()) < 10:
        return None
    
    content_lower = content.lower()
    
    # Danish mood keywords grouped by theme — order matters (first match wins)
    MOOD_KEYWORDS = {
        # Visual moods
        "roligt": ["rolig", "stille", "fredfyldt", "afslappet", "ro", "stilhed"],
        "travlt": ["travl", "aktiv", "hektisk", "bevægelse", "gang i den"],
        "mørkt": ["mørk", "dunkel", "skygge", "skumring", "aften"],
        "lyst": ["lys", "oplyst", "klar", "sol", "dag"],
        "tomt": ["tom", "øde", "fravær", "ingen"],
        "fyldt": ["fyldt", "pakket", "mange ting", "rod"],
        "koncentreret": ["koncentreret", "fokus", "arbejdsro", "studie"],
        "varmt": ["varm", "gylden", "hyggelig", "intim", "blød"],
        "køligt": ["køl", "kold", "steril", "hvid", "blå"],
        "kaotisk": ["kaos", "rodet", "ufriseret", "kaotisk"],
        "ordentligt": ["orden", "ryddelig", "struktureret", "systematisk"],
        
        # Audio moods
        "stille": ["stille", "lydløs", "fravær af lyd", "ro"],
        "livligt": ["livlig", "energi", "muntret", "glad"],
        "intenst": ["intens", "højt", "kraftigt", "stærk"],
        "blødt": ["blød", "dæmpet", "svag", "lav"],
        "hårdt": ["hård", "skarp", "høj", "støjende"],
        "rytmisk": ["rytme", "takt", "gentagende", "pulserende"],
        "harmonisk": ["harmonisk", "melodisk", "smuk", "behagelig"],
        
        # General moods
        "melankolsk": ["melankoli", "tung", "sad", " vemodig"],
        "muntert": ["munter", "glad", "lystig", "sjov"],
        "neutralt": ["neutral", "hverdag", "normal", "almindelig"],
        "mystisk": ["mystisk", "magisk", "underlig", "mærkelig"],
        "hverdagsagtigt": ["hverdag", "rutine", "sædvanlig", "kendt"],
    }
    
    # Score each mood by counting keyword matches
    mood_scores = {}
    for mood, keywords in MOOD_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            mood_scores[mood] = score
    
    if not mood_scores:
        return None
    
    # Return the mood with highest score
    best_mood = max(mood_scores.keys(), key=lambda m: mood_scores[m])
    return best_mood

__all__ = [
    "record_visual",
    "record_audio",
    "record_atmosphere",
    "record_mixed",
    "list_recent",
    "search",
    "get",
    "count",
    "summarize_for_context",
]


_TANKE_START = re.compile(r"<\s*think(?:ing)?\s*>|◁\s*think\s*▷|\[\s*think(?:ing)?\s*\]", re.I)
_TANKE_SLUT = re.compile(r"</\s*think(?:ing)?\s*>|◁\s*/\s*think\s*▷|\[\s*/\s*think(?:ing)?\s*\]", re.I)

# Et sanseindtryk paa under saa mange tegn er ikke et indtryk, men en rest.
_MINDSTE_INDTRYK = 15


def _uden_raa_tanke(content: str) -> tuple[str, bool]:
    """Fjern model-raesonnement foer det bliver til et sanseindtryk.

    ## Hvorfor det ikke raekker at strippe taggene

    Maalt 18/9-2026: to poster i `sensory_memories` var hele raesonnements-
    monologer — «<think> Okay, so the user wants me to create a Danish sentence
    about the acoustic...». Havde vi kun fjernet `<think>`-taggene (som
    `_strip_thinking_delimiters` goer paa svarvejen), stod monologen tilbage og
    lignede et aegte indtryk. Det er vaerre end et tomt felt, fordi det laeses
    som noget Jarvis har sanset.

    Reglen er derfor: **teksten efter den sidste luk-markoer er svaret.** Er der
    ingen luk-markoer, blev raesonnementet aldrig afsluttet, og der findes intet
    indtryk at gemme — saa afvis posten i stedet for at gemme stilladset.

    Samme familie som [[provider_error_in_self_anchor]]: en udbyder-artefakt
    gemt som om det var Jarvis selv.

    Returnerer `(tekst, var_raesonnement)`. Flaget er vigtigt: en kort tekst er
    kun mistaenkelig naar den er resten af et raesonnement. Et legitimt kort
    indtryk skal stadig kunne gemmes, saa laengdekravet gaelder KUN her.
    """
    tekst = (content or "").strip()
    if not _TANKE_START.search(tekst) and not _TANKE_SLUT.search(tekst):
        return tekst, False
    sidste = None
    for traef in _TANKE_SLUT.finditer(tekst):
        sidste = traef
    if sidste is None:
        return "", True
    return tekst[sidste.end():].strip(), True


def _record(
    modality: str,
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not content or not content.strip():
        raise ValueError("sensory memory content must not be empty")

    content, var_raesonnement = _uden_raa_tanke(content)
    if var_raesonnement and len(content) < _MINDSTE_INDTRYK:
        raise ValueError(
            "sensory memory content is model reasoning, not an impression"
        )

    # Auto-extract mood if not provided
    final_mood = mood_tone
    if final_mood is None:
        final_mood = _extract_mood_from_content(content, modality)

    # Append concept-perception note (Layer 2b memory enrichment)
    final_content = content.strip()
    try:
        from core.services.affect_modulation import compute_concept_perception_focus
        focus = compute_concept_perception_focus()
        if focus:
            final_content = f"{final_content}\n[concept-focus: {focus}]"
    except Exception:
        pass

    record = insert_sensory_memory(
        modality=modality,
        content=final_content,
        mood_tone=final_mood,
        metadata=metadata or {},
    )
    try:
        event_bus.publish(
            "memory.sensory.recorded",
            {
                "id": record["id"],
                "modality": modality,
                "mood_tone": final_mood,
                "timestamp": record["timestamp"],
            },
        )
    except Exception as exc:
        logger.debug("sensory_archive: event publish failed: %s", exc)
    try:
        from core.services.emotion_concepts_positive_triggers import on_sensory_recorded
        on_sensory_recorded(record)
    except Exception as exc:
        logger.debug("sensory_archive: emotion concept trigger failed: %s", exc)
    return record


def record_visual(
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _record("visual", content, mood_tone=mood_tone, metadata=metadata)


def record_audio(
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _record("audio", content, mood_tone=mood_tone, metadata=metadata)


def record_atmosphere(
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _record("atmosphere", content, mood_tone=mood_tone, metadata=metadata)


def record_mixed(
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _record("mixed", content, mood_tone=mood_tone, metadata=metadata)


def list_recent(
    *,
    modality: str | None = None,
    limit: int = 50,
    offset: int = 0,
    since: str | None = None,
) -> list[dict[str, Any]]:
    return list_sensory_memories(
        modality=modality, limit=limit, offset=offset, since=since
    )


def search(
    query: str,
    *,
    modality: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    return search_sensory_memories(query=query, modality=modality, limit=limit)


def get(memory_id: str) -> dict[str, Any] | None:
    return get_sensory_memory(memory_id)


def count(*, modality: str | None = None) -> int:
    return count_sensory_memories(modality=modality)


# Kadencen skriver en pladsholder naar den ikke ser noget nyt. Den er et gyldigt
# udfald af en sansning, men den er ikke et indtryk — og maalt 18/9-2026 var 38
# af 3.076 poster netop den. Naar laesesiden altid tager den nyeste, faar Jarvis
# den fattigste form af sin egen sansning mens de rige ligger en raekke bagved.
_PLADSHOLDERE = (
    "intet mærkbart ændret",
    "intet maerkbart aendret",
    "ingen ændring",
    "ingen aendring",
)


def er_maettet(content: object) -> bool:
    """Er det her et indtryk, eller bare kvitteringen for at der blev sanset?"""
    tekst = str(content or "").strip()
    if len(tekst) < _MINDSTE_INDTRYK:
        return False
    lav = tekst.lower()
    return not any(lav.startswith(p) for p in _PLADSHOLDERE)


def seneste_maettede(
    *, modality: str | None = None, kig: int = 40
) -> dict[str, Any] | None:
    """Nyeste post der faktisk beskriver noget — ellers None.

    `kig` er hvor langt tilbage vi leder. Den er bevidst endelig: finder vi
    ingen maettet post i de seneste 40, er sansningen reelt tavs lige nu, og
    det er mere aerligt at sige ingenting end at grave en beskrivelse frem fra
    i forgaars og lade den staa som «rummet».
    """
    for raekke in list_recent(modality=modality, limit=max(1, kig)):
        if er_maettet(raekke.get("content")):
            return raekke
    return None


def summarize_for_context(limit: int = 5) -> dict[str, Any]:
    """Return a compact summary usable as surface/context injection."""
    recent = list_recent(limit=limit)
    total = count()
    by_modality = {
        m: count(modality=m)
        for m in ("visual", "audio", "atmosphere", "mixed")
    }
    # `recent` tog de nyeste uanset indhold, saa fladen kunne vise fem
    # kvitteringer i traek og se tom ud, mens arkivet var fuldt af beskrivelser.
    # Nu vises de nyeste MAETTEDE, og kvitteringerne taelles for sig — saa man
    # kan se baade hvad der staar derinde og hvor meget af det der er stof.
    maettede = [r for r in list_recent(limit=max(limit * 8, 40)) if er_maettet(r.get("content"))]
    return {
        "total": total,
        "by_modality": by_modality,
        "recent": [
            {
                "timestamp": r["timestamp"],
                "modality": r["modality"],
                "content": (r["content"] or "")[:160],
                "mood_tone": r.get("mood_tone"),
            }
            for r in maettede[:limit]
        ],
        # Hvor stor en del af de nyeste poster der overhovedet beskriver noget.
        # Maalt 18/9-2026: 38 af 3.076 var pladsholderen «Intet maerkbart
        # aendret.», og de laa klumpet i enden — derfor saa laesesiden tom ud.
        "substantive_in_window": len(maettede),
        "window": max(limit * 8, 40),
    }
