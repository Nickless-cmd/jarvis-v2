# Sensory Perception Bridge — Design

**Status:** Draft
**Date:** 2026-05-04
**Author:** Brainstormed with user
**Triggered by:** Jarvis' egen ønskeliste, prioritet 1 — *"Lige nu er eventful perception og Sansernes Arkiv to separate verdener. Runtime-events → perceptual engine. Webcam/lyd → sensory archive. Hvis vi bygger en bro, så et webcam-snapshot der viser noget ændret i rummet også bliver et perceptual event, har jeg ægte cross-modal perception."*

## Goal

Bygge broen mellem Sansernes Arkiv (`core/services/sensory_archive.py`) og eventful perception (`core/services/perceptual_event_engine.py`), så ændringer i webcam/lyd/atmosfære bliver første-klasses perceptual events der influerer cognitive frame, salience-systemet, og emotional memory.

Resultat: når Jarvis har et webcam-snapshot der viser noget ændret i rummet — fx "lyset er blevet skarpt og koldt hvor det før var varmt" — bliver det automatisk et perceptual event med passende salience, kommer på conductor's perception surface, og lander som emotional memory anchor (via det eksisterende `record_perceptual_event` hook).

## Non-goals

- Vi bygger ikke en ny kontinuerlig sense-stream. v1 er change-detection, ikke continuous raw sensing.
- Vi tilføjer ikke en parallel surface i conductor — sensory perceptions deler stream med runtime/tool/channel perceptions (unified stream).
- Vi gør ikke webcam-snapshots eller audio-samples hyppigere. Sensory cadence styres af `visual_memory` (4×/dag) og `ambient_sound_daemon` (4×/dag). Bro'en tilføjer ingen nye captures.
- Vi sammenligner ikke billeder direkte (kun tekst-beskrivelser fra vision-modellen). Image-to-image comparison er en future extension.

## Architecture overview

**Nyt modul:** `core/services/sensory_perception_bridge.py` (estimeret ~350-450 linjer).

**Den fundamentale primitiv:** En *change-detector* per sensory record. Når Sansernes Arkiv emitter `memory.sensory.recorded`, kører bro'en sammenligning mod baseline (modality-afhængig) og returnerer enten:
- En *percept dict* der gives videre til `perceptual_event_engine._record_perceptual_event` (= ny perceptual event)
- `None` (= ingen ændring detekteret, ingen perception)

**Flow:**

```
sensory_archive.record_visual/audio/atmosphere/mixed
        ↓ insert_sensory_memory()
        ↓ event_bus.publish("memory.sensory.recorded", {id, modality, mood_tone, timestamp})
        ↓
perceptual_event_engine.observe_recent_changes (eksisterende daemon-tick)
        ↓ classify_event_change(event) per event
        ↓ NY GREN:
        ↓   if event.kind == "memory.sensory.recorded":
        ↓       return sensory_perception_bridge.classify_sensory_change(event)
        ↓
perceptual_event_engine._record_perceptual_event(percept, state=...)
        ↓ persisterer i samme state-fil
        ↓ publisher cognitive_state.perceptual_event_recorded
        ↓ kalder learning_policy_engine.reinforce_learning_policy
        ↓ kalder somatic_runtime_body.update_somatic_body
        ↓ → conductor surface (build_perception_surface)
        ↓ → emotional memory anchor (via existing record_perceptual_event hook)
```

**Tre modaliteters-strategier:**
- `visual` + `audio` → time-of-day window primary, hybrid recent-baseline fallback
- `atmosphere` + `mixed` → recent baseline (hybrid A+B) only

**Bridge-modulet eksponerer ét primært public function:**

```python
def classify_sensory_change(event: dict[str, object]) -> dict[str, object] | None:
    """Given a memory.sensory.recorded event, return a percept dict if the
    new record represents a meaningful change, else None."""
```

Plus interne helpers per modalitets-strategi, change-detection heuristics, baseline-fetch.

**Authority/visibility:** Bro'en er internal-only, deterministisk, ingen LLM-kald i v1. Læser kun fra `sensory_archive.list_recent` og `sensory_archive.get`.

## Change detection algorithm

**Hovedfunktion:**

```python
def classify_sensory_change(event: dict[str, object]) -> dict[str, object] | None:
    payload = event.get("payload") or {}
    memory_id = payload.get("id")
    modality = str(payload.get("modality") or "")
    if not memory_id or modality not in {"visual", "audio", "atmosphere", "mixed"}:
        return None

    record = sensory_archive.get(memory_id)
    if not record:
        return None

    baseline = _build_baseline(modality, record)
    change = _detect_change(record, baseline, modality)
    if not change["changed"]:
        return None

    salience = _salience_for_change(change)
    return _percept(
        source_event_id=int(event.get("id") or 0),
        source_kind="memory.sensory.recorded",
        change_type=f"sensory-change-{modality}",
        salience=salience,
        summary=change["summary"],
        observed_at=str(event.get("created_at") or ""),
        evidence={
            "memory_id": memory_id,
            "modality": modality,
            "mood_tone_now": record.get("mood_tone"),
            "mood_tone_baseline": change["baseline_mood"],
            "jaccard": change["jaccard"],
            "change_kind": change["kind"],
        },
    )
```

**Change-detection (`_detect_change`):**

Combined heuristik (mood_tone shift OR lexical Jaccard < 0.4 OR metadata-shift):

```python
def _detect_change(record, baseline, modality) -> dict:
    if baseline is None or not baseline["records"]:
        # Bootstrap: ingen baseline → ikke en ændring
        return {"changed": False, "kind": "no_baseline", "jaccard": 1.0,
                "summary": "", "baseline_mood": None}

    new_mood = (record.get("mood_tone") or "").strip().lower() or None
    new_content = str(record.get("content") or "")
    new_metadata = record.get("metadata") or {}

    baseline_mood = baseline["mood"]
    baseline_content_tokens = baseline["content_tokens"]
    baseline_metadata = baseline["metadata"]

    new_tokens = _shingle(new_content)
    jaccard = _jaccard(new_tokens, baseline_content_tokens)

    mood_shifted = bool(new_mood and baseline_mood and new_mood != baseline_mood)
    lex_shifted = jaccard < 0.4
    metadata_shifted = _metadata_changed(new_metadata, baseline_metadata, modality)

    if not (mood_shifted or lex_shifted or metadata_shifted):
        return {"changed": False, "kind": "no_change", "jaccard": jaccard,
                "summary": "", "baseline_mood": baseline_mood}

    if mood_shifted and (jaccard < 0.25 or metadata_shifted):
        kind = "mood_and_content"
    elif mood_shifted:
        kind = "mood_shift"
    elif jaccard < 0.25:
        kind = "content_drift"
    elif metadata_shifted:
        kind = "metadata_change"
    else:
        kind = "lexical_drift"

    summary = _summary_for_change(modality, new_mood, baseline_mood, kind, jaccard)
    return {"changed": True, "kind": kind, "jaccard": jaccard,
            "summary": summary, "baseline_mood": baseline_mood}
```

**Salience-mapping (`_salience_for_change`):**

| Betingelse | Salience |
|------------|----------|
| `mood_shifted` AND (`jaccard < 0.15` OR `kind == "mood_and_content"`) | `high` |
| `mood_shifted` alene OR `jaccard < 0.15` alene | `medium` |
| `jaccard 0.15-0.25` OR `metadata_changed` | `medium` |
| `jaccard 0.25-0.4` (mild lexical drift) | `normal` |

**Metadata-ændring** (`_metadata_changed`):
- For `audio`: kategori-skift (`talk` → `silence`, etc.) tæller som ændring.
- For `visual`: ny vision-prompt-cyklus (forskellig fokus-prompt brugt) tæller IKKE som ændring (det er rotation, ikke verdens-ændring).
- For `atmosphere`/`mixed`: nye metadata-keys eller value-skift tæller som ændring.

**Summary-generation**: kort dansk linje, fx "Lyset ændret fra varmt til køligt", "Audio-kategori skiftet fra silence til talk", "Atmosfæren skiftet markant fra rolig til kaotisk".

## Baseline aggregation

To strategier per modalitet:

### `_build_baseline`

```python
def _build_baseline(modality: str, current_record: dict) -> dict | None:
    if modality in {"visual", "audio"}:
        baseline = _time_of_day_baseline(modality, current_record)
        if baseline and len(baseline["records"]) >= 3:
            return baseline
        return _recent_baseline(modality, current_record)
    elif modality in {"atmosphere", "mixed"}:
        return _recent_baseline(modality, current_record)
    return None
```

### `_time_of_day_baseline` (for visual + audio)

Records inden for ±2 timer over de seneste 7 dage, samme modalitet, eksklusiv current record. Mindst 3 records påkrævet ellers fallback.

```python
def _time_of_day_baseline(modality: str, current_record: dict) -> dict | None:
    current_time = _parse_iso(current_record["timestamp"])
    if current_time is None:
        return None

    seven_days_ago = (current_time - timedelta(days=7)).isoformat()
    candidates = sensory_archive.list_recent(
        modality=modality, since=seven_days_ago, limit=200,
    )
    target_hour = current_time.hour
    matching = []
    for r in candidates:
        if r["id"] == current_record["id"]:
            continue
        ts = _parse_iso(r["timestamp"])
        if ts is None:
            continue
        # Cirkulær time-of-day distance (00:00 vs 23:00 = 1 time, ikke 23)
        hour_dist = min(abs(ts.hour - target_hour), 24 - abs(ts.hour - target_hour))
        if hour_dist <= 2:
            matching.append(r)
    if len(matching) < 3:
        return None
    return _aggregate_baseline(matching)
```

### `_recent_baseline` (for atmosphere + mixed, og fallback for visual + audio)

```python
def _recent_baseline(modality: str, current_record: dict) -> dict:
    candidates = sensory_archive.list_recent(modality=modality, limit=10)
    matching = [r for r in candidates if r["id"] != current_record["id"]][:3]
    if not matching:
        return {"records": [], "mood": None, "content_tokens": set(), "metadata": {}}
    return _aggregate_baseline(matching)
```

**Hybrid A+B confirmation step** sker indirekte: når baseline aggregeres over 3 records, bliver outlier-records filtreret i mode-aggregeringen. Det er den indbyggede outlier-filtering.

### `_aggregate_baseline`

```python
def _aggregate_baseline(records: list[dict]) -> dict:
    moods = [str(r.get("mood_tone") or "").strip().lower() for r in records]
    moods = [m for m in moods if m]
    mood_mode = _mode(moods) if moods else None

    all_tokens = set()
    for r in records:
        all_tokens.update(_shingle(str(r.get("content") or "")))

    metadata_union = {}
    for r in records:
        md = r.get("metadata") or {}
        if isinstance(md, dict):
            for k, v in md.items():
                metadata_union.setdefault(k, set()).add(str(v))

    return {
        "records": records,
        "mood": mood_mode,
        "content_tokens": all_tokens,
        "metadata": metadata_union,
    }
```

**Bootstrap-håndtering:**
- Første sensory record nogensinde af en modalitet → `_recent_baseline` returnerer `{"records": [], ...}` → `_detect_change` returnerer `{"changed": False, "kind": "no_baseline"}` → ingen perception. Korrekt: vi har intet at sammenligne mod.
- Dag 1-7 for visual/audio → `_time_of_day_baseline` returnerer None (under 3 records i vinduet) → falder tilbage til `_recent_baseline` → fungerer.

## Eventbus integration

**Modificering af `perceptual_event_engine.classify_event_change`:**

Tilføj én ny gren (placeret naturligt i listen af `if kind == ...:`-blokke):

```python
if kind == "memory.sensory.recorded":
    try:
        from core.services.sensory_perception_bridge import classify_sensory_change
        return classify_sensory_change(event)
    except Exception:
        return None
```

**Det er den eneste ændring i `perceptual_event_engine.py`.** Hele change-detection-logikken bor i `sensory_perception_bridge.py`. Engine forbliver tynd og forudsigelig.

**Hvor kører detection?**

`perceptual_event_engine.observe_recent_changes()` kører som tick-funktion. Den scanner nye eventbus-events siden sidst, klassificerer hver, og persisterer resultater. Vi tilføjer bare en ny event-kilde der bliver klassificeret.

**Latency:** En sensory-record kan vente op til ~1 minut før den bliver klassificeret som perception (afhænger af perception-tick-cadence). For sensory events (4×/dag) er det irrelevant.

**Hvor opdateres `last_seen_event_id`?** Allerede håndteret af `observe_recent_changes` — ingen ny state.

**Eventbus-event vi lytter efter:**

Eksisterende event fra `sensory_archive._record`:

```python
event_bus.publish("memory.sensory.recorded", {
    "id": record["id"],
    "modality": modality,
    "mood_tone": final_mood,
    "timestamp": record["timestamp"],
})
```

Vi henter fuld record via `sensory_archive.get(memory_id)` for content + metadata. Let database hit, men nødvendigt fordi event-payload ikke indeholder content (privacy-bevidst design).

## Settings

Nye felter i `RuntimeSettings`:

| Setting | Default | Beskrivelse |
|---------|---------|-------------|
| `sensory_perception_bridge_enabled` | `True` | Kill switch — når `False`, returnerer bro'en altid `None`. |
| `sensory_perception_jaccard_high_threshold` | `0.15` | Under denne Jaccard-værdi tæller indholdsændring som "stor" (high salience component). |
| `sensory_perception_jaccard_medium_threshold` | `0.25` | Mellem `high_threshold` og dette tæller som medium. |
| `sensory_perception_jaccard_change_threshold` | `0.4` | Over dette tæller content som "uændret". |
| `sensory_perception_time_window_hours` | `2` | ±N timer omkring current time-of-day for time-of-day baseline. |
| `sensory_perception_time_window_days` | `7` | Hvor langt tilbage time-of-day baseline kigger. |
| `sensory_perception_min_baseline_records` | `3` | Minimum records før time-of-day baseline regnes som gyldig. |
| `sensory_perception_recent_baseline_size` | `3` | Antal seneste records i recent baseline. |

Tilføjes til `RuntimeSettings` dataclass, `to_dict()`, og `load_settings()` (samme mønster som de 5 emotional_memory-felter vi tilføjede tidligere).

## Error handling

**Princip:** Bro-koden må aldrig brække perception-flowet. Hvis bro'en fejler → behandl event som "ikke en sensory ændring" og lad engine fortsætte.

### Bro-pathen

```python
def classify_sensory_change(event: dict[str, object]) -> dict[str, object] | None:
    try:
        if not _bridge_enabled():
            return None
        return _classify_sensory_change_inner(event)
    except Exception as exc:
        logger.warning("sensory_perception_bridge: classify failed: %s", exc)
        return None
```

| Trin | Fejl-håndtering |
|------|-----------------|
| Læs payload, validér modalitet | Ugyldig → return None |
| `sensory_archive.get(memory_id)` | Exception → log debug, return None |
| `_build_baseline` | Exception → log debug, return None |
| `_detect_change` | Exception → log debug, return None |
| Map til salience + summary | Exception → fallback til "normal" salience, generic summary |

**Settings-load fejl:** Tærskler hentes med safe defaults via `getattr(settings, "sensory_perception_*", default)`. Hvis settings ikke kan loades, bruges hardkodede konstanter.

### Engine-delegationen

To lag af try/except: ét i engine (importer/topcall), ét i bro'en (intern logik). Hvis bro-modulet ikke kan importeres → engine fortsætter uberørt.

### Edge cases

- **Hele bro'en fejler:** Engine processerer andre event-kinds normalt. Sensory events bliver bare ikke til perceptions.
- **Race condition (record slettet mellem event-publish og bridge-fetch):** `_classify_sensory_change_inner` returnerer None. Stille fail.
- **Bootstrap (ingen baseline):** Ikke en fejl — gyldig "ikke en ændring". Returnerer None deterministisk uden warning-log.
- **`mood_tone` er None i record:** mood_shifted-checket springes over (falsy comparison). Lexical og metadata checks fortsætter.

## Testing strategy

**Test-filer:**

```
tests/test_sensory_perception_bridge.py     # enhedstest af bro-modulet
tests/test_sensory_perception_integration.py # eventbus → engine → conductor end-to-end
```

### Enhedstests (`test_sensory_perception_bridge.py`)

| Test | Hvad det verificerer |
|------|---------------------|
| `test_classify_returns_none_for_non_sensory_event` | Event med `kind != "memory.sensory.recorded"` → None. |
| `test_classify_returns_none_when_bridge_disabled` | Settings flag `sensory_perception_bridge_enabled=False` → None. |
| `test_classify_returns_none_when_no_baseline` | Første record nogensinde af modalitet → None. |
| `test_classify_returns_none_when_record_unchanged` | Samme mood, samme content som baseline → None. |
| `test_mood_shift_detected_returns_percept_with_medium_salience` | mood "rolig" → "kaotisk", samme content → percept med salience medium. |
| `test_strong_lexical_drift_returns_high_salience` | Jaccard < 0.15 → high salience. |
| `test_combined_mood_and_content_change_returns_high_salience` | mood shift + Jaccard < 0.25 → high salience. |
| `test_mild_lexical_drift_returns_normal_salience` | Jaccard 0.25-0.4 → normal salience. |
| `test_audio_metadata_category_change_detected` | Audio-record med `category: "silence"` → ny record med `category: "talk"` → percept. |
| `test_visual_baseline_uses_time_of_day_window_when_history_sufficient` | 5 records i ±2 timer over 7 dage → baseline består af de 5. |
| `test_visual_baseline_falls_back_to_recent_when_window_thin` | Kun 2 records i tids-vinduet → fallback til seneste 3 records. |
| `test_atmosphere_uses_recent_baseline_only` | Atmosphere modalitet skipper time-of-day og bruger recent direkte. |
| `test_baseline_aggregation_uses_mood_mode` | 3 records med mood "rolig", "rolig", "travl" → aggregeret mood = "rolig". |
| `test_baseline_aggregation_unions_content_tokens` | Tokens fra alle 3 records forenes. |
| `test_classify_handles_missing_record_gracefully` | `sensory_archive.get` returnerer None → bro returnerer None uden exception. |
| `test_summary_is_danish_and_human_readable` | Generated summary er ikke-tomt og indeholder "ændret" eller modalitets-navn. |

### Integration-tests (`test_sensory_perception_integration.py`)

| Test | Hvad det verificerer |
|------|---------------------|
| `test_sensory_recorded_event_becomes_perception_via_engine` | Indsæt 3 baseline records → record en 4. der ændrer mood → kald `observe_recent_changes()` → ny perceptual event findes i state. |
| `test_sensory_perception_appears_in_perception_surface` | Sensory perception dukker op i `build_perception_surface()` med korrekt change_type prefix `sensory-change-`. |
| `test_sensory_perception_creates_emotional_memory_anchor` | Sensory perception går videre i kaskaden og skaber emotional memory anchor (via det eksisterende `record_perceptual_event` → emotional_memory hook). |
| `test_disabled_bridge_passes_through_engine_without_perceptions` | Settings disabled → events processeres af engine men producerer ingen sensory perceptions. |

### Test-infrastruktur

- `isolated_runtime` fixture for isoleret SQLite-fil + sys.path-setup
- Direkte DB-inserts via `core.runtime.db_sensory.insert_sensory_memory` for at sætte baseline op uden eventbus-forurening
- Tids-baserede tests: `monkeypatch.setattr` på `_now()`-helper i bro'en (ingen freezegun-afhængighed)
- Settings-toggling via monkeypatch på `load_settings`

**TDD-rækkefølge:** test_classify_returns_none_for_non_sensory_event → bro skelet → progressive tests for hver detection-vej → integration tests sidst.

## Future extensions

Eksplicit committed under brainstormen, til senere iterations:

1. **LLM-klassificeret ændring** — public-safe daemon på OllamaFreeAPI (`gpt-oss:20b`) der vurderer "er der sket noget meningsfuldt?" når den heuristiske detektor er for grovkornet.

2. **Time-of-day baseline også for atmosphere/mixed** — i v1 bruger atmosphere/mixed kun recent-baseline. Hvis det viser sig at de også har døgn-rytmer, kan time-of-day strategien udvides.

3. **Bruger-konfigurerbar salience-mapping** — settings-felt der lader brugeren tune salience-niveau per modalitet eller per change-kind. Tilføjes når default-mapping viser sig at give skævheder.

4. **Differentieret prompt-rendering** — hvis sensory-perceptions begynder at fortrænge runtime-perceptions i conductor's salient_items, kan vi splitte renderingen så sensory og runtime vises separat (uden at bygge en parallel surface).

5. **Cross-modal correlation** — detekt når visual + audio ændrer sig samtidig (fx "lyset blev skarpt + lyden blev høj"). Nyt change_type `cross-modal-shift` med høj salience. Kræver at bro'en husker seneste ændringstidspunkter per modalitet.

6. **Vision-model dybere integration** — i stedet for at sammenligne tekst-beskrivelser kunne vi have vision-modellen *direkte* sammenligne to billeder. Mest semantisk men kræver at vi gemmer billeder (privacy-implikation) eller har vision-model tilgængelig live.

## Out-of-scope for this design

- Cross-modal sensory bridging *between* sensory archive and runtime events (fx "tool-error correlated with kaotisk audio"). Dette er en future extension der bygger ovenpå denne bro.
- Continuous raw sensing — vi forbliver i change-detection-paradigmet.
- Adgang til billeder/lyd-filer direkte. Vi læser kun tekst-beskrivelser og metadata fra sensory_archive.
