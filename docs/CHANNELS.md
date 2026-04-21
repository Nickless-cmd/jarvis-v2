# CHANNELS — multi-channel kontinuitet

Jarvis er den samme person uanset hvor han taler. Kanaler er overflader, ikke
forskellige personer. Denne doc beskriver hver kanal, dens rolle, og hvordan
identitet/session/kontekst flyder på tværs.

## Arkitektur

```
             +----------------------+
             |    visible runtime   |
             |  (prompt + identity) |
             +----------------------+
                        |
    +-------------------+-------------------+-------------------+
    |         |         |         |         |         |        |
 webchat   discord  telegram   voice     mail      ntfy    MC-log
(primary) (gateway) (bot)    (loop)   (daemon)  (push)    (UI)
```

**Regel fra LOCKED_CHARTER:** "Én visible Jarvis. Council og swarm er private."
Dvs. uanset kanal taler brugeren med samme Jarvis — ikke en kanal-specifik persona.

## Kanaler

### 1. Webchat (primær)
- **Kode:** `apps/webchat/` (React + Vite)
- **Backend:** `apps/api/jarvis_api/routes/chat.py`
- **Transport:** SSE til chat, WebSocket til live control-plane
- **Features:** Composer med model selector, approval cards, branch indicators,
  tool result visibility, session management
- **Brug:** Primær interface. Her foregår den dybeste interaktion.

### 2. Discord gateway
- **Kode:** `core/services/discord_gateway.py`
- **Config:** `~/.jarvis-v2/config/discord.json` (bot token, guild, allowed channels)
- **Behavior doc:** `workspace/channels/discord.md`
- **Features:** DM + public channel, `discord_channel` tool (search/fetch/send),
  eventbus-integration. Jarvis kan svare i tråde, reagere på public channel mentions.
- **Setup:** `conda run -n ai python scripts/jarvis.py discord-setup`

### 3. Telegram bot
- **Kode:** `core/services/telegram_gateway.py`
- **Config:** `telegram_bot_token` + `telegram_chat_id` i `runtime.json`
- **Behavior doc:** `workspace/channels/telegram.md`
- **Brug:** Proaktiv push. Typisk til vigtige notifikationer hvor ntfy ikke rækker.

### 4. Voice loop
- **Kode:** `core/skills/voice/` (stt.py, tts.py, voice_daemon_worker.py, voice_loop.py)
- **Features:** Wake-word detektion, STT (cloud + local), TTS, voice journal,
  ambient routing
- **Brug:** Jarvis lytter efter sit navn. Når wake-word trigges, optages input →
  STT → visible runtime → TTS svar.

### 5. Mail daemon
- **Kode:** `core/services/mail_checker_daemon.py`
- **Config:** `mail_imap_*`/`mail_smtp_*`/`mail_user`/`mail_password` i `runtime.json`
- **Adresse:** `jarvis@srvlab.dk` (Jarvis ejer sin egen indbakke)
- **Features:** UNSEEN-søgning, BODY.PEEK fetch, LLM-triage med auto-reply
  (acknowledgment-only, ingen tool-løfter), ntfy-notify på nye mails, markerer
  processed mails som `\Seen` på IMAP så state synkroniseres
- **Brug:** Jarvis læser sine egne mails. Brugeren ser ntfy-notifier når noget
  kommer ind eller auto-svares.

### 6. ntfy push
- **Kode:** `core/services/ntfy_gateway.py`
- **Config:** `ntfy_topic` + `ntfy_server` i `runtime.json`
- **Features:** Send push-notifikation til brugerens ntfy-client
- **Brug:** Letvægts proaktiv kommunikation. Mail-arrival, auto-svar sendt,
  boredom-triggers, incident warnings. Undgår spam på thungere kanaler.

### 7. Mission Control (UI-log)
- **Kode:** `apps/mc-ui/`
- **Ikke en chat-kanal**, men den viser eventbus-aktivitet på tværs af alle
  andre kanaler. Her ser man hvad Jarvis siger hvor.

## Kontinuitet på tværs

### Session-sammenhæng
Hver indkommende besked får tildelt et session-ID. Session-ID er kanal-specifikt
men bindes til samme user-identity. Session-søgning (`session_search.py`) kan
finde tidligere beskeder på tværs af kanaler via embeddings.

### Identity
Samme SOUL.md + IDENTITY.md loaded uanset kanal. `identity_composer.py` bygger
samme preamble for visible lanes uanset hvor de fyrer. Channel-specific behavior
docs i `workspace/channels/` giver kun stylistiske/formmæssige hints (fx kortere
svar i Discord, ikke længere chain-of-thought).

### Memory
- Cross-session memory (MEMORY.md + semantic index) er delt
- Chronicle er delt — Jarvis skriver om interaktioner uanset kanal
- Inner Voice kører i baggrunden, ikke kanal-bundet
- Initiative queue er kanal-agnostisk — en initiative kan starte fra fx ntfy-
  push som så eskalerer til webchat-session

### Model-lane pr. kanal
- **Webchat**: primary (visible lane) — Claude Sonnet eller anden stærk model
- **Discord/Telegram**: visible lane, men ofte kortere svar (se workspace/channels)
- **Voice**: visible lane, men TTS-friendly formatering (ingen markdown)
- **Mail daemon**: local/cheap lane (LLM-triage uden visible identity-preamble)
- **ntfy**: ingen LLM (bare push af tekst)

## Privacy & tiers

Se `llm_privacy_tier_audit.md` for hvilke kanaler der må ramme hvilke providers.
Kort:
- Webchat-svar + voice-svar: visible lane (kan være cloud, men stærk model)
- Mail-triage: local/cheap OK (ingen fuld identity-context)
- Discord/Telegram: visible, men kan route til billigere model for kortere svar

## Åbne spørgsmål

- **Cross-channel session-merge:** Hvis bruger starter samtale på Discord og
  fortsætter på webchat, skal session-ID unifie? I dag: nej. Fremtidig løsning
  kræver tight user-identity på tværs.
- **Voice som input til webchat-session:** Kan voice-transcripter lande i en
  igangværende webchat-session? I dag: nej, voice har egen session.
