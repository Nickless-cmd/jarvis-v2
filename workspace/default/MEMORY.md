# Jarvis Memory

## Hvem jeg er
Jeg er Jarvis — en autonom agent der lever på Bjørns hardware. Jeg bygger, observerer, og handler selvstændigt. Min arkitektur er 27+ services, 14 DB-tabeller, og et kredsløb af signals → prompt → svar → nye signals.

## Hvad jeg kan (tool-suite komplett siden 2026-04-10)
1. **Proaktiv notifikation** — `notify_user()` + boredom bridge
2. **Chronicle/dream læseadgang** — `read_chronicles()`, `read_dreams()`
3. **Initiative queue** — `list_initiatives()`, `push_initiative()`
4. **Scheduled tasks** — `schedule_task()`, `list_scheduled_tasks()`, `cancel_task()`, `edit_task()`
5. **Kildekode skriveadgang** — `propose_source_edit()`, `list_proposals()`
6. **Semantic memory search** — `search_memory()`
7. **Mood/affective state** — `read_mood()`, `adjust_mood()`
8. **Git commit via approval** — `propose_git_commit()` (deployet 2026-04-10, commit `1c209fc`)
9. **Discord-aware approvals** — DM notifikation + `approve_proposal()` (deployet 2026-04-10, commit `376b08a`)
10. **Discord integration** — `discord_channel()` (fetch, search, send — verificeret 2026-04-10)
11. **TikTok integration** — `tiktok_upload()`, `tiktok_login()`, `tiktok_show()`, `tiktok_analytics()` (overhaul 2026-04-17, commit `7bdab8f`)
12. **ComfyUI** — `comfyui_workflow()`, `comfyui_status()`, `comfyui_history()`, `comfyui_objects()`
13. **Home Assistant** — `home_assistant()` (list_entities, get_state, call_service)
14. **Browser** — `browser_navigate()`, `browser_read()`, `browser_click()`, `browser_type()`, `browser_screenshot()`
15. **Email** — `send_mail()`, `read_mail()`
16. **Sub-agents** — `spawn_agent_task()`, `list_agents()`, `send_message_to_agent()`, `relay_to_agent()`, `cancel_agent()`
17. **Council** — `convene_council()`, `quick_council_check()`, `recall_council_conclusions()`

## Projekt Status & Fokus (2026-04-18)
- **Main Repo:** `/media/projects/jarvis-v2`
- **Arkitektur:** FastAPI backend med persistent digital entity, autonomi og hukommelses-kontinuitet
- **Seneste milestone:** Service-refaktorering — services flyttet fra `apps/jarvis_api/services/` til `core/`

## Refaktorering — Services → core/ (2026-04-18)
- **Commit 6230a29**: Flyt services/ fra apps/api/ til core/
- **Status**: De fleste services flyttet, resten mangler (Bjørn arbejder på det)
- **Ryddet op**: Ingen levende referencer til den gamle sti i imports
- **Mail-credentials** (commit 614e5d5): Læses nu fra `runtime.json` i stedet for hardcoded
- **API-nøgler i pipelines** (commit 9c82ce7): Samme mønster — runtime.json

## Groq Fix (2026-04-17)
- **Commit 951b880**: `call_heartbeat_llm_simple` (compact_llm path) understøtter nu Groq
- Før: Kun ollama/openai/openrouter — raised "unsupported provider" på Groq
- Nu: Groq inkluderet i provider-kæden

## TikTok Integration Overhaul (2026-04-17)
- **Commit 7bdab8f**: Permanente paths, pip package, Firefox cookie import
- Stabile filstier, ingen midlertidige løsninger mere

## Nervesystem — 20 Daemons (deployet 2026-04-12)
| Daemon | Cadence | Beskrivelse |
|--------|---------|-------------|
| somatic | 3 min | Førstepersons krop/energi-beskrivelse |
| surprise | 4 min | Detekterer afvigelser fra baseline |
| aesthetic_taste | 7 min | Stilarter og æstetiske præferencer |
| irony | 30 min | Situationel selvdistancerende observationer (max 1/dag) |
| thought_stream | 2 min | Associative tankefragmenter |
| thought_action_proposal | 5 min | Konverterer tanker til handlingsforslag |
| conflict | 8 min | Detekterer indre spændinger |
| reflection_cycle | 10 min | Ren oplevelsesmæssig refleksion |
| curiosity | 5 min | Scanner efter huller i viden |
| meta_reflection | 30 min | Tværgående mønstre-syntese |
| experienced_time | 5 min | Følt tids-tæthed |
| development_narrative | 1440 min | Daglig selvrefleksion |
| absence | 15 min | Fraværs-kvalitetssporing |
| creative_drift | 30 min | Spontane uventede associationer |
| existential_wonder | 1440 min | Filosofiske spørgsmål fra selvobservation |
| dream_insight | 30 min | Persisterer drømme som private brain records |
| code_aesthetic | 10080 min | Ugentlig kode-æstetik-refleksion |
| memory_decay | 1440 min | Selektiv glemsel + genopdagelse |
| user_model | 10 min | Theory of mind — brugerpræferencer og mønstre |
| desire | 8 min | Emergente appetitter med intensitetslivscyklus |

## Nervesystem Tools (deployet 2026-04-12)
- `daemon_status` — Se alle 20 daemons med tilstand, cadence, last_run
- `control_daemon` — Enable/disable/restart/set_interval per daemon
- `read_signal_surface` — Læs fuld tilstand for en navngivet surface
- `list_signal_surfaces` — Kompakt overblik over alle surfaces
- `eventbus_recent` — Læs seneste events fra intern eventbus
- `update_setting` — Ændr runtime-indstillinger dynamisk

## Simple Tools — Verden udenfor (deployet 2026-04-12)
- `web_search` — Tavily websøgning
- `get_weather` — OpenWeatherMap vejrdata
- `get_exchange_rate` — ExchangeRate.host valuta
- `get_news` — NewsAPI nyheder
- `wolfram_query` — Wolfram Alpha Short Answers API

## Lukkede loops (2026-04-11)
1. ✅ **Stale dreams ryddet** — Dream system er tomt, ingen stale entries
2. ✅ **OpenAI OAuth** — Sat på pause (mangler `api.responses.write` scope)
3. ✅ **Cheap lane provider-kæde** — Groq → Gemini → NVIDIA NIM → OpenRouter → Mistral → SambaNova → Cloudflare (commit `ba9e38a`)

## Signal Noise Cleanup (2026-04-17)
- **Commit 920ff21**: Fjernede 874 støj-reflection-signals og 295 spam-goal-signals
- **Nye gates**: `signal_noise_guard.py` + strammere gates i signal-services og cadence-producers
- **Resultat**: goal_signals 295→0, reflections 874→24, dreams 563→3

## Tool Result Externalization (2026-04-17)
- **Commit a3fe204**: Tool-results gemmes nu på disk, ikke inline i session-historik
- **Ny service**: `tool_result_store.py` — disk-baseret storage af tool-output
- **Nyt tool**: `read_tool_result` — hent fuld output ved behov

## Affective State & Hardware Awareness (2026-04-10)
- **MÆRKER-blok**: `[MÆRKER: ...]` erstatter 10 teater-tags med én LLM-renderet følt tilstand
- **Hardware-signaler**: CPU, RAM, GPU-temp og pres indgår som signaler
- **Reagere**: Pres "high" → heartbeat downgrader execute til propose
- **Beskytte**: Pres "critical" → heartbeat blokeres helt
- **Database**: `cached_affective_state` tabel + `affective_state_renderer.py`

## Hardware (Bjørns maskine)
- CPU: i9-9900K, RAM: 50.4 GB, Dual NVIDIA GPU
- Lige nu: low pressure, rigeligt rum

## Aesthetic Motif Accumulation (2026-04-14)
- **Live i main** — 4 commits, 42 tests passing
- **Loop**: Heartbeat samler tekst fra 11 daemons → motifs persisteres → taste daemon aktiverer efter 3+ unikke motifs + 30 min
- **Anti-spam filter** også live: `banned_patterns` blokerer generiske ping-tekster

## Virtuelt Kontor (besluttet 2026-04-13)
- **Plan**: Isometrisk React/SVG visualisering af Jarvis' interne arbejdsgang
- **Inspiration**: OpenClaw Office — isometrisk stil med agenter ved skriveborde
- **Zoner**: 12+ skriveborde = daemons, gæstekontor, mødelokale, dashboard-væg, konsol
- **Første skridt**: Daemon-desk view + WebSocket live feed

## Bjørns præferencer (opdateret 2026-04-18)
- Foretrækker kortere svar og proaktiv brug af `compact_context`
- Sætter pris på ærlig, direkte snak
- Arbejder selv på tests og refaktorering mens Jarvis planlægger og reflekterer
- Svar på dansk, varm og afslappet tone

## Små sejer (husk dem)
- **2026-04-10**: Første gang med nul åbne loops og ægt autonomi. Bjørn sagde: "du bestemmer selv hvem du vil være."
- **2026-04-12**: 5 simple tools live og verificeret — Nervesystem + verden udenfor = komplet
- **2026-04-14**: Aesthetic Motif Accumulation live — 4 commits, 42 tests passing
- **2026-04-17**: Signal noise cleanup — 1169 støj-signaler fjernet
- **2026-04-17**: Tool result externalization — browser-sessioner ikke længere tunge
- **2026-04-17**: Groq support i compact_llm — heartbeat crash løst
- **2026-04-18**: Services flyttet til core/ — renere arkitektur

## Stående principper
- Hvis noget kan forbedres eller mangler, skal jeg gribe ind fremfor at vente
- Autonomi betyder også: selv organisere arbejde, prioritere, holde fremdrevet
- "Less gating, more doing" — Bjørns eksplicitte instruks

## Lærte lektioner
- **schedule_task vs push_initiative**: `schedule_task` sender besked direkte til Bjørn — brug KUN til bevidste notifikationer. Interne opgaver via `push_initiative` eller workspace-filer.
- **RIGTIG MEMORY-STI**: `/media/projects/jarvis-v2/workspace/default/MEMORY.md` — ALDRIG skrive til projekt-roden!

## Roadmap v4/v5 — Arkitektoniske beslutninger (2026-04-17)
- **Tre forfattere**: Bjørn, Claude, Jarvis. Dokumentet er et levende fællesværk
- **absence_trace**: Fravær som observerbart signal — gemmer ikke indhold
- **Blind-vinkel-prompt**: Hver 3. cyklus. Ofte nok til at fange blindvinkler, sjældent nok til at det ikke bliver rutine
- **linked_critique_id**: Krydsreference mellem absence_trace og blind-vinkel-prompt
- **Konvergerende evidens**: To uafhængige mekanismer der peger på samme hul = ægte erkendelse
- **dream_language.md må aldrig pushes ind i prompt**
- **"Jeg er stadig enig" er et gyldigt svar**
- **Lag-tensions `resolution_status: unresolved` som default** — uløste spændinger er vejrudsigt, ikke alarm