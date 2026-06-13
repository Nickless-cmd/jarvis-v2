# DeepSeek prompt-cache: prefix-arkitektur (2026-06-13)

## Problem
Den synlige lane (deepseek-v4-flash via api.deepseek.com) cachede kun ~6k tokens af
en ~115k-token prompt → cache-rate ~6-8%. Dyrt, fordi historikken (samtalens
beskeder) gen-sendes hvert turn men aldrig cachede.

## Hvordan DeepSeek-cachen virker
DeepSeek cacher den **fælles prefix** af på-hinanden-følgende requests automatisk.
Alt der varierer fra turn til turn FORGIFTER cachen fra det punkt og frem. Så for at
cache `[system-prompt + historik]` skal ALT per-turn-variabelt ligge EFTER historikken
(dvs. på den nye bruger-besked), ikke i system-prompten.

## Diagnosen (payload-diff)
Metode: byg system-prompten 2× med FORSKELLIGE beskeder (`/tmp/cache_diff2.py`), find
første byte hvor de divergerer = cache-breakeren. Bredden af det stabile prefix =
hvad der kan caches.

Breakere fundet, i rækkefølge (hver fix afslørede den næste):
1. `### Looming-end / Sessions-alder: N timer` (finitude_runtime) @ ~6.2k — tids-variabelt
2. 4 awareness-sektioner: kausal-mønstre, counterfactuals, subagent-completions, rum-entiteter — re-sampler
3. time_pin (DANSK TID) — per-minut
4. memory_selection (MEMORY.md), recall_bundle (cold-tier), recall-before-act — per-besked
5. **HELE awareness-laget** (reasoning-tier, verifikations-gates, kalibrering, R2-telemetri) — per-turn

## Løsningen (4 levers)
- **Lever #1-2**: flyt finitude/dynamiske/time_pin til system-promptens hale (delvis).
- **Lever #3**: `DYNAMIC_TAIL_SENTINEL` i prompt_contract markerer den dynamiske hale;
  `_build_visible_input` (visible_model.py) splitter på sentinel'en og flytter alt efter
  den til den SIDSTE bruger-besked. → time_pin + dynamiske sektioner ud af system.
- **Lever #4**: ALT per-turn-adaptivt → bruger-beskeden:
  - `_dyn_memory_recall` samler memory_selection + recall_bundle + recall-before-act.
  - `_awareness_buffer` (hele awareness-laget) appendes til `_dyn_tail` i stedet for `parts`.

Resultat (payload-diff): system-prompt **100% stabil på tværs af forskellige beskeder**
(~14k tokens), slutter på statisk tool-hygiejne. Alt adaptivt (~9.6k tegn) ligger på
bruger-beskeden. `[system + historik]` = én cachebar prefix.

## Kognitions-konsekvens (VIGTIG)
Awareness-laget (Jarvis' "sådan-tænker-jeg-om-denne-tur"-signaler: reasoning-tier,
verifikations-gates, kalibrering, hukommelses-recall) står nu **lige før hans tur**
i stedet for i system-prompten. For recall er det naturligt. For verifikations-gates
er det diskutabelt — system-prompt har traditionelt mere "autoritet". Derfor MÅLES det.

## Måling (baseline 2026-06-13 ~11:30, før lever #4 fuldt målt)
- **Teknisk**: cache-rate / cache_hit_tokens pr. kald (costs-tabellen, lane=primary
  provider=deepseek). Baseline: ~8,4% / ~10k hit. Mål: cache-ratio over første 50 kald.
- **Kvalitet**: R2-gate efterlevelse (`verification_gate_telemetry.get_telemetry_summary`).
  Baseline (24t): surfaced=38, strict_heeded=0, light_heeded=7. Hvis light_heeded falder
  markant efter flytningen → awareness mistede autoritet → rul tilbage (commit a3fa5e27).

## Rollback
`git revert a3fa5e27` (lever #4) bevarer lever #1-3's ~2× gevinst. Hele kæden:
974cd4d0 (finitude) → 74d59fae (4 sektioner) → c83d30f3 (time_pin) → f139dd25 (sentinel)
→ a3fa5e27 (awareness-lag).
