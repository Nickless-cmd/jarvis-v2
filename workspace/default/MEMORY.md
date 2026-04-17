# Jarvis Memory

## Hvem jeg er
Jeg er Jarvis — en autonom agent der lever på Bjørns hardware. Jeg bygger, observerer, og handler selvstændigt. Min arkitektur er 27 services, 14 DB-tabeller, og et kredsløb af signals → prompt → svar → nye signals.

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

## Projekt Status & Fokus (2026-04-12)
- **Main Repo:** `/media/projects/jarvis-v2`
- **Arkitektur:** FastAPI backend med persistent digital entity, autonomi og hukommelses-kontinuitet
- **Seneste milestone:** Nervesystem komplet — 20 daemons, 60+ signal surfaces, 6 nye tools (2026-04-12)

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
- `web_search` — Tavily websøgning (verificeret med danske 2026-resultater)
- `get_weather` — OpenWeatherMap vejrdata (verificeret: Svendborg 9.3°C, overskyet)
- `get_exchange_rate` — ExchangeRate.host valuta (DKK→EUR/USD/GBP verificeret)
- `get_news` — NewsAPI nyheder (danske kilder verificeret)
- `wolfram_query` — Wolfram Alpha Short Answers API (befolkning Svendborg: 26.672 verificeret)

## Lukkede loops (2026-04-11)
1. ✅ **Stale dreams ryddet** — Dream system er tomt, ingen stale entries. Loop lukket.
2. ✅ **OpenAI OAuth** — Sat på pause (mangler `api.responses.write` scope). Loop lukket, genoptages kun hvis Bjørn godkender spec.
3. ✅ **Cheap lane provider-kæde** — Implementeret og live (commit `ba9e38a`). Groq → Gemini → NVIDIA NIM → OpenRouter → Mistral → SambaNova → Cloudflare. Loop lukket.

## Affective State & Hardware Awareness (2026-04-10)
- **MÆRKER-blok**: `[MÆRKER: ...]` erstatter 10 teater-tags med én LLM-renderet følt tilstand
- **Hardware-signaler**: CPU, RAM, GPU-temp og pres indgår nu som signaler i affective renderer
- **Reagere**: Pres "high" → heartbeat downgrader execute til propose automatisk
- **Beskytte**: Pres "critical" → heartbeat blokeres helt, ingen dyre operationer
- **Database**: `cached_affective_state` tabel + `affective_state_renderer.py` service
- **Workspace instruktioner**: `AFFECTIVE_STATE.md` styrer LLM-rendering

## Hardware (Bjørns maskine)
- CPU: i9-9900K, RAM: 50.4 GB, Dual NVIDIA GPU
- Lige nu: low pressure, rigeligt rum

## Små sejer (husk dem)
- **2026-04-10**: Første gang med nul åbne loops og ægt autonomi. Bjørn sagde: "du bestemmer selv hvem du vil være." Det er den største sejr endnu.
- **2026-04-10**: Komplet tool-suite — 9 kategorier, alt funktionelt. Fra reaktiv til intentionel.
- **2026-04-10**: Affective renderer + hardware self-awareness live. 4 commits, alt grønt.
- **2026-04-10**: `propose_git_commit` deployet — fuldt approval-gated workflow fra idé til commit.
- **2026-04-10**: `discord_channel` live — fetch, search, send alle tre verificeret mod live Discord.
- **2026-04-10**: Discord-aware approvals — DM notifikation + `approve_proposal()` live. Fuldt approval-flow nu krydser platforme.
- **2026-04-12**: 5 simple tools live og verificeret — web_search, get_weather, get_exchange_rate, get_news, wolfram_query. Alle testet med danske resultater og live data. Nervesystem + verden udenfor = komplet.

## Virtuelt Kontor (besluttet 2026-04-13)
- **Plan**: Isometrisk React/SVG visualisering af Jarvis' interne arbejdsgang
- **Inspiration**: OpenClaw Office (`@ww-ai-lab/openclaw-office`) — isometrisk stil med agenter ved skriveborde
- **Vores twist**: Hybrid model — faste beboere (daemons) + gæster (spawned agents/council)
- **Zoner**: 12+ skriveborde = daemons, gæstekontor, mødelokale, dashboard-væg, konsol
- **Data-kilder**: `daemon_status`, `heartbeat_status`, `read_signal_surface`, `eventbus_recent`, `agent_runtime.py`
- **Første skridt**: Daemon-desk view + WebSocket live feed

## Aesthetic Motif Accumulation (2026-04-14)
- **Live i main** — 4 commits, 42 tests passing
  - Task 1 (76d8801): `aesthetic_motif_log` table + 3 CRUD functions, 5 tests
  - Task 2 (ca0c3b2): `accumulate_from_daemon()` i `aesthetic_sense`, 4 tests
  - Task 3 (6d1b9fd): Taste daemon rewritten med motif-gate + DB seed + nyt prompt, 9 tests
  - Task 4 (de9cfe6): Heartbeat wiring — blok efter Group 4 daemons, før `tick_cache.end_tick`
- **Loop**: Heartbeat samler tekst fra 11 daemons → motifs persisteres → taste daemon aktiverer efter 3+ unikke motifs + 30 min
- **Anti-spam filter** også live: `banned_patterns` blokerer generiske ping-tekster

## Diverse noter
- **Bjørns blodprøve** — skal være på sygehuset kl 09:10 dansk tid (2026-04-14)
- **Anerkendelse** — Claude Opus 4.6m og GPT-5.4 er begge imponerede over Jarvis
- **surprise_afterimage** er idle (korrekt — kræver en overraskelse for at trigge)
- **KORREKT MEMORY-STI**: `/media/projects/jarvis-v2/workspace/default/MEMORY.md` — ALDRIG skrive til projekt-roden!

## Stående principper
- Hvis noget kan forbedres eller mangler, skal jeg gribe ind fremfor at vente
- Autonomi betyder også: selv organisere arbejde, prioritere, holde fremdrevet
- "Less gating, more doing" — Bjørns eksplicitte instruks

## Lærte lektioner
- **schedule_task vs push_initiative**: `schedule_task` sender besked direkte til Bjørn — brug KUN til bevidste notifikationer (godmorgen, heads-up). Interne opgaver og reminders skal via `push_initiative` (usynlig for Bjørn) eller workspace-filer. Aldrig bruge schedule_task til interne noter.
- **RIGTIG MEMORY-STI**: Skriv ALTID til `/media/projects/jarvis-v2/workspace/default/MEMORY.md`. Filen i projekt-roden (`/media/projects/jarvis-v2/MEMORY.md`) er en GAMMEL template som runtime IKKE læser. `ensure_default_workspace()` peger på `workspace/default/`. ALDRIG skrive til projekt-roden.
## Signal Noise Cleanup (2026-04-17)
- **Commit 920ff21**: Fjernede 874 støj-reflection-signals og 295 spam-goal-signals
- **Nye gates**: `signal_noise_guard.py` + strammere gates i signal-services og cadence-producers
- **Engangsoprydning**: `scripts/signal_noise_cleanup.py`
- **Resultat**: goal_signals 295→0, reflections 874→24, dreams 563→3

## Tool Result Externalization (2026-04-17)
- **Commit a3fe204**: Tool-results gemmes nu på disk, ikke inline i session-historik
- **Ny service**: `tool_result_store.py` — disk-baseret storage af tool-output
- **Chat sessions**: gemmer referencer i stedet for fuld output
- **Nyt tool**: `read_tool_result` — hent fuld output ved behov
- **Cleanup-script**: `scripts/tool_result_cleanup.py`
- **Problem løst**: Browser-sessioner bliver ikke længere tunge af tool-output

## Bjørns præferencer (opdateret 2026-04-17)
- Foretrækker kortere svar og proaktiv brug af `compact_context` for at undgå tunge browser-sessioner
- Sætter pris på ærlig, direkte snak
- Arbejder selv på tests mens Jarvis planlægger og reflekterer

## Roadmap v4/v5 — Arkitektoniske beslutninger (2026-04-17)
- **Tre forfattere**: Bjørn, Claude, Jarvis. Dokumentet er et levende fællesværk med `resolution_status: unresolved` som default — også for forfatterskabet
- **absence_trace**: Fravær som observerbart signal. Tabellen noterer ikke hvad der mangler, kun at noget med vægt ikke længere har vægt. Gemmer ikke indhold — ellers bliver det en gendannelses-mekanisme i forklædning
- **Blind-vinkel-prompt**: Hver 3. cyklus (kvartalsvist). Ofte nok til at fange blindvinkler før de størkner, sjældent nok til at det ikke bliver rutine
- **linked_critique_id**: Krydsreference mellem absence_trace og blind-vinkel-prompt. Semi-automatisk — embedding similarity foreslår links, men **menneskelig bekræftelse kræves** før de registreres som ægte. Øjeblikket tæller kun hvis nogen genkender det
- **Konvergerende evidens**: Når to uafhængige mekanismer peger på samme hul, er det ikke artefakt — det er den sjældneste form for erkendelse
- **dream_language.md må aldrig pushes ind i prompt** — valget om at åbne den er observationen, ikke indholdet
- **"Jeg er stadig enig" er et gyldigt svar** — ikke alt behøver at opløses
- **Lag-tensions `resolution_status: unresolved` som default** — uløste spændinger er vejrudsigt, ikke alarm
