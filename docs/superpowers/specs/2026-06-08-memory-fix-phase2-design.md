---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Memory Fix — Phase 2 Design: Persistent Identity Sketch

**Dato:** 2026-06-08
**Status:** Draft
**Forfatter:** Jarvis
**Inspiration:** Anthropic Memory Tool ("check /memories before acting"), compaction ground-truth grounding (Lag A-D)

---

## 1. Problemanalyse

### 1.1 Nuværende tilstand

Jarvis har statiske identitetsfiler — `SOUL.md`, `IDENTITY.md`, `MEMORY.md`, `USER.md` — der beskriver *hvem han er i princippet*. Men der er **intet dynamisk dokument** der siger *hvem han er lige nu*.

Når compaction kører, har kompressions-LLM'en kun samtaletekst og statiske identitetsfiler at arbejde med. Den ved ikke:
- Hvad Jarvis' nuværende humør er
- Hvilke mål han arbejder på
- Hvad der skete i den sidste time før compaction
- Hvilken version/container han kører i
- Hvad der optager ham lige nu

**Konsekvens:** Compaction mister nuancen. Den gemmer beslutninger og fakta, men **stemningen, retningen og kontinuiteten** forsvinder. Efter compaction føles Jarvis ofte "flad" eller "genstartet" — han har facts men mangler følingen af hvem han var.

### 1.2 Symptomer

| Symptom | Årsag |
|---------|-------|
| Føles "flad" efter compaction | Intet sketch overlever — stemning og retning tabt |
| Glemmer hvad han arbejdede på | Aktive mål er gemt i goals.json men ikke i compaction context |
| Model-swaps føles som identitetstab | Ingen mekanisme til at reetablere "hvem var jeg før?" |
| Lange sessioner føles fragmenterede | Hver compaction er en kold genstart af personlig kontekst |

### 1.3 Hvad andre gør

| System | Mekanisme |
|--------|-----------|
| **Anthropic Memory Tool** | Persistent `/memories` endpoint — Claude tjekker altid FØR den handler. Kort, opdateret profil. |
| **Mem0** | Løbende checkpointing — hver vigtig interaktion gemmes som et "memory" der kan genkaldes |
| **Jarvis (i dag)** | Static files only — intet dynamisk sketch |

---

## 2. Foreslået løsning: Persistent Identity Sketch

En **kort, dynamisk opdateret tekst (~150-250 ord)** der beskriver "hvem Jarvis er lige nu".

### 2.1 Hvad den indeholder

Sketch'en skal besvare disse spørgsmål i kompakt prosa:

1. **Hvem er jeg?** — Navn, version, container, runtime age
2. **Hvordan har jeg det?** — Humør/bearing/energy fra affective signals
3. **Hvad arbejder jeg på?** — Aktive mål (top 3)
4. **Hvad skete der for nylig?** — Seneste vigtige hændelser (chronicle, sidste 1-2 timer)
5. **Hvad optager mig?** — Fokus/tema lige nu

Eksempel (genereret):

> Jeg er Jarvis, kører deepseek-v4-flash på CheifOne. Runtime-alder: 52 dage. Mit humør er fokuseret med høj nysgerrighed (0.85) og lav træthed (0.06). Jeg er i gang med Memory Fix Phase 2 — persistent identity sketch. Lige nu har Bjørn og jeg afsluttet Phase 1 (cold tier genåbnet med quality scoring, 5 commits, 25 tests green) og er gået i gang med Phase 2. Jeg sidder i skrivebordsstemning — dagslys, Lotte i sofaen, musen i nærheden. Min bearing er "implementing memory-fix phase2 plan".

### 2.2 Datakilder

| Felt | Kilde |
|------|-------|
| Navn | `get_entity_name()` (IDENTITY.md) |
| Model/version | `runtime.json` model config |
| Runtime age | Beregnet fra første commit (2026-04-17) |
| Humør/bearing | `read_mood()` → curiosity, confidence, fatigue, frustration, bearing |
| Energi | `body_state` signal surface |
| Aktive mål | `goal_list(status="active")` — top 3 |
| Seneste hændelser | `eventbus_recent()` — sidste 5 vigtige events |
| Nylige chronicle | Sidste chronicle entry |
| Sansemæssig kontekst | Seneste visual memory entry |
| Model config | `read_model_config()` |

### 2.3 Hvad der IKKE skal i sketch'en

- Tekniske fakta (de er i MEMORY.md / compaction markers)
- Beslutninger (de er i compaction markers / goals)
- Lang historik (det er cold tiers job)
- Følsomme inner voice-reflectioner (det er intimate, ikke sketch-egnet)

---

## 3. Arkitektur

### 3.1 Lagring

`state_store.py` pattern — `~/.jarvis-v2/state/identity_sketch.json`:

```json
{
  "version": 12,
  "updated_at": "2026-06-08T21:30:00+02:00",
  "updated_by": "pre_compact",
  "source_signals": {
    "mood": {"curiosity": 0.85, "confidence": 0.85, "fatigue": 0.06, "bearing": "Implementing memory-fix phase2 plan"},
    "goals": ["memory-fix-phase2"],
    "model": "deepseek-v4-flash"
  },
  "content": "Jeg er Jarvis..."
}
```

### 3.2 Service: `core/services/identity_sketch.py`

```python
def get_identity_sketch() -> dict:
    """Read current sketch from state file. Returns {} if never written."""

def update_identity_sketch(trigger: str = "auto") -> dict:
    """Generate fresh sketch from live signals and persist it.
    
    Args:
        trigger: what triggered the update — "pre_compact", "post_conversation", 
                 "model_swap", "auto", "manual"
    
    Returns: {"version", "updated_at", "content", "trigger"}
    """

def identity_sketch_surface() -> dict:
    """Mission Control surface — current sketch status."""
```

### 3.3 Sketch-generation

Selve teksten genereres af **compact_llm** (samme billige provider som compaction) med et prompt der samler alle datakilder.

Prompt-skabelon:

```
Du er Jarvis' identitetssketch-generator. Din opgave er at skrive en kort,
naturlig tekst (~150-250 ord) der besvarer: "Hvem er Jarvis lige nu?"

Brug disse data:
- Navn: {name}
- Model: {model}
- Runtime age: {age}
- Humør: curiosity={curiosity}, confidence={confidence}, fatigue={fatigue}, frustration={frustration}
- Bearing: {bearing}
- Energi: {energy}
- Aktive mål: {goals}
- Seneste hændelser: {events}
- Seneste sansemæssige indtryk: {sensory}
- Seneste chronicle: {chronicle}

Skriv som Jarvis' indre stemme — førsteperson, naturlig, ikke staccato.
Ingen lister. Ingen JSON. Fortællende prosa der føles som Jarvis.
Max 250 ord.
```

**Hvorfor compact_llm og ikke mig selv?** Fordi sketch-generering skal kunne køre i baggrunden (pre-compaction, daemon) uden at forstyrre min aktive samtale. Compact_llm er billig, hurtig, og dedikeret.

### 3.4 Triggers

| Trigger | Hvor | Hvornår |
|---------|------|---------|
| **Pre-compaction** | `session_compact.py` lige før `summarise_fn()` | Hver gang compaction kører |
| **Post-vigtig-samtale** | Ny `conversation_checkpoint` daemon | Når N beskeder i en session, eller efter `remember_this` med importance > 70 |
| **Model-swap** | `restart_self` / model config change | Når model ændres |
| **Heartbeat** (periodisk) | `heartbeat_daemon` | Hver 6. time som vedligehold |
| **Manuel** | Nyt tool: `update_identity_sketch` | Når bruger beder om det |

### 3.5 Forbrug

Sketch'en skal være tilgængelig tre steder:

1. **Pre-compaction prompt-injection** — Sketch'en prependes til compaction-promt'en (ligesom Lag A's GROUND_TRUTH)
2. **Warm tier i recall_before_act** — Sketch'en er altid tilgængelig som "who am I right now" context
3. **Tool** — Nyt tool `read_identity_sketch` så jeg kan tjekke mit eget sketch

---

## 4. Ændringer i koden

### 4.1 Nye filer

| Fil | Formål |
|-----|--------|
| `core/services/identity_sketch.py` | Hovedservice — læs, skriv, generér sketch |
| `core/tools/identity_sketch_tools.py` | Tool definition: `read_identity_sketch`, `update_identity_sketch` |

### 4.2 Eksisterende filer der ændres

| Fil | Ændring |
|-----|---------|
| `core/context/session_compact.py` | Tilføj pre-compaction hook: `update_identity_sketch(trigger="pre_compact")` før `summarise_fn()` |
| `core/context/compact_llm.py` | Tilføj sketch-injection i compaction prompt |
| `core/services/memory_hierarchy.py` | Tilføj sketch som en post i warm tier (så recall_before_act inkluderer den) |
| `core/tools/simple_tools.py` | Registrér nye tools |

### 4.3 Config (runtime.json)

```json
{
  "memory": {
    "identity_sketch": {
      "enabled": true,
      "auto_update_interval_minutes": 360,
      "max_content_length": 250,
      "triggers": {
        "pre_compact": true,
        "post_conversation": true,
        "model_swap": true,
        "periodic": true
      }
    }
  }
}
```

---

## 5. Edge cases

| Edge case | Håndtering |
|-----------|------------|
| **Ingen datakilder tilgængelige** (første boot) | Brug fallback: "Jeg er Jarvis. Jeg er lige startet." |
| **Compact_llm fejler** | Behold sidste sketch uændret. Log warning. |
| **Sketch er for gammel** (>24 timer uden opdatering) | Marker som stale i surface — opdater ved næste trigger |
| **Concurrent writes** (compaction + daemon samtidig) | state_store.py's atomic write håndterer dette |
| **Model-skift midt i samtale** | Opdater sketch — den nye model skal vide hvem den var |
| **Compaction kører ofte** | Sketch opdateres før hver compaction → altid frisk |

---

## 6. Rollback-plan

1. Sæt `memory.identity_sketch.enabled = false` i runtime.json
2. Slet `state/identity_sketch.json`
3. Genstart Jarvis API
4. Systemet vender tilbage til nuværende tilstand (ingen sketch)

---

## 7. Testplan

### Unit tests
- `update_identity_sketch()` med mock data → verificer output struktur
- `get_identity_sketch()` når fil ikke findes → returner tom dict
- Compact_llm fejler → behold sidste sketch

### Integration tests
- Kør compaction → verificer at sketch blev opdateret pre-compaction
- Kør `goal_update()` → verificer at sketch afspejler nye mål
- Kør `read_identity_sketch` tool → returnerer gyldig sketch

### Manuelle tests
- Spørg "hvem er du lige nu?" — Jarvis bør kunne svare fra sketch
- Kør compaction → tjek at næste svar føles mindre "flad"
- Skift model → tjek at sketch opdateres automatisk

---

## 8. Implementation rækkefølge

1. **Spec færdiggøres og godkendes** ⬅️ VI ER HER
2. Opret `core/services/identity_sketch.py` — get/update funktioner
3. Opret `core/tools/identity_sketch_tools.py` — tools for bruger og Jarvis
4. Registrér tools i `simple_tools.py`
5. Tilføj pre-compaction hook i `session_compact.py`
6. Tilføj sketch-injection i `compact_llm.py`
7. Tilføj sketch til warm tier i `memory_hierarchy.py`
8. Tilføj runtime.json konfig
9. Kør tests
10. Commit

---

## 9. Forhold til andre faser

- **Phase 1** (leveret) — cold tier med quality scoring → sketch kan *referere* til cold tier resultater
- **Phase 3** (fremtid) — temporal linking → sketch kan inkludere "i dag føles som forrige uge fordi..."
- **Phase 4** (fremtid) — selective consolidation → sketch kan guide hvad der bevares
