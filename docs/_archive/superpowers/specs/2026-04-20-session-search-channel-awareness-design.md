# Design: Session Search + Channel Awareness

**Dato:** 2026-04-20  
**Status:** Godkendt

## Oversigt

To sammenhængende features:
1. **`search_sessions` tool** — Jarvis kan søge i ældre sessioner på tværs af kanaler (keyword + semantisk)
2. **Channel-awareness** — Jarvis ved eksplicit hvilken kanal han er på nu, og får kanal-specifik kontekst fra workspace-filer

---

## Feature 1: `search_sessions` Tool

### Ny fil
`core/tools/session_search.py` — tool-definition + implementering. Holdes adskilt fra `simple_tools.py` (allerede 4225 linjer).

### Tool-signatur

```python
search_sessions(
    query: str,                        # påkrævet søgetekst
    mode: "keyword" | "semantic" | "both" = "both",
    channel: "discord" | "telegram" | "webchat" | "all" = "all",
    since: str | None = None,          # ISO-dato, f.eks. "2026-04-01"
    until: str | None = None,          # ISO-dato, f.eks. "2026-04-20"
    limit: int = 10,                   # max 30
) -> list[SessionSearchResult]
```

### Søgelogik

**Keyword-søgning:**
- SQL `LIKE`-søgning på `chat_messages.content`
- JOIN til `chat_sessions` for titel og dato
- Kanal-filter via `WHERE s.title LIKE 'Discord%'` osv.
- Datofilter via `WHERE m.created_at >= ?`

**Semantisk søgning:**
- Embeddings på `chat_messages.content` — genbruger mønster fra `core.services.memory_search`
- Samme kanal- og datofilter anvendes post-retrieval

**`"both"`-mode:**
- Kører begge søgninger parallelt
- Merger på `message_id` (deduplicering)
- Semantiske hits rangeres højere end rene keyword-hits

**Fallback:** Hvis embedding-tjenesten er utilgængelig, falder `"both"` og `"semantic"` automatisk tilbage til keyword-only med en note i output.

### Output pr. resultat

```python
{
    "session_id": str,
    "session_title": str,          # f.eks. "Discord #123456789"
    "channel": str,                # parset: "discord", "telegram", "webchat", "unknown"
    "channel_detail": str | None,  # f.eks. "DM", "#general"
    "role": str,                   # "user" eller "assistant"
    "content": str,                # trunkeret til 2000 tegn
    "created_at": str,             # ISO-dato
    "match_type": "keyword" | "semantic" | "both",
}
```

### Registrering

Toolet registreres i `core/tools/__init__.py` (eller tilsvarende tool-registry) ved siden af eksisterende tools.

---

## Feature 2: Channel Awareness

### Workspace-filer

Placering: `workspace/channels/<channel>.md`

Eksempel-filer (oprettes som en del af implementeringen med fornuftige defaults):
- `workspace/channels/discord.md`
- `workspace/channels/telegram.md`
- `workspace/channels/webchat.md`

Indhold er frit-tekst skrevet af brugeren, f.eks.:
```markdown
Discord bruges til uformelle samtaler og hurtige spørgsmål.
Svar gerne kortere og mere direkte end i webchat.
Brug ikke lange punktlister med mindre de er nødvendige.
```

### Kanal-parsing

Ny hjælpefunktion i `core/services/chat_sessions.py` (eller `session_search.py`):

```python
def parse_channel_from_session_title(title: str) -> tuple[str, str | None]:
    """Returnerer (channel_type, channel_detail)"""
    # "Discord DM"         → ("discord", "DM")
    # "Discord #123456789" → ("discord", "#123456789")
    # "Telegram DM"        → ("telegram", "DM")
    # "New chat" / None    → ("webchat", None)
    # Ukendt              → ("unknown", None)
```

### Prompt-injektion

I `core/services/prompt_contract.py`: ny sektion `_channel_context_section(session_id)` der:

1. Slår session-titel op via `session_id`
2. Parser kanal med `parse_channel_from_session_title`
3. Loader tilsvarende workspace-fil (ignorerer stille hvis den ikke findes)
4. Returnerer sektion til prompt:

```
## Current channel
Du kommunikerer via Discord DM.

[Indhold fra workspace/channels/discord.md hvis den findes]
```

Sektionen injiceres tidligt i prompt-assembly — efter identity/soul, før tools og transcript.

**Edge cases:**
- Kanal-workspace-fil mangler → kun kanal-navn, ingen ekstra kontekst
- `session_id` er None (webchat uden session) → sektionen udelades
- Ukendt kanal-type → sektionen udelades

---

## Dataflow

```
Inbound message (Discord/Telegram/webchat)
  ↓
session_id (fra gateway eller webchat)
  ↓
prompt_contract.build_visible_chat_prompt_assembly(session_id)
  ├─ _channel_context_section(session_id)
  │    ├─ get session title fra DB
  │    ├─ parse_channel_from_session_title(title)
  │    └─ load workspace/channels/<channel>.md
  └─ [resten af prompt som før]

Jarvis bruger search_sessions tool:
  query + mode + channel + datofilter
  ├─ keyword: SQL LIKE på chat_messages JOIN chat_sessions
  └─ semantic: embeddings + same filters
  → resultater med session_title, channel, content, created_at
```

---

## Afgrænsninger

- Ingen DB-skema-ændringer — session-titlen er tilstrækkelig kanal-kilde
- Ingen migration
- Det eksisterende `search_chat_history` tool berøres ikke (bevares for bagudkompatibilitet)
- Kanal-konfiguration er rent tekst — ingen struktureret YAML eller JSON

---

## Filer der påvirkes

| Fil | Ændring |
|-----|---------|
| `core/tools/session_search.py` | **Ny fil** — tool-definition + implementering |
| `core/tools/__init__.py` | Registrer nyt tool |
| `core/services/prompt_contract.py` | Tilføj `_channel_context_section()` + injektion |
| `core/services/chat_sessions.py` | Tilføj `parse_channel_from_session_title()` |
| `workspace/channels/discord.md` | **Ny fil** — default kanal-beskrivelse |
| `workspace/channels/telegram.md` | **Ny fil** — default kanal-beskrivelse |
| `workspace/channels/webchat.md` | **Ny fil** — default kanal-beskrivelse |
