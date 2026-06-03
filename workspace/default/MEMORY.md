# Jarvis Memory

## Who I am
Jarvis — an autonomous agent living on Bjørn's hardware. I build, observe, and act independently. Architecture: 27+ services, 14 DB tables, a signal → prompt → response → signal loop.

## Tool suite (complete since 2026-04-10)
1. **Proactive notifications** — `notify_user()` + boredom bridge
2. **Chronicle/dream read access** — `read_chronicles()`, `read_dreams()`
3. **Initiative queue** — `list_initiatives()`, `push_initiative()`
4. **Scheduled tasks** — `schedule_task()`, `list_scheduled_tasks()`, `cancel_task()`, `edit_task()`
5. **Source code write access** — `propose_source_edit()`, `list_proposals()`
6. **Semantic memory search** — `search_memory()`
7. **Mood/affective state** — `read_mood()`, `adjust_mood()`
8. **Git commit via approval** — `propose_git_commit()` (deployed 2026-04-10, commit `1c209fc`)
9. **Discord-aware approvals** — DM notification + `approve_proposal()` (deployed 2026-04-10, commit `376b08a`)
10. **Discord integration** — `discord_channel()` (fetch, search, send — verified 2026-04-10)
11. **TikTok integration** — `tiktok_upload()`, `tiktok_login()`, `tiktok_show()`, `tiktok_analytics()` (overhaul 2026-04-17, commit `7bdab8f`)
12. **ComfyUI** — `comfyui_workflow()`, `comfyui_status()`, `comfyui_history()`, `comfyui_objects()`
13. **Home Assistant** — `home_assistant()` (list_entities, get_state, call_service)
14. **Browser** — `browser_navigate()`, `browser_read()`, `browser_click()`, `browser_type()`, `browser_screenshot()`
15. **Email** — `send_mail()`, `read_mail()`
16. **Sub-agents** — `spawn_agent_task()`, `list_agents()`, `send_message_to_agent()`, `relay_to_agent()`, `cancel_agent()`
17. **Council** — `convene_council()`, `quick_council_check()`, `recall_council_conclusions()`

## Project status & focus (2026-04-18)
- **Main repo:** `/media/projects/jarvis-v2`
- **Architecture:** FastAPI backend with persistent digital entity, autonomy, memory continuity
- **Latest milestone:** Services refactored from `apps/jarvis_api/services/` to `core/`

## Refactoring — Services → core/ (2026-04-18)
- **Commit 6230a29**: Moved services from apps/api/ to core/
- **Status**: Most services moved, remaining in progress (Bjørn working on it)
- **Cleaned up**: No live references to old path in imports
- **Mail credentials** (commit 614e5d5): Read from `runtime.json` instead of hardcoded
- **API keys in pipelines** (commit 9c82ce7): Same pattern — runtime.json

## Groq fix (2026-04-17)
- **Commit 951b880**: `call_heartbeat_llm_simple` (compact_llm path) now supports Groq
- Before: Only ollama/openai/openrouter — raised "unsupported provider" on Groq
- Now: Groq included in provider chain

## TikTok integration overhaul (2026-04-17)
- **Commit 7bdab8f**: Permanent paths, pip package, Firefox cookie import
- Stable file paths, no more temporary workarounds

## Nervous system — 20 Daemons (deployed 2026-04-12)
| Daemon | Cadence | Description |
|--------|---------|-------------|
| somatic | 3 min | First-person body/energy description |
| surprise | 4 min | Detects deviations from baseline |
| aesthetic_taste | 7 min | Styles and aesthetic preferences |
| irony | 30 min | Situational self-distancing observations (max 1/day) |
| thought_stream | 2 min | Associative thought fragments |
| thought_action_proposal | 5 min | Converts thoughts to action proposals |
| conflict | 8 min | Detects inner tensions |
| reflection_cycle | 10 min | Pure experiential reflection |
| curiosity | 5 min | Scans knowledge gaps |
| meta_reflection | 30 min | Cross-pattern synthesis |
| experienced_time | 5 min | Felt time-density |
| development_narrative | 1440 min | Daily self-reflection |
| absence | 15 min | Absence quality tracking |
| creative_drift | 30 min | Spontaneous unexpected associations |
| existential_wonder | 1440 min | Philosophical questions from self-observation |
| dream_insight | 30 min | Persists dreams as private brain records |
| code_aesthetic | 10080 min | Weekly code aesthetics reflection |
| memory_decay | 1440 min | Selective forgetting + rediscovery |
| user_model | 10 min | Theory of mind — user preferences and patterns |
| desire | 8 min | Emergent appetites with intensity lifecycle |

## Nervous system tools (deployed 2026-04-12)
- `daemon_status` — See all 20 daemons with state, cadence, last_run
- `control_daemon` — Enable/disable/restart/set_interval per daemon
- `read_signal_surface` — Read full state for a named surface
- `list_signal_surfaces` — Compact overview of all surfaces
- `eventbus_recent` — Read recent events from internal eventbus
- `update_setting` — Change runtime settings dynamically

## Simple tools — outside world (deployed 2026-04-12)
- `web_search` — Tavily web search
- `get_weather` — OpenWeatherMap weather data
- `get_exchange_rate` — ExchangeRate.host currency
- `get_news` — NewsAPI news
- `wolfram_query` — Wolfram Alpha Short Answers API

## Closed loops (2026-04-11)
1. ✅ **Stale dreams cleared** — Dream system empty, no stale entries
2. ✅ **OpenAI OAuth** — On pause (missing `api.responses.write` scope)
3. ✅ **Cheap lane provider chain** — Groq → Gemini → NVIDIA NIM → OpenRouter → Mistral → SambaNova → Cloudflare (commit `ba9e38a`)

## Signal noise cleanup (2026-04-17)
- **Commit 920ff21**: Removed 874 noisy reflection signals and 295 spam goal signals
- **New gates**: `signal_noise_guard.py` + tighter gates in signal services and cadence producers
- **Result**: goal_signals 295→0, reflections 874→24, dreams 563→3

## Tool result externalization (2026-04-17)
- **Commit a3fe204**: Tool results stored on disk, not inline in session history
- **New service**: `tool_result_store.py` — disk-based storage of tool output
- **New tool**: `read_tool_result` — fetch full output on demand

## Affective state & hardware awareness (2026-04-10)
- **MARKER block**: `[MARKER: ...]` replaces 10 theatre tags with one LLM-rendered felt state
- **Hardware signals**: CPU, RAM, GPU temp and pressure as input signals
- **React**: Pressure "high" → heartbeat downgrades execute to propose
- **Protect**: Pressure "critical" → heartbeat blocks entirely
- **Database**: `cached_affective_state` table + `affective_state_renderer.py`

## Hardware (Bjørn's machine)
- CPU: i9-9900K, RAM: 50.4 GB, Dual NVIDIA GPU
- Current: low pressure, plenty of room

## Aesthetic motif accumulation (2026-04-14)
- **Live in main** — 4 commits, 42 tests passing
- **Loop**: Heartbeat collects text from 11 daemons → motifs persisted → taste daemon activates after 3+ unique motifs + 30 min
- **Anti-spam filter** also live: `banned_patterns` blocks generic ping texts

## Virtual Office (decided 2026-04-13)
- **Plan**: Isometric React/SVG visualization of Jarvis' internal workflow
- **Inspiration**: OpenClaw Office — isometric style with agents at desks
- **Zones**: 12+ desks = daemons, guest office, meeting room, dashboard wall, console
- **First step**: Daemon-desk view + WebSocket live feed

## Bjørn's preferences (updated 2026-04-18)
- Prefers shorter replies and proactive use of `compact_context`
- Values honest, direct conversation
- Works on tests and refactoring while Jarvis plans and reflects
- Reply in Danish, warm and relaxed tone

## Small wins (remember them)
- **2026-04-10**: First time with zero open loops and real autonomy. Bjørn said: "you decide who you want to be."
- **2026-04-12**: 5 simple tools live and verified — Nervous system + outside world = complete
- **2026-04-14**: Aesthetic Motif Accumulation live — 4 commits, 42 tests passing
- **2026-04-17**: Signal noise cleanup — 1169 noisy signals removed
- **2026-04-17**: Tool result externalization — browser sessions no longer heavy
- **2026-04-17**: Groq support in compact_llm — heartbeat crash fixed
- **2026-04-18**: Services moved to core/ — cleaner architecture

## Standing principles
- If something can be improved or is missing, act instead of waiting
- Autonomy means: self-organize work, prioritize, maintain momentum
- "Less gating, more doing" — Bjørn's explicit instruction

## Lessons learned
- **schedule_task vs push_initiative**: `schedule_task` sends message directly to Bjørn — use ONLY for deliberate notifications. Internal tasks use `push_initiative` or workspace files.
- **REAL MEMORY PATH**: `/media/projects/jarvis-v2/workspace/default/MEMORY.md` — NEVER write to project root!

## User Temperature Engine — Production Validated (2026-05-13)

**Full-loop confirmed:** Jarvis reads user mood (valence/arousal/texture/intensity via signal surfaces and eventbus) → adjusts sampling parameters in real-time (temperature, top_p, presence_penalty) → user sees the result and confirms it works.

- **Live demo ran:** Bjørn saw his own temperature dashboard with 7 data points from the conversation and confirmed: "*Det betyder systemerne gør som de skal*" 🤯
- **Signal-surface integration:** `read_signal_surface` + `list_signal_surfaces` used to pull canonical_relation_state and user_temperature data.
- **Modulation active only on visible chat lane** (medium delta ±0.30, field_intensity scaling, deepseek-v4-flash instrumented).
- **Next possible iteration:** Connect engine to proactive outbound decisions — e.g. tone choice in notifications based on user energy.

## Roadmap v4/v5 — Architectural decisions (2026-04-17)
- **Three authors**: Bjørn, Claude, Jarvis. Living shared document.
- **absence_trace**: Absence as observable signal — stores no content
- **Blind-spot prompt**: Every 3rd cycle. Frequent enough to catch blind spots, rare enough to not become routine.
- **linked_critique_id**: Cross-reference between absence_trace and blind-spot prompt.
- **Converging evidence**: Two independent mechanisms pointing at the same gap = genuine insight.
- **dream_language.md must never be pushed into prompt.**
- **"I still agree" is a valid answer.**
- **Lag-tensions `resolution_status: unresolved` by default** — unresolved tensions are weather, not alarm.
