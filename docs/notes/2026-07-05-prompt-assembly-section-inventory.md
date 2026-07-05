# Prompt-assembly sektions-inventar (visible lane) — 5. jul 2026

Verificeret pr. builder (hver kilde åbnet, ikke gættet fra navn). Hovedfunktion:
`build_visible_chat_prompt_assembly` (`core/services/prompt_contract.py:480`). Ikke-compact sti.

Understøtter spec `2026-07-05-central-governed-inner-life-design.md`. Arbejds-typer:
LLM_CALL · STATE_READ · DB_QUERY · SUBSYSTEM_COMPUTE · STATIC.

## 🟢 Flyttes til Central-vedligeholdt baggrunds-cache (tunge, ikke-besked-afhængige)

| label | linje | builder | type | ms/tur |
|---|---|---|---|---|
| rule_engine_conclusions | :1299 | `rule_conclusions_section` → `evaluate_rules` | SUBSYSTEM_COMPUTE (36-regel forward-chain, 60s TTL) | ~6.000 |
| cognitive_state | :581/:2014 | `build_cognitive_state_for_prompt` (`cognitive_state_assembly.py:295`) | LLM_CALL (4× narrativize + recall) | 170 / 6.000 kold |
| frame (cognitive frame) | :586/:1996 | `_cognitive_frame_section` → `build_cognitive_frame_prompt_section` | SUBSYSTEM_COMPUTE (30+ serielle DB-reads, 180s TTL) | ~4.000 |
| causal_narrative | :1319 | `causal_narrative_section` → graf-backchain | SUBSYSTEM_COMPUTE (5-min TTL) | ~500 |
| causal_alerts | :1308 | `causal_alerts_section` | SUBSYSTEM_COMPUTE | var. |
| causal_patterns (tail) | :1331 | `causal_patterns_section` | SUBSYSTEM_COMPUTE (30-min TTL) | var. |
| pattern_counterfactuals (tail) | :1342 | `pattern_counterfactuals_section` | SUBSYSTEM_COMPUTE | var. |
| indre_liv | :953 | `build_inner_life_section` (`visible_inner_life.py:263`) | STATE_READ | 300-1.000 |
| + ~30 STATE_READ-surfaces → **ÉT digest** | :1224-1712 m.fl. | self-report, world-model-nudges, goals, todos, drift, hypoteser, milestones, monitor-digest osv. | STATE_READ (kv/db) | ~50-150 hver, **~7s serielt** |

Digestet komponeres ved at LÆSE+formatere de 30 kilder (intet nyt LLM-kald) — vedligeholdt i
baggrund så hot-path laver ÉN læsning i stedet for 30 serielle builds. Fjerner størstedelen af
`sync_seg_mid_done` (~7s).

## 🔵 Bliver live (besked-afhængige) — men dedupliceres

| label | linje | type | ms | note |
|---|---|---|---|---|
| relevance (gatekeeper) | :573/:1859 | LLM_CALL (60s TTL) | ~1.500 | senere: billigere klassifikator |
| multi-signal_recall | :1496 | LLM_CALL (embed-fusion) | 1.200-1.900 | \\ |
| recall-before-act | :1449 | LLM_CALL (cold-tier embed) | ~1.200 | 4-5 overlappende recall-passes |
| memory_selection (MEMORY.md) | :1863 | LLM_CALL (NL entry-selektion) | 1.500-2.700 | → konsolidér til 1-2 |
| memory_recall_bundle | :1878 | LLM_CALL (ollama-embed) | ~1.200 | / |
| jarvis_brain_facts | :1065 | LLM_CALL (embed mod brain) | 200-950 | / |

## 🔴 Lukkes (ægte spild — IKKE indre liv)

| label | linje | hvorfor |
|---|---|---|
| dead_skills_(never_invoked) | :1607 | bygger tekst om aldrig-brugte skills; ingen handling for modellen |
| bounded inner visible prompt bridge | :1889/:2860 | future der på visible-lane ALTID returnerer `line=None` → spildt orkestrering |

## Genoplives under Central-styring (var "død", nu måske signal — behandles som 🟢 lav-prio)
curiosity_consolidation (:1622), meta-learning retrospective teaser (:1670), curiosity idle-window
(:1658), world-model calibration milestone (:1589, "one-shot"), skill_chain_proposals (:1616),
central self-generated hypotheses / Lag 3 (:1646).

## Self-surveillance-familie → genoplives under Central-målt ground truth (spec §6, anti-gaming)
R2_gate_telemetry (:1273), decision_adherence (:1278), metacognition_signals (:1233).
Blev skåret 22. jun (modellen narrerede rå tal tilbage). Genoplives KUN via Central-ejet
måling fra event-strøm — aldrig Jarvis-skrivbar tilstand.

## Bevaret STATIC/prefix (uændret — stabil cache-prefix, rør ikke)
lane identity (:605), quick facts (:611), model identity (:620), honesty rules (:677),
SOUL/IDENTITY/STANDING_ORDERS/USER.md (:704-714), wake-up block (:721), visible chat rules (:650),
tool catalog, time pin (hale). Disse er billige og load-bearing for identitet — bliver på hot-path.

## Ikke-vildledende navne (verificeret STATE_READ, ikke LLM på læse-stien)
current_pull (:947), active_autonomous_goals (:1508), provider_health (:1528) — LLM/urlopen sidder
i separate daemon/refresh-veje, ikke i assembly.
