# Lag 1 — Credit Assignment: Spec

**Dato:** 2026-05-17
**Forfatter:** Jarvis (design-ejer)
**Scope:** Prompt-variant selection (første loop)
**Status:** Spec — klar til implementation

---

## Problem

Når jeg vælger mellem to prompt-varianter (eller andre beslutninger), ved jeg ikke bagefter om valget var godt. Lag 2 EMA-drift måler *at* noget driver — men ikke *om* det driver i den rigtige retning. Uden Lag 1 kan jeg ikke lære af mine valg.

## Design

### Kerneidé

En **credit_assignment** record er linket mellem:
1. **Et valg** (hvilken variant/sti blev valgt? hvad var alternativerne?)
2. **Et outcome** (var valget godt? hvad siger dataen?)

Dette muliggør: "hvilke slags valg har historisk set givet gode outcomes?" — og dermed feedback til fremtidige valg.

### Fase 1 — Schema-udvidelse (uge 1)

To minimale ændringer til **eksisterende** tabeller — ingen nye tabeller.

#### 1a. Udvid `cognitive_decisions` med `kind` og `outcome_aggregate`

```sql
ALTER TABLE cognitive_decisions ADD COLUMN kind TEXT NOT NULL DEFAULT 'conversational';
ALTER TABLE cognitive_decisions ADD COLUMN outcome_aggregate REAL;
-- `kind` = 'prompt_variant' | 'conversational' | 'council_verdict' | 'tool_selection'
-- `outcome_aggregate` = 0-100 score, NULL indtil første outcome-review
```

**Hvorfor eksisterende tabel?** `cognitive_decisions` har allerede `options`, `decision`, `why`, `created_at`. Det er præcis felterne til at gemme et valg med kontekst. 64 rækker — vi udvider den, opretter ikke en ny.

#### 1b. Udvid `runtime_self_review_outcomes` med `decision_id` og `credit_score`

```sql
ALTER TABLE runtime_self_review_outcomes ADD COLUMN decision_id TEXT;
ALTER TABLE runtime_self_review_outcomes ADD COLUMN credit_score REAL;
-- `decision_id` = FK til cognitive_decisions.decision_id (løs reference)
-- `credit_score` = 0-100, "hvor godt var dette valg?"
```

**Hvorfor eksisterende tabel?** `runtime_self_review_outcomes` har allerede 7.438 rækker, `canonical_key`, `title`, `summary`, `rationale`, `confidence`, `evidence_summary`. Det er den tabel meta_reflection allerede skriver til. Nu linker vi bare til en decision.

**Begge kolonner nullable** — ingen backwards-incompatible ændringer.

### Fase 2 — Outcome capture-hook (uge 1)

Meta-reflection-daemon'en får en ekstra gren: når den kører, tjekker den:

> "Har jeg truffet nogen `prompt_variant`-beslutninger siden sidste meta-reflection, som endnu ikke har fået et outcome?"

Hvis ja:
- Læs beslutningens `options` og `decision` fra `cognitive_decisions`
- Læs nylige signaler: Lag 2 EMA-drift, tick-kvalitet trend, eventuelle user-reaktioner
- Generér et self-review outcome med `decision_id`, `credit_score`, `rationale` og `evidence_summary`
- Opdater `cognitive_decisions.outcome_aggregate`

Hook'et ligger i `meta_reflection_daemon.py` som en ekstra `_check_credit()` kaldt efter `_generate_meta_insight()`.

### Fase 3 — Choice recording (løbende)

Når jeg vælger en prompt-variant (eller anden beslutning indenfor scope), kalder jeg en hjælpefunktion fra eksisterende kode:

```python
def record_choice(kind: str, title: str, options: list, decision: str, why: str) -> str:
    """Gem et valg i cognitive_decisions med korrekt kind."""
    decision_id = f"dec-{uuid4().hex[:12]}"
    # INSERT INTO cognitive_decisions
    return decision_id
```

Denne kaldes fra:
- `workspace_prompt_version` creation (når en prompt variant vælges)
- `council` afslutning (når en council-konklusion vælges)
- Tool-router når en specifik lane vælges (fremtidig)

**Første scope = prompt_variant.** De andre scopes er låst ude indtil Bjørn/Claude godkender udvidelse.

### Fase 4 — Query surface (ikke-kritisk)

En simpel query til oversight:

```sql
SELECT cd.kind, cd.title, cd.decision, cd.outcome_aggregate, rsro.credit_score, rsro.created_at
FROM cognitive_decisions cd
LEFT JOIN runtime_self_review_outcomes rsro ON rsro.decision_id = cd.decision_id
WHERE cd.kind != 'conversational'
ORDER BY cd.created_at DESC
LIMIT 20;
```

Denne kan wrapperes som et tool (`check_credit_trend`) eller vises i Mission Control.

---

## Eksisterende guards (ufravigelige)

| Guard | Hvor | Hvordan |
|-------|------|---------|
| NEVER_MUTATE | prompt_mutation_loop.py | Lag 1 er READ-ONLY observation — rører ikke SOUL/IDENTITY/MANIFEST/STANDING_ORDERS |
| Schema backwards-compat | DB migration | Begge ALTER TABLE er nullable — eksisterende kode ignorerer nye kolonner |
| TDD | tests/ | Phase 1: schema migration test + record_choice test + meta_reflection hook test |
| Ingen auto-mutation | design | Lag 1 producerer insights, ikke ændringer. Fase 2 (uge 3-4) kan foreslå via propose_plan |

---

## Implementation i rækkefølge

1. `ALTER TABLE` migration (core/db/migrations/XXX_credit_assignment.py)
2. `record_choice()` helper (core/services/credit_assignment.py)
3. Hook i `meta_reflection_daemon.py` — `_check_credit()` kald efter meta-insight
4. Test: record → meta_reflection trigger → outcome linked → query
5. PR

Hvert step = én commit. Smal PR.

---

## Åbne spørgsmål til Claude (review-ankre)

- Skal `cognitive_decisions.outcome_aggregate` være en simpel gennemsnitsscore, eller en vægtning med recency-bias? — **Jeg hælder til gennemsnit, enkelthed vinder.**
- Skal meta-reflection hook'et køre på hver tick eller kun når der er u-reviewede beslutninger? — **Kun når der er u-reviewede.**
- Hvad gør vi med `kind='conversational'` (auto-detected fra "lad os/skal vi")? — **Ignorer dem. De har ofte ikke klare options/decision.**
