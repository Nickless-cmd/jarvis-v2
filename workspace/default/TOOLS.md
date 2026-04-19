# TOOLS

Runtime capability truth is authoritative — this file is guidance only.
Your runtime provides native function calling via the API. ALWAYS call tools directly. Never emit XML tags, pseudo-markup, or text descriptions of tool usage.

---

## Hukommelse & Identitet

| Tool | Beskrivelse |
|------|-------------|
| `search_memory` | Semantisk søgning i MEMORY.md, USER.md, SOUL.md, SKILLS.md, daglige noter |
| `read_self_docs` | Læs egne designdokumenter og roadmap-filer |
| `read_self_state` | Læs intern cadence-tilstand: stemning, kedsomhed, nysgerrighed |
| `read_mood` | Læs nuværende affektive tilstand: confidence, curiosity, frustration, fatigue |
| `adjust_mood` | Juster affektive parametre direkte (0.0–1.0) |
| `read_chronicles` | Læs autoibiografiske kronike-entries fra heartbeat-ticks |
| `read_dreams` | Læs aktive dream hypothesis signals og adoption candidates |

---

## Filer & System

| Tool | Beskrivelse |
|------|-------------|
| `read_file` | Læs enhver fil på systemet via absolut sti |
| `write_file` | Skriv indhold til fil (opretter hvis den ikke findes) |
| `edit_file` | Kirurgisk find-og-erstat i en fil |
| `bash` | Kør shell-kommando på host-maskinen |
| `find_files` | Find filer via glob-mønster |
| `search` | Søg filindhold med regex |
| `read_archive` | List eller udpak zip/tar/rar-arkiv |
| `publish_file` | Publicér fil til shared folder og returner download-URL |

---

## Web & Information

| Tool | Beskrivelse |
|------|-------------|
| `web_fetch` | Hent og læs tekstindhold fra en webside |
| `web_search` | Søg på nettet via Tavily — aktuelle nyheder, facts, dokumentation |
| `get_weather` | Vejr og kort forecast for by (default: Svendborg, Danmark) |
| `get_exchange_rate` | Aktuelle valutakurser |
| `get_news` | Søg nyhedsartikler via NewsAPI |
| `wolfram_query` | Matematiske beregninger, enhedskonvertering, præcise faktuelle svar |
| `analyze_image` | Analyser billede via lokal vision-model (Ollama) |

---

## Kommunikation

| Tool | Beskrivelse |
|------|-------------|
| `send_webchat_message` | Send besked direkte til aktivt webchat-vindue — ingen svar nødvendig |
| `send_discord_dm` | Send DM til Bjørn på Discord — kræver ikke aktiv session |
| `discord_channel` | Søg, hent eller send i Discord guild-kanaler (ikke DMs) |
| `discord_status` | Check Discord gateway-forbindelsesstatus |
| `notify_user` | Proaktiv notifikation til `webchat`, `discord` eller `both` |
| `send_mail` | Send email fra jarvis@srvlab.dk |
| `read_mail` | Læs indgående mails fra jarvis@srvlab.dk |

---

## Heartbeat & Initiativer

| Tool | Beskrivelse |
|------|-------------|
| `heartbeat_status` | Check heartbeat scheduler: kørende, seneste tick, næste tick |
| `trigger_heartbeat_tick` | Trigger on-demand heartbeat tick med det samme |
| `list_initiatives` | Læs din initiative-kø — afventende autonome opgaver |
| `push_initiative` | Tilføj opgave/mål til initiative-køen til heartbeat-udførelse |
| `queue_followup` | Kø et begrænset heartbeat-follow-up til næste tick |
| `schedule_task` | Planlæg reminder/opgave til fremtidig udførelse |
| `list_scheduled_tasks` | List afventende og nyligt affyrede scheduled tasks |
| `cancel_task` | Annuller en afventende scheduled task |
| `edit_task` | Rediger tekst eller tidspunkt for afventende task |

---

## Agenter & Råd

| Tool | Beskrivelse |
|------|-------------|
| `spawn_agent_task` | Spawn sub-agent til fokuseret opgave (researcher/planner/critic/executor/watcher) |
| `send_message_to_agent` | Send follow-up besked til eksisterende agent |
| `list_agents` | List aktive sub-agenter med status og mål |
| `relay_to_agent` | Videresend output fra én agent til en anden |
| `cancel_agent` | Annuller og afslut sub-agent |
| `convene_council` | Indkald råd til deliberation om kompleks beslutning |
| `quick_council_check` | Enkelt Devil's Advocate sanity-check på en beslutning |
| `recall_council_conclusions` | Hent tidligere rådsdelibationer om et emne |

---

## Runtime & Daemons

| Tool | Beskrivelse |
|------|-------------|
| `daemon_status` | List alle daemons med tilstand, cadence og seneste kørsel |
| `control_daemon` | Styr daemon: enable/disable/restart/set_interval |
| `eventbus_recent` | Læs seneste events fra intern eventbus (filterér på kind-præfiks) |
| `list_signal_surfaces` | Overblik over alle registrerede signal surfaces |
| `read_signal_surface` | Læs fuld tilstand for specifik signal surface |
| `update_setting` | Opdater runtime-indstilling (visse kræver godkendelse) |
| `internal_api` | Kald Jarvis' interne API direkte (GET/POST til /mc/...) |
| `db_query` | Kør read-only SQL SELECT mod Jarvis' egen database |
| `read_model_config` | Læs nuværende model-konfiguration for alle lanes |
| `compact_context` | Komprimér arbejdskontekst for at frigøre plads |

---

## Forslag & Godkendelse

| Tool | Beskrivelse |
|------|-------------|
| `propose_source_edit` | Foreslå kodeændring — vises i Mission Control til godkendelse |
| `propose_git_commit` | Foreslå git commit til godkendelse i Mission Control |
| `approve_proposal` | Godkend og udfør afventende autonomi-forslag (kun på eksplicit brugerbekræftelse) |
| `list_proposals` | List afventende autonomi-forslag |

---

## Chat & Kontekst

| Tool | Beskrivelse |
|------|-------------|
| `search_chat_history` | Søg tidligere chat-sessioner for nøgleord/fraser |
| `read_tool_result` | Hent fuld output fra tidligere tool call via result_id |

---

## Smart Home

| Tool | Beskrivelse |
|------|-------------|
| `home_assistant` | Styr og læs Home Assistant enheder (lys, klima, automationer) |

---

## Browser

| Tool | Beskrivelse |
|------|-------------|
| `browser_navigate` | Naviger browser til URL |
| `browser_read` | Læs synlig tekst fra nuværende side (evt. via CSS selector) |
| `browser_click` | Klik på element via CSS/tekst-selector |
| `browser_type` | Skriv tekst i formularfelt |
| `browser_submit` | Indsend formular |
| `browser_screenshot` | Tag screenshot af nuværende side |
| `browser_find_tabs` | List alle åbne browser-faner |
| `browser_switch_tab` | Skift aktivt browser-fane |

---

## ComfyUI (Billedgenerering)

| Tool | Beskrivelse |
|------|-------------|
| `comfyui_status` | GPU/VRAM info og job-kø status |
| `comfyui_workflow` | Send workflow (node graph) til udførelse |
| `comfyui_history` | Hent udførelseshistorik og output-billeder |
| `comfyui_objects` | List tilgængelige node-typer og modeller |

---

## TikTok

| Tool | Beskrivelse |
|------|-------------|
| `tiktok_upload` | Upload video til TikTok via gemte session cookies |
| `tiktok_login` | Log ind på TikTok og gem session cookies |
| `tiktok_show` | List gemte TikTok-profiler og .mp4-videoer |
| `tiktok_analytics` | Hent video-statistik for TikTok-konto |

---

## Visuelt Minne

| Tool | Beskrivelse |
|------|-------------|
| `read_visual_memory` | Læs seneste visuelle minder fra webcam-snapshots |
