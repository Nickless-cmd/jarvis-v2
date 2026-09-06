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

# Cosine-taerskel. Spec'en foreslog 0,45; maalt paa 60 aegte beskeder ville den
# have nudget paa 60 af 60 ture — 100 %. Kalibreret paa data:
#     0,45 → 60/60 (100 %)   0,70 → 38/60 (63 %)
#     0,75 →  8/60 ( 13 %)   0,80 →  1/60 (  2 %)
# 0,75 er den eneste vaerdi med en frekvens der overhovedet kan forsvares.
# Spec'en vaelger >= (ikke >) — laast i test.
_THRESHOLD = 0.75
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
    """Kill-switch. **Default OFF** — se maalingen nedenfor.

    Spec'en satte default True. Maalt mod den aegte embedding-DB 6/9-2026 holder
    den praemis ikke endnu, fordi modellen (``nomic-embed-text``) er
    engelsk-centrisk mens Bjoern skriver dansk:

        «create a calendar event for friday meeting»
            0.706 create_event · 0.657 delete_event · 0.654 list_events
            → alle fire top-traef er kalender-vaerktoejer. Rent signal.

        «kan du laegge et moede ind i min kalender paa fredag»
            0.694 curiosity_read_dreams · 0.678 read_learning_memo
            · 0.674 note_add · 0.665 calendar_list_events
            → stoej oeverst, det rigtige vaerktoej som nr. 4.

    Scorerne ligger i et smalt baand (0,64-0,75), saa INGEN absolut taerskel kan
    skille signal fra stoej paa danske beskeder: 0,70 ville lukke
    ``curiosity_read_dreams`` ind og ``calendar_list_events`` ude. En
    margin-regel hjaelper heller ikke — selv et korrekt traef som ``gmail_send``
    (0,753) ligger kun 0,009 over stoejen ``nudge_send`` (0,744).

    Spec'ens egen regel afgoer sagen: stoej er vaerre end ingen nudge, fordi han
    laerer at ignorere kanalen. Alt er bygget, testet og logget — det kraever ét
    config-flag at taende, naar sprog-spoergsmaalet er afgjort (flersproget
    embedding-model, eller normalisering af forespoergslen til engelsk).

    Self-safe: kan config ikke laeses, er svaret OFF.

    Samme form som arketypens ``_enabled``. Sektionen faar DERUDOVER den live
    sektion-kontakt gratis, fordi den registreres som en navngiven sektion i
    prompt-assembly (``central_switches`` scope ``prompt_section``).
    """
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("tool_discovery_nudge_enabled", False))
    except Exception:
        return False


def _skygge() -> bool:
    """Skygge-tilstand: REGN nudgen ud og LOG den, men injicér den ikke.

    Uden den er default-OFF en blindgyde: sektionen returnerer tomt foer den
    logger, saa der kommer aldrig fremadrettet data — og fremadrettet data er
    den ENESTE valide test af en taerskel der er kalibreret paa ét datasaet
    (Jarvis' overfit-indvending, 6/9). Skyggen giver maalingen uden at roere
    prompten. Samme moenster som reasoning_interceptor og Agent Smith.

    Default TIL, netop fordi den ikke koster prompten noget.
    """
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("tool_discovery_nudge_shadow", True))
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


# ── Intent-filter (Jarvis' gennemgang 6/9) ─────────────────────────────────
# Broen loeste SPROGET; tilbage stod at embedding-lighed ikke kan skelne «han
# har brug for et vaerktoej» fra «han sagde et ord der ligner et vaerktoej».
# Et «tak for samtalen» ligner note_list i vektorrummet. Tre billige,
# deterministiske lag — ingen model, intet kald — hvert enkelt maalt mod de
# faktiske falske positiver fra 60 aegte beskeder.

# Lag 1: hans EGET maskineri. Markoerer i beskrivelsen, ikke en navneliste, saa
# reglen holder naar der kommer nye vaerktoejer til.
#   nudge_send        «efter inspektion af broenden»   → hans egen nudge-broend
#   resolve_prediction «marker en aaben prediction»     → selvmodel-bogholderi
#   curiosity_*       «laes DINE droemme … 1/5 actions» → eget nysgerrighedsbudget
_INTERNE_MARKOERER = (
    "curiosity:", "bruger 1/", "bruger 2/", "actions.",
    "prediction", "hypothesis", "hypotese", "forudsig",
    "din egen", "dine egne", "dit eget",
    "selvmodel", "self-model", "broenden", "brønden",
    "idle-genererede", "autonom", "internt", "internal use",
)

# Lag 2: sociale ture. «Tak. Det var saa vores foerste samtale.» udloeste
# note_list — der er ingen opgave i en tak.
_SOCIALE = (
    "tak", "takker", "farvel", "hej", "hejsa", "godmorgen", "godnat",
    "held og lykke", "tillykke", "velbekomme", "ha en god", "hav en god",
    "super", "perfekt", "fedt", "nice", "godt arbejde", "veludført",
)
_SOCIAL_MAX_TEGN = 90

# Handleverber. Var foreslaaet som et selvstaendigt LAG 3 (kraev et verbum foer
# nudge). Maalt paa de samme 60 beskeder gjorde den mere skade end gavn:
#     lag 1+2      → 6 nudges, heraf git_log og propose_new_skill (aegte)
#     + lag 3      → 2 nudges — den draebte BEGGE de aegte og kun én stoej
# Grunden er at ekstra sprog er skroebeligt: den aegte besked var «Hebt lige git
# log» med en slaafejl, og «Hebt» er ikke et verbum den kender. Porten er derfor
# ikke i brug; listen lever videre som lag 2's undtagelse, saa «send en mail og
# sig tak» ikke tælles som en ren social tur.
_HANDLEVERBER = (
    "læg", "lægge", "hent", "henter", "vis", "vise", "send", "sende",
    "find", "finde", "søg", "søge", "opret", "oprette", "slet", "slette",
    "skriv", "skrive", "læs", "læse", "kør", "køre", "tjek", "tjekke",
    "start", "starte", "stop", "stoppe", "ret", "rette", "lav", "lave",
    "tilføj", "tilføje", "fjern", "fjerne", "book", "booke", "husk",
    "get", "list", "show", "create", "delete", "run", "check", "add",
    "remove", "search", "read", "write", "open", "fetch", "make",
)


def _er_internt(beskrivelse: str) -> bool:
    """Handler vaerktoejet om HANS indre maskineri frem for Bjoerns verden?"""
    b = str(beskrivelse or "").lower()
    return any(m in b for m in _INTERNE_MARKOERER)


def _er_social(besked: str) -> bool:
    """Kort OG socialt. Laengden alene raekker ikke — «send en mail til bjorn og
    sig tak» er kort og indeholder «tak», men er en opgave."""
    b = str(besked or "").lower().strip()
    if len(b) > _SOCIAL_MAX_TEGN:
        return False
    if not any(re.search(rf"\b{re.escape(o)}\b", b) for o in _SOCIALE):
        return False
    # Et handleverbum ophaever det: saa er der en opgave i saetningen.
    return not _har_handleverbum(b)


# Kun AEGTE boejningsendelser. Et frit \w* lod «find» matche «findings» og
# «list» matche «listen» — saa «Research mode: answer with sourced findings»
# talte som en opgave.
_BOEJNING = r"(?:e|er|ede|et|te|de|r)?"


def _har_handleverbum(besked: str) -> bool:
    b = str(besked or "").lower()
    return any(re.search(rf"\b{re.escape(v)}{_BOEJNING}\b", b) for v in _HANDLEVERBER)


def _registrerede_navne() -> dict[str, str]:
    """Navne der FAKTISK findes lige nu.

    Embedding-DB'en har 458 vektorer mod 429 registrerede — forskellen er
    foraeldede og aliassede vektorer. Uden dette krydstjek ville nudgen kunne
    foreslaa et navn der ikke laengere findes, og saa ville han kalde
    load_more_tools paa noget der ikke er der.
    """
    try:
        from core.tools.simple_tools import get_tool_definitions
        ud: dict[str, str] = {}
        for d in get_tool_definitions() or []:
            f = d.get("function") or {}
            navn = str(f.get("name") or d.get("name") or "")
            if navn:
                ud[navn] = str(f.get("description") or d.get("description") or "")
        return ud
    except Exception as exc:
        logger.debug("tool_discovery_nudge: kunne ikke laese registret: %s", exc)
        return {}


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
    from core.services.query_language_bridge import normalise_for_embedding
    from core.services.tool_embeddings import top_k_similar

    # Broen over sprogforskellen: modellen er engelsk-centrisk, tool-navnene er
    # engelske, og han skriver dansk. Uden den kom curiosity_read_dreams (0,694)
    # foer calendar_list_events (0,665) paa en kalender-besked.
    ud: list[tuple[str, float]] = []
    for r in top_k_similar(normalise_for_embedding(besked), k=_TOP_K) or []:
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
    if not _enabled() and not _skygge():
        return ""
    # Lag 2 foer opslaget: en tak skal heller ikke koste et embedding-kald.
    if _er_social(besked):
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
        if _er_internt(registreret[navn]):
            continue                      # hans eget maskineri, ikke Bjoerns verden
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
    _log_nudge(navn, sid, score)
    if not _enabled():
        # Skygge: maalingen er skrevet, men prompten er urørt. Vi husker heller
        # ikke nudget — suppression hoerer til den synlige kanal.
        return ""
    _husk_nudge(sid, navn)
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
        "shadow": _skygge() and not _enabled(),
        "message_chars": len(besked),
        "skipped_short": len(besked) < _MIN_MESSAGE_CHARS,
        "threshold": _THRESHOLD,
        "suppression_seconds": _SUPPRESSION_S,
        "matched": bool(tekst),
        "section_chars": len(tekst),
    }
