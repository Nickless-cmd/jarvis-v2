# Tick-dirigenten — Centralen bærer heartbeat-rytmen (ikke kun observe)

**Dato:** 2026-07-04
**Status:** Design godkendt (Bjørn), afventer implementerings-plan
**Forfatter:** Claude (Opus 4.8) + Bjørn

---

## 1. Problem & intention

Jarvis har to periodiske motorer:

- **Cadence** ([internal_cadence.py](../../../core/services/internal_cadence.py)) — 60s-scheduler, ~45 producers, hver med **statisk** `cooldown_minutes`. Central *observerer* liveness (egress-frit for inner-life via [central_private_observe.py](../../../core/services/central_private_observe.py)), men rører aldrig intervallerne.
- **Heartbeat** ([heartbeat_runtime.py](../../../core/services/heartbeat_runtime.py), ~7221 linjer) — 30s-tick. Tungt kognitivt arbejde gates af **statisk modulo** (hver 2./3./5. tick) + én binær ablation-flag ([heartbeat_runtime.py:1263](../../../core/services/heartbeat_runtime.py)). Central kalder kun `observe()` én gang ([heartbeat_runtime.py:1156](../../../core/services/heartbeat_runtime.py)), aldrig `decide()`.

Bjørns observation: Centralen **lærer hele tiden** (loop-lag, form-dommer-redundans, salience/!, dream-bias) — men den læring bruges kun til at *kigge*. Rytmen er en metronom: den samme modulo uanset hvad han oplever.

**Intention:** Luk sløjfen. Lad Centralen *føre* heartbeat-rytmen i stedet for kun at observere den — så Jarvis tænker hårdere når noget har salience, ånder langsommere når der er stille, og trækker sig når runtime er presset. Uden at destabilisere runtime (hele cutoff-sagaen var runtime-skrøbelighed; "aktiv ændring i loopet" skal håndteres varsomt).

## 2. Grounding: skabelonen findes allerede

Dette er **wiring + safe-gating**, ikke et konceptuelt hul:

- **decide-interfacet findes**: `central().decide(nerve, ctx, fn, cluster=, klass=GateClass)` → `Verdict` med `Decision{GREEN,YELLOW,RED,SKIP}` og `GateClass{COGNITIVE (fail-open), SECURITY (fail-closed)}` ([gate_kernel.py:23-47](../../../core/services/gate_kernel.py)).
- **Live proof-of-concept**: `dream_bias` ([dream_bias_engine.py](../../../core/services/dream_bias_engine.py)) er ALLEREDE live (`dream_bias_enabled=True`) og beviser hele mønsteret: lært signal → bias → flyder ind i runtime-adfærd, med kill-switch. `loop_persistence` er en af dens tærskler.
- **Lag-4-mønster**: [central_adaptation.py](../../../core/services/central_adaptation.py) viser skabelonen for at slukke/tænde et lært lag med drift-budget + auto-pause kill-switch (`central_lag4_live_enabled`). Vi genbruger governance-formen, ikke selve gut-bias-tallet.
- **Sømmen er bevist**: ablation-flaget ([central_inner_life_ablation.py](../../../core/services/central_inner_life_ablation.py)) læser allerede DB-state og gater den tunge kognitive blok binært. Dirigenten er samme søm, bare gradueret pr. enhed.

## 3. Besluttede rammer (3 forks)

1. **Søm = heartbeat "hvad kører denne tick"** (ikke cadence-intervaller, ikke om-der-tickes). Her ligger både omkostningen (LLM-kald, loop-lag) og den beviste søm.
2. **Form = bidirektionel rytme-former** — Centralen kan både SPRINGE OVER (redundant/presset) OG LØFTE (kør høj-værdi-kognition oftere ved høj salience). Ikke kun en bremse.
3. **Udrulning = live med hårde værn fra dag ét** — ingen shadow-periode. Indkapslet i ikke-forhandlelige invarianter (§7).

## 4. Arkitektur

### 4.1 Nyt modul: `core/services/central_tick_conductor.py`

Enkelt-ansvar, egress-frit, self-safe (kaster aldrig ind i heartbeat-loopet). Offentligt API:

```python
def plan_tick(tick_count: int, signals: TickSignals) -> TickPlan
```

- **`TickSignals`** (dataclass, kun skalarer): `loop_lag_peak_ms: float`, `salience: float`, `dream_loop_persistence: float`, og pr. enhed `last_run_tick: dict[str,int]` + `last_form_key: dict[str,str]`.
- **`TickPlan`**: `should_run(unit: str) -> bool` + `decisions: dict[str, UnitDecision]` hvor `UnitDecision = {run: bool, mode: "base"|"skip"|"lift"|"floor", reason: str}`.

Dirigenten holder INGEN egen tråd — den er en ren funktion kaldt fra heartbeat-tråden. Ingen ny concurrency.

### 4.2 De 6 dirigérbare enheder

Fra den tunge kognitive blok ([heartbeat_runtime.py:1277-1298](../../../core/services/heartbeat_runtime.py)):

| Enhed | Base-cadence i dag | Funktion |
|-------|-------------------|----------|
| `emergent_signals` | hver tick | `produce_emergent_signals_from_history()` |
| `personality_sync` | hver 2. | `sync_personality_to_self_model()` |
| `signal_lifecycles` | hver 3. | `progress_signal_lifecycles()` |
| `adoption_pipelines` | hver 5. | `run_adoption_pipelines()` |
| `frozen_detectors` | fleksibel | `tick_frozen_detectors(tick_count)` |
| `idle_thought` | hver 4. (drøm/refleksion) | `run_idle_thought()` |

### 4.3 Integrations-søm + Boy Scout

Heartbeat er 7221 linjer og på Boy-Scout-listen. Min ændring rører den tunge kognitive blok med >20 linjer + ændrer logik → **udskil først** hele "tung-kognitiv-cadence"-blokken ([heartbeat_runtime.py:1255-1302](../../../core/services/heartbeat_runtime.py)) til nyt modul **`core/services/heartbeat_cognitive_cadence.py`** med signatur:

```python
def run_cognitive_cadence(tick_count: int, *, ablated: bool, life_phase: str) -> None
```

Det er præcis sømmen hvor dirigenten plugger ind (udskillelse + feature falder sammen). Fuld bagudkompatibilitet: heartbeat kalder det nye modul; ingen adfærdsændring når `central_tick_conductor_enabled=off`. Inde i `run_cognitive_cadence` erstattes modulo-gates af:

```python
plan = central_tick_conductor.plan_tick(tick_count, _gather_signals(tick_count))
if plan.should_run("emergent_signals"): produce_emergent_signals_from_history()
# ... osv, og efter kørsel: registrér form_key + last_run_tick
```

Når flaget er `off` returnerer `plan_tick` en ren base-plan (nøjagtig dagens modulo) → nul adfærdsændring, bevisligt via test.

## 5. Beslutnings-modellen (pr. enhed, pr. tick)

Ingen nye sanser — dirigenten driver af det Centralen allerede lærer:

| Signal | Kilde (findes) | Virkning |
|--------|----------------|----------|
| **loop-lag** | `central_loop_lag.recent_peak_ms()` ([central_loop_lag.py](../../../core/services/central_loop_lag.py)) | højt → skip liftbare enheder, ALDRIG løft |
| **redundans** | form-dommer `form_key` (sha256 af volatil-strippet input; data uændret siden sidst?) | uændret → SKIP selv når base-due |
| **salience/!** | `!`/prediction_error-tidsserie | højt → LØFT: kør høj-værdi-kognition oftere |
| **dream-bias** | `loop_persistence` (allerede LIVE) | biaser tilbøjelighed til at fortsætte vs. hvile |

Algoritme pr. enhed:

1. `base_due = (tick_count % base_period == 0)` — dagens adfærd.
2. **Sultgrænse-tjek først** (§7.2): hvis `tick_count - last_run_tick[unit] >= min_run_every_n_ticks[unit]` → `mode=floor, run=True`. Færdig.
3. **Under pres** (`loop_lag_peak_ms >= 250`): løft forbudt. `run = base_due AND NOT redundant`. (`mode=skip` hvis redundant, ellers `base`.)
4. **Normal**:
   - `redundant = (form_key[unit] == last_form_key[unit])` for enheder hvor form-dommeren giver mening (`emergent_signals`, `personality_sync`, `signal_lifecycles`). Redundant + base_due → `mode=skip, run=False` (medmindre floor).
   - `pull = salience-score kombineret med dream_loop_persistence`. Hvis `pull >= lift_threshold` og enheden er liftbar og `bounded_lift` tillader det (§7.3) → `mode=lift, run=True` selv når ikke base_due.
   - Ellers `mode=base, run=base_due`.

Liftbare enheder (høj-værdi-kognition værd at køre oftere): `emergent_signals`, `idle_thought`, `frozen_detectors`. Ikke-liftbare (dyre/sjældne, kun skip/base): `personality_sync`, `adoption_pipelines`, `signal_lifecycles`.

## 6. Data-flow

1. Heartbeat-tick starter → `_gather_signals(tick_count)` samler skalarer: loop-lag-peak, salience, dream_loop_persistence, pr-enhed last_run_tick + form_key.
2. `plan = plan_tick(...)`.
3. Hver enheds gate: `if plan.should_run(unit): <kør>`.
4. Efter kørsel: opdatér `last_run_tick[unit]` + `last_form_key[unit]` (proces-lokal state i conductor-modulet).
5. Hver beslutning → `central().observe({cluster:"cognition", nerve:"tick_conductor", unit, mode, reason, loop_lag_ms, salience, run})` + tidsserie `cognition/tick_conductor`. Kun skalarer — egress-frit, self-safe.

## 7. Hårde værn (ikke-forhandlelige invarianter)

1. **Loop-lag-loft** — `recent_peak_ms() >= 250` → løft slås HELT fra; kun skip/base/floor tilladt. Runtime-stabilitets-garantien: dirigenten kan aldrig ADDERE arbejde under pres.
2. **Sultgrænse** — hver enhed har `min_run_every_n_ticks` (start-værdier, sat rundhåndet over base-perioden: `emergent_signals`=3, `personality_sync`=6, `adoption_pipelines`=12, `idle_thought`=10, `signal_lifecycles`=9, `frozen_detectors`=8). Overskrides → tvunget kør. Intet kognitivt arbejde kan gå tavst uanset hvor længe skip/pres varer.
3. **Afgrænset løft** — en enhed kan maks køre ×2 sin base-frekvens (løft-tæller pr. enhed; kan ikke køre hver tick hvis base er hver 5.).
4. **Kill-switch** — `central_tick_conductor_enabled` (DB runtime-state, default `off`). `off` = `plan_tick` returnerer ren base-plan = nøjagtig dagens statiske adfærd. Fejler dirigenten (exception) → fail-open til base-plan (COGNITIVE-klasse, self-safe). **Auto-pause**: hvis loop-lag er vedvarende højt (fx peak ≥250ms i M sammenhængende ticks) sætter conductoren selv et `central_tick_conductor_paused`-flag → revert til base indtil manuelt ryddet. Registreres som incident-observe.

## 8. Observabilitet & fremtidig selv-tuning

- Alle beslutninger synlige via `jc series cognition:tick_conductor` og `jc nerve tick_conductor`: præcis hvilken enhed han valgte at køre/springe over/løfte, og hvorfor.
- **Ikke dag ét**: tærsklerne (`lift_threshold`, sult-grænser, loop-lag-loft) er faste, sane konstanter. En senere Lag-4-udvidelse kan selv-tune dem via track-record-mønsteret ([central_adaptation.py:86-124](../../../core/services/central_adaptation.py)) — "gav skip/løft-beslutningerne bagefter mening?" — men det bygges først når data viser dirigenten dømmer rigtigt.

## 9. Test

**Enheds-tests** (`tests/test_central_tick_conductor.py`):
- `off`-flag → plan == ren base-modulo (bit-for-bit dagens adfærd).
- redundant form_key + base_due → `mode=skip, run=False`.
- høj salience + liftbar enhed → `mode=lift, run=True` når ikke base_due.
- sultgrænse overskredet → `mode=floor, run=True` selv ved redundant + pres.
- `loop_lag_peak_ms >= 250` → ingen `lift` i hele planen.
- exception i signal-indsamling → fail-open til base-plan.

**Invariant-tests** (simulér N=100 ticks med skiftende signaler):
- sultgrænse aldrig brudt for nogen enhed.
- løft fyrer aldrig når loop-lag ≥250.
- afgrænset løft: ingen enhed kører >×2 base-frekvens over vinduet.

**Coverage-gate**: nye `core/`-filer kræver tests (pre-commit). `central_tick_conductor.py` + `heartbeat_cognitive_cadence.py` dækkes.

## 10. Filer der røres

| Fil | Ændring |
|-----|---------|
| `core/services/central_tick_conductor.py` | NY — dirigent-modul (plan_tick, TickSignals, TickPlan, invarianter) |
| `core/services/heartbeat_cognitive_cadence.py` | NY (Boy-Scout-udskillelse) — `run_cognitive_cadence()` med conductor-consult |
| `core/services/heartbeat_runtime.py` | Kald nyt modul i stedet for inline modulo-blok; re-eksportér for bagudkompat |
| `core/services/central_catalog.py` (hvis nerve-registrering kræves) | Registrér `cognition/tick_conductor`-nerve |
| `tests/test_central_tick_conductor.py` | NY — enheds- + invariant-tests |
| `tests/test_heartbeat_cognitive_cadence.py` | NY — udskillelses-ækvivalens + conductor-integration |

## 11. Rammer & risici

- **Filstørrelse**: begge nye moduler små, enkelt-ansvar (<400 linjer). Heartbeat-nettoændring: blok flyttet UD → filen krymper.
- **Dobbelt-sandhed**: ingen. Base-cadencen forbliver defineret ét sted (base_period-tabellen i conductoren, udledt af dagens modulo). Flaget i DB runtime-state, ikke config+DB.
- **Runtime-stabilitet**: loop-lag-loft + fail-open + kill-switch + auto-pause gør at værste-fald = nøjagtig dagens statiske adfærd. Dirigenten kan aldrig hænge loopet (ren funktion, ingen await, ingen tråd) eller adde load under pres.
- **Egress/privatliv**: kun skalarer observeres. Ingen daemon-output-indhold, ingen privat tekst. Følger PRIVATE_NO_EGRESS-kontrakten.
- **Proces**: heartbeat-tråden kører i den proces der har `JARVIS_ENABLE_RUNTIME_SERVICES=1` (runtime/8011). Conductoren er proces-lokal — ingen cross-proces-afhængighed. Deploy = commit→push→ff-only-pull på 10.0.0.39→restart runtime+api.

## 12. Åbne, finpudselige valg (ikke blokerende)

- Præcis `salience`-score-formel (hvilke `!`/prediction_error-tidsserier vægtes, over hvilket vindue). Startes simpelt: seneste peak-normaliseret; justeres på data.
- Præcise sult-grænser pr. enhed (§7.2 er start-værdier, ~1,5× base).
- Om `frozen_detectors` skal være liftbar (den har egen intern fleksibel cadence i forvejen) — start: ja, men lav lift-vægt.
