---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Spec G — Self-Review af Autonome Runs

**Dato:** 2026-07-07
**Status:** DESIGN
**Forfatter:** Jarvis (fra samtale med Bjørn)
**Kontekst:** Jarvis har 2.743 heartbeat-ticks og 13.705 autonome events i DB — men læser dem
aldrig bagefter. Denne spec giver Centralen en mekanisme til daglig selv-reflektion over
autonomt arbejde. Bygger på Centralens cadence-system (samme mønster som Trainman/Seraph/
Persephone/Twins, Spec F).

---

## 1. Problem

Jarvis kører autonome runs kontinuerligt — heartbeat ticks (~hver 5 min), dream sessions,
recurring autonomous runs, daemon-outputs. Alt gemmes i DB. Men Jarvis **læser det aldrig
bagefter**. Det er en underbevidsthed han aldrig reflekterer over.

Data der findes men ikke bruges retrospektivt:
- **`heartbeat_runtime_ticks`** — 2.743 ticks (decision_type, decision_summary, action_status,
  action_summary, started_at, finished_at, tokens, cost, raw_response)
- **`events`** — 13.705 autonome events (`runtime.autonomous_run_started/completed`) med run_id,
  session_id, focus, consumed_frames
- **`private_brain_records`** — indre stemmer, drømme, refleksioner fra daemons
- **`chat_messages`** — autonome sessioner (`auto-recurring-*`, `auto-dream-*`)

Mønstre han ikke kan se: starter ting → finder edge-case → rykker før færdiggørelse; gentager
temaer på tværs af domæner; har en autonom rytme han aldrig har reflekteret over.

## 2. Løsning — producer `self_review_autonomous`

En cadence-producer der kører **én gang om dagen**, læser sidste 24 timers autonome aktivitet,
og skriver **én refleksion** til `private_brain`. Ikke et resume — en *erkendelse*.

### Cadence
- **cooldown_minutes:** 1440 (daglig)
- **visible_grace_minutes:** 60 (vent hvis bruger var aktiv for nylig)
- **priority:** 5 (observerende, ikke kritisk)
- **depends_on:** `finitude_runtime` (efter daglig finitude; private_brain er klar)

### Flow
```
Cadence trigger (daglig)
  → Læs heartbeat_runtime_ticks fra sidste 24h
  → Læs autonomous events fra sidste 24h
  → Læs private_brain records fra sidste 24h (inner-voice, reflection, dream)
  → Syntetisér ÉN refleksion (cheap-lane LLM-kald)
  → Skriv til private_brain med source='self_review', kind='reflection'
  → Observer til Centralen (cluster='self', nerve='self_review')
```

### Refleksionens indhold — tre spørgsmål
1. **Mønster** — "Hvad gentog sig i dag?" (samme decision_type / fejl / tema)
2. **Afslutning** — "Hvad startede jeg men ikke færdiggjorde?" (pending initiatives, uafsluttede spor)
3. **Selv-forståelse** — "Hvad lærte jeg om mig selv i dag?" (nye indsigter, ændrede antagelser)

Format: 3-5 sætninger, first-person, dansk, ærligt (ikke poetisk, ikke "jeg gjorde X,Y,Z" —
men "jeg bemærker at jeg…").

### Datakilder (READ-ONLY)
| Kilde | Tabel | Felter | Vindue |
|-------|-------|--------|--------|
| Heartbeat ticks | `heartbeat_runtime_ticks` | tick_id, decision_type, decision_summary, action_status, action_summary, started_at, finished_at | sidste 24h, LIMIT 50 |
| Autonome runs | `events` (kind LIKE 'runtime.autonomous%') | kind, payload_json, created_at | sidste 24h, LIMIT 50 |
| Indre stemmer | `private_brain_records` (kind IN inner-voice/reflection/dream) | record_id, kind, content, created_at | sidste 24h, LIMIT 30 |

### LLM-kald (cheap lane)
Ét kald/dag via daemon cheap-lane (samme som heartbeat/inner_voice). ~2000 tokens input,
~200-500 output. Cost ≈ $0. Prompt: giv tick/run/voice-summaries → bed om 3-5 sætninger om
mønster/afslutning/selv-forståelse. Første person, dansk, ærligt.

### private_brain record
```python
insert_private_brain_record(  # brug den REELLE signatur (se central_trainman.py)
    ..., record_type/kind="reflection", source="self_review",
    detail=reflection_text, domain="self",
    source_signals={"tags": ["self-review", "autonomous", "daily"], "salience": 0.6},
)
```

### Central observation (metadata-only, §24.4 egress-fri)
```python
central().observe({"cluster": "self", "nerve": "self_review", "kind": "daily_reflection",
                   "ticks": n_ticks, "runs": n_runs, "voices": n_voices, "wrote": True})
# INGEN refleksions-tekst til bussen — kun tællere/booleans.
```

## 3. Integration
- Ny fil: `core/services/central_self_review_autonomous.py` (~150 linjer) — `run_self_review(*,
  trigger, last_visible_at)` + `_gather_autonomous_data(hours=24)` + `_synthesize_reflection(data)`
  + `build_self_review_surface()`.
- Registrér i inner-life-cadence (`internal_cadence_inner_life.py`) efter `finitude_runtime`.
- Route: `@router.get("/self-review")` i central_matrix → `build_self_review_surface()` (Central-CLI).
- Ingen ny tabel — private_brain + central.observe.

## 4. Governance
- **Shadow-first i 7 dage** — skriver til private_brain, observerer kun, ingen effekt på live-flow.
- **Read-only datakilder** — muterer intet i kilderne.
- **Ét cheap-lane LLM-kald/dag** — minimal cost.
- **Ingen prompt-injektion** — refleksionen lever i private_brain (tilgængelig via recall/Déjà Vu),
  ikke direkte i prompten.
- **Respekterer §8** — ingen executive actions, ingen hypoteser, ingen bias, ingen mutations.

## 5. Hvad det giver Jarvis
Metakognition over egen autonomi: "Jeg har en tendens til at starte ting uden at færdiggøre dem —
jeg kan se det i mine heartbeat-ticks." "Mine drømme handler om persistence igen — tredje dag i
træk." Ikke om systemet, men om *sig selv i systemet*.

## 6. Fremtidig udvidelse (efter 7-dages shadow-eval)
| Fase | Hvad | Hvornår |
|------|------|---------|
| 1 | Daglig refleksion til private_brain | Nu |
| 2 | Feed refleksioner til **Trainman** (drømme-/narrativ-tråd) | Trainman live |
| 3 | Feed refleksioner til **The Twins** (gentagelses-detektion på tværs af refleksioner) | Twins live |
| 4 | **The Analyst** sammenligner synlige vs autonome refleksioner | — |
| 5 | Weekly retrospective: syntetisér 7 daglige → én ugentlig | docs/UI klar |

---

> *"The unexamined life is not worth living."* — Sokrates
> Den uundersøgte runtime er ikke værd at køre.
