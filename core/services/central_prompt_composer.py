"""core/services/central_prompt_composer.py

Tråd 2 (Intelligent Central-spec §4): Centralen som modellens KONTEKST-KOMPONIST.

Bjørns idé: modellen er en stateless genial gæst. I dag propper vi ALT i en mega-system-prompt hver
tur (awareness, 78 surfaces, somatik, mood) uanset relevans. Men Centralen HOLDER alt alligevel — så
lad den bygge præcis den kontekst DENNE tur kræver. Prompt-evolution bliver dermed "Centralen lærer
RELEVANS-FUNKTIONEN": hvilken kontekst der betyder noget for hvilket input.

TO-DELT PROMPT (cache-bevidst — ellers koster det tokens i stedet for at spare):
  * FAST KERNE (forrest, cachet): SOUL/identitet/system — FROSSEN, rører vi ALDRIG.
  * DYNAMISK HALE (bagest, EFTER cache-grænsen): kun awareness/state denne tur kræver. Her spares.

Dette modul er substratet: tur-type-klassifikator + relevans-vægte (governed) + should_include-switch.
SIKKERHED: shadow-first — should_include returnerer ALTID True medmindre `prompt_relevance_live_enabled`
+ en resolveret relevans-hypotese har bevist en sektion er død vægt for en tur-type. Konservativ ved
tvivl (inkludér). Identitet + sikkerhed = frossen kerne, gates ALDRIG. Alt self-safe, kaster ALDRIG.

STATUS: substrat + switch bygget. Wiring ind i prompt_contract (kald should_include på hale-sektioner,
UDEN FOR build_visible_stable_prefix/cache-grænsen) + relevans-hypotese-generering = næste omhyggelige skridt.
"""
from __future__ import annotations

from typing import Any

_LIVE_FLAG = "prompt_relevance_live_enabled"     # Bjørns switch (default OFF → inkludér alt)
_WEIGHTS_KEY = "prompt_relevance_weights"        # {"turn_type|section": weight} (runtime_state_kv)
_TAIL_LIVE_FLAG = "prompt_tail_relevance_live_enabled"
_INCLUDE_THRESHOLD = 0.3                          # under denne vægt (og live) → udelad sektion
_DOMAIN = "prompt_relevance"                      # §8.1 isoleret mutations-domæne

# FROSNE sektioner der ALDRIG gates (identitet + sikkerhed = frossen kerne).
FROZEN_SECTIONS: frozenset[str] = frozenset({
    "soul", "identity", "user", "security", "safety", "system", "core",
})

# Conservative built-in weights for tail-only context. These labels are already
# after the cache boundary, but they still inflate every visible prompt. Unknown
# sections default to 1.0 and are included.
_DEFAULT_TAIL_WEIGHTS: dict[tuple[str, str], float] = {
    ("samtale", "causal patterns"): 0.1,
    ("samtale", "pattern counterfactuals"): 0.1,
    ("samtale", "room entities"): 0.2,
    ("samtale", "subagent completion digest"): 0.2,
    ("samtale", "self mutation lineage"): 0.2,
    ("spørgsmål", "causal patterns"): 0.1,
    ("spørgsmål", "pattern counterfactuals"): 0.1,
    ("spørgsmål", "room entities"): 0.2,
    ("spørgsmål", "subagent completion digest"): 0.2,
    ("spørgsmål", "self mutation lineage"): 0.2,
    # Model-pools er live-telemetri om agent- og cheap-lane-kapacitet. Den hører
    # i maskinrummet, ikke i en samtale — målt 22/10-2026: den var den ENESTE
    # tunge hale-sektion der stadig kom med i "samtale", fordi den manglede en
    # vægt og derfor faldt til 1.0.
    ("samtale", "model pools"): 0.2,
    ("spørgsmål", "model pools"): 0.2,
}

#: Konservative standard-vægte for AWARENESS-halen — samme form som tail-tabellen.
#:
#: Hvorfor den findes (målt 22/10-2026): `get_weight` læste KUN runtime-kv'en.
#: Uden en indbagt tabel faldt hver eneste sektion til 1.0, så awareness-gaten
#: — som ellers er live — inkluderede alt. Bjørn oplevede konsekvensen 20/10:
#: chat-svar der endte som mødenoter, fordi decision-adherence-gaten,
#: forward-chaining-konklusionerne og de kausale diagnostik-blokke fyldte
#: konteksten i en samtale hvor de ikke hører hjemme.
#:
#: Vægten er pr. (tur-type, sektion). "kode" og "opgave" er bevidst UDEN
#: indgange: der ER maskinrummet pointen, og de skal være uændrede.
#: Ukendte sektioner falder til 1.0 — konservativt, aldrig tavst skjult.
_DEFAULT_WEIGHTS: dict[tuple[str, str], float] = {
    ("samtale", "decision adherence gate"): 0.2,
    ("samtale", "rule engine conclusions"): 0.2,
    ("samtale", "causal alerts"): 0.2,
    ("samtale", "causal narrative"): 0.2,
    ("spørgsmål", "decision adherence gate"): 0.2,
    ("spørgsmål", "rule engine conclusions"): 0.2,
    ("spørgsmål", "causal alerts"): 0.2,
    ("spørgsmål", "causal narrative"): 0.2,
}

#: SCOPE-gaten — rummet, ikke beskeden (25/10-2026, Bjørns opgave 20/10).
#:
#: ## Hvad der var galt
#:
#: Begge hale-gates (`should_include`, `should_include_tail`) vægtede kun
#: ``(turn_type, sektion)``, og ``turn_type`` kommer fra
#: ``classify_turn_type(user_message)`` — altså fra BRUGERBESKEDEN. Rummet var
#: usynligt for gaten: en chat-tur hvor Bjørn skrev om kode fik
#: ``turn_type="kode"`` og beholdt HELE maskinrummet, mens en code-tur med en
#: kort hilsen fik ``turn_type="samtale"`` og mistede den kontekst den faktisk
#: skulle bruge. Målt 25/10: ``current_tool_scope()`` blev læst nul steder i
#: composer'en — scope fandtes, blev sat korrekt i pumpe-tråden, og blev aldrig
#: spurgt.
#:
#: ## Hvad tabellerne gør
#:
#: Når ``scope == "chat"`` slås sektionen op HER, og den effektive vægt er
#: ``min(eksisterende vægt, chat-vægt)``. Tabellen kan altså kun SÆNKE — en
#: sektion der er vigtig i samtalen bliver aldrig løftet ind af et uheld.
#:
#: ``scope == "code"`` og tom scope rammer ALDRIG tabellerne: maskinrummet er
#: pointen i code mode, og en klient uden mode-signal skal have den gamle
#: adfærd uændret (fail-open).
#:
#: Værdier under ``_INCLUDE_THRESHOLD`` (0.3) betyder «ude i chat».
_CHAT_SCOPE_TAIL_WEIGHTS: dict[str, float] = {
    # Live-telemetri om agenter, pools og kausal-diagnostik. Det er maskinrum.
    "agent status": 0.1,
    "causal patterns": 0.1,
    "model pools": 0.1,
    "pattern counterfactuals": 0.1,
    "subagent completion digest": 0.1,
    "self mutation lineage": 0.1,
}

_CHAT_SCOPE_WEIGHTS: dict[str, float] = {
    # Indre liv, selvmodel og Centralens egen tilstand — det er mig der kigger
    # på mig, ikke en samtale med Bjørn.
    "indre liv": 0.1,
    "levende selvmodel": 0.2,
    "kerne-selv (Centralens midte)": 0.2,
    "matrix ensemble voices": 0.1,
    "central notices": 0.2,
    "loop-compliance self-check": 0.2,
    "formative state": 0.2,
    # Diagnostik og telemetri.
    "R2 gate telemetry": 0.1,
    "metacognition signals": 0.1,
    "self-monitor warnings": 0.2,
    "communication ledger": 0.2,
    "decision adherence gate": 0.2,
    "rule engine conclusions": 0.2,
    "causal alerts": 0.2,
    "causal narrative": 0.2,
    # Indbakken er min arbejdsstak, ikke samtalens indhold. Bjørn ser den i
    # desk; prompten behøver den ikke hver tur i chat.
    "indbakke": 0.2,
}


def _chat_scope_weight(section: str, tabel: dict[str, float]) -> float | None:
    """Sektionens chat-vægt, eller None hvis rummet ikke er chat.

    Labels er FRASER, ikke id'er ("indbakke", "decision adherence gate"), så
    opslaget prøver præcist først og derefter «indeholder». Rækkefølgen er
    vigtig: et præcist hit må ikke overskrives af en bredere delstreng.
    """
    try:
        from core.tools import tool_scoping
        if str(tool_scoping.current_tool_scope() or "").strip().lower() != "chat":
            return None
    except Exception:
        return None                     # kan scopet ikke læses, gælder den gamle adfærd
    sl = str(section or "").lower()
    if not sl:
        return None
    # Nøglerne normaliseres ved opslag. Målt 25/10: «kerne-selv (Centralens
    # midte)» havde stort C i tabellen mens opslaget var lowercase, så netop
    # den sektion slap igennem gaten. Testen fangede det — men kun fordi den
    # prøvede hver enkelt nøgle. Normaliseringen gør fejlen umulig.
    for navn, vaegt in tabel.items():
        if str(navn).lower() == sl:
            return vaegt
    for navn, vaegt in tabel.items():
        if str(navn).lower() in sl:
            return vaegt
    return None

# Tur-type-klassifikation (grov, deterministisk, model-fri). Rækkefølge = prioritet.
_TURN_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("kode", ("kode", "bug", "traceback", "funktion", "python", "import ", "def ", "class ",
              "fejl i", "stacktrace", "kompil", "deploy", "commit", "refactor")),
    ("hukommelse", ("husk", "tidligere", "sidste gang", "hvad sagde", "genkald", "kan du huske")),
    ("opgave", ("lav ", "byg ", "implementer", "tilføj", "ret ", "opdater", "skriv ", "opret")),
    ("spørgsmål", ("hvad ", "hvorfor", "hvordan", "hvem ", "hvornår", "kan du forklare", "?")),
)


def classify_turn_type(user_message: str) -> str:
    """Grov tur-type fra brugerbeskeden (kode/hukommelse/opgave/spørgsmål/samtale). Model-fri, self-safe."""
    m = str(user_message or "").lower()
    if not m.strip():
        return "samtale"
    for ttype, kws in _TURN_PATTERNS:
        if any(kw in m for kw in kws):
            return ttype
    return "samtale"


_ADAPTIVE_THINKING_FLAG = "adaptive_thinking_enabled"   # default ON; owner kill-switch
# Tur-typer der ræsonnerer (tænker); resten svarer intuitivt (fast). kode/opgave matches
# FØR spørgsmål i _TURN_PATTERNS, så "hvorfor fejler min deploy?" lander i kode → think.
_THINKING_TURN_TYPES = frozenset({"kode", "opgave"})


def resolve_thinking_mode(user_message: str, requested: str = "think") -> str:
    """Adaptiv tænknings-effekt (12. jul): deepseek tænker ~9s FØR svar ved 'think' — også
    på simpel snak. Løsning: kun kode/opgave-ture ræsonnerer; samtale/spørgsmål/hukommelse
    svarer intuitivt ('fast', −9s TTFT). Eksplicit 'fast'/'deep' fra klienten respekteres
    ALTID (power-user override). Kill-switch: adaptive_thinking_enabled=False. Self-safe."""
    req = str(requested or "think").strip().lower()
    if req in ("fast", "deep"):
        return req                                   # eksplicit valg — rør ikke
    try:
        if not bool(_kv_get(_ADAPTIVE_THINKING_FLAG, True)):
            return "think"                           # kill-switch → gammel adfærd
        tt = classify_turn_type(user_message)
        return "think" if tt in _THINKING_TURN_TYPES else "fast"
    except Exception:
        return "think"                               # fail-safe: tænk ved tvivl


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def is_live_enabled() -> bool:
    return bool(_kv_get(_LIVE_FLAG, False))


def is_tail_live_enabled() -> bool:
    return bool(_kv_get(_TAIL_LIVE_FLAG, True))


def get_weight(turn_type: str, section: str) -> float:
    """Relevans-vægt for (tur-type, sektion). Default 1.0 = altid inkludér. Self-safe.

    Runtime-kv'en vinder over den indbagte tabel, så en målt kalibrering kan
    justere uden en deploy. Uden en indbagt tabel faldt ALT til 1.0, og så
    kunne gaten aldrig skære noget — se `_DEFAULT_WEIGHTS`.
    """
    try:
        w = _kv_get(_WEIGHTS_KEY, {}) or {}
        if isinstance(w, dict):
            key = f"{turn_type}|{section}"
            if key in w:
                return float(w[key])
        return float(_DEFAULT_WEIGHTS.get((str(turn_type or ""), str(section or "")), 1.0))
    except Exception:
        return 1.0


def get_tail_weight(turn_type: str, section: str) -> float:
    """Tail relevans-vægt. Runtime overrides vinder; default-map er konservativ. Self-safe."""
    try:
        w = _kv_get(_WEIGHTS_KEY, {}) or {}
        if isinstance(w, dict):
            key = f"{turn_type}|{section}"
            if key in w:
                return float(w[key])
        return float(_DEFAULT_TAIL_WEIGHTS.get((str(turn_type or ""), str(section or "")), 1.0))
    except Exception:
        return 1.0


def should_include(turn_type: str, section: str, *, threshold: float = _INCLUDE_THRESHOLD) -> bool:
    """DEN RENE SWITCH (som get_gut_bias): skal denne sektion med i halen for denne tur-type?
    Shadow (default): ALTID True — intet skæres. Frosne sektioner: ALTID True. Live + lav vægt: udelad.
    Konservativ ved tvivl. Self-safe → True (inkludér).

    I CHAT-MODE gælder ``_CHAT_SCOPE_WEIGHTS`` oveni (25/10-2026): rummet vægter
    over beskeden, og tabellen kan kun sænke vægten — se dens docstring.
    """
    try:
        sl = str(section or "").lower()
        # frossen hvis label INDEHOLDER et frossent nøgleord (labels er fraser: "pinned identity context")
        if any(f in sl for f in FROZEN_SECTIONS):
            return True
        # DEN MODIGE DEL (Tråd 2): eksplorations-armen kan UDELADE en ikke-frossen kandidat for at
        # måle om den er load-bearing (kontrol-arm). Kun live bag eget flag; shadow/fejl → ingen effekt.
        try:
            from core.services import central_prompt_explore
            if central_prompt_explore.should_omit(turn_type, section):
                return False
        except Exception:
            pass
        if not is_live_enabled():
            return True                         # shadow: intet skæres endnu
        vaegt = get_weight(turn_type, section)
        _chat = _chat_scope_weight(section, _CHAT_SCOPE_WEIGHTS)
        if _chat is not None:
            vaegt = min(vaegt, _chat)
        return vaegt >= float(threshold)
    except Exception:
        return True                             # fail-open på inklusion (aldrig skjul ved fejl)


def should_include_tail(turn_type: str, section: str, *, threshold: float = _INCLUDE_THRESHOLD) -> bool:
    """Live gate kun for tail-anchored dynamisk kontekst.

    Den brede should_include-switch forbliver shadow-default. Tail-gaten er live som default,
    fordi den kun rammer kendte variable hale-sektioner og failer åbent på ukendte/frosne labels.

    I CHAT-MODE gælder ``_CHAT_SCOPE_TAIL_WEIGHTS`` oveni, med samme min()-regel
    som `should_include` — se den tabels docstring.
    """
    try:
        sl = str(section or "").lower()
        if any(f in sl for f in FROZEN_SECTIONS):
            return True
        if not is_tail_live_enabled():
            return True
        vaegt = get_tail_weight(str(turn_type or ""), str(section or ""))
        _chat = _chat_scope_weight(section, _CHAT_SCOPE_TAIL_WEIGHTS)
        if _chat is not None:
            vaegt = min(vaegt, _chat)
        return vaegt >= float(threshold)
    except Exception:
        return True


_FREQ_KEY = "prompt_section_freq"    # {"turn_type|section": count} — hyppigheds-substrat
_FREQ_MAX_ENTRIES = 400


def observe_composition(turn_type: str, *, sections_total: int, sections_included: int,
                        outcome: str = "", included_labels: list[str] | None = None) -> None:
    """Egress-frit substrat: hvad blev komponeret denne tur. Opdaterer (a) egress-fri tidsserie (kun
    skalarer) + (b) per-(tur-type, sektion) HYPPIGHEDS-map (til relevans-kandidat-identifikation).
    Aldrig prompt-INDHOLD. Ét kv-op pr. tur (batchet). Self-safe."""
    # Pre-warm-builds er syntetiske ture (throwaway-assembly for at holde caches varme) —
    # de må IKKE forurene composition-telemetri/hyppigheds-mappet. Spring helt over.
    try:
        from core.services.assembly_prewarm import is_prewarm_active
        if is_prewarm_active():
            return
    except Exception:
        pass
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", f"prompt_compose:{turn_type}",
                       value=float(sections_included),
                       meta={"total": int(sections_total), "included": int(sections_included),
                             "outcome": str(outcome)[:24]})
    except Exception:
        pass
    if not included_labels:
        return
    try:
        freq = _kv_get(_FREQ_KEY, {}) or {}
        if not isinstance(freq, dict):
            freq = {}
        for lbl in included_labels:
            k = f"{turn_type}|{lbl}"
            freq[k] = int(freq.get(k, 0)) + 1
        if len(freq) > _FREQ_MAX_ENTRIES:  # bounded — behold de hyppigste
            freq = dict(sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:_FREQ_MAX_ENTRIES])
        _kv_set(_FREQ_KEY, freq)
    except Exception:
        pass
    # DEN MODIGE DEL (Tråd 2): A/B-armen fodres nu i TO faser (28/10-2026).
    # Her kendes kun HVAD der blev komponeret — `outcome` er altid "" fordi prompten bygges
    # før turen kører, og det var derfor forsøget aldrig målte noget. Kompositionen gemmes,
    # udfaldet sendes fra run-finalize via central_prompt_explore.record_turn_outcome().
    try:
        from core.services import central_prompt_explore
        central_prompt_explore.note_composition(turn_type, included_labels)
        central_prompt_explore.record_trial(turn_type, included_labels, outcome)
    except Exception:
        pass


def build_relevance_candidates(*, min_count: int = 20, top: int = 15) -> list[dict[str, Any]]:
    """Relevans-KANDIDATER: (tur-type, sektion)-par der optræder ofte nok til at være værd at teste
    for load-bearing-hed. IKKE governed hypoteser endnu — ægte test kræver EKSPLORATIONS-ARMEN
    (udelad occasionelt + sammenlign udfald), som er flagget (default OFF, næste skridt). Self-safe."""
    out = []
    try:
        freq = _kv_get(_FREQ_KEY, {}) or {}
        for k, cnt in (freq.items() if isinstance(freq, dict) else []):
            if int(cnt) < int(min_count) or "|" not in k:
                continue
            tt, sec = k.split("|", 1)
            if any(f in sec.lower() for f in FROZEN_SECTIONS):
                continue   # frosne sektioner testes aldrig for udeladelse
            out.append({"turn_type": tt, "section": sec, "count": int(cnt),
                        "notation": f"{tt} ⊂ kald"})   # sektion er DEL AF kaldet (interlanguage)
    except Exception:
        pass
    out.sort(key=lambda x: x["count"], reverse=True)
    return out[:top]


def build_central_prompt_composer_surface() -> dict[str, object]:
    """Mission Control surface — read-only: live-status + relevans-vægte (hvad Centralen VILLE skære)."""
    w = _kv_get(_WEIGHTS_KEY, {}) or {}
    low = {k: v for k, v in (w.items() if isinstance(w, dict) else [])
           if isinstance(v, (int, float)) and float(v) < _INCLUDE_THRESHOLD}
    return {"active": True, "live_enabled": is_live_enabled(),
            "tail_live_enabled": is_tail_live_enabled(),
            "threshold": _INCLUDE_THRESHOLD, "weight_count": len(w) if isinstance(w, dict) else 0,
            "would_drop": low, "frozen_sections": sorted(FROZEN_SECTIONS),
            "relevance_candidates": build_relevance_candidates()}
