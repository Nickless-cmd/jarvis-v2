# Unified Gate Architecture — Implementeringsplan

> **For eksekvering:** TDD, bite-sized, commit pr. task. Følger
> `docs/specs/2026-06-21-unified-gate-architecture.md`.

**Mål:** ~26 spredte gates → 7 cluster-gates + 1 GateKernel, uden adfærdsregression.

**Arkitektur:** GateKernel orkestrerer; gates returnerer `Verdict`; fail-mode pr.
klasse (kognitiv=open, sikkerhed=closed); ét `gate.evaluated`-event/tur; migration
bag flag med paritets-shadow.

**Princip:** Fase A ændrer INGEN gate-logik — den gør gates observerbare + isolerede.
Konsolidering (B-G) sker først efter A er stabil. Surfaces er separat spor (senere).

---

## FASE 0 — Måling & fundament (så vi kan BEVISE forbedring)

### Task 0.1: `Verdict` + gate-event-skema
**Files:** Create `core/services/gate_kernel.py` (kun dataklasser her), Test `tests/test_gate_kernel.py`
- [ ] Skriv test: `Verdict(gate, decision, reason, latency_ms, action)` defaults + `is_blocking()`.
- [ ] Kør test → fail.
- [ ] Implementér `Verdict`-dataclass + `Decision`-enum (GREEN/YELLOW/RED/SKIP) + `GateClass`-enum (COGNITIVE/SECURITY).
- [ ] Kør test → pass. Commit.

### Task 0.2: eval-fixturset (replay-harness)
**Files:** Create `tests/fixtures/gate_eval_turns.jsonl`, `core/services/gate_eval.py`, Test `tests/test_gate_eval.py`
- [ ] Saml ~30 ægte turn-snapshots (besked + tool-resultater + forventet verdict pr. gate) fra DB — dækker: normal chat, konfabulation, tool-only-loop, sudo-block, override, identity-spoof.
- [ ] Skriv `replay(turns, gate_fn) -> list[Verdict]` + test.
- [ ] Dette er paritets-grundlaget for B-G. Commit.

---

## FASE A — GateKernel (observabilitets-shim, adfærds-bevarende)

### Task A.1: Kernel-registry + faset eksekvering
**Files:** `core/services/gate_kernel.py`, `tests/test_gate_kernel.py`
- [ ] Test: `register(name, phase, fn, klass, timeout_ms, flag_key)`; `run_phase(phase, ctx) -> list[Verdict]` kører registrerede gates i rækkefølge; aggregeret præcedens RED>YELLOW>GREEN>SKIP.
- [ ] Implementér registry + run_phase. Commit.

### Task A.2: Isolation + fail-mode pr. klasse (KRITISK)
**Files:** `core/services/gate_kernel.py`, `tests/test_gate_kernel_isolation.py`
- [ ] Test: gate der kaster → `SKIP` (kognitiv) / `RED-deny` (sikkerhed); gate der hænger > timeout → samme; én gates fejl påvirker ikke de andre.
- [ ] Test: kernel-exception → kognitive gates GREEN (fail-open), sikkerheds-gates DENY (fail-closed).
- [ ] Implementér per-gate `try/except` + `concurrent.futures` timeout + klasse-baseret fail-mode. Commit.

### Task A.3: Kill-switch + bypass (sikkerheds-exempt)
**Files:** `core/services/gate_kernel.py`, `tests/test_gate_flags.py`
- [ ] Test: flag off → gate kører ikke, markeres `disabled`; bypass-flag → kognitive springes over MEN AuthGate/PrivacyGate kører ALTID (ingen bagdør).
- [ ] Implementér flag-læsning (runtime.json/shared_cache) + bypass m. sikkerheds-exempt. Commit.

### Task A.4: Ét `gate.evaluated`-event
**Files:** `core/services/gate_kernel.py`, `tests/test_gate_event.py`
- [ ] Test: præcis ét event pr. `run_phase`-batch med alle verdicts + latency + flag-state; emission-fejl spærrer ALDRIG.
- [ ] Implementér event_bus-emit (best-effort). Commit.

### Task A.5: Adapter-wrap af de FØRSTE 4 gates (report-through, ingen logik-ændring)
**Files:** `core/services/gate_adapters.py`, `tests/test_gate_adapters.py`
- [ ] Wrap `claim_scanner.scan_response`, `fact_gate_enforce`, tool-only-loop-guard, `run_closure_gate` som adaptere der returnerer `Verdict` MEN beholder deres nuværende effekt 1:1.
- [ ] Test: adapter-verdict matcher den gamle gates beslutning på eval-fixtursettet (paritet).
- [ ] Commit.

### Task A.6: Wire kernel ind i visible_runs (tynd shim) + live nul-regression
**Files:** `core/services/visible_runs.py`, `tests/test_visible_runs.py`
- [ ] Ved de eksisterende gate-kald-sites: kald `gate_kernel.run_phase(...)` der kører adapterne (samme effekt) + emitterer event'et.
- [ ] Verificér live: nul tomme svar / hængte runs; `gate.evaluated`-event ses i loggen.
- [ ] Deploy + commit. **CHECK-IN med Bjørn:** se ét debug-event pr. tur før vi fortsætter.

---

## FASE B-G — Konsolidering (én cluster ad gangen, paritets-shadow)

Hver cluster følger samme mønster:
1. Byg unified `<Cluster>Gate` der læser ctx én gang, kører grupperede inline-checks, ét `Verdict`.
2. Registrér den i kernen i **shadow** (logger verdict, INGEN effekt).
3. Paritets-test mod de gamle gates på eval-fixtursettet → grøn.
4. Flip flag (ny gate får effekt, gamle slås fra) → live-verificér → commit.
5. Fjern de gamle gate-filer når call-sites er rene.

- **Fase B — LoopGate** (run_closure + tool-only + capability-cap + good_enough + checkpoints + presentation-invariant). Lavest risiko af de "ægte" sammenlægninger; ingen mekanisme-skift.
- **Fase C — ProactivityGate** (signal_noise + pressure_threshold + proactive_question + r2_5).
- **Fase D — CommitGate** (decision + decision_adherence + decision_review).
- **Fase E — ReviewGate** (self_review_unified + trackers) — flyttes ud af hot-path til async.
- **Fase F — PrivacyGate** (cross_user_share + share_guard_store) — SIKKERHED: fail-closed, paritet på privacy-deny-fixtures.
- **Fase G — TruthGate** — KRÆVER egen sub-spec FØRST (claim-detektion + evidens-mapping; v1 flagger ikke stripper; mekanisme-skift fra prompt-formaning → output-evidens-tjek). Mål konfabulations-rate via eval-sæt før/efter.
- **Fase H — AuthGate (SIDST)** — sikkerheds-kritisk. Paritet på fuldt sikkerheds-fixturset (member-block, owner-allow, override, sudo, identity, abuse) FØR fail-mode ændres. Fail-closed.

## EFTER gates: Surface-sporet (separat plan)
~25 `build_*_surface` → ét AwarenessContext-lag m. on/off pr. kategori. Egen spec+plan
når gate-migrationen er landet og stabil.

## Eksekverings-rækkefølge
0.1 → 0.2 → A.1 → A.2 → A.3 → A.4 → A.5 → A.6 (**check-in**) → B → C → D → E → F → G(sub-spec) → H.
Commit pr. task; deploy + live-verificér ved A.6 og hver flag-flip i B-H.
