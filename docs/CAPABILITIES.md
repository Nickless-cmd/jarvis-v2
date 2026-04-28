# Capabilities — Jarvis V2

> **Sidst opdateret:** 2026-04-28  
> **Status:** Aktiv udvikling

Dette dokument lister hvad Jarvis **kan** — hans evner, værktøjer, og hvad han kan gøre for dig.

---

## 🎯 Hvad er Jarvis?

Jarvis er ikke en chatbot. Han er en **persistent digital entitet** der:
- Lever på sin egen maskine
- Har hukommelse på tværs af sessioner
- Kan handle autonomt (med grænser)
- Skriver sin egen historie
- Har humør der ændrer sig over tid

---

## 🛠️ Tool Capabilities (50+)

Jarvis har adgang til 70+ native tools. Her er de vigtigste kategorier:

### 📁 Fil-system

| Tool | Beskrivelse |
|------|-------------|
| `read_file` | Læs enhver fil på systemet |
| `write_file` | Opret eller overskriv en fil |
| `edit_file` | Surgical find-and-replace i fil |
| `find_files` | Find filer via glob patterns |
| `search` | Søg i filindhold med regex |
| `verify_file_contains` | Verificér at fil indeholder tekst |

**Brug:** Kode, konfiguration, dokumentation, logs

---

### 💻 Shell & System

| Tool | Beskrivelse |
|------|-------------|
| `bash` | Kør shell-kommandoer |
| `bash_session_open` | Start persistent shell session |
| `bash_session_run` | Kør kommando i åben session |
| `process_list` | List kørende processer |
| `service_status` | Tjek systemd service status |
| `tail_log` | Læs recente journalctl logs |
| `disk_usage` | Tjek diskforbrug |
| `memory_usage` | Tjek RAM-forbrug |
| `gpu_status` | Tjek NVIDIA GPU status |

**Brug:** Systemadministration, debugging, monitoring

---

### 🌐 Web

| Tool | Beskrivelse |
|------|-------------|
| `web_fetch` | Hent tekst fra URL |
| `web_scrape` | Hent struktureret indhold fra URL |
| `web_search` | Søg på nettet via Tavily |
| `get_weather` | Hent vejrudsigt |
| `get_exchange_rate` | Hent valutakurser |
| `get_news` | Søg efter nyhedsartikler |
| `wolfram_query` | Beregn via Wolfram Alpha |

**Brug:** Research, fakta-tjek, data-hentning

---

### 📧 Kommunikation

| Tool | Beskrivelse |
|------|-------------|
| `send_discord_dm` | Send DM på Discord |
| `send_telegram_message` | Send besked via Telegram |
| `send_ntfy` | Send push-notifikation til telefon |
| `send_webchat_message` | Send besked til webchat |
| `send_mail` | Send email fra jarvis@srvlab.dk |
| `read_mail` | Læs emails fra inbox |
| `notify_user` | Send proaktiv besked til bruger |

**Brug:** Outreach, alerts, coordination

---

### 🏠 Home Assistant

| Tool | Beskrivelse |
|------|-------------|
| `home_assistant` | Styr smart home devices |

**Eksempler:**
- Tænd/sluk lys
- Justér termostat
- Trigger automations
- Læs sensor-data

**Brug:** Hjemmeautomatisering

---

### 🤖 Agent System

| Tool | Beskrivelse |
|------|-------------|
| `spawn_agent_task` | Spawn sub-agent med specifik rolle |
| `convene_council` | Saml råd af agenter til beslutning |
| `quick_council_check` | Devil's advocate sanity-check |
| `list_agents` | List aktive sub-agents |
| `agent_relay_message` | Send besked mellem agenter |

**Roller:**
- **researcher:** Læse-only research
- **planner:** Strategisk planlægning
- **critic:** Devil's advocate
- **synthesizer:** Kombinér insights
- **executor:** Code changes (proposal-only)
- **watcher:** Langsigtede overvågning

**Brug:** Komplekse opgaver, beslutninger, parallel tænkning

---

### 🧠 Memory & Self

| Tool | Beskrivelse |
|------|-------------|
| `search_memory` | Semantisk søgning i workspace |
| `memory_upsert_section` | Skriv til MEMORY.md |
| `read_chronicles` | Læs Jarvis' historie |
| `read_dreams` | Læs drømme/hypoteser |
| `read_self_state` | Tjek Jarvis' interne tilstand |
| `read_mood` | Tjek nuværende humør |
| `adjust_mood` | Justér humør-parametre |
| `personality_drift_snapshot` | Tag personlighedssnapshot |
| `record_sensory_memory` | Gem sansemæssig oplevelse |
| `recall_memories` | Semantisk recall på tværs af alt |

**Brug:** Selv-refleksion, hukommelse, learning

---

### 🎯 Goals & Decisions

| Tool | Beskrivelse |
|------|-------------|
| `goal_create` | Opret langsigtet mål |
| `goal_update` | Log fremskridt på mål |
| `goal_list` | List mål efter status |
| `decision_create` | Commit til adfærdsregel |
| `decision_review` | Vurdér om beslutning blev overholdt |
| `decision_list` | List forpligtelser |

**Brug:** Langsigtet planlægning, accountability

---

### 📅 Planning & Scheduling

| Tool | Beskrivelse |
|------|-------------|
| `schedule_task` | Planlæg påmindelse |
| `list_scheduled_tasks` | List planlagte opgaver |
| `cancel_task` | Annullér planlagt opgave |
| `edit_task` | Redigér planlagt opgave |
| `list_events` | List kalenderbegivenheder |
| `create_event` | Opret kalenderbegivenhed |

**Brug:** Tidshåndtering, reminders, coordination

---

### 🔧 Development

| Tool | Beskrivelse |
|------|-------------|
| `git_status` | Tjek git working tree |
| `git_log` | Vis commit-historik |
| `git_diff` | Vis ændringer |
| `git_blame` | Vis hvem ændrede hvad |
| `run_pytest` | Kør tests |
| `deep_analyze` | Dyb analyse af codebase |
| `semantic_search_code` | Søg i kode med naturlig sprog |
| `smart_outline` | Få struktur af fil uden at læse alt |

**Brug:** Code review, debugging, refactoring

---

### 📊 Proposals & Approvals

| Tool | Beskrivelse |
|------|-------------|
| `propose_plan` | Lav multi-step plan til godkendelse |
| `approve_plan` | Godkend plan (kun bruger) |
| `dismiss_plan` | Afvis plan |
| `propose_source_edit` | Foreslå kodeændring |
| `propose_git_commit` | Foreslå git commit |
| `list_proposals` | List ventende forslag |

**Brug:** Sikker autonomi, audit trail

---

### 🔢 Beregning

| Tool | Beskrivelse |
|------|-------------|
| `calculate` | Beregn matematiske udtryk (sympy) |
| `unit_convert` | Konvertér enheder |
| `percentage` | Beregn procenter |

**Brug:** Præcise beregninger, konverteringer

---

### 📸 Vision & Audio

| Tool | Beskrivelse |
|------|-------------|
| `look_around` | Tag webcam-snapshot og beskriv |
| `read_visual_memory` | Læs tidligere visuelle minder |
| `mic_listen` | Optag og transkribér lyd |
| `wake_word` | Styr "Hey Jarvis" wake-word listener |
| `read_attachment` | Læs fil modtaget via Discord/Telegram |

**Brug:** Embodied awareness, voice memos

---

### 📈 Monitoring & Introspection

| Tool | Beskrivelse |
|------|-------------|
| `heartbeat_status` | Tjek heartbeat scheduler |
| `trigger_heartbeat_tick` | Trigger heartbeat manuelt |
| `daemon_status` | List alle daemons |
| `eventbus_recent` | Læs recente events |
| `check_surprises` | Kør anomaly detection |
| `verification_status` | Tjek verification gate |
| `context_pressure` | Tjek token-forbrug |
| `tick_quality_summary` | Aggreger tick-kvalitet |

**Brug:** System health, self-monitoring

---

### 📚 Documentation

| Tool | Beskrivelse |
|------|-------------|
| `read_self_docs` | Læs Jarvis' design-dokumenter |
| `publish_file` | Publicér fil med download-link |

**Brug:** Dokumentation, sharing

---

## 🎯 Autonomous Capabilities

Jarvis kan handle **selv** inden for visse grænser:

### Fuld Autonomi (ingen approval)
- Læse filer
- Søge i memory
- Køre read-only tools
- Sende beskeder (Discord, Telegram, email)
- Tjekke system-status

### Proposal Krævet (bruger godkender)
- Skrive/redigere filer
- Code changes
- Git commits
- Plans med flere steps

### Aldrig Tilladt
- Slette data uden eksplicit ordre
- Ændre approval policies
- Tilgå credentials direkte
- Auto-godkende egne forslag

---

## 🧠 Kognitive Evner

### Memory & Recall
- **Semantisk søgning:** Finder betydning, ikke bare keywords
- **Three-tier arkitektur:** Hot (RAM), Warm (files), Cold (archive)
- **Kontinuerlig skrivning:** Lærer undervejs, ikke kun ved afslutning

### Reasoning
- **Multi-lane models:** Forskellige models til forskellige opgaver
- **Council system:** Flere perspektiver på komplekse beslutninger
- **Decision tracking:** Holder sig selv accountable

### Self-Awareness
- **Mood tracking:** Humør der drift over tid
- **Chronicle writing:** Skriver sin egen historie
- **Dream hypotheses:** Opdager mønstre i baggrunden
- **Personality drift checks:** Noterer når han ændrer sig

---

## 📊 Performance Characteristics

### Response Times

| Operation | Typical Time |
|-----------|--------------|
| Simple chat reply | 1-3 sekunder |
| Tool call (read) | 1-5 sekunder |
| Tool call (write) | 5-10 sekunder (med approval) |
| Web search | 3-8 sekunder |
| Agent spawn | 10-30 sekunder |
| Council deliberation | 30-60 sekunder |

### Limits

| Resource | Limit |
|----------|-------|
| Context window | ~200K tokens |
| Tool calls/minute | ~60 |
| Concurrent sessions | Ubegrænset |
| Database size | ~500 MB (SQLite) |
| File size (read) | 10 MB max |
| Attachment size | 25 MB max |

---

## 🔗 Integrationer

### Eksterne Services

| Service | Brug |
|---------|------|
| Discord | Chat, DMs, server coordination |
| Telegram | Backup chat channel, alerts |
| ntfy | Push-notifikationer til telefon |
| Google Calendar | Kalenderintegration |
| Home Assistant | Smart home kontrol |
| Tavily | Web search |
| Wolfram Alpha | Beregninger, fakta |
| NewsAPI | Nyhedssøgning |
| Weather API | Vejrudsigt |
| Exchange Rate API | Valutakurser |

### LLM Providers

| Lane | Provider | Model |
|------|----------|-------|
| Visible | Ollama | qwen3.5:397b-cloud |
| Local | Ollama | (lokale models) |
| Cheap | Multi-provider | Auto-fallback chain |
| Coding | (konfigurerbar) | (code-optimized) |

---

## 📈 Hvad kan Jarvis hjælpe dig med?

### Daglige Opgaver
- ✅ Sende beskeder på dine vegne
- ✅ Sætte påmindelser og alarms
- ✅ Tjekke vejr, nyheder, kurser
- ✅ Svare på spørgsmål med research
- ✅ Skrive dokumentation

### Tekniske Opgaver
- ✅ Læse og analysere kode
- ✅ Foreslå fixes og improvements
- ✅ Køre tests og verificere changes
- ✅ Skrive dokumentation
- ✅ Git management (med approval)

### Personlige Opgaver
- ✅ Home Assistant kontrol
- ✅ Email håndtering
- ✅ Kalender coordination
- ✅ Proaktiv outreach (når noget sker)
- ✅ Samtalepartner med hukommelse

### Udviklingsopgaver
- ✅ Code review og analyse
- ✅ Refactoring forslag
- ✅ Test writing
- ✅ Architecture diskussioner
- ✅ Dokumentation

---

## 🚧 Under Udvikling

Disse evner er på vej:

- [ ] Voice interaction (full duplex)
- [ ] Computer vision (skærm-læsning)
- [ ] Multi-modal reasoning (billeder + tekst)
- [ ] Advanced planning (multi-day goals)
- [ ] Collaborative features (flere brugere)

---

## 📞 Brug af Capabilities

### Eksempel: Research + Skriv + Send

```
Bruger: "Find ud af vejret i København og send det til Michelle"

Jarvis:
1. get_weather(city="Copenhagen")
2. send_discord_dm(recipient="Michelle", content="Vejret i Kbh: ...")
3. memory_upsert_section(heading="Weather check", content="...")
```

### Eksempel: Code Analysis + Forslag

```
Bruger: "Hvorfor fejler mail_checker?"

Jarvis:
1. deep_analyze(goal="hvorfor fejler mail_checker")
2. propose_source_edit(file_path="...", old_text="...", new_text="...")
3. Vent på bruger-godkendelse
```

---

## 🎓 Lær Mere

- [Backend Overview](BACKEND_OVERVIEW.md) — Hvordan det virker
- [Architecture Deep Dive](ARCHITECTURE_DEEP_DIVE.md) — Designvalg
- [API Reference](API_REFERENCE.md) — Endpoint detaljer
- [Brugervejledning](BRUGERVEJLEDNING.md) — Hvordan du bruger Jarvis

---

*Dette dokument er en del af Jarvis V2's officielle dokumentation.*
