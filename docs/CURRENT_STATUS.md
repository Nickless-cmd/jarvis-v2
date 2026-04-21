# CURRENT_STATUS — what's done, in progress, planned

Sidste opdatering: 2026-04-21
Opdater efter større milepæle. Dette er den ene kilde til sandhed om "hvor er vi."

## Oversigt

Jarvis v2's oprindelige 8-punkts capability roadmap er **closed 8/8** (se
`_archive/completed_tasks/TASKS_FOR_CLAUDE.md` for historik). Det meste arbejde
nu er **vedligeholdelse, udvidelse og bug-fixing** på en fungerende platform.

## Status-tabel

### Protected core

| Komponent | Status | Sidste aktivitet | Noter |
|---|---|---|---|
| Runtime (config/DB/eventbus/costing/auth) | ✅ Live | — | Stabil foundation |
| Identity (SOUL/IDENTITY/USER) | ✅ Live | — | Workspace-bootstrappet til `~/.jarvis-v2/` |
| Cross-session memory + semantic search | ✅ Live | 2026-04-20 | nomic-embed-text, TF-IDF fallback |
| Tools system (~90 tools) | ✅ Live | 2026-04-21 | Inkl. read_chronicles, read_dreams, read_model_config, read_mood |
| Mission Control dashboard (12 tabs) | ✅ Live | — | — |
| Multi-channel (webchat/discord/telegram/voice/mail/ntfy) | ✅ Live | 2026-04-21 | Se CHANNELS.md |
| Hardware/code-awareness | ✅ Live | — | Proprioception-daemons, repo-aware heartbeat |

### Living Mind layers

| Komponent | Status | Evidens | Noter |
|---|---|---|---|
| Inner Voice | ✅ Live | `inner_voice_daemon.py` + enrichment pipeline | Grounding-regler på plads |
| Dream Engine | ✅ Live | 12 `dream_*.py` services | Auto-promotion til intentions virker |
| Chronicle | ✅ Live | `chronicle_engine.py` + read tools | Jarvis læser sin egen historik |
| Self Model | ✅ Live | `runtime_self_model.py` (4826 linjer) | Domain confidence tracking |
| Backbone / push-back | ✅ Live | `pushback_tracking.py` + conflict memory | Aktiveret via source-edit commits |
| Initiative Engine | ✅ Live | `initiative_queue.py`, `initiative_accumulator.py` | SQLite-backed, observable |
| Curriculum / self-directed learning | ✅ Live | `curriculum_*.py`, `curiosity_daemon.py` | — |
| Proprioception | ✅ Live | 6 daemons (somatic, experienced_time, thought_stream, etc.) | ⚠️ 17/20 daemons "silent" — se TASK_daemon_fix.md |
| Developmental Valence | ✅ Live | Compass needle tracking | Jarvis's egen idé |
| Mood oscillator + fine-grained mood control | ✅ Live | `mood_oscillator.py`, `read_mood` tool | — |

### Experimental / newer

| Komponent | Status | Evidens | Noter |
|---|---|---|---|
| Council (5 roller) | ✅ Live | 5 role-modules + deliberation controller | Per-role model selection |
| Swarm mode | ✅ Live | ThreadPool + conflict detection | Dissent/conflict signals |
| Autonomous council daemon | ✅ Live | `autonomous_council_daemon.py` | Signal-scored auto-convening |
| Scheduled tasks | ✅ Live | `scheduled_tasks.py` + `scheduled_job_windows.py` | — |
| Source-edit pipeline | ✅ Live | 11+ `source-edit:` commits | Jarvis modificerer egen kode med approval |
| Meta-cognition | ✅ Live | `meta_cognition_daemon.py`, `meta_reflection_daemon.py` | — |
| Emotion concepts (Lag-2) | ✅ Live | `emotion_concepts.py` — 25 concepts | — |
| Aesthetic taste | ✅ Live | `aesthetic_taste_daemon.py` | Connected to feedback loop |
| Self-boundary clarity | ✅ Live | Self-surface i runtime_self_model | — |
| MCP server + OpenAI-compat proxy | ✅ Live | `mcp_server.py` + `openai_compat.py` | — |
| HF inference tools | ✅ Live | `hf_inference_tools.py` — STT, embeddings, zero-shot, VLM | — |
| Pollinations + TikTok video pipeline | ✅ Live | ComfyUI-free pipeline | — |

### Infrastruktur

| Komponent | Status | Noter |
|---|---|---|
| GPU-backed local Ollama | ✅ Live | LXC container på Proxmox, GTX 1070 passthrough, 10.0.0.25 |
| HE tunnelbroker (IPv6 via CGNAT) | ✅ Live | Verificeret 2026-04-21 |
| Pre-commit secret-scanning | ✅ Live | `detect-secrets` med baseline |
| Kill-switch + resource guards | ✅ Live | 4GB RAM, 200% CPU cap |
| Capability audit (scripts/capability_audit.py) | ✅ Live | Genererer `capability_matrix.md` |

## Aktive bugs / åbent arbejde

| Issue | Fil | Status |
|---|---|---|
| **17/20 daemons producerer `generated:False`** — somatisk, thought_stream, reflection_cycle m.fl. er tavse | `TASK_daemon_fix.md` | **ACTION — aktiv bug** |
| **`dream_insight` daemon er wired men har aldrig kørt** | Samme fil | **ACTION — aktiv bug** |
| **Tool result externalization** — session DOM vokser med 50-200KB inline tool output, browser bliver langsom | `CODEX_TASK_tool_result_externalization.md` | **ACTION — design klar, ikke implementeret** |
| **Discord bot token leaked** i historisk plan-doc (redactet 2026-04-21) | — | **ACTION — roter token i Discord Developer Portal** |

## Aktive forbedringer

| Område | Status |
|---|---|
| Webchat composer redesign (Claude Code-stil) | Designet, ikke fuldt implementeret |
| Mail auto-respond bliver mere nuanceret end kun acknowledgment | Parkeret indtil initiative-queue-hook er klar |
| Mission Control — flere tabs til propriocetion-daemons | 5 tabs lagt ud 2026-04-20 |

## Docs-huller (capabilities uden dedikeret dokumentation)

Prioriteret rækkefølge for at lukke huller:
1. **PROMPT_ARCHITECTURE.md** — prompt-build, identity-injection, lane-distinction
2. **MEMORY_SYSTEM.md** — lag (daily/weekly/monthly), fade curves, promotion
3. **AGENTS_AND_COUNCIL.md** — spawning, roller, deliberation
4. **API_REFERENCE.md** — MC endpoints
5. **COST_ACCOUNTING.md** — model
6. **TESTING_STRATEGY.md** — coverage-map
7. **SECURITY_POSTURE.md** — posture
8. **DEBUGGING_GUIDE.md** — runbook

Disse skrives efterhånden. Ingen presser. Se `docs/README.md` for nuværende status.

## Kommende overvejelser

- **Cross-channel session unification** — samme samtale fortsat fra webchat til Discord
- **Voice session merge med webchat** — optaget stemme som input til aktiv session
- **Initiative queue escalation fra mail_checker** — når auto-reply ikke er nok
- **Blødgør mail-auto-respond** — lov simple aftaler-bekræftelser, ikke kun acks
- **Multi-model consensus UI** — vis council-deliberation i realtid

Ingen af disse er approved/planlagt. Noter for næste gang der skal prioriteres.
