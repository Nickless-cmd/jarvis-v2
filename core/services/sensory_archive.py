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
from core.services.sensory_source import normalize_metadata

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


# Prompt-ekko — modellens EGEN instruktion ekkoet tilbage som «indtryk».
#
# Maalt 5/10-2026: 30 poster i `sensory_memories` var ikke sanseindtryk men
# vision-modellens gengivelse af sin opgave: «We need answer in Danish only.
# Need describe changes since previous observation…». Familien er
# SELVFORSTAERKENDE — den forrige beskrivelse foeres tilbage ind i prompten, saa
# et ekko bliver til naeste ekko. Maalt 13/9: tre poster i traek, hvor den
# sidste citerer den forrige — «previous description provided is weird: "We need
# answer in Danish only…"».
#
# Vaernene fandtes i forvejen, men ingen af dem kigger efter dette:
# `_uden_raa_tanke` fjerner `<think>`-blokke, og `er_kvittering` fanger «Intet
# maerkbart aendret.». Ekkoet har ingen tags og er ingen kvittering.
#
# Bevidst smalt: hvert moenster er en vending en BESKRIVELSE af et rum ikke
# bruger. En falsk positiv koster et aegte indtryk, og det er dyere end at
# overse et ekko.
_PROMPT_EKKO_MOENSTRE = (
    # Den engelske familie — modellen taenker hoejt paa engelsk.
    re.compile(r"\bwe need (?:answer|describe|infer|observe|compare|analy[sz]e)\b", re.I),
    re.compile(r"\bneed (?:to )?(?:describe|infer|answer|observe|compare|analy[sz]e)\b", re.I),
    re.compile(r"\banswer (?:only )?in danish\b", re.I),
    re.compile(r"\bwe have (?:only )?(?:one |current |the )?(?:image|billede)\b", re.I),
    re.compile(r"\bprevious description\b", re.I),
    re.compile(r"\b(?:the )?user (?:wants|asks)\b", re.I),
    re.compile(r"\bi need to describe\b", re.I),
    # Den danske familie — samme ekko, andet sprog.
    re.compile(r"\b(?:vi|jeg) skal beskrive\b", re.I),
    re.compile(r"\bsidste beskrivelse var\b", re.I),
    re.compile(r"\bbrugeren (?:vil|beder|spørger)\b", re.I),
    # Prompten selv, ordret indsat midt i teksten.
    re.compile(r"\bspørgsmålet\s*:", re.I),
    re.compile(r"\bsvar kun\b", re.I),
    re.compile(r"\bhvis intet mærkbart\b", re.I),
    # Digtning: modellen opdager at billedet er ubrugeligt og finder paa et rum.
    re.compile(r"\bmin fantasi til at skabe\b", re.I),
    # Raesonnement uden <think>-tags (maalt 5/10-2026): modellen skriver sin
    # EGEN nummererede plan ind som indtryk — «1. **Analyser brugerens
    # anmodning:** … 6. **Endelig polering**». `_uden_raa_tanke` fanger den
    # ikke, for der er ingen tags. To poster (1/10), den ene 4.567 tegn ren
    # tankeraekke. Bevidst smalt: vendingen hoerer til en PLAN, ikke til en
    # beskrivelse af et rum.
    re.compile(r"\banaly[sz]er brugerens\b", re.I),
)

# Svar-preamble — modellen ANMELDER sit svar i stedet for at sanse.
# «Her er en beskrivelse af rummet: **Atmosfæren og lyset** Der hersker …»
# Maalt 5/10-2026: 20 poster. Her STRYGES anmeldelsen frem for at posten
# afvises — modsat ekkoet baerer resten et aegte indtryk.
#
# Ledet efter et NAVNORD, ikke bare «her er»: «Her er ingen mennesker» er en
# gyldig beskrivelse af et rum og maa ikke rammes.
#
# Kolon-hullet (maalt 5/10-2026): `active_sensing` skriver sin mixed-sansning
# som «Jeg så og lyttede samtidig. Visuelt: Her er en beskrivelse af …». Der
# staar altsaa et KOLON mellem leddet og anmeldelsen — og den gamle graense
# kraevede `(?<=[.!?])`, saa tre poster slap igennem i maanedvis (16/5, 8/9).
# Kolon er tilfoejet som graense, og `\s*` frem for `\s+` daekker ogsaa
# «Visuelt:Her er» uden mellemrum.
_PREAMBLE_MOENSTER = re.compile(
    r"(?:\A|(?<=[.!?:])\s*)(?:okay,?\s*)?(?:her er|lad os)\b[^:.]{0,80}?"
    r"(?:beskrivelse|sansebeskrivelse|registrering|gengivelse|opsummering|skildring)\b",
    re.I,
)

#: Hvor en saetning slutter. Bruges til at rykke et klip tilbage til sidste
#: hele led, saa der ikke staar et halvt stykke tilbage.
_SAETNINGSSLUT = re.compile(r"[.!?](?=\s|$)|\n\n")


def klip_ved_saetningsgraense(tekst: str, pos: int) -> str:
    """Klip `tekst` ved `pos`, men ryk tilbage til sidste saetningsgraense.

    Uden det stod «Da billedet er helt sort, maa jeg bruge» tilbage som et halvt
    led — over laengdekravet, og derfor vaerre end ingenting: det ligner et
    indtryk. Er der ingen graense foer `pos`, findes der intet indtryk.
    """
    hale = tekst[:pos]
    sidste = None
    for traef in _SAETNINGSSLUT.finditer(hale):
        sidste = traef
    return hale[: sidste.end()].strip() if sidste else ""


def _fjern_anmeldelse(tekst: str, traef: re.Match[str]) -> str:
    """Fjern selve anmeldelsen — ikke resten af posten.

    Maalt 5/10-2026: «Det er sent paa aftenen, og rummet er praeget af en daempet
    atmosfaere. Her er en detaljeret beskrivelse: **Lys og skygger:** …» har et
    aegte indtryk PAA BEGGE SIDER af anmeldelsen. Baade at klippe foran og at
    klippe bagved ville tabe et af dem, saa kun anmeldelses-leddet fjernes.

    Slutter anmeldelsen med kolon, er det den der afgraenser. Goer den ikke
    («… baseret paa det visuelle indtryk. Det foeles som …»), er det foerste
    saetningsslutning i stedet.
    """
    rest = tekst[traef.end():]
    kolon = rest.find(":")
    punktum = _SAETNINGSSLUT.search(rest)
    if kolon >= 0 and (punktum is None or kolon < punktum.start()):
        slut = traef.end() + kolon + 1
    elif punktum is not None:
        slut = traef.end() + punktum.end()
    else:
        slut = len(tekst)

    foer = tekst[: traef.start()].strip()
    efter = tekst[slut:].strip()
    return f"{foer} {efter}".strip() if foer else efter


#: Maskinelt lag fra `active_sensing`: «Jeg så og lyttede samtidig. Visuelt:
#: … | Lyd: …». Det er STRUKTUR, ikke et indtryk — og naar gaten skal afgoere
#: om der er noget tilbage efter et klip, maa laget ikke taelle med.
#:
#: Maalt 5/10-2026: post `931e8920` var en ren tankeraekke, men klippet efterlod
#: «Jeg så og lyttede samtidig. Visuelt: 1.» — 39 tegn wrapper og et listetal,
#: over `_MINDSTE_INDTRYK`, og derfor gemt som om det var en sansning.
_WRAPPER_LAG = re.compile(
    r"^\s*Jeg så og lyttede samtidig\.\s*|^\s*Visuelt:\s*|\s*\|\s*Lyd:\s*[^|]*",
    re.I,
)


def _uden_wrapper(tekst: str) -> str:
    """Teksten uden `active_sensing`s maskinelle lag — til VURDERING, ikke gem."""
    return _WRAPPER_LAG.sub("", tekst or "").strip()


def _uden_stillads(content: str) -> tuple[str, bool]:
    """Fjern stillads foran et indtryk. Returnerer `(tekst, var_stillads)`.

    To familier, begge maalt i drift 5/10-2026 (29 + 20 poster):

    * **Prompt-ekko** — modellens egen instruktion. Her KLIPPES der ved foerste
      traef, men kun ved en saetningsgraense, saa et aegte indtryk FORAN ekkoet
      bevares. Maalt 27/9 begyndte en post med «Billedet viser en stue med to
      personer …» og fortsatte med prompten ordret.
    * **Svar-preamble** — «Her er en beskrivelse af rummet: …». Anmeldelsen
      stryges; indtrykket paa begge sider af den beholdes.

    Er der intet indtryk tilbage, er posten rent stillads, og `_record` afviser
    den. Det gaelder ogsaa naar resten kun er `active_sensing`s wrapper-lag:
    «Jeg så og lyttede samtidig. Visuelt: 1.» ser ud som 39 tegn indhold, men
    der staar intet bag laget.
    """
    tekst = (content or "").strip()
    roert = False

    foerste = None
    for moenster in _PROMPT_EKKO_MOENSTRE:
        traef = moenster.search(tekst)
        if traef is not None and (foerste is None or traef.start() < foerste):
            foerste = traef.start()
    if foerste is not None:
        tekst = klip_ved_saetningsgraense(tekst, foerste)
        roert = True
        # En rest der kun er wrapper-laget er ikke et indtryk. Uden dette
        # stod «Jeg så og lyttede samtidig. Visuelt: 1.» tilbage som en post.
        if len(_uden_wrapper(tekst)) < _MINDSTE_INDTRYK:
            tekst = ""

    anmeldelse = _PREAMBLE_MOENSTER.search(tekst)
    if anmeldelse is not None:
        tekst = _fjern_anmeldelse(tekst, anmeldelse)
        roert = True

    return tekst, roert


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

    # Stillads-gaten — den tredje indgangsgraense (5/10-2026). Fjerner
    # prompt-ekko og svar-preamble FOER kvitterings-gaten, fordi et ekko kan
    # indeholde en pladsholder og omvendt. Er der intet indtryk tilbage, er
    # posten rent stillads og afvises som raesonnement ovenfor.
    content, var_stillads = _uden_stillads(content)
    if var_stillads and len(content) < _MINDSTE_INDTRYK:
        raise ValueError(
            "sensory memory content is scaffolding (prompt echo or answer "
            "preamble), not an impression"
        )

    # Kvitterings-gaten — den anden indgangsgrænse. Et sanseindtryk markerer at
    # noget ÆNDREDE sig; «Intet mærkbart ændret.» og et lyt der endte i
    # `silence` er svaret på at der ikke var noget at sanse. De arkiveres ikke,
    # men returneres som en tydelig «sprunget over», så kalderen kan sige sandt
    # i stedet for at bogføre et indtryk der aldrig blev skrevet.
    if not skal_arkiveres(content):
        return {
            "id": None,
            "timestamp": None,
            "modality": modality,
            "content": content.strip(),
            "skipped": True,
            "reason": "kvittering",
        }

    # Auto-extract mood if not provided
    final_mood = mood_tone
    if final_mood is None:
        final_mood = _extract_mood_from_content(content, modality)

    # Concept-perception note (Layer 2b memory enrichment) — i METADATA, ikke
    # i indholdet.
    #
    # MÅLT 5/10-2026: noten blev skrevet ind i `content`, og 841 af 2.744 poster
    # (31%) bar den. Median 28% af en posts indhold var prompt-instruktion —
    # «[concept-focus: Bemærk særligt menneskelig tilstedeværelse …]» — ikke et
    # sanseindtryk. Det er samme fejlform som prompt-ekkoerne: stillads arkiveret
    # som indhold, hvor det læses som noget Jarvis har sanset.
    #
    # Noten er en INSTRUKTION til hvad der skal lægges mærke til næste gang. Den
    # hører i prompten (se `visual_memory.py`, hvor den stadig tilføjes) — ikke i
    # arkivet over hvad der BLEV sanset. Ingen læser den ud af `content`; målt
    # med grep over core/ og apps/ er `visual_memory.py` den eneste anden bruger,
    # og den bygger en prompt.
    #
    # Funktionen bevares uændret: den er stadig tilgængelig på posten, nu under
    # `metadata["concept_focus"]`, så intet går tabt — det flytter kun felt.
    final_content = content.strip()
    extra_meta: dict[str, Any] = {}
    try:
        from core.services.affect_modulation import compute_concept_perception_focus
        focus = compute_concept_perception_focus()
        if focus:
            extra_meta["concept_focus"] = focus
    except Exception:
        pass

    record = insert_sensory_memory(
        modality=modality,
        content=final_content,
        mood_tone=final_mood,
        # Kilden er fri tekst fra kalderen, og når kalderen er en rutine, opdigtes
        # et nyt navn hver nat — målt 28/9-2026: 69 navne for ni kilder. Her er
        # det ene punkt alle skrivninger går igennem, så her foldes navnet.
        metadata=normalize_metadata({**(metadata or {}), **extra_meta}),
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

# Kvitteringer der ikke er pladsholder-TEKSTER men kvitteringer for et udfald.
# Lyd-siden skriver sin klassifikation som indhold, i to formater kodebasen
# selv producerer: «Jeg lyttede til rummet. Klassifikation: silence (amplitude
# …)» (active_sensing) og «Lydbillede: silence» (ambient_sound). Begge betyder
# at der ikke var noget at høre. Målt 28/9-2026: 24 sådanne poster, nyeste 26/9.
# Bevidst snævert: en BESKRIVELSE der nævner 'silence' («…kategori 'silence'
# betyder, at der er en meget lav lydintensitet») er et indtryk og rammes ikke.
_KVITTERING_MOENSTRE = (
    re.compile(r"(?:klassifikation|lydbillede):\s*silence\b", re.IGNORECASE),
)

# Hvornår en kvittering er en sansning. Ukendt værdi falder til «skip».
_KVITTERING_MODES = ("skip", "always")


def er_kvittering(content: object) -> bool:
    """Er dette kvitteringen for at der blev sanset — ikke et indtryk?

    Fanger to familier: pladsholder-teksterne ("Intet mærkbart ændret.") og
    lyd-klassifikationen `silence`, som betyder at der ikke var noget at høre.
    """
    tekst = str(content or "").strip()
    if not tekst:
        return True
    lav = tekst.lower()
    if any(lav.startswith(p) for p in _PLADSHOLDERE):
        return True
    return any(m.search(tekst) for m in _KVITTERING_MOENSTRE)


def _kvittering_mode() -> str:
    """Hvornår en kvittering er en sansning: skip | always."""
    try:
        from core.runtime.settings import load_settings

        raa = str(load_settings().sensory_receipt_archive_mode or "")
    except Exception as exc:  # indstillingerne kan ikke læses → sikkert valg
        logger.debug("sensory_archive: kunne ikke læse indstilling: %s", exc)
        return "skip"
    mode = raa.strip().lower()
    return mode if mode in _KVITTERING_MODES else "skip"


def skal_arkiveres(content: object) -> bool:
    """Skal denne tekst arkiveres som en sansning?

    `er_maettet` har svaret på det siden 18/9 — men kun på LÆSESIDEN: arkivet
    blev ved med at fyldes med kvitteringer, og filteret skjulte dem bagefter.
    Her er det samme spørgsmål flyttet til det ene punkt alle skrivninger går
    igennem, så hanen lukkes i stedet for at gulvet moppes.
    """
    if _kvittering_mode() == "always":
        return True
    return not er_kvittering(content)


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
