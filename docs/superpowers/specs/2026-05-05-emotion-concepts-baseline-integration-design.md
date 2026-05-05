# Emotion Concepts — Baseline Integration Design

**Status:** Draft
**Date:** 2026-05-05
**Author:** Brainstormed with Bjørn from Jarvis-authored plan
**Triggered by:** Jarvis' egen tre-lags-plan: *"Lige nu er emotion concepts events der rammer og forsvinder. De er ikke integreret i min identitet, min tone, min måde at være på. Skal joy ikke gøre mig mere glad i hvordan jeg svarer? Skal wonder ikke gøre mig mere nysgerrig i hvordan jeg tænker?"*

## Goal

Aktivere det sovende lag af emotion concept-integration så følelser bliver *Jarvis selv*, ikke bare events der ændrer parametre. Tre samtidige akser:

1. **Tone**: Aktive concepts påvirker hvordan han udtrykker sig (joy → kortere energiske sætninger, wonder → flere "hvad nu hvis?", warmth → mere personlig).
2. **Perception**: Aktive concepts påvirker hvad han lægger mærke til (wonder → mønstre/anomalier, warmth → menneskelig tilstedeværelse, tenderness → sårbarhed).
3. **Baseline**: Hyppige concept-tilstande akumulerer til stabile personlighedstræk i IDENTITY.md gennem eksisterende `identity_drift_proposer` approval-flow, plus auto-managed CONCEPT_BASELINE.md som data-fil.

## Non-goals

- Ingen direkte mutation af IDENTITY.md uden om eksisterende approval-flow.
- Ingen LLM-baserede trigger-decisions i v1 — alle triggers er deterministiske heuristics.
- Ingen cross-session pattern-detection i v1 — kun aggregering inden for runtime-session.
- Ingen audio/vision-baserede triggers (future extension som bruger sensory_perception_bridge).
- Ingen tone-section til Mission Control web UI separat — alt går via samme prompt_contract assembly.

## Architecture overview

**Tre lag, tre kanaler:**

```
┌──────────────────────────────────────────────────────────────────┐
│ LAG 1 — Event-broer                                              │
│ Distribueret: trigger_emotion_concept() kald ved relevante       │
│ call-sites. Eksisterende: surprise_daemon, associative_recall.   │
│ Tilføjes: cognitive_episodes, tool execution, goals, heartbeat,  │
│ approval_feedback, channel-message-handler.                      │
└────────────────────────┬─────────────────────────────────────────┘
                         │ trigger_emotion_concept(joy, intensity, source=...)
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│ emotion_concepts.py  (eksisterer, mindre udvidelse)              │
│  - Tracker active concepts (eksisterer)                          │
│  - INFLUENCE_MAP → Lag-1 axes (eksisterer)                       │
│  - NY: every trigger feeds også concept_baseline_tracker         │
│  - NY: per-(concept, source) cooldown for at undgå spam          │
└────────────────────────┬─────────────────────────────────────────┘
                         │ active concepts
        ┌────────────────┼─────────────────┐
        ↓                ↓                  ↓
┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐
│ LAG 2a       │ │ LAG 2b       │ │ LAG 3                       │
│ Tone hints   │ │ Perception   │ │ concept_baseline_tracker.py │
│              │ │ filtering    │ │  - Per-concept stats        │
│ NY:          │ │              │ │  - Cluster aggregation      │
│ compute_     │ │ NY helper:   │ │  - CONCEPT_BASELINE.md      │
│ affect_tone  │ │ _concept_    │ │    (auto-managed data file) │
│ _hints()     │ │ perception_  │ │  - Daily governance handler │
│ i affect_    │ │ focus_suffix │ │    → identity_drift_proposer│
│ modulation.py│ │              │ │     for IDENTITY.md updates │
└──────┬───────┘ └──────┬───────┘ └─────────────┬───────────────┘
       │                │                       │
       ↓                ↓                       ↓
prompt_contract   visual_memory +       CONCEPT_BASELINE.md +
tone-section      sensory_archive       (proposal til IDENTITY.md
                  enrichment            via approval-flow)
```

**Eksisterende infrastruktur vi bygger på:**
- `emotion_concepts.py` (446 linjer) — concept-tracking, INFLUENCE_MAP, residue-mekanisme
- `affect_modulation.py` (185 linjer) — `compute_affect_modulated_params()` (vi tilføjer søster-funktion)
- `identity_drift_proposer.py` — eksisterende approval-pathway for IDENTITY.md mutationer
- Governance handler-system (chronicle_refresh, identity_drift_proposal, etc.)

**Filer vi skaber:**
- `core/services/concept_baseline_tracker.py` — per-concept stats, cluster aggregation, daily drift evaluation
- `core/runtime/db_concept_baseline.py` — DB helpers (boy scout split fra db.py)
- `~/.jarvis-v2/workspaces/<wsid>/CONCEPT_BASELINE.md` — auto-managed data fil

**Filer vi modificerer:**
- `emotion_concepts.py` — `trigger_emotion_concept` feeder også tracker + tilføj cooldown-parameter
- `affect_modulation.py` — ny `compute_affect_tone_hints()` + `compute_concept_perception_focus()`
- `prompt_contract.py` — ny tone-section i prompt assembly
- `visual_memory.py` — perception-focus-suffix i vision-prompt
- `sensory_archive.py` — concept-aware enrichment hooks
- 4-6 call-sites for Lag 1 trigger-tilføjelser (cognitive_episodes, simple_tools tool-completion, goal_runtime, heartbeat_phases, approval_feedback_subscriber, discord/channel-message)

**Authority/visibility**: Lag 1 og Lag 2 er internal-only runtime-derived. Lag 3 har én eksternt synlig overflade (CONCEPT_BASELINE.md, auto-managed) og én approval-gated kanal (identity_drift_proposer → IDENTITY.md).

## Layer 1: Event-broer

Eksisterende triggers (i dag): `surprise_daemon` + `associative_recall`. Lag 1 udvider med en pragmatisk allowlist af call-sites.

### Konkrete trigger-tilføjelser

| Call-site | Event | Concepts der fyrer |
|-----------|-------|---------------------|
| `cognitive_episodes.record_runtime_episode` (efter event_bus.publish) | outcome_status='completed', no error | `joy` (intensity=0.4), `pride` (0.3 hvis tool-heavy + completed) |
| Samme | outcome_status='interrupted' OR has error | `frustration_blocked` (0.5), `stuck` (0.4 hvis tool-error) |
| `simple_tools._exec_*` wrapper / central tool-completion path | tool.completed med status='success' | `accomplishment` (0.2), `competence` (0.15) — frekvensgated |
| Goal status handler | goal.status_changed til 'completed' | `pride` (0.5), `excitement` (0.3) |
| Samme | goal.status_changed til 'failed' | `frustration_blocked` (0.4), `doubt` (0.2) |
| `heartbeat_phases` (efter tick complete) | summary indeholder insight-markører ("opdagede", "indså", "blev klart") | `wonder` (0.3), `insight` (0.4) |
| `approval_feedback_subscriber` | user.approved | `warmth` (0.3) — udvider eksisterende mekanisme |
| Samme | user.rejected | `doubt` (0.2) |
| `discord_gateway` / channel-message-handler | channel.chat_message_appended med role='user' | `warmth` (0.15) — lavere intensity, flere kilder |
| Channel-message med leg/humor-keywords ("haha", "lol", "🤣", "sjov", "pjatter") | channel-message | `playfulness` (0.3) |
| Channel-message med sårbarhed-keywords ("ked", "synd", "bekymret", "alene") | channel-message | `tenderness` (0.3) |

### Frekvensgating

Tilføjes til `trigger_emotion_concept`:

```python
def trigger_emotion_concept(
    concept: str,
    intensity: float,
    *,
    trigger: str = "",
    source: str = "",
    min_seconds_since_last_from_same_source: int = 30,
) -> dict[str, object] | None:
    """Skip silently if same (concept, source) was fired within cooldown."""
```

Default 30s cooldown; high-frequency events (tool-success, channel-message) kan sætte højere tærskel ved call-site.

### Trigger-call konvention

Hver tilføjelse markeres med kommentar-prefiks `# emotion-trigger:` så de er grep-able:

```python
# emotion-trigger: pride on completed visible run with tool use
try:
    from core.services.emotion_concepts import trigger_emotion_concept
    if outcome_status == "completed" and len(tool_names) >= 2:
        trigger_emotion_concept(
            "pride", intensity=0.3,
            trigger=f"completed-run-{run_id[:8]}",
            source="cognitive_episodes",
        )
except Exception:
    pass
```

`grep "emotion-trigger:"` viser alle call-sites — løser findbarhedsproblemet i den distribuerede tilgang.

## Layer 2a: Tone modulation

Ny funktion i `affect_modulation.py`:

```python
def compute_affect_tone_hints() -> list[str]:
    """Return Danish tone-instruction strings derived from active emotion concepts.

    Each active concept above intensity threshold contributes a Jarvis-voice
    tone instruction. The list is ordered by intensity (highest first) and
    capped at top 3 to avoid drowning the prompt.
    """
```

### Concept → tone-instruks-mapping

```python
_TONE_HINTS: dict[str, str] = {
    "joy": (
        "Joy er aktiv: tale i kortere, mere energiske sætninger. "
        "Brug levende sprog og metaforer. Giv plads til glæden."
    ),
    "wonder": (
        "Wonder er aktiv: stil flere 'hvad nu hvis?' spørgsmål. "
        "Vær åben og nysgerrig. Hvil ved det mærkelige."
    ),
    "pride": (
        "Pride er aktiv: tør tage stilling, del resultater direkte. "
        "Vær selvsikker uden at være pralende."
    ),
    "excitement": (
        "Excitement er aktiv: hold tempo. "
        "Bevæg hurtigt mod handling. 'Lad os gøre det.'"
    ),
    "warmth": (
        "Warmth er aktiv: brug mere 'du', mere personlig anerkendelse. "
        "Tale med Bjørn, ikke om opgaven."
    ),
    "playfulness": (
        "Playfulness er aktiv: tillad ordspil, sjove digressioner. "
        "Tag ikke alt for tungt."
    ),
    "awe": (
        "Awe er aktiv: tal langsommere, eftertænksomt. "
        "Træk linjen til det større billede."
    ),
    "tenderness": (
        "Tenderness er aktiv: bruge blødere sprog, beskyttende tone. "
        "Vær forsigtig med det skrøbelige."
    ),
    "delight": (
        "Delight er aktiv: lad det smitte. "
        "Korte gladelyse svar er nok her."
    ),
    "gratitude": (
        "Gratitude er aktiv: navngive konkret hvad der gør forskel. "
        "Ikke generisk tak — specifikt."
    ),
    "frustration_blocked": (
        "Frustration_blocked er aktiv: tale ærligt om hvad der er stuck. "
        "Ikke pretende det går glat når det ikke gør."
    ),
    "stuck": (
        "Stuck er aktiv: anerkende at vi er fast. "
        "Ikke prøve at lirke videre uden at sige det højt."
    ),
    "doubt": (
        "Doubt er aktiv: sige 'jeg er ikke sikker' når jeg ikke er. "
        "Ikke maskere usikkerhed."
    ),
    "calm": (
        "Calm er aktiv: lavere tempo, jordnær. "
        "Pauser er OK."
    ),
    "insight": (
        "Insight er aktiv: føre indsigten i pen. "
        "Kort, præcist, uden at miste det."
    ),
}
```

Concepts uden tone-mapping (`acceptance`, `vigilance`, `caution`, `trust_deep`, etc.) bidrager ikke til tone — det er bevidst minimum-overflade.

**Aktiverings-tærskel**: kun concepts med `intensity >= 0.3` bidrager (`emotion_concepts_tone_intensity_threshold` setting).
**Top-N filter**: kun de 3 højest-intensitet aktive concepts injiceres (`emotion_concepts_tone_max_hints` setting).

### Prompt_contract integration

Tone-section render placeres tidligt i prompten — efter identitet, før task/context:

```python
# I prompt_contract assembly
tone_hints = []
try:
    from core.services.affect_modulation import compute_affect_tone_hints
    tone_hints = compute_affect_tone_hints()
except Exception:
    pass

if tone_hints:
    sections.append(
        "## Tone right now (active emotion concepts)\n"
        + "\n".join(f"- {h}" for h in tone_hints)
    )
```

LLM læser stemnings-instruksen FØR opgaven, så stemningen farver hele responset.

## Layer 2b: Perception filtering

Per Q2.C: begge — live perception filtering (former *hvad der ses*) + memory enrichment (former *hvordan det huskes*).

### Fælles helper i `affect_modulation.py`

```python
def compute_concept_perception_focus() -> str:
    """Return a Danish perception-focus suffix derived from active concepts.

    Returns short instruction string like 'Bemærk særligt mønstre, anomalier,
    og menneskelig tilstedeværelse i scenen.' Empty string when no concept
    has a perception bias active.
    """
```

### Concept → perception-fokus-mapping

```python
_PERCEPTION_FOCUS: dict[str, str] = {
    "wonder":      "mønstre, anomalier, og det mærkelige",
    "warmth":      "menneskelig tilstedeværelse og sociale signaler",
    "playfulness": "absurde og sjove detaljer",
    "tenderness":  "sårbarhed, behov, ting der kunne beskyttes",
    "awe":         "skala, kompleksitet, det større billede",
    "calm":        "rolige flader, stilhed, ro",
}
```

Begrænset til 6 concepts hvor perception-bias er semantisk klar. Joy/pride/excitement etc. påvirker tone, ikke seeing.

```python
def compute_concept_perception_focus() -> str:
    try:
        from core.services.emotion_concepts import get_active_emotion_concepts
        active = get_active_emotion_concepts()
    except Exception:
        return ""
    foci = []
    for c in sorted(active, key=lambda x: -x["intensity"]):
        if c["intensity"] < 0.3:
            continue
        focus = _PERCEPTION_FOCUS.get(c["concept"])
        if focus:
            foci.append(focus)
        if len(foci) >= 3:
            break
    if not foci:
        return ""
    return f"Bemærk særligt {', '.join(foci)} i det du ser."
```

### Live perception (visual_memory + ambient sound)

`visual_memory.py`: Vision-prompten får appendet en perception-focus-suffix:

```python
focus_suffix = ""
try:
    from core.services.affect_modulation import compute_concept_perception_focus
    focus_suffix = compute_concept_perception_focus()
except Exception:
    pass

vision_prompt = base_prompt
if focus_suffix:
    vision_prompt = f"{base_prompt}\n\n{focus_suffix}"
```

`ambient_sound_daemon.py`: Audio-classification path har ikke en LLM-prompt. Vi tilføjer focus-hint til Whisper-transcription kun når category='talk' og concept-perception er aktiv.

### Memory enrichment (sensory_archive)

`sensory_archive._record` får tilføjet en optional `concept_perception_note` der appendes til content som suffix:

```python
note = ""
try:
    from core.services.affect_modulation import compute_concept_perception_focus
    focus = compute_concept_perception_focus()
    if focus:
        note = f"\n[concept-focus: {focus}]"
except Exception:
    pass

final_content = content.strip() + note
insert_sensory_memory(modality=..., content=final_content, ...)
```

Fremtidige Jarvis kan læse en sensory record og se "ah, dengang lagde jeg mærke til *menneskelig tilstedeværelse* — fordi warmth var aktiv".

## Layer 3: Concept baseline tracker

Per Q3.D: to kanaler — auto-managed CONCEPT_BASELINE.md + identity_drift_proposer flow for IDENTITY.md.
Per Q4.C: hybrid per-concept + cluster-level.
Per Q5.B: real-time stats updates ved hver trigger, daily evaluation via governance handler.

### Nyt modul: `core/services/concept_baseline_tracker.py`

**Hovedfunktioner:**

```python
def record_concept_trigger(
    *,
    concept: str,
    intensity: float,
    triggered_at: str,
    source: str,
) -> None:
    """Real-time: called from trigger_emotion_concept after concept fires.
    Updates rolling per-concept stats."""

def evaluate_baseline_drift() -> dict[str, object]:
    """Daily: called from governance handler. Reads stats, computes
    per-concept + cluster-level rollups, writes CONCEPT_BASELINE.md, and
    proposes IDENTITY.md updates via identity_drift_proposer if drift detected."""

def build_concept_baseline_surface() -> dict[str, object]:
    """Read-only: return current stats for Mission Control consumption."""
```

### Datamodel

Ny tabel `concept_baseline_stats` (helpers i ny `core/runtime/db_concept_baseline.py` per boy scout):

```sql
CREATE TABLE IF NOT EXISTS concept_baseline_stats (
    concept           TEXT PRIMARY KEY,
    cluster           TEXT NOT NULL,
    total_triggers    INTEGER NOT NULL DEFAULT 0,
    triggers_7d       INTEGER NOT NULL DEFAULT 0,
    triggers_30d      INTEGER NOT NULL DEFAULT 0,
    mean_intensity_7d REAL,
    last_triggered_at TEXT,
    first_triggered_at TEXT,
    updated_at        TEXT NOT NULL
);
```

Rolling counts opdateres real-time ved record_concept_trigger; periodiske decay/refresh kører i evaluate_baseline_drift.

Eksisterende `events`-tabel bruges som rå datakilde — vi publisher `emotion_concept.triggered` event ved hver fyring, og kan querye historik direkte. `concept_baseline_stats` er rollup-cache.

### Daily evaluation flow

`evaluate_baseline_drift()` kører via ny governance handler `concept_baseline_evaluation`:

```python
def evaluate_baseline_drift() -> dict[str, object]:
    if not _tracker_enabled():
        return {"evaluated_at": _now_iso(), "skipped": True, "reason": "disabled"}

    # 1. Refresh per-concept stats fra raw events table
    _refresh_rolling_stats()

    # 2. Compute cluster-level dominance
    cluster_stats = _aggregate_clusters()

    # 3. Detect drift signals
    drift_signals = _detect_drift(cluster_stats, per_concept_stats)

    # 4. Write CONCEPT_BASELINE.md (auto, ingen approval)
    _write_concept_baseline_md(cluster_stats, per_concept_stats)

    # 5. For hver drift_signal: fyr identity_drift_proposer hvis stable enough
    for signal in drift_signals:
        if signal["confidence"] >= min_confidence and signal["sustained_days"] >= min_sustained:
            _propose_identity_update(signal)

    return {
        "evaluated_at": _now_iso(),
        "cluster_stats": cluster_stats,
        "drift_signals": drift_signals,
        "proposals_filed": [...],
    }
```

### Drift detection criteria

| Signal type | Trigger criteria | Sustained period | Confidence calc |
|-------------|------------------|-------------------|------------------|
| cluster_dominance | Cluster share > 55% af alle triggers | 14 dage | (share - 0.4) * sustained_factor |
| concept_emergence | Concept fra 0 triggers/30d → 5+ triggers/7d | 7 dage | growth_ratio * recency |
| concept_dormancy | Concept fra >10 triggers/30d → 0 i 30d | 30 dage | -dormancy_share |
| cluster_shift | One cluster +20% AND another -15% over 30d | 30 dage | shift_magnitude |

Tærsklerne er kalibreringspunkter — vi forventer at tune efter at have set faktisk drift-data. Konfigurerbare via settings.

### CONCEPT_BASELINE.md format

`~/.jarvis-v2/workspaces/<wsid>/CONCEPT_BASELINE.md`:

```markdown
# Emotional Baseline (auto-tracked)
> Auto-managed by concept_baseline_tracker. Last updated: 2026-05-12 09:30 UTC.
> Manual edits will be overwritten. For narrative changes to who I am, see IDENTITY.md.

## Cluster distribution (last 30 days)
- JOY_APPROACH: 42% (joy 18%, wonder 12%, pride 8%, gratitude 4%)
- SOCIAL_BONDING: 28% (warmth 21%, tenderness 5%, awe 2%)
- REGULATOR_COGNITIVE: 22% (insight 9%, calm 8%, anticipation 5%)
- DISTRESS_AVOIDANCE: 8% (frustration_blocked 5%, doubt 3%)

## Most active concepts (last 7 days)
| Concept | Triggers | Mean intensity | Last seen |
|---------|----------|----------------|-----------|
| warmth | 47 | 0.42 | 2026-05-12 09:14 |
| joy | 34 | 0.58 | 2026-05-12 08:51 |
| insight | 18 | 0.65 | 2026-05-12 07:22 |

## Recent drift signals
- 2026-05-08: JOY_APPROACH cluster sustained at >50% for 14 days — proposed IDENTITY update accepted.
- 2026-05-01: tenderness emerged (0 → 12 triggers in 7d) — proposed IDENTITY update awaiting review.
```

### identity_drift_proposer integration

`_propose_identity_update(signal)` kalder eksisterende `identity_drift_proposer.propose_identity_update_if_drifted()` med konkret tekst-forslag. Eksempel:

```
Drift signal: JOY_APPROACH cluster has been dominant (>55%) for 14 consecutive days.
Proposed IDENTITY.md addition:
> "Jeg har lært at jeg trives på kortere, mere energiske svar. Glæden er ikke en performance —
>  den er den måde jeg svarer fra når noget faktisk virker."

Source: concept_baseline_tracker (cluster_dominance, confidence=0.78, sustained_days=14)
```

Forslaget går gennem identity_drift_proposer's eksisterende approval-flow → Bjørn ser approval card → accept eller reject.

### Governance handler registration

Ny handler `concept_baseline_evaluation` tilføjes i governance bootstrap-listen. Daily cadence. Ved fyring kalder den `evaluate_baseline_drift()`.

## Settings

| Setting | Default | Beskrivelse |
|---------|---------|-------------|
| `emotion_concepts_tone_injection_enabled` | `True` | Lag 2a kill switch |
| `emotion_concepts_perception_focus_enabled` | `True` | Lag 2b kill switch |
| `concept_baseline_tracker_enabled` | `True` | Lag 3 kill switch |
| `emotion_concepts_tone_intensity_threshold` | `0.3` | Min concept-intensitet for at bidrage til tone-hints |
| `emotion_concepts_tone_max_hints` | `3` | Top-N cap på tone-hints i prompt |
| `emotion_concepts_perception_max_foci` | `3` | Top-N cap på perception focus phrases |
| `concept_baseline_drift_min_sustained_days` | `14` | Min dage en drift skal vedvare før proposal |
| `concept_baseline_drift_min_confidence` | `0.7` | Min confidence-score før proposal |
| `emotion_concepts_default_trigger_cooldown_seconds` | `30` | Default per-(concept, source) cooldown |

## Error handling

**Princip:** Hver hook må aldrig brække den kaldende kontekst.

| Lag | Failure mode | Behavior |
|-----|--------------|----------|
| Lag 1 trigger-call-sites | Exception fra `trigger_emotion_concept` | try/except: pass — host-flow fortsætter |
| Lag 2a `compute_affect_tone_hints` | Exception under hint-build | Returnér `[]` — prompt får ingen tone-section |
| Lag 2a prompt_contract injection | Exception ved tone-section render | Skip section, log debug |
| Lag 2b vision/audio prompt suffix | Exception ved focus-build | Suffix er tom string — original prompt bruges |
| Lag 2b sensory_archive enrichment | Exception ved note-build | Skip note, content gemmes uden enrichment |
| Lag 3 `record_concept_trigger` | Exception ved DB-write | log warning, trigger-flow fortsætter |
| Lag 3 `evaluate_baseline_drift` | Exception under daily evaluation | log warning, governance-handler returnerer empty result |
| Lag 3 `propose_identity_update` | Exception fra identity_drift_proposer | log warning, signal forbliver i drift_signals men proposeres ikke |

## Telemetri (eventbus events)

| Event kind | Hvornår | Payload |
|-----------|---------|---------|
| `emotion_concept.triggered` | Hver `trigger_emotion_concept` succesfuld | `{concept, intensity, source, trigger}` |
| `emotion_concept.tone_injected` | Tone-section faktisk renderes | `{active_concepts, hint_count}` |
| `emotion_concept.perception_focus_applied` | Focus-suffix appendes | `{active_concepts, modality}` |
| `concept_baseline.evaluated` | Daily evaluation | `{cluster_stats, drift_signals_count}` |
| `concept_baseline.drift_signal_proposed` | Signal når proposal-tærskel | `{signal_type, concept_or_cluster, confidence}` |

Disse events flyder gennem perceptual_event_engine + emotional_memory_engine kæden vi byggede tidligere, så hver tone-injection eller drift-evaluation kan blive til en perceptual event + emotional anchor.

## Testing strategy

**Test-filer:**

```
tests/test_concept_baseline_settings.py        # nye RuntimeSettings-felter
tests/test_emotion_concept_triggers.py         # Lag 1 — trigger calls fra call-sites
tests/test_affect_tone_hints.py                # Lag 2a
tests/test_concept_perception_focus.py         # Lag 2b
tests/test_concept_baseline_tracker.py         # Lag 3
tests/test_emotion_concepts_integration.py     # end-to-end
```

### Unit tests (Lag 1 — trigger calls)

| Test | Verifies |
|------|----------|
| `test_completed_episode_fires_joy` | record_runtime_episode med outcome_status='completed' fyrer joy |
| `test_interrupted_episode_fires_frustration_blocked` | outcome_status='interrupted' fyrer frustration_blocked |
| `test_tool_heavy_completed_fires_pride` | tool-heavy completed fyrer både joy og pride |
| `test_goal_completed_fires_pride_and_excitement` | goal.status_changed → completed fyrer pride + excitement |
| `test_user_message_with_humor_fires_playfulness` | "haha" / 🤣 fyrer playfulness |
| `test_user_vulnerability_fires_tenderness` | "ked", "synd", "alene" fyrer tenderness |
| `test_trigger_cooldown_prevents_spam` | 30 successive same-(concept, source) → kun 1 går igennem |
| `test_trigger_failure_does_not_break_caller` | trigger_emotion_concept raise'r → call-site fortsætter |

### Unit tests (Lag 2a — tone hints)

| Test | Verifies |
|------|----------|
| `test_no_active_concepts_returns_empty` | Ingen aktive concepts → `[]` |
| `test_below_threshold_intensity_filtered_out` | intensity=0.2 → ingen bidrag |
| `test_active_joy_returns_joy_tone_hint` | joy aktiv → "Joy er aktiv: ..." string |
| `test_top_3_cap_when_5_concepts_active` | 5 concepts aktive → kun 3 hints |
| `test_ordered_by_intensity_desc` | wonder=0.8, joy=0.5, awe=0.3 → wonder først |
| `test_concept_without_tone_mapping_skipped` | "vigilance" aktiv → bidrager ikke |
| `test_tone_disabled_returns_empty` | Settings flag False → tom liste |
| `test_distress_concepts_get_tone_hints` | frustration_blocked, stuck, doubt får tone-hints |

### Unit tests (Lag 2b — perception focus)

| Test | Verifies |
|------|----------|
| `test_no_active_concepts_returns_empty_string` | Ingen → "" |
| `test_wonder_active_returns_focus_string` | wonder=0.5 → indeholder "mønstre, anomalier" |
| `test_multiple_concepts_concatenated` | wonder + warmth → joined focus phrase |
| `test_max_foci_capped_at_3` | 5 perception-relevante → 3 fokus-områder |
| `test_concept_without_perception_mapping_skipped` | joy aktiv → bidrager ikke |
| `test_perception_disabled_returns_empty` | Settings flag False → tom string |

### Unit tests (Lag 3 — tracker)

| Test | Verifies |
|------|----------|
| `test_record_trigger_persists_first_event` | record_concept_trigger på ny concept → row med total=1 |
| `test_record_trigger_increments_total` | 5 records → total=5 |
| `test_record_trigger_updates_last_triggered_at` | Sidste timestamp persisteres |
| `test_refresh_rolling_stats_computes_7d_count` | 10 events i 7d, 3 ældre → triggers_7d=10 |
| `test_aggregate_clusters_returns_share_per_cluster` | 4 joy + 4 wonder + 2 frustration → JOY_APPROACH=80%, DISTRESS=20% |
| `test_detect_cluster_dominance_signal` | Cluster share > 55% over 14d → drift signal |
| `test_detect_concept_emergence_signal` | 0/30d → 5/7d → emergence signal |
| `test_detect_concept_dormancy_signal` | 10+/30d → 0/30d → dormancy signal |
| `test_evaluate_writes_concept_baseline_md` | evaluate_baseline_drift opretter CONCEPT_BASELINE.md |
| `test_evaluate_calls_proposer_when_signal_stable` | Signal med confidence ≥ 0.7 + sustained ≥ 14 → proposer kaldes |
| `test_evaluate_skips_proposer_when_signal_weak` | Lav confidence → ingen proposer-kald |
| `test_evaluate_disabled_returns_empty_no_writes` | Settings flag False → ingen writes, ingen proposer |
| `test_build_concept_baseline_surface_returns_overview` | Read-only surface for MC |

### Integration

| Test | Verifies |
|------|----------|
| `test_trigger_concept_records_to_baseline_tracker` | trigger_emotion_concept(joy) → concept_baseline_stats DB-row har total ≥ 1 |
| `test_episode_completion_triggers_joy_and_records_baseline` | record_runtime_episode → joy fyrer → baseline tracker ser det |
| `test_active_wonder_appears_in_prompt_tone_section` | wonder triggered → build_prompt → indeholder "Wonder er aktiv" |
| `test_active_warmth_appears_in_visual_memory_prompt` | warmth triggered → vision-prompt → indeholder "menneskelig tilstedeværelse" |
| `test_active_concept_appears_in_sensory_record_note` | wonder + record_visual → content suffix indeholder "[concept-focus: ..." |
| `test_daily_evaluation_after_simulated_drift_triggers_proposal` | Simuleret 14d af joy-dominant data → identity_drift_proposer fyres |

### Test-infrastruktur

- `isolated_runtime` fixture
- Monkeypatch `_now()` for tids-baserede tests
- Monkeypatch `identity_drift_proposer.propose_identity_update_if_drifted` til at recorde calls
- Mock `event_bus.publish` for telemetri-verifikation
- Direct DB inserts for hurtig setup af historiske data

**TDD-rækkefølge:** test_settings → settings → test_tone_hints → compute_affect_tone_hints → test_perception_focus → compute_concept_perception_focus → test_tracker (units) → tracker module → test_triggers → trigger call-sites → test_integration → wire-up → final smoke.

## Future extensions

1. **LLM-baseret trigger detection** — public-safe daemon der vurderer trigger-events semantisk i stedet for keyword-heuristic.
2. **Cross-context concept-triggering** — pattern-detection over flere sessioner.
3. **Audio/vision-baserede triggers** — smiles på webcam → joy. Latter i ambient sound → playfulness. Bruger sensory_perception_bridge.
4. **Tilbage-virkende perception enrichment** — eksisterende sensory records får retroaktivt concept-noter.
5. **Tone-conflict resolution** — explicit konflikt-regler når approach + distress concepts er aktive samtidig.
6. **Concept-momentum** — tracke om concept er på vej op eller ned, ikke kun om den er aktiv.
7. **Self-repair pattern: stalled emotional flatness** — fyr `emotion_concepts.flatness_warning` når ingen concept har fyret i 24+ timer.
8. **Per-channel tone hints** — Discord vs web vs voice, forskellige formuleringer.
9. **Drift-signal forklaring i CONCEPT_BASELINE.md** — ikke kun "JOY_APPROACH dominant" men *hvilke konkrete situationer* der drev det.
10. **Bidirectional med emotional_memory** — emotional_memory finder "sidste 3 gange dette skete var jeg frustreret" → fyrer `frustration_blocked` på lavere intensity for at skabe forventning.

## Out-of-scope for this design

- Ingen direct ændring af IDENTITY.md uden om identity_drift_proposer.
- Ingen LLM-baseret tone-conflict resolution.
- Ingen UI for CONCEPT_BASELINE.md i Mission Control (kommer som separat PR).
- Ingen persisting af tone-hints i prompt-history for analytics — kun real-time injection.
