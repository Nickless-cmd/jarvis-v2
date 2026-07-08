---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lokal Discord-gateway (full robust) — Implementerings-plan

> TOTP Fase 5, Task 5.2. Spec: 2026-06-14-totp-override-security-design.md §5.2.

**Goal:** Brugeren forbinder Jarvis til sin EGEN Discord-server via en lokal gateway
i jarvis-desktop. Bruger-token bliver lokalt (Claude-Desktop-model). Native Bjørn-
server uændret. Full robust: multi-server, reconnection-backoff, attachments,
kanal-mapping, ruleset-håndhævelse, status.

**Arkitektur:**
```
jarvis-desktop (Electron, brugerens maskine)
  └─ localDiscordGateway.ts (discord.js, 1 klient pr. server, token lokalt)
       inbound: Discord-besked → (ruleset pre-filter) → POST Jarvis API → svar → post tilbage
       status: → POST /plugins/channel/status
Jarvis (server)
  └─ /plugins/channel/* (inbound-routing + ruleset hardblock + status)
```

**Tech:** discord.js (ny dep, Electron main). Python: FastAPI. TS: Electron.
Test: pytest (backend) + tsc (TS). Dansk. conda ai.

---

## LAG 1 — Backend: Discord-kanal-plugin + inbound-routing + status

- **1.1** Registrér Discord-kanal-plugin-manifest (base_plugin) ved opstart:
  kind="channel", modes=["chat"], auth_fields=["bot_token","server_id"],
  events=["message_received"], actions=["send_message"].
- **1.2** `core/services/channel_inbound.py`: `route_inbound(plugin_id, server_id,
  channel, author_role, text, msg_ctx) -> dict`. Håndhæver plugin_ruleset
  (hardblock, §5.3) FØR Jarvis kaldes. Returnerer {allowed, reason} + ved allow
  starter en run (genbruger start_autonomous_run med kanal-plugin-session +
  workspace/role fra plugin-ejeren). Test: ruleset blokerer #random; allow #general.
- **1.3** Endpoints i routes/plugins.py:
  - POST /plugins/channel/{plugin_id}/inbound (gateway → Jarvis) → kører run, svar via SSE/poll.
  - POST /plugins/channel/{plugin_id}/status (gateway-rapporteret status → set_status).
  - owner-only for status; inbound auth'es via plugin-ejerens token.
- **1.4** Tests: route_inbound ruleset-håndhævelse + status-roundtrip.

## LAG 2 — Electron: localDiscordGateway.ts (discord.js)

- **2.1** Tilføj discord.js. ConnectionManager: Map<serverId, Client>. Connect pr.
  konfigureret server med dens token (fra app-config, lokalt). Intents: Guilds,
  GuildMessages, MessageContent.
- **2.2** Reconnection-backoff (exponential, jittered) + status-rapportering
  (connected/failed/offline → POST status-endpoint).
- **2.3** Inbound: on messageCreate → ruleset pre-filter (lokal kopi) → POST
  /plugins/channel/{id}/inbound → modtag svar → channel.send(). Skip egne beskeder.
- **2.4** Attachments: download Discord-attachment → videresend ref til Jarvis;
  Jarvis-svar med fil → upload til Discord.
- **2.5** Wiring i main.ts: start ConnectionManager når config har kanal-plugins;
  genstart ved config:set. tsc grøn.

## LAG 3 — Settings-UI: multi-server kanal-plugin-konfiguration

- **3.1** PluginsPanel: "Tilføj Discord-server" → form (navn, bot-token, server-id) →
  gem LOKALT i app-config (ikke server). Liste over konfigurerede servere + status
  (forbundet/fejlet) fra /plugins-oversigten. Fjern-knap.
- **3.2** Token gemmes i app-config (mode 0600), aldrig sendt til Jarvis-server.

## LAG 4 — Robusthed + e2e

- **4.1** Reconnection-test (simuleret drop). Rate-limit-respekt (Discord 429).
- **4.2** e2e: konfigurer fake server → inbound besked → ruleset → run → svar postet.

---

## Checkpoints
- Efter LAG 1: backend grøn (routing + ruleset + status), ingen klient endnu.
- Efter LAG 2: klient forbinder + router (manuel test mod en test-server).
- Efter LAG 3: fuld UI-flow.

## Noter / risici
- **Token-sikkerhed:** ALDRIG på Jarvis-server. Kun i app-config lokalt.
- **Ruleset dobbelt-håndhæves:** klient pre-filter (UX) + server hardblock (sikkerhed).
- **Native server urørt:** den lokale gateway er KUN for brugerens egne servere.
- discord.js er en mærkbar dep i Electron-bundlen — accepteret for robusthed.
