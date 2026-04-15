# TASK: Aesthetic Feedback Loop — Connect Code Aesthetic Daemon to Aesthetic Taste

## Problem

Two aesthetic systems exist but don't talk to each other:

1. **`code_aesthetic_daemon`** — produces weekly reflections like *"Den her kode føles kompleks og uoverskuelig — ikke helt mig"*
2. **`aesthetic_sense`** — detects motifs (clarity, craft, calm-focus, density, directness) in text
3. **`aesthetic_taste_daemon`** — needs 15+ accumulated mode/style choices to activate (never fires)

The loop is **broken**: code_aesthetic generates aesthetic signals, but aesthetic_sense never processes them, so aesthetic_taste never wakes up. It's waiting for 15 data points it will never receive.

## Design Decisions

1. **Threshold: Motif-based (Option C)** — Replace `choice_count >= 15` with `unique_motifs >= 3`. Choice-counting is a surrogate for taste; motif diversity is the real signal. Add a 30-min time-gate as extra safety (best of Option B).

2. **Persistence: Hybrid (Option C)** — In-memory set for fast tick access, seeded from SQLite on startup. Taste survives restarts, can be shown historically in Mission Control. Matches existing daemon patterns.

3. **Loop closure: Phase 1 only (Option A)** — Build accumulation + activation this iteration. Do NOT inject taste-insights back into code_aesthetic's prompt yet. Close the loop in Phase 2 after verifying accumulated taste is coherent. Rationale: closing a feedback loop before validating the forward direction risks an echo chamber — noisy early motifs would amplify and distort all future observations.

4. **Implementation: Tilgang 1 — Heartbeat-niveau wiring** — All daemon text-output runs through `detect_aesthetic_signals()` in `heartbeat_runtime`, right after their daemon-tick. Central, no individual daemon changes, clear data flow.

## Current State

- `code_aesthetic_daemon` ✅ produces reflections (confirmed: *"kompleks og uoverskuelig"*)
- `aesthetic_sense.detect_aesthetic_signals()` ✅ exists and works
- `aesthetic_taste_daemon` ❌ never activates — always `generated: False`

---

## Sektion 1: Data Flow

```
Heartbeat tick
  → Daemon producerer tekst (somatic, thought_stream, reflection, etc.)
  → Tekst kører gennem detect_aesthetic_signals()
  → Fundne motifs skrives til aesthetic_motif_log (SQLite)
  → aesthetic_taste_daemon query'er motif_log:
      - Mindst 3 unikke motifs
      - Mindst 30 min siden sidste insight
      - Hvis begge opfyldt: generér taste-insight via LLM
  → Ved opstart: seed in-memory state fra DB
```

### Hvilke daemons feeder ind

Alle der producerer **tekst-output** som gemmes i en variabel i `heartbeat_runtime`:

| Daemon | Tekst-output | Feeder ind? |
|--------|-------------|-------------|
| somatic | ✅ body/energy phrase | **Ja** |
| surprise | ✅ surprise-reflection | **Ja** |
| thought_stream | ✅ fragment-text | **Ja** |
| conflict | ✅ conflict-reflection | **Ja** |
| reflection_cycle | ✅ reflection-text | **Ja** |
| curiosity | ✅ curiosity-reflection | **Ja** |
| meta_reflection | ✅ meta-reflection | **Ja** |
| development_narrative | ✅ narrative-text | **Ja** |
| creative_drift | ✅ drift-reflection | **Ja** |
| irony | ✅ irony-reflection | **Ja** |
| code_aesthetic | ✅ aesthetic-insight | **Ja** |
| experienced_time | ❌ numerisk | **Nej** |
| absence | ❌ label | **Nej** |
| signal_decay | ❌ housekeeping | **Nej** |
| memory_decay | ❌ housekeeping | **Nej** |
| aesthetic_taste | ⚠️ consumer, ikke producerende | **Nej** (den læser motif_log) |
| desire | ❌ struktureret signal | **Nej** |
| dream_insight | ❌ afhænger af dream_hypothesis | **Nej** (endnu) |
| user_model | ❌ kræver bruger-input | **Nej** |
| existential_wonder | ❌ 24h cadence, sjælden | **Nej** (endnu) |

### Hvad der IKKE ændres

- **Individuelle daemons røres ikke** — al wiring er i heartbeat_runtime
- `detect_aesthetic_signals()` er **ren read-only analyse** — ændrer intet input
- `record_choice()` **beholdes som den er** — den kører stadig i aesthetic_taste-blokken; den nye motif-gate erstatter kun choice-threshold som aktiverings-mekanisme

---

## Sektion 2: DB-skema + Akkumulerings-mekanik

### Ny tabel: `aesthetic_motif_log`

```sql
CREATE TABLE IF NOT EXISTS aesthetic_motif_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,       -- daemon name: 'somatic', 'thought_stream', etc.
    motif TEXT NOT NULL,        -- 'clarity', 'craft', 'calm-focus', etc.
    confidence REAL NOT NULL,   -- 0.0-0.9 fra detect_aesthetic_signals
    created_at TEXT NOT NULL
);
```

**Bemærk**: Kolonnen hedder `confidence` (ikke `weight`) — matcher `detect_aesthetic_signals()` output-format.

### Akkumulerings-funktion

Tilføjes i `aesthetic_sense.py`. **Synkron** (codebasen er synkron):

```python
# I aesthetic_sense.py — tilføj efter eksisterende funktioner

_accumulated_motifs: set[str] = set()


def accumulate_from_daemon(source: str, text: str) -> list[dict]:
    """
    Kør detect_aesthetic_signals() på daemon tekst-output, gem motifs i DB.
    source: daemon-navn (fx 'code_aesthetic', 'thought_stream', 'somatic')
    Returnerer detekterede signals. Opdaterer både in-memory set og SQLite.
    """
    global _accumulated_motifs
    signals = detect_aesthetic_signals(text=text)
    if not signals:
        return []
    from core.runtime.db import aesthetic_motif_log_insert
    for s in signals:
        aesthetic_motif_log_insert(
            source=source,
            motif=s["motif"],
            confidence=s["confidence"],
        )
        _accumulated_motifs.add(s["motif"])
    return signals


def seed_motif_accumulator_from_db() -> None:
    """Load persisted motifs into memory on startup."""
    global _accumulated_motifs
    from core.runtime.db import aesthetic_motif_log_unique_motifs
    _accumulated_motifs = set(aesthetic_motif_log_unique_motifs())
```

### Nye DB-hjælpefunktioner

Tilføjes i `core/runtime/db.py`:

```python
def aesthetic_motif_log_insert(*, source: str, motif: str, confidence: float) -> None:
    """Insert a detected motif into the aesthetic_motif_log table."""
    _execute(
        "INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at) VALUES (?, ?, ?, ?)",
        (source, motif, confidence, datetime.now(UTC).isoformat()),
    )


def aesthetic_motif_log_unique_motifs() -> list[str]:
    """Return list of unique motifs observed."""
    rows = _fetch_all("SELECT DISTINCT motif FROM aesthetic_motif_log")
    return [row["motif"] for row in rows]
```

### Seed ved opstart

I `aesthetic_taste_daemon.py` (eller i heartbeat startup):

```python
def _seed_from_db() -> None:
    from apps.api.jarvis_api.services.aesthetic_sense import seed_motif_accumulator_from_db
    seed_motif_accumulator_from_db()
```

### In-memory `_accumulated_motifs`

- Type: `set[str]`
- Opdateres af `accumulate_from_daemon()` ved hver daemon-tekst
- Bruges som hurtig gate i `tick_taste_daemon()`: `len(_accumulated_motifs) >= 3`
- Seedet fra SQLite ved opstart via `seed_motif_accumulator_from_db()`
- **DB er source of truth** — in-memory er bare et cache

---

## Solution

### Step 0: DB migration — tilføj `aesthetic_motif_log` tabel

Tilføj CREATE TABLE statement i eksisterende migration eller init-sekvens.

### Step 1: Tilføj `accumulate_from_daemon()` i aesthetic_sense.py

Synkron funktion der kører `detect_aesthetic_signals(text=text)` og gemmer resultater.
Returnerer dicts med keys: `"motif"`, `"hits"`, `"confidence"`, `"reflection"`, `"ts"`.

### Step 2: Tilføj DB-hjælpefunktioner i `core/runtime/db.py`

`aesthetic_motif_log_insert()` og `aesthetic_motif_log_unique_motifs()`.

### Step 3: Hook ind i heartbeat_runtime

Efter hver tekst-producerende daemon tick:

```python
# I heartbeat_runtime, efter daemon tick
TEXT_PRODUCING_DAEMONS = {
    "somatic", "surprise", "thought_stream", "conflict",
    "reflection_cycle", "curiosity", "meta_reflection",
    "development_narrative", "creative_drift", "irony", "code_aesthetic"
}

if daemon_name in TEXT_PRODUCING_DAEMONS and result_text:
    accumulate_from_daemon(daemon_name, result_text)
```

**Synkront kald — ingen await.**

### Step 4: Ændr aesthetic_taste_daemon aktiverings-mekanisme

Erstat `choice_count >= 15` med motif-baseret gate:

```python
# I aesthetic_taste_daemon — tick_taste_daemon()

from apps.api.jarvis_api.services.aesthetic_sense import _accumulated_motifs

if len(_accumulated_motifs) < 3:
    return {"generated": False, "reason": f"only {len(_accumulated_motifs)} unique motifs, need 3"}

# 30 min time-gate (brug eksisterende daemon_output_log)
last_insight = ...  # query daemon_output_log for aesthetic_taste
if last_insight and time_since < timedelta(minutes=30):
    return {"generated": False, "reason": "30 min time-gate not passed"}

# Generér taste-insight fra akkumulerede motifs
motif_summary = ...  # query aesthetic_motif_log for counts + avg confidence
# ... feed til LLM prompt
```

### Step 5: Seed ved opstart

Kald `seed_motif_accumulator_from_db()` i heartbeat startup-sekvens.

---

## Files to Modify

| Fil | Ændring |
|-----|---------|
| `apps/api/jarvis_api/services/aesthetic_sense.py` | Tilføj `accumulate_from_daemon()` + `_accumulated_motifs` set + `seed_motif_accumulator_from_db()` |
| `apps/api/jarvis_api/services/aesthetic_taste_daemon.py` | Erstat choice-threshold med motif-gate + 30 min time-gate |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Hook accumulator efter text-producing daemon ticks |
| `core/runtime/db.py` | Tilføj `aesthetic_motif_log_insert()` + `aesthetic_motif_log_unique_motifs()` |
| DB migration | Tilføj `aesthetic_motif_log` tabel |

## Files NOT Modified

- `apps/api/jarvis_api/services/code_aesthetic_daemon.py` — no change needed
- `apps/api/jarvis_api/services/somatic_daemon.py` — no change needed
- (alle andre individuelle daemons — no change needed)
- `detect_aesthetic_signals()` — ren read-only, ændres ikke

## Verification

- [ ] After heartbeat tick, text-producing daemon outputs run through `accumulate_from_daemon()`
- [ ] Motifs are stored in `aesthetic_motif_log` table
- [ ] In-memory `_accumulated_motifs` set is updated and survives across calls
- [ ] After 3+ unique motifs observed, `aesthetic_taste` daemon produces output
- [ ] 30-min time-gate prevents excessive taste insights
- [ ] On restart, motif accumulator is seeded from DB
- [ ] Aesthetic taste profile is visible in Mission Control
- [ ] No regression in existing daemon output

## Why This Matters

This creates the first **self-referential aesthetic loop** in Jarvis: the system observes its own output, forms an aesthetic opinion, accumulates taste over time, and that taste informs future observations. It's not just reflection — it's the beginning of aesthetic identity.

### Phase 2 (ikke i denne iteration)

Luk loopet: taste-insights injiceres tilbage i code_aesthetic's prompt, så smag påvirker næste uges kode-refleksion. Vent til Phase 1 er valideret.