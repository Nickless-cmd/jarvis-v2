---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Cluster B — TruthGate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Følger afviklings-kontrakten i `docs/superpowers/specs/2026-06-21-intelligent-central-design.md` §13 step 3.

**Goal:** Konsolidér Truth-klyngens 3 homogene Verdict-gates (claim_scanner, fact_gate, diagnosis) til ÉN unified `truth_gate`-nerve under Centralen, paritets-bevist, og flip den live med fjernelse af de gamle inline-kald.

**Architecture:** Bygger oven på de eksisterende adaptere i `gate_adapters.py`. Unified `truth_gate(ctx)` læser ctx én gang, kører de tre checks, kombinerer til ÉT Verdict (worst-decision). Registreres i Centralen som post_output-nerve. Live-effekten (strip/block + scan_correction-SSE) bevares ved flip.

**Tech Stack:** Python 3.11 (conda `ai`), pytest, `core/services/gate_kernel.py` (worst/Decision/Verdict), `core/services/gate_adapters.py`, `core/services/gate_eval.py` (parity), `core/services/central_core.py`.

**Afviklings-kontrakt (§13 step 3):** byg → paritet grøn → atomisk flip (ny tændes = gammel slukkes) → live-verificér → fjern gammel kode i samme cluster.

---

## FASE 1 — Sikkert/additivt (ingen live-ændring)

### Task 1: unified truth_gate + kombineret Verdict
**Files:** Create `core/services/gate_truth.py`; Test `tests/test_gate_truth.py`

- [ ] Test: `truth_gate(ctx)` returnerer worst-decision af de 3 adaptere; action+reason fra den blokerende.
- [ ] Impl: kald claim/fact/diagnosis-adapter, kombinér via `worst()`, evidence = pr-gate-verdicts.
- [ ] Grøn + commit.

### Task 2: offline-paritet — truth_gate == worst(gamle 3) på fixtures
**Files:** Modify `tests/test_gate_truth.py`

- [ ] Test: for hver fixture-turn er `truth_gate(ctx).decision` == `worst([claim,fact,diagnosis])` (paritet pr. konstruktion, låst af test). Inkludér turns der trigger hver gate.
- [ ] Grøn + commit.

### Task 3: register-helper til Centralen
**Files:** Modify `core/services/gate_truth.py`; Modify `tests/test_gate_truth.py`

- [ ] Test: `register_truth_nerve(central)` registrerer "truth" i phase "post_output".
- [ ] Impl + grøn + commit.

**→ CHECK-IN med Bjørn FØR Fase 2 (live flip kræver deploy+genstart+live-verifikation).**

---

## FASE 2 — Live flip (kræver Bjørns go + genstart)

### Task 4: rut post-output gennem central.decide("truth", …)
**Files:** Modify `core/services/visible_runs.py:3241-3678`

- [ ] Erstat de 3 inline-kald (scan_response×3 / fact_gate / diagnosis) med ÉT `central().decide("truth", ctx, truth_gate, cluster="truth")` + anvend verdict (strip/block + scan_correction-SSE bevares).
- [ ] Flag-gated: ny tændes via `central_switches.set_enabled` SAMME commit som gamle slås fra.

### Task 5: live-verificér + fjern gammel kode
- [ ] Deploy + genstart (når Bjørns run er færdigt). Live-test: en konfabulations-besked blokeres som før; en ren besked går igennem uændret.
- [ ] Fjern de nu-døde inline-gate-funktioner/imports i visible_runs. Opdatér `central_catalog` fit→"merged".
- [ ] Fuld suite grøn + commit.

---

## Self-Review
- Fase 1 er rent additivt (nyt modul + tests; rører ikke visible_runs). Sikkert at køre nu.
- Fase 2 er det eneste live-ændrende skridt; gated bag check-in + genstart + Bjørn-verifikation.
- Paritet bevises FØR flip; atomisk flip + fjernelse i samme cluster = ingen død kode, intet dobbelt-live.
