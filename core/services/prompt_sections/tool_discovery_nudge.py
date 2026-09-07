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

# Taersklerne bor i matcheren (``tool_lexical_match.GULV`` og ``FAKTOR``) og
# importeres kun her til observationsfladen. Den gamle cosine-taerskel paa 0,75
# stod haardkodet BEGGE steder, saa fladen blev ved med at rapportere 0,75
# efter at matcheren var skiftet — én kilde, ikke to.

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

    **Skyggen var lukket i nogle timer 7/9 og er TAENDT igen samme dag** — men
    paa en ny matcher. Historien er vaerd at have, saa den ikke skal genfindes:

    Cosinus-varianten koerte et doegn i skygge og svarede nej. Maalt paa 40-60
    aegte beskeder: 0 nudges, afstand top1→top2 = 0,0106 i snit, saa
    ranglisten var reelt vilkaarlig — ``curiosity_read_mood`` laa 0,017 fra
    toppen paa en besked om agenter. To ting jeg proevede foerst hjalp ikke:
    porten foer opslaget flyttede margin 0,0099 → 0,0108 (intet), og z-score
    var 2,6-4,1 paa HVER besked, saa den kunne ikke skille noget fra noget.

    Det der VIRKEDE i de faa rigtige traef var altid leksikalsk — «branches» →
    ``git_branch``, «interlanguage» → ``interlanguage_protocol``. Matcheren er
    derfor skiftet til ``core.services.tool_lexical_match``, hvor et aegte traef
    staar KLART over feltet (``provider_health_check`` 2,22 mod 1,36) og et
    tilfaeldigt ligger lige med et dusin andre. 10 af 60 beskeder faar et bud;
    de foerste ti var rigtige nok til at maale videre paa.

    Skyggen er taendt igen fordi den nu er gratis: opslaget roerer ingen model,
    saa den koster ikke laengere et embedding-kald pr. besked. Fremadrettede
    data er stadig den eneste valide test af en taerskel kalibreret paa ét
    datasaet (Jarvis' overfit-indvending), og nu kan vi faa dem uden at betale.

    ``_enabled`` er stadig OFF: skyggen skal levere sit doegn foerst.

    Self-safe: kan config ikke laeses, maaler vi videre — skyggen kan pr.
    konstruktion ikke naa prompten, saa den sikre vej her er TIL (modsat
    ``_enabled``, hvor en fejl ville havne i hans prompt).
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


def _log_nudge(navn: str, session_id: str, score: float, *, gate: bool | None = None) -> None:
    """Fase-1-logging. Uden den kan vi ikke maale om nudgen virker — hverken
    konvertering (nudge -> load -> brug) eller falsk-positiv-raten.

    ``gate`` er intent-gatens dom over det leksikalske bud (None = gaten kørte
    ikke). Den logges OGSAA naar dommen er nej, saa skyggen viser hvad gaten
    fjerner — ellers ville dens virkning vaere usynlig i data.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("tool_discovery.nudge", {
            "tool": navn, "session_id": session_id, "score": round(float(score), 4),
            "gate": gate,
        })
    except Exception as exc:
        logger.debug("tool_discovery_nudge: event fejlede: %s", exc)


_korpus_cache: tuple[int, object] | None = None


def _korpus():
    """Leksikalsk korpus over vaerktoejerne, bygget én gang pr. vaerktoejssaet.

    Cachen noegles paa ANTALLET af definitioner, saa den bygges om naar
    vaerktoejer kommer til eller falder fra, men ikke pr. tur. IDF aendrer sig
    kun med korpuset.
    """
    global _korpus_cache
    from core.services.tool_lexical_match import byg_korpus_fra_definitioner
    from core.tools.simple_tools import get_tool_definitions

    defs = get_tool_definitions() or []
    if _korpus_cache is not None and _korpus_cache[0] == len(defs):
        return _korpus_cache[1]
    k = byg_korpus_fra_definitioner(defs)
    _korpus_cache = (len(defs), k)
    return k


def _matches(besked: str, kandidater: list[str] | None = None):
    """Bedste leksikalske bud blandt ``kandidater``, eller ``None``.

    **Skiftet fra cosinus 7/9-2026.** Embedding-lighed blev maalt paa 60 aegte
    beskeder og kunne ikke skelne: afstanden top1→top2 var 0,0106 i snit, saa
    ranglisten var vilkaarlig, og 40 beskeder gav nul brugbare bud. De faa
    rigtige traef var ALTID leksikalske — «branches» → git_branch — hvor
    embeddingen intet tilfoejede og tit foerte vild («**slet** ikk faa lov» →
    note_delete). Se ``core.services.tool_lexical_match``.

    To ting foelger med skiftet:

    * **Ingen model i vejen.** Opslaget er rene strengoperationer, saa
      sektionen koster ikke laengere et embedding-kald pr. besked — hverken
      taendt eller i skygge.
    * **Porten ligger FOER opslaget.** Foer scorede vi mod alle 448 og kasserede
      bagefter dem der stod i kataloget; det aad topplaceringen i 38 % af
      turene. Nu rangeres kun blandt de usynlige.
    """
    try:
        return _korpus().slaa_op(besked, kandidater, _brugerens_hyppige_ord())
    except Exception as exc:
        logger.debug("tool_discovery_nudge: opslag fejlede: %s", exc)
        return None


_BRUGERORD_NOEGLE = "tool_discovery_nudge:brugerord"
_BRUGERORD_TTL = 6 * 3600
_BRUGERORD_STIKPROEVE = 1500


def _brugerens_hyppige_ord() -> frozenset[str]:
    """Ord han bruger hele tiden — spaerret uanset hvor saerkende de er.

    IDF er ensidig: den maaler sjaeldenhed blandt VAERKTOEJERNE og ved intet
    om hans sprog. Maalt 7/9-2026 var det matcherens stoerste stoejkilde:
    «claude» staar i 7,2 % af hans beskeder, og `dispatch_to_claude_code` tog
    derfor 22 af 72 bud (30 %) — hver gang paa saetninger som «Claude kigger
    paa det..», hvor han fortaeller mig hvad der sker, ikke beder om noget.

    Samme gjaldt «vision» (9 bud, alle mens han talte OM vision-modeller) og
    «listen» → mic_listen (dansk bestemt form af «liste»).

    Beregnes af hans egne beskeder og caches i 6 timer; fejler den, falder vi
    tilbage til den haandlavede stopordsliste alene. Aldrig en undtagelse ud —
    sektionens kontrakt er at den ikke kan vaelte prompt-bygningen.
    """
    try:
        from core.services import shared_cache
        cachet = shared_cache.get(_BRUGERORD_NOEGLE)
        if cachet is not None:
            return frozenset(cachet)
    except Exception as exc:
        logger.debug("tool_discovery_nudge: brugerord-cache utilgaengelig: %s", exc)

    try:
        from core.services.chat_sessions import recent_user_message_texts
        beskeder = recent_user_message_texts(limit=_BRUGERORD_STIKPROEVE)
    except Exception as exc:
        logger.debug("tool_discovery_nudge: kunne ikke laese beskeder: %s", exc)
        return frozenset()

    try:
        from core.services.tool_lexical_match import hyppige_ord_hos_brugeren
        ord_ = hyppige_ord_hos_brugeren(list(beskeder or ()))
    except Exception as exc:
        logger.debug("tool_discovery_nudge: brugerord fejlede: %s", exc)
        return frozenset()

    try:
        from core.services import shared_cache
        shared_cache.set(_BRUGERORD_NOEGLE, sorted(ord_), ttl_seconds=_BRUGERORD_TTL)
    except Exception as exc:
        logger.debug("tool_discovery_nudge: kunne ikke cache brugerord: %s", exc)
    return ord_


def _intent_gate(besked: str, navn: str) -> bool:
    """Modellens dom, eller ``False`` hvis den ikke kunne afgives.

    Fejler LUKKET med vilje: stoej er vaerre end ingen nudge, saa tvivl skal
    koste buddet. Gaten har sin egen hårde deadline (1,5 s mod maalte 0,19 s),
    fordi ollama-kald koeer 28-91 s naar den er optaget — samme risiko der er
    dokumenteret som cut-off-roden i ``prompt_contract._timed_result``.
    """
    try:
        from core.services.local_intent_gate import er_bestilt
        return bool(er_bestilt(besked, navn, _registrerede_navne().get(navn, "")))
    except Exception as exc:
        logger.debug("tool_discovery_nudge: intent-gate fejlede: %s", exc)
        return False


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

    registreret = _registrerede_navne()
    if not registreret:
        return ""  # kan vi ikke krydstjekke, foreslaar vi ingenting
    katalog = _katalog_tekst()

    # Porten FOER opslaget. Tidligere scorede vi mod alle 448 vaerktoejer og
    # kasserede bagefter dem der allerede stod i kataloget — det aad
    # topplaceringen i 38 % af turene, saa de usynlige (som hele sektionen
    # findes for) konkurrerede om pladser der alligevel blev smidt vaek.
    kandidater = [
        navn for navn, beskrivelse in registreret.items()
        if not _er_internt(beskrivelse)      # hans eget maskineri, ikke Bjoerns verden
        and not _staar_i_katalog(navn, katalog)  # staar allerede i klartekst
        and not _undertrykt(sid, navn)
    ]
    if not kandidater:
        return ""

    # Dobbelt vaern med vilje: ``_matches`` fanger selv sine egne fejl, men
    # sektionens kontrakt er «kaster aldrig», og den maa ikke afhaenge af at
    # en fremtidig matcher husker at vaere hoeflig.
    try:
        traef = _matches(besked, kandidater)
    except Exception as exc:
        logger.debug("tool_discovery_nudge: opslag fejlede: %s", exc)
        return ""
    if traef is None:
        return ""   # det NORMALE svar: 50 af 60 aegte beskeder

    # ANDET LED: ordmatchen fandt HVILKET vaerktoej; en lille lokal model
    # afgoer OM beskeden er en bestilling. Maalt paa 35 aegte bud: praecision
    # 17 % -> 100 %, 26 af 26 forkerte afvist. Se core.services.local_intent_gate.
    bestilt = _intent_gate(besked, traef.navn)
    _log_nudge(traef.navn, sid, traef.score, gate=bestilt)
    if not bestilt:
        return ""
    if not _enabled():
        # Skygge: maalingen er skrevet, men prompten er urørt. Vi husker heller
        # ikke nudget — suppression hoerer til den synlige kanal.
        return ""
    _husk_nudge(sid, traef.navn)
    # Traeffet baerer de ord det byggede paa, saa han kan afvise et daarligt bud
    # paa stedet i stedet for at skulle tro paa et tal.
    return (
        "📎 Vaerktoej uden for din nuvaerende kasse: `%s` — din besked naevner "
        "%s. Kald load_more_tools(names=[\"%s\"]) hvis det er relevant."
        % (traef.navn, ", ".join("«%s»" % o for o in traef.ord), traef.navn)
    )


def _GULV() -> float:
    """Laeses ved kaldet, ikke ved import — saa fladen ikke fryser en gammel vaerdi."""
    from core.services.tool_lexical_match import GULV
    return GULV


def _FAKTOR() -> float:
    from core.services.tool_lexical_match import FAKTOR
    return FAKTOR


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
        "gulv": _GULV(),
        "margin_faktor": _FAKTOR(),
        "suppression_seconds": _SUPPRESSION_S,
        "matched": bool(tekst),
        "section_chars": len(tekst),
    }
