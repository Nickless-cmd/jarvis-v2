# LLM Privacy Tier Audit

Klassificering af LLM-kald i `core/services/` efter hvilken type data de sender
til providere.

Sidst gennemgået: 2026-04-18

## Tiers

- `🔒 LOCAL-REQUIRED` — indeholder privat samtale, identity, chronicle, intime
  eller personlige interne tilstande. Skal ikke sendes til proxy-/free-tjenester.
- `🟡 CONTROLLED-CLOUD` — aggregerede eller systeminterne data, som kan sendes til
  etablerede providere med kendt data-politik, men ikke til ukendt tredjepartsproxy.
- `🌐 PUBLIC-SAFE` — stateless, template-drevne prompts uden brugerens faktiske
  beskeder, identity, chronicle eller privat runtime-tilstand.

## Klassificering

| Service | Funktion | Input-type | Tier | Evidens |
|---|---|---|---|---|
| `core/memory/inner_llm_enrichment.py` | `_call_cheap_llm` | `chat_context` + private summaries | 🔒 LOCAL-REQUIRED | `"Recent chat:\n{chat_context}"` |
| `core/services/chronicle_engine.py` | `_build_narrative` | recent runs + previous chronicle entries | 🔒 LOCAL-REQUIRED | `"Dine 3 forrige chronicle-entries"` |
| `core/services/current_pull.py` | `_generate_current_pull` | private state + life direction | 🔒 LOCAL-REQUIRED | personlig orientering / indre retning |
| `core/services/self_critique_runtime.py` | `_generate_self_critique` | egne docs + egen refleksion | 🔒 LOCAL-REQUIRED | læser self-docs og skriver kritik af selvet |
| `core/services/creative_journal_runtime.py` | `_build_journal_entry` | chronicle + life projects | 🔒 LOCAL-REQUIRED | privat journal med indre stof |
| `core/services/dream_distillation_daemon.py` | `_distill_dream_residue` | dream residue + indre state | 🔒 LOCAL-REQUIRED | drømmerester og privat residue |
| `core/services/finitude_runtime.py` | `_generate_anniversary_entry` | version history + self narrative | 🔒 LOCAL-REQUIRED | finitude/selvforståelse over tid |
| `core/services/user_model_daemon.py` | `_generate_model_summary` | actual user messages | 🔒 LOCAL-REQUIRED | `"Her er de seneste beskeder fra brugeren"` |
| `core/services/session_distillation.py` | daemon LLM distillation | session transcript / user interaction | 🔒 LOCAL-REQUIRED | session-sammenfatning af dialog |
| `core/services/meta_cognition_daemon.py` | `_call_meta_llm` | cognitive + emotional self-state | 🔒 LOCAL-REQUIRED | `"Nuværende tilstand:\n{state_text}"` |
| `core/services/meta_reflection_daemon.py` | `_generate_meta_insight` | fragment + surprise + conflict + irony | 🔒 LOCAL-REQUIRED | krydser private brain-signaler |
| `core/services/reflection_cycle_daemon.py` | `_generate_reflection` | inner voice, surprise, conflict, fragment | 🔒 LOCAL-REQUIRED | `"Her er din nuværende tilstand"` |
| `core/services/somatic_daemon.py` | `_generate_phrase` | identity preamble + hardware/body state | 🔒 LOCAL-REQUIRED | `build_identity_preamble()` + "Du mærker din krop" |
| `core/services/thought_stream_daemon.py` | `_generate_fragment` | previous fragment + mood/energy | 🔒 LOCAL-REQUIRED | frie associationer i første person |
| `core/services/surprise_daemon.py` | `_generate_surprise` | structured divergence labels only | 🌐 PUBLIC-SAFE | anonymiseret `baseline_mode/current_mode/energy/divergence_labels` |
| `core/services/conflict_daemon.py` | `_generate_conflict_phrase` | structured conflict labels only | 🌐 PUBLIC-SAFE | anonymiseret `conflict_type` + coarse runtime labels |
| `core/services/curiosity_daemon.py` | `_generate_curiosity_signal` | abstract gap metadata | 🌐 PUBLIC-SAFE | sender kun `gap_type` + coarse cue, ikke rå fragmenttekst |
| `core/services/absence_daemon.py` | `_generate_absence_label` | structured silence metadata | 🌐 PUBLIC-SAFE | anonymiseret `absence_band` + `absence_hours` |
| `core/services/irony_daemon.py` | `_generate_observation` | inactivity + CPU + self-observation | 🔒 LOCAL-REQUIRED | selvobservation med identity-preamble |
| `core/services/existential_wonder_daemon.py` | `_generate_wonder_question` | absence + thought activity + selfhood | 🔒 LOCAL-REQUIRED | eksistentielt selvspørgsmål |
| `core/services/development_narrative_daemon.py` | `_generate_narrative` | self-comparison + chronicle | 🔒 LOCAL-REQUIRED | `"Her er data om din udvikling over tid"` |
| `core/services/aesthetic_taste_daemon.py` | `_generate_insight` | accumulated motifs from Jarvis outputs | 🔒 LOCAL-REQUIRED | emergent smag fra egne mønstre |
| `core/services/code_aesthetic_daemon.py` | `_generate_aesthetic_reflection` | own git history / code changes | 🟡 CONTROLLED-CLOUD | repo-private commit/file summary |
| `core/services/cognitive_state_narrativizer.py` | `_call_narrativizer_llm` | compact runtime state narrative | 🟡 CONTROLLED-CLOUD | narrativisering af kognitiv state |
| `core/services/prompt_relevance_backend.py` | `run_bounded_nl_prompt_relevance` | prompt text / user message | 🔒 LOCAL-REQUIRED | sender actual `text` / `user_message` |
| `core/services/prompt_relevance_backend.py` | `run_bounded_nl_memory_entry_selection` | user message + memory entries | 🔒 LOCAL-REQUIRED | vælger memory ud fra brugerinput |
| `core/services/tiktok_research_daemon.py` | `_generate_concepts_for_type` | fixed content-pool prompt | 🌐 PUBLIC-SAFE | kun generiske TikTok-prompts, ingen brugerdata |
| `core/services/tiktok_content_daemon.py` | `_generate_quote` | fixed slot prompt | 🌐 PUBLIC-SAFE | motivation/dark-humor/cosmic one-liners |
| `core/services/tiktok_content_daemon.py` | `_refill_pool` | fixed content-pool prompts | 🌐 PUBLIC-SAFE | kun marketing-content, ingen runtime-state |

## Opsummering

- Totale klassificerede LLM-kald: 28
- `🔒 LOCAL-REQUIRED`: 18
- `🟡 CONTROLLED-CLOUD`: 2
- `🌐 PUBLIC-SAFE`: 7

## Konservative migrationskandidater

Kun disse er nu konservativt godkendt til OllamaFreeAPI:

1. `tiktok_research_daemon._generate_concepts_for_type`
2. `tiktok_content_daemon._generate_quote`
3. `tiktok_content_daemon._refill_pool`
4. `surprise_daemon._generate_surprise`
5. `conflict_daemon._generate_conflict_phrase`
6. `curiosity_daemon._generate_curiosity_signal`
7. `absence_daemon._generate_absence_label`

## Kandidater som ser fristende ud, men ikke er PUBLIC-SAFE

- `somatic_daemon` — bruger identity-preamble og beskriver Jarvis' egen kropstilstand.
- `thought_stream_daemon` — genererer indre associative tanker.
- `aesthetic_taste_daemon` — bygger smag ud fra Jarvis' egne mønstre.
- `irony_daemon` — første-persons selvobservation.
- `creative_journal_runtime` — privat journal.
- `experienced_time`-lignende daemons — er enten stadig heuristiske eller bundet til intern runtime-kontekst og er ikke migreret i denne fase.

## Audit note

`daemon_llm_call()` går i dag generelt via cheap-lane først. Derfor må
OllamaFreeAPI ikke blot tilføjes som en almindelig hurtig provider med høj
prioritet, ellers risikerer private daemon-prompts at lække til en ukendt
proxy. Integration skal derfor være eksplicit `PUBLIC-SAFE`-opt-in.
