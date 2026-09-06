"""Peg paa de vaerktoejer han ikke kan se — han kan ikke soege efter det han ikke ved findes.

Maalt 6/9-2026: 429 registrerede tools, 328 (76 %) aldrig brugt. Ikke fordi de
er ubrugelige, men fordi de er usynlige. Visible-lane sender 48 pr. tur
(``VISIBLE_MAX_TOOLS``), og ``build_catalog_text()`` viser kun kerne-grupperne i
klartekst — resten naevnes som gruppe-ord. ``load_more_tools`` er REAKTIV: den
hjaelper kun hvis han allerede ved at noget findes. Opdagelse er ikke soegning.

Det her er ``skill_relevance_surface`` for tools, ikke en ny mekanisme. Samme
grund (et ritual om at huske at slaa op holder ikke), samme form: matcheren
koster et embedding-kald, saa den submittes som future i fase 1-trádpuljen og
hentes med ``_timed_result(..., default="")`` — fejler den, forsvinder
sektionen bare.

Definition af «usynligt tool» (skarp, fra spec'en): et tool hvis navn IKKE
staar i klartekst i ``build_catalog_text()``-outputtet. Puljen paa 48 vaelges
FOERST efter prompt-assembly, saa den kan ikke filtreres imod her — kataloget
er det rigtige filter.

Spec: docs/superpowers/specs/2026-09-06-tool-discovery-nudge-design.md
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Cosine-taerskel. Spec'en vaelger >= (ikke >) — laast i test.
_THRESHOLD = 0.45
_TOP_K = 8

# Max ét nudge pr. tur. Stoej er vaerre end ingen nudge: laerer han at kanalen
# er stoej, holder han op med at laese den, og saa er den doed for altid.
_MAX_NUDGES = 1

# Samme tool nudges ikke igen i samme session foer vinduet er ude.
_SUPPRESSION_S = 1800  # 30 min
_SUPPRESSION_PREFIX = "tool_discovery_nudge:"

# Arvet fra arketypen: under denne laengde er beskeden smaasnak. Sparer et
# embed-kald pr. tur paa praecis de ture hvor der alligevel aldrig er et match.
_MIN_MESSAGE_CHARS = 15


def _enabled() -> bool:
    """Kill-switch. Self-safe: kan config ikke laeses, nudger vi.

    Samme form som arketypens ``_enabled``. Sektionen faar DERUDOVER den live
    sektion-kontakt gratis, fordi den registreres som en navngiven sektion i
    prompt-assembly (``central_switches`` scope ``prompt_section``).
    """
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("tool_discovery_nudge_enabled", True))
    except Exception:
        return True


def _er_prewarm(session_id: str) -> bool:
    """Prewarm-ture varmer cachen — de skal ikke koste et embedding-kald.

    To signaler, begge brugt i prompt_contract: throwaway-sessionen
    ``__prewarm__`` og ``assembly_prewarm.is_prewarm_active()``.
    """
    if str(session_id or "").strip() == "__prewarm__":
        return True
    try:
        from core.services.assembly_prewarm import is_prewarm_active
        return bool(is_prewarm_active())
    except Exception:
        return False


def _registrerede_navne() -> set[str]:
    """Navne der FAKTISK findes lige nu.

    Embedding-DB'en har 458 vektorer mod 429 registrerede — forskellen er
    foraeldede og aliassede vektorer. Uden dette krydstjek ville nudgen kunne
    foreslaa et navn der ikke laengere findes, og saa ville han kalde
    load_more_tools paa noget der ikke er der.
    """
    try:
        from core.tools.simple_tools import get_tool_definitions
        ud: set[str] = set()
        for d in get_tool_definitions() or []:
            navn = ((d.get("function") or {}).get("name") or d.get("name") or "")
            if navn:
                ud.add(str(navn))
        return ud
    except Exception as exc:
        logger.debug("tool_discovery_nudge: kunne ikke laese registret: %s", exc)
        return set()


def _katalog_tekst() -> str:
    """Katalogets klartekst. Tom streng hvis den ikke kan laeses."""
    try:
        from core.services.tool_catalog import build_catalog_text
        return build_catalog_text() or ""
    except Exception as exc:
        logger.debug("tool_discovery_nudge: kunne ikke laese kataloget: %s", exc)
        return ""


def _staar_i_katalog(navn: str, katalog: str) -> bool:
    """Staar NAVNET i klartekst i kataloget? Saa behoever han intet nudge.

    Praecist navne-opslag frem for at tokenisere katalogets prosa: et tool der
    hedder «search» ville ellers blive filtreret af ordet «search» i en
    saetning. Ordgraenserne sikrer at «read_file» ikke ogsaa matcher
    «read_file_lines».
    """
    if not navn or not katalog:
        return False
    return re.search(rf"\b{re.escape(navn)}\b", katalog, re.IGNORECASE) is not None


def _undertrykt(session_id: str, navn: str) -> bool:
    if not session_id:
        return False  # uden session kan vi ikke huske — men vi tier ikke af den grund
    try:
        from core.services import shared_cache
        return shared_cache.get(f"{_SUPPRESSION_PREFIX}{session_id}:{navn}") is not None
    except Exception:
        return False


def _husk_nudge(session_id: str, navn: str) -> None:
    if not session_id:
        return
    try:
        from core.services import shared_cache
        shared_cache.set(
            f"{_SUPPRESSION_PREFIX}{session_id}:{navn}", True, ttl_seconds=_SUPPRESSION_S,
        )
    except Exception as exc:
        logger.debug("tool_discovery_nudge: kunne ikke gemme suppression: %s", exc)


def _log_nudge(navn: str, session_id: str, score: float) -> None:
    """Fase-1-logging. Uden den kan vi ikke maale om nudgen virker — hverken
    konvertering (nudge -> load -> brug) eller falsk-positiv-raten."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("tool_discovery.nudge", {
            "tool": navn, "session_id": session_id, "score": round(float(score), 4),
        })
    except Exception as exc:
        logger.debug("tool_discovery_nudge: event fejlede: %s", exc)


def _matches(besked: str) -> list[tuple[str, float]]:
    """``top_k_similar`` returnerer (navn, score)-TUPLER — ikke dicts som
    arketypens matcher. Defensiv udpakning: en misformet raekke springes over
    frem for at vaelte sektionen."""
    from core.services.tool_embeddings import top_k_similar
    ud: list[tuple[str, float]] = []
    for r in top_k_similar(besked, k=_TOP_K) or []:
        try:
            navn, score = str(r[0] or "").strip(), float(r[1])
        except Exception:
            continue
        if navn:
            ud.append((navn, score))
    return ud


def tool_discovery_nudge_section(
    user_message: str, session_id: str | None = None,
) -> str:
    """Prompt-sektion der peger paa ET relevant vaerktoej uden for hans kasse.

    Kaster aldrig — en fejlende matcher maa ikke kunne vaelte prompt-bygningen.
    """
    besked = str(user_message or "").strip()
    if not besked or len(besked) < _MIN_MESSAGE_CHARS:
        return ""
    # prompt-assembly sender session_id=None paa ture uden session. Normalisér
    # ét sted, saa hverken suppression eller event-payloaden ser et None.
    sid = str(session_id or "")
    if _er_prewarm(sid):
        return ""
    if not _enabled():
        return ""

    try:
        traef = _matches(besked)
    except Exception as exc:
        # Ollama nede, tom embedding-DB, DB-laas — alle ender her.
        logger.debug("tool_discovery_nudge: opslag fejlede: %s", exc)
        return ""
    if not traef:
        return ""

    registreret = _registrerede_navne()
    if not registreret:
        return ""  # kan vi ikke krydstjekke, foreslaar vi ingenting
    katalog = _katalog_tekst()

    valgt: list[tuple[str, float]] = []
    for navn, score in traef:
        if score < _THRESHOLD:
            continue                      # sorteret desc → resten er ogsaa under
        if navn not in registreret:
            continue                      # foraeldet/alias-vektor
        if _staar_i_katalog(navn, katalog):
            continue                      # staar allerede i klartekst
        if _undertrykt(sid, navn):
            continue
        valgt.append((navn, score))
        if len(valgt) >= _MAX_NUDGES:
            break

    if not valgt:
        return ""

    navn, score = valgt[0]
    _husk_nudge(sid, navn)
    _log_nudge(navn, sid, score)
    return (
        "📎 Vaerktoej uden for din nuvaerende kasse: `%s` — opgaven matcher det "
        "(%.2f). Kald load_more_tools(names=[\"%s\"]) hvis det er relevant."
        % (navn, score, navn)
    )


def build_tool_discovery_nudge_surface(
    user_message: str = "", session_id: str | None = None,
) -> dict[str, object]:
    """Observationsflade — hvad nudgen ville sige om denne besked."""
    tekst = tool_discovery_nudge_section(user_message, session_id)
    besked = str(user_message or "").strip()
    return {
        "active": _enabled(),
        "message_chars": len(besked),
        "skipped_short": len(besked) < _MIN_MESSAGE_CHARS,
        "threshold": _THRESHOLD,
        "suppression_seconds": _SUPPRESSION_S,
        "matched": bool(tekst),
        "section_chars": len(tekst),
    }
