---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Skill Chain Phase 2 — Auto-planner + Adaptive Re-planning: Design

**Date:** 2026-05-12
**AGI track:** #10 Skill komposition Phase 2
**Status:** Approved, ready for plan
**Phase 1 reference:** `docs/superpowers/specs/2026-05-10-skill-chain-design.md` (deployed)

## Goal

Lukke to gap fra Phase 1's `skill_chain` tool:

1. **Plan-tid gap:** Jarvis gætter når han manuelt plukker en kæde fra 50+ skills.
   Hans citat: *"At plukke en kæde manuelt er dyrt og tilfældigt. Jeg gætter."*
2. **Kør-tid gap:** Når en kæde viser sig forældet (pre-execution eller mid-chain),
   findes der intet eksplicit verb til at revidere. Et nyt kald skjuler intent og
   forhindrer observability.

Phase 2 leverer `propose_skill_chain` (auto-planner via cheap-lane) +
`revise_skill_chain` (eksplicit revision-verb, dual-context). Eksisterende
`skill_chain` tool er uændret.

## Why this matters

Multi-step Planner havde stale-signal uden destination — vi lukkede det med
`revise_plan`. Curiosity havde indre rum uden indre drivkraft — vi lukkede det
med budget. Skill Chain har et stort katalog uden navigation — Phase 2 lukker
det med en planner. Hver gang er det samme mønster: vi har infrastrukturen,
men ikke hjælpen til at bruge den.

## Locked decisions (brainstorm 2026-05-12)

1. **Scope (a)+(b) i ét spor:** Auto-planner + adaptiv re-planning er
   komplementære. (a) sørger for kvalificeret start, (b) sørger for at rette
   undervejs. Separate events til disambiguering i 30-day-review.
2. **Planner-implementering (b):** Cheap-lane LLM (DeepSeek), ikke heuristik.
   Confidence-felt er Jarvis' filter — låg confidence → han justerer selv;
   høj confidence → han stoler på.
3. **Revise-interface (b) eksplicit verb, dual-context:** `revise_skill_chain`
   gyldig både pre-execution (revidér et forslag) og mid-chain (pivot på
   intermediate result). Event `revision_context` felt disambiguer brugen.
4. **Prompt-format (b) navne + 1-linje description:** Send fuld skill-katalog
   med korte descriptions (~2-3k tokens), ikke kun navne, ikke pre-filtreret.
   Eksplicit tom-kæde-fallback: hvis cheap-lane ikke kan kæde meningsfuldt,
   returnér tom plan med rationale.

## Arkitektur i 3 lag

### Lag 1: Auto-planner (propose_skill_chain)

**Ny tool i nyt modul `core/tools/skill_chain_propose_tool.py`:**

```
propose_skill_chain(task_description: str) -> {
    "status": "ok" | "error",
    "plan": list[str],          # kan være tom hvis cheap-lane ikke kan kæde
    "rationale": str,
    "confidence": float,         # 0.0-1.0
    "model_used": str,
}
```

**Eksekverings-flow:**

1. Killswitch-check (`skill_chain_phase2_enabled`).
2. Validate `task_description` ≥ 10 tegn.
3. Hent skill-katalog via `skill_engine.list_skills()` — returnér
   `[{"name", "description"}]`.
4. Byg cheap-lane prompt:
   ```
   System: Du er en skill-planner. Givet en opgave-beskrivelse og et katalog
   af tilgængelige skills, foreslå en ordnet kæde af 2-5 skills der løser
   opgaven. Hvis ingen meningsfuld kæde findes, returnér tom plan.

   Returnér JSON: {"plan": [...], "rationale": "...", "confidence": 0.0-1.0}
   - plan: 2-5 skill-navne i eksekveringsrækkefølge, eller [] hvis ingen
   - rationale: 1-2 sætninger om hvorfor denne kæde løser opgaven, eller
     hvorfor ingen kæde virker
   - confidence: dit estimat af hvor godt kæden løser opgaven

   User: Opgave: {task_description}
         Katalog (50 skills):
         - analyze_image: Extract structured data from image content
         - web_scrape: Fetch and parse web pages
         - fact_check: Verify factual claims against sources
         ...
   ```
5. Cheap-lane kald via `core.providers.cheap_lane.invoke_json()` (eksisterende
   helper, returnerer parsed JSON eller error).
6. Validate response: `plan` er liste af eksisterende skill-navne (2-5 eller 0),
   `confidence` i [0,1], `rationale` non-empty.
7. Emit `cognitive_skill_chain.proposed`-event med
   `{plan, confidence, rationale_length, model_used, task_excerpt}` (max 120
   tegn af task — ikke fuld task af PII-hensyn).
8. Returnér forslag til Jarvis.

**Token-budget:** ~2-3k input + 500 output på cheap-lane. Forventet brug:
3-10 kald/dag → <1 kr/måned.

**Tom-kæde-fallback:** Hvis cheap-lane returnerer `plan=[]`, accepter det og
returnér til Jarvis. Det er et legitimt signal ("jeg kan ikke kæde dette"),
ikke en fejl.

### Lag 2: Adaptiv revise (revise_skill_chain)

**Ny tool i nyt modul `core/tools/skill_chain_revise_tool.py`:**

```
revise_skill_chain(
    reason: str,
    new_plan: list[str],
    revision_context: "pre_execution" | "mid_chain",
) -> {
    "status": "ok" | "error",
    "instructions": str,        # kombinerede instruktioner for new_plan
    "new_plan": list[str],
}
```

**Eksekverings-flow:**

1. Killswitch-check.
2. Validate: `reason` ≥ 10 tegn, `new_plan` 2-5 eksisterende skills,
   `revision_context` i {pre_execution, mid_chain}.
3. Pre-validér alle skills eksisterer (mirror Phase 1 skill_chain pattern).
4. Byg combined-instructions via samme `_build_combined_instructions`
   helper som Phase 1 skill_chain bruger.
5. Emit `cognitive_skill_chain.revised` event:
   `{new_plan, reason: reason[:200], revision_context, instructions_length}`.
6. Returnér combined instructions til Jarvis.

**Vigtigt — ingen state-machine:** Vi gemmer ikke "original plan" eller
"completed steps." Tool capturer *intent*, ikke *eksekverings-tilstand*. Hvis
Jarvis vil rulle tilbage, kalder han bare originalen igen. Samme stateless-
filosofi som Phase 1.

**Dual-context-disambiguering:** `revision_context` lader 30-day-review skille
mellem "Jarvis stolede ikke på propose's forslag" (pre_execution) og "Jarvis
indså midt i kæden at den ikke virkede" (mid_chain). Begge er legitime, men
de fortæller forskellige ting om systemet.

### Lag 3: Settings + events

**`core/runtime/settings.py`:**

```python
# Skill Chain Phase 2 — auto-planner + adaptive revise (added 2026-05-12)
skill_chain_phase2_enabled: bool = True
```

Én master-killswitch for begge nye tools. Reverter fuldt til Phase 1 (manuel
plukning af kæder).

**Events (`cognitive_skill_chain` family — eksisterer fra Phase 1):**

| Event | Trigger | Payload |
|-------|---------|---------|
| `cognitive_skill_chain.proposed` | propose_skill_chain returnerer | plan, confidence, rationale_length, model_used, task_excerpt |
| `cognitive_skill_chain.revised` | revise_skill_chain succeeds | new_plan, reason, revision_context, instructions_length |
| `cognitive_skill_chain.executed` | Phase 1 — uændret | (existing) |

Alle `event_bus.publish`-kald wrappes i `try/except` (defensiv mod
test-pollution, samme mønster som world_model/plan_revision/curiosity).

## Cheap-lane integration

Genbrug eksisterende infrastruktur — ingen ny provider-kode.

Forventet lookup: `from core.providers.cheap_lane import invoke_json` eller
tilsvarende helper. Plan-tasken vil bekræfte den faktiske API ved at læse
en eksisterende cheap-lane-bruger (fx `dispatch_to_claude_code` eller
`predict_outcome`).

**Timeout:** 8 sekunder (cheap-lane default). Hvis timeout → returnér
`status: "error", error: "cheap-lane timeout"`. Tom-kæde er IKKE fallback for
timeout — det er en eksplicit "ved ikke" fra cheap-lane selv.

**Defensive parsing:** Hvis cheap-lane returnerer non-JSON eller malformed
JSON, returnér `status: "error", error: "cheap-lane response invalid"`. Ingen
silent-fail-to-empty.

## Backwards-compat

- Phase 1 `skill_chain` tool **uændret** — Jarvis kan stadig kalde den direkte
  med en manuelt plukket plan
- Phase 1 `skill_gate` `chain_candidates`/`chain_hint`-felter **uændrede**
- Eksisterende 50+ skills uberørte — ingen krav om metadata-tilføjelser
- Killswitch=False reverter alt: begge nye tools fejler immediately, Phase 1
  fungerer som før
- Ingen ny event-family — `cognitive_skill_chain` allerede registreret
- Ingen DB-tabeller, ingen daemons
- Eksisterende cheap-lane infrastruktur — ingen ny provider-konfig

## Phase 2 scope — det vi IKKE bygger

- **Per-skill input/output metadata** (deferred fra brainstorm option (c)):
  type-checked chaining kræver at alle skills får schema-felter — Phase 3.
- **State-aware revise med `completed_so_far`:** kun simpel revise i Phase 2.
  Hvis 30-day-review viser at "fortsæt fra step N" er almindeligt, tilføj i
  Phase 2.1.
- **Auto-eksekvering af propose-forslag:** propose_skill_chain returnerer KUN
  et forslag. Jarvis bestemmer om han kører `skill_chain(plan=...)`. Ingen
  auto-pipe.
- **Mission Control UI** for proposed/revised chains — kun rå events i Phase 2.

## 30-day review (2026-06-11)

**Måle-punkter:**

1. **Propose-brug:** Hvor mange `propose_skill_chain`-kald/dag?
2. **Confidence-fordeling:** Histogram af confidence-værdier. Klumper det sig
   ved ekstremer (0.2 eller 0.9) eller ligger det rundt 0.5?
3. **Proposal-to-execution rate:** Hvor ofte kalder Jarvis `skill_chain(plan=...)`
   med en plan der matcher et propose-forslag inden for 5 minutter? (Indirekte
   "stoler han på forslagene"-metric.)
4. **Revision-rate split:** `revision_context` fordeling — pre_execution vs
   mid_chain. Pre_execution >> mid_chain er forventet baseline.
5. **Tom-kæde-rate:** Hvor ofte returnerer cheap-lane `plan=[]`? Hvis >40%,
   prompten er for restriktiv eller kataloget er for stort.
6. **Cost:** Faktisk månedlig cheap-lane cost.
7. **Apophenia-tegn:** Læs 10 tilfældige rationale-felter. Er der
   overinterpretation, opfundne kæder?

**Beslutninger som review kan trigge:**

- Hvis confidence-felt klumper sig ved 0.9 uanset kvalitet → cheap-lane er for
  optimistisk, juster prompt
- Hvis pre_execution-revision-rate >50% → propose-kvalitet er lav, overvej
  (c) hybrid-tilgang (skill_gate-filtreret prompt)
- Hvis mid_chain-revisions er almindelige → tilføj `completed_so_far`-felt i
  Phase 2.1
- Hvis tom-kæde-rate er stabilt høj → tilføj `skip_when_single_skill_suffices`
  prompt-instruktion, eller reducer katalog-størrelse i prompten

## Test-plan

**Unit-tests (~25-30 tests):**

- propose: killswitch, validation (task_description ≥ 10 chars), katalog-fetch
- propose: cheap-lane mocking — returner gyldig JSON, malformed JSON, timeout,
  tom-kæde
- propose: validate skill-navne eksisterer, plan-længde 2-5 eller 0
- propose: confidence i [0,1] grænser
- propose: event-publish wrapped i try/except
- propose: rationale_length-felt i event (ikke fuld text)
- revise: killswitch, validation (reason ≥ 10 chars, plan 2-5, revision_context)
- revise: pre-validation af skills (mirror Phase 1 alt-eller-intet)
- revise: combined-instructions builder genbrugt fra Phase 1
- revise: revision_context propageret i event
- revise: dual-context fungerer for begge værdier
- revise: kalder skill_chain-builder fra Phase 1
- Tool-registrering via simple_tools splat
- Backwards-compat: Phase 1 skill_chain tests stadig grønne

**Smoke-test:** Import + tool-registrering + cheap-lane reachability.

## Filer berørt

**Nye:**
- `core/tools/skill_chain_propose_tool.py` (~180 LOC — propose handler +
  cheap-lane integration + validation)
- `core/tools/skill_chain_revise_tool.py` (~120 LOC — revise handler +
  validation, genbruger Phase 1 builders)
- `tests/test_skill_chain_phase2.py` (~25-30 tests)

**Modificeret:**
- `core/runtime/settings.py` — `skill_chain_phase2_enabled: bool = True`
- `core/tools/simple_tools.py` — import + splat af 2 nye tool-sets
- `scripts/smoke_test_startup.py` — import-block for Phase 2

**Reused fra Phase 1 (uberørt):**
- `core/tools/skill_chain_tool.py` — `_build_combined_instructions`,
  `_validate_plan_existence` — importeres af revise-tool
- `core/services/skill_engine.py` — `list_skills`, `skill_exists`
- `cognitive_skill_chain` event family

## Successkriterier (deployment-dag)

- Alle tests grønne (Phase 2 + Phase 1 skill_chain + alle eksisterende AGI-spor)
- Smoke-test import OK
- jarvis-api restartet uden errors
- `skill_chain_phase2_enabled=True` aktiv
- Manuel test:
  1. Kald `propose_skill_chain("fact-check this article and format as markdown")`
     → modtag struktureret forslag
  2. Kald `revise_skill_chain(reason="...", new_plan=[...], revision_context="pre_execution")`
     → modtag combined instructions
  3. Bekræft begge events lander i events-tabel
- Ingen regression i Phase 1 skill_chain eller skill_gate
