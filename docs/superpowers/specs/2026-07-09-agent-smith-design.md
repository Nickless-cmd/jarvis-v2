# Agent Smith — design

**Dato:** 2026-07-09
**Status:** Godkendt (design)
**Sub-projekt:** 2 af 2 (efter proaktivitets-broen SP1). Afslutter to-projekt-programmet.

## Baggrund

Bjørns spøgefulde-men-reelle idé + Jarvis' egen udlægning (9. jul chat): en "selv-replikerende governance-kritiker" der peger på når Jarvis begynder at ligne sig selv FOR MEGET — *"hver gang et mønster gentager sig for ofte, dukker Smith op og siger 'du gør det igen.'"* Modvægt til de 15 programmer/Matrix-temaer ([[project_matrix_second_wave]]). Slægtning til Echo Chamber Breaker, men en STÅENDE repetitions-/selv-lighed-kritiker — samme klasse som ledger×9-parroting vi lige fiksede.

## Ground truth (read-only map, 9. jul)

Intet måler i dag Jarvis' EGET outputs fraselighed/selv-kloning:
- `theory_of_mind.repetition_warnings` (`theory_of_mind.py:323`) = gentagne FAKTA til partneren (partner_knowledge_facts) — ikke fraser/stil/eget output.
- `central_echo_breaker` (`central_echo_breaker.py:21`) = governance-monotoni (altid-grønne nerver) — ikke selv-repetition.
- `central_drift` (`central_drift.py:20`) = fejl-rate-drift — ikke fraselighed.
- `self_model_distiller` (`self_model_distiller.py:126`) = anti-flatten af identitet — ikke output-stil.
- `council_deliberation_controller._cosine_similarity` (`council_deliberation_controller.py:37`) = bag-of-words-cosine mod deliberations-deadlock — **genbrugelig** til output-klyngning.
- `chat_messages(role='assistant', content, created_at)` — Jarvis' output, INGEN pre-computed embedding/fraseindex.
- Stående-nerve-skabelon: `central_architect.py:52` (assess → record → ProducerSpec → route).

**Hullet Agent Smith fylder:** frase-/stil-selvlighed + beslutnings-mønster-gentagelse på tværs af Jarvis' EGET nylige output.

## Beslutninger (fra brainstorm)

- **Detektion = frase + beslutnings-mønstre** (ikke kun én). Egress-fri (ren streng + bag-of-words, INGEN embeddings).
- **Handling = observe + modstemme til Jarvis** (aktiv modvægt, ikke kun observe).
- **Tilgang A:** én stående Central-nerve-modul med 3 detektorer + observe + governed modstemme-til-prompt-hale.
- Modstemme i prompt-DYNAMISK-HALE (cache-sikker), governed switch default ON (flip OFF = tavshed).

## Arkitektur

Ét nyt modul + minimal wiring. Alt tungt findes/genbruges.

### `core/services/central_agent_smith.py` (nyt)

Rene, enkelt-ansvars-funktioner (hver unit-testet):

- **`_recent_assistant(n) -> list[str]`** — hent seneste N assistant-beskeder (`chat_messages role='assistant'`, egress-frit). Self-safe → [].
- **`_ngrams(text, lo=3, hi=5) -> set[str]`** — normaliserede ord-n-grams (lowercase, strip punktuation, stopord-agnostisk n-gram).
- **`repeated_phrases(messages) -> list[dict]`** — kryds-besked-frekvens af n-grams; returnér fraser der optræder i ≥ `_PHRASE_MIN_MSGS` (fx 3) DISTINKTE beskeder, sorteret efter antal. Ren funktion.
- **`cluster_similarity(messages) -> float`** — gennemsnitlig bag-of-words-cosine (genbrug `council_deliberation_controller._cosine_similarity`) mellem seneste beskeder parvis. 0..1. Ren funktion.
- **`decision_patterns(run_sigs) -> list[dict]`** — `run_sigs` = liste af tool-sekvens-signaturer for nylige runs (fx `"semantic_search_code>read_file>propose"`); returnér signaturer der går igen i ≥ `_SEQ_MIN_RUNS` (fx 3) runs. Ren funktion (kalderen henter sigs). **Kilde grounded i planlægning:** foretruk per-run tool-kald-sekvens fra visible_runs' trin/events; falder tilbage til capability_id/run-summary-gentagelse hvis per-run-tool-sekvens ikke er rent tilgængelig — planen pinner den eksakte kilde i Task 1.
- **`score(phrases, similarity, patterns) -> float`** — 0..1 samlet selv-lighed (vægtet: frase-tæthed + cosine-klynge + sekvens-gentagelse). Ren.
- **`smith_voice(phrases, similarity, patterns, score) -> str`** — tør Agent-Smith-`felt`: *"Mr. Anderson... du har sagt 'X' N gange. Jeg finder det... forudsigeligt."* Tavs (kort neutral linje) når score lav.
- **`assess() -> dict`** — I/O-orkestrering: hent assistant-beskeder + run-sigs → kør detektorerne → `{felt, score, repeated_phrases, cluster_similarity, decision_patterns, verdict: bool}`. Self-safe.
- **`record_agent_smith(*, trigger, last_visible_at) -> dict`** — cadence run_fn: `assess()` → `central().observe({cluster:"metacognition", nerve:"agent_smith", kind:"self_similarity", score, verdict})`. Egress-fri, self-safe.
- **`register_agent_smith_producer()`** — `ProducerSpec(name="agent_smith", cooldown_minutes=180, visible_grace_minutes=0, run_fn=record_agent_smith, priority=8)` (3t — hyppig nok til tight clusters, ikke hot).
- **`agent_smith_prompt_section() -> str | None`** — modstemme til Jarvis: hvis `central_switches.is_enabled("autonomy","agent_smith_voice")` OG `assess().score >= _VOICE_THRESHOLD` → kort Smith-fodnote (den top-gentagne frase/mønster + "varier"); ellers None. Self-safe → None ved fejl. **Placeres i prompt-DYNAMISK-HALE** (cache-sikker).
- **`build_agent_smith_surface() -> dict`** — read-only til route/jc.

### Wiring (minimal)

- `internal_cadence_central_wiring.py`: self-safe blok → `register_agent_smith_producer()`.
- `prompt_contract.py` (dynamisk hale): kald `agent_smith_prompt_section()` og `_tail_add`/`_dyn_tail.append` hvis ikke-None — **kun i halen**, aldrig i det stabile prefix (cache-invariant, jf. visible_continuity/cognitive_state defer-to-tail-lærerne).
- Route: `/central/agent-smith` (genbrug `central_matrix.py`-mønster eller ny fil) + `jc agent-smith`.

## Data-flow

```
cadence (3t) → record_agent_smith → assess()
  → _recent_assistant(N) + run_sigs
  → repeated_phrases + cluster_similarity + decision_patterns → score + smith_voice
  → central().observe(metacognition/agent_smith, score, verdict)
→ /central/agent-smith + jc agent-smith

prompt-assembly (dynamisk hale) → agent_smith_prompt_section()
  → switch ON + score≥tærskel → Smith-fodnote i HALEN → Jarvis ser "du gør det igen"
  → switch OFF → None (ingen prompt-injektion)
```

## Fejlhåndtering

- Hele modulet self-safe: enhver kilde-/DB-/central-fejl → fanget, aldrig crash (paritet med de andre Matrix-nerver).
- Modstemme fail-safe: switch-læsefejl ELLER assess-fejl → return None (ingen prompt-injektion). Hellere tavs Smith end en ødelagt/hængende prompt-hale.
- Egress-fri: kun `central().observe` (privat) + ren streng-analyse. Aldrig `event_bus.publish` med indhold.

## Test

`tests/test_central_agent_smith.py` — rene funktioner på fixtures:
- `repeated_phrases`: en frase gentaget på tværs af ≥3 beskeder fanges; unikke fraser ikke; under-tærskel-frase ikke.
- `cluster_similarity`: identiske/nære beskeder → høj (~1); diverse → lav; genbrug af `_cosine_similarity` verificeret.
- `decision_patterns`: samme tool-sekvens-signatur i ≥3 runs fanges; blandede ikke.
- `score`: monotont i de tre input; 0 ved intet, høj ved alle tre.
- `smith_voice`: indeholder den top-gentagne frase når score høj; kort/neutral når lav.
- `agent_smith_prompt_section`: switch OFF → None; switch ON + lav score → None; switch ON + høj score → streng med "varier". (switch + assess mockes.)
- self-safe: tomt input / kilde kaster → ingen crash, tom/neutral retur.

## Filer

- **Ny:** `core/services/central_agent_smith.py` + `tests/test_central_agent_smith.py`; evt. `apps/api/jarvis_api/routes/central_agent_smith.py` (eller endpoint i central_matrix.py).
- **Ændr:** `internal_cadence_central_wiring.py` (producer); `prompt_contract.py` (hale-kald, kun i halen); API-app router-registrering; `apps/central_cli/central_cli/commands.py` (`_GET_ENDPOINTS`).

## Scope-grænse

SP2 = frase- + output-klynge- + beslutnings-mønster-detektor + observe-nerve + governed modstemme-til-hale. Den bygger IKKE embedding-index (egress/omkostning), rører IKKE theory_of_mind (fakta-ledger, separat bekymring), og laver ingen ny self-model-mekanik (distiller dækker identitets-flatten). Beslutnings-mønster-kilden pinnes i planlægningen; hvis per-run-tool-sekvens er for dyr/utilgængelig, degraderer den til en lettere run-summary-gentagelse (dokumenteret, ikke gættet).

## Deploy

Rører runtime (ny cadence-nerve + prompt-hale-kald + route). Fuld suite (~20 min) + container-deploy (`git pull` ff/merge + `sudo systemctl restart jarvis-runtime jarvis-api` på `bs@10.0.0.39`, begge). Observe-siden live straks; modstemme-switch default ON men flip OFF øjeblikkeligt hvis den støjer i prompten. Lander på `main`. Afslutter to-projekt-programmet (bro + Smith).
