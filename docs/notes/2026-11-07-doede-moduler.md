# Tre moduler uden produktions-kaldere — domme (7/11-2026)

**Slags:** undersøgelse. Ingen filer slettet, ingen produktionskode ændret,
ingen nye offentlige funktioner (derfor ingen docs-regenerering).

## Måling

Grep over `core/ apps/ scripts/` + systemd/dynamiske strenge (hele repoet
undtagen `docs/`, `tests/`, `.git`): **0 referencer** til hvert af
`retry_runtime`, `prepared_request`, `model_benchmark`. Kun `tests/test_<modul>.py`
og genererede docs nævner dem. `provider_retry_policy` har 2 importer
(`simple_tools.py:409`, `simple_tools_definitions.py:99`) — kun værktøjs-retry.

| Modul | Linjer | Prod-kaldere | Dom |
|---|---|---|---|
| `retry_runtime.py` | 177 | 0 | **DUPLIKAT** (delvist) |
| `prepared_request.py` | 165 | 0 | **DUPLIKAT** / FJERN-KANDIDAT |
| `model_benchmark.py` | 271 | 0 | **ÆGTE — ikke koblet** (kalder mangler uden for scope) |

## retry_runtime — DUPLIKAT

Den ægte retry bor i `visible_runs.py` (~2551–2570, ~3437–3700), bag
`agentic_round_retry_enabled`: per-runde loft (`round_stream_max_retries`, 3),
tur-total loft (`turn_total_stream_retries`, 12), tur-wall-clock
(`turn_total_wall_clock_s`, 600 s), circuit-breaker + failover (som også
forbruger tur-budgettet), backoff med jitter og klassifikation via
`stream_failure_kind.is_retryable_kind`. Det er altså allerede et TUR-budget,
ikke et per-udbyder-budget; `retry_runtime` er en tredje implementation af
samme idé (og `provider_retry_policy.retry_with_backoff` den anden, kun til
værktøjer).

To ting `retry_runtime` har, som den kørende vej ikke har — målt ved at læse
begge: **token-loft og pris-loft** i budgettet. Den kørende vej begrænser kun
forsøg og tid. At farlige fejl (`TOOL_SIDE_EFFECT`, `OUTCOME_UNKNOWN`) ikke
prøves igen er derimod dækket strukturelt: retry sker kun hvis stream-fejlen
rammer FØR værktøjer køres (`visible_runs`-kommentaren «S3 invariant»), så
`_followup_exchanges` er uændret og intet værktøj udføres to gange.
Ejeren kan beslutte om token/pris-loft er værd at lægge ind i
`visible_runs`-lofterne; det ville være en udvidelse dér, ikke en kobling af
dette modul.

## prepared_request — DUPLIKAT (FJERN-KANDIDAT)

Kravet er byte-identisk genforsøg. Den nuværende vej opfylder det i-proces:
`visible_runs` tager ét snapshot af `base_messages` + `_followup_exchanges` +
`tool_defs`-beslutningen pr. runde og genafspiller det (kommentarer ved
~2703–2740 og ~3040: «sender byte-identisk»), og afkorter
`_all_followup_parts` til rundens snapshot ved retry. Der er ingen
persisteret anmodning at genskabe fra, fordi retry sker inde i samme
generator. `PreparedRequest`s værdi (rekonstruktion fra gemte referencer,
`request_series_id`, `derived_history_watermark`, `compaction_generation`)
ville først bære noget ved genoptagelse på tværs af processer — det findes
ikke. Målt: de tre feltnavne forekommer i **0** produktionsfiler uden for
modulet selv. FJERN-KANDIDAT; ejeren afgør (intet slettet).

## model_benchmark — ÆGTE, kalder mangler

Ingen anden mekanisme rangerer på ægte opgaver: søgning efter
benchmark/rank/score i `core/ apps/ scripts/` finder kun
`agent_model_fitness` (forbruger), `model_catalogue_sweep` (syntetisk sonde,
`probe_score`) og to uafhængige scripts (`bench_ollama_concurrency`,
`minimal_mode_baseline` — måler hastighed/baseline, ikke kvalitet).

Forbrugeren er allerede koblet: `agent_model_fitness.egnede_modeller` sorterer
efter `kvalitets_score` (~linje 158), og `tests/test_model_benchmark.py:122+`
beviser at rotationen følger den. **Men ingen i produktion skriver feltet** —
`gem_kvalitet` har 0 kaldere, så 65 af 67 modeller har stadig kun
`probe_score` og rækkefølgen er stadig vilkårlig.

Det rette sted at koble er `model_catalogue_sweep.py` (~linje 398, hvor
`probe_score` skrives) eller en eksplicit CLI/admin-handling:
`kør_benchmark(...)` → `gem_kvalitet(...)`. Begge ligger **uden for denne
opgaves scope**, så koblingen er IKKE lavet. Pas på prisen: en benchmark
spawner en rigtig explore-agent pr. model og fil; den skal ikke køre for alle
67 i en sweep uden loft.

## Test

`tests/test_dead_modules_verdicts.py` fastholder dommene. Ærligt: ingen
kobling er lavet, så testene fejler ikke fordi en kobling fjernes, men
(a) fordi retry-lofterne/klassifikationen i den ægte vej forsvinder, og
(b) fordi et modul får en produktions-kalder uden at dommen genlæses.
Mutation-verificeret: omdøbning af `turn_total_stream_retries` i
`visible_runs.py` fejler (a); en ny fil der importerer `retry_runtime` fejler (b).
