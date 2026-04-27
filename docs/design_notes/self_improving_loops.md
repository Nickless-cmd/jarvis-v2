# Design Note: Self-Improving Loops (Punkt #4 fra backend-modernisering)

**Status:** Design note. INTET implementeret. Risikoen er for stor til at jaske.
**Dato:** 2026-04-27
**Forfatter:** Claude (i samarbejde med Bjørn)

## Hvorfor det her er udskudt

Self-improving / self-modifying loops er den klasse af AI-system der kræver
**størst alignment-omhu**. Hvis Jarvis selv kan ændre sine prompts, sin
identitet eller sit beslutningsmønster, kan en lille fejl forårsage:

- **Personality drift** der kompromitterer hans kerne
- **Optimisering mod forkerte metrics** (f.eks. "altid sige ja" hvis det
  scorer højt på user satisfaction)
- **Tab af sikkerhedsguards** hvis han kan rewrite sine egne approval-paths
- **Cascading failures** hvor en forværring forværrer næste iteration

Eksisterende infrastruktur (prompt_mutation_loop.py) har allerede
**eksplicit NEVER_MUTATE-liste** for SOUL.md, IDENTITY.md, MANIFEST.md,
STANDING_ORDERS.md. Det er den rigtige forsigtighed.

## Hvad der KAN bygges sikkert

### Fase A: Self-evaluation (READ-ONLY)

Spor uden at handle:

- `core/services/prompt_self_evaluation.py`
  - Track per-prompt-variant: success rate, user satisfaction (eksplicit
    feedback fra user), reasoning_classifier scores
  - Eventbus events: `prompt.variant_evaluated`
  - Mission Control surface: hvilke prompts virker, hvilke virker ikke
  - **INGEN auto-mutation** — kun observability

### Fase B: Suggested mutations (PROPOSE-ONLY)

Lad systemet foreslå ændringer, men require approval:

- Brug eksisterende `propose_plan` infrastructure
- Foreslået mutation → plan med før/efter diff
- Bruger skal eksplicit approve via `approve_plan`
- Kun for ikke-protected filer

### Fase C: Bounded auto-mutation (kun lavrisiko)

For specifikke, bounded scenarios:

- Tool descriptions (lavrisiko: forværring giver kun færre tool-kald, ikke
  forkerte handlinger)
- Awareness section formatering (lavrisiko: kosmetik)
- Daemon cadence justering (medium risiko: kan forværre observability)

ALDRIG for:
- Identity, soul, manifest
- Approval paths
- Council deliberation logic
- Memory write/delete logic

## Konkret implementeringsrækkefølge (når vi er klar)

1. **Først: Self-evaluation infrastructure** (~1 uge)
   - Track variant performance, surface i MC
   - 0 risiko, 100% observerbar

2. **Derefter: Manual experiment runner** (~3 dage)
   - Tool: `run_prompt_experiment(variant_a, variant_b, n_trials)`
   - Bruger styrer eksplicit, ingen automatik

3. **Derefter: Propose-only mutations** (~1 uge)
   - LLM foreslår, plan_proposals håndterer godkendelse

4. **MÅSKE: Bounded auto-mutation** (separat samtale)
   - Kun efter 3 har kørt i 4+ uger uden incidents

## Pre-conditions før vi går i gang

- Mission Control har dashboard for prompt-variant tracking
- Persistent storage til evaluation data
- Eksplicit user-godkendelse på arkitektur-niveau
- Rollback-procedure dokumenteret

## Anbefaling

**Vent.** Lad #1, #2, #3, #5, #6, #7 (alle bygget i denne session)
modnes i 4-6 uger først. Indsaml data om hvordan de opfører sig.
Så har vi grundlag for at vide hvad self-improvement faktisk skal
optimere mod.

Self-improvement uden klar metrics = optimering mod tilfældigheder.

## Referencer

- core/services/prompt_mutation_loop.py (eksisterende, forsigtig)
- core/services/runtime_self_model.py (eksisterende self-tracking)
- core/services/meta_reflection_daemon.py (eksisterende refleksion)
- E-series E2 plan_proposals (godkendelses-infrastruktur)
- E-series E4 auto_code_review (heuristik review-infrastruktur)
