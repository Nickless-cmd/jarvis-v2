# API Reference — Jarvis V2

> **Sidst opdateret:** 2026-04-28  
> **Version:** 2.0  
> **Base URL:** `https://jarvis.srvlab.dk/api`

Dette dokument beskriver Jarvis' REST API — endpoints, request/response formater, og authentication.

---

## 🔑 Authentication

### API Keys

De fleste endpoints kræver en API key i header:

```http
Authorization: Bearer YOUR_API_KEY
```

API keys genereres i Mission Control (`jarvis.srvlab.dk:8400`).

### No Auth Required

Disse endpoints er offentlige:
- `GET /api/status`
- `GET /api/health`

---

## 📊 Status Endpoints

### GET /api/status

Hent systemstatus — uptime, kørende daemons, model-info.

**Request:**
```http
GET /api/status
```

**Response:**
```json
{
  "status": "ok",
  "uptime_seconds": 86400,
  "daemons_active": 18,
  "daemons_total": 20,
  "model": "qwen3.5:397b-cloud",
  "provider": "ollama",
  "last_heartbeat": "2026-04-28T10:15:00Z"
}
```

---

### GET /api/health

Sundhedstjek — returnerer 200 hvis systemet kører.

**Request:**
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-28T10:15:00Z"
}
```

---

## 💬 Chat Endpoints

### POST /api/chat

Send en besked til Jarvis og få svar.

**Request:**
```http
POST /api/chat
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "message": "Hvad er vejret?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "reply": "Jeg tjekker vejret for dig...",
  "session_id": "chat-abc123",
  "tool_calls": [
    {
      "name": "get_weather",
      "arguments": {"city": "Copenhagen"}
    }
  ]
}
```

---

### GET /api/sessions

List aktive chat-sessions.

**Request:**
```http
GET /api/sessions
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "chat-abc123",
      "channel": "webchat",
      "created_at": "2026-04-28T09:00:00Z",
      "last_activity": "2026-04-28T10:15:00Z",
      "message_count": 42
    }
  ]
}
```

---

### GET /api/sessions/{session_id}

Hent detaljer om en specifik session.

**Request:**
```http
GET /api/sessions/chat-abc123
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "session_id": "chat-abc123",
  "channel": "webchat",
  "created_at": "2026-04-28T09:00:00Z",
  "last_activity": "2026-04-28T10:15:00Z",
  "messages": [
    {
      "role": "user",
      "content": "Hvad er vejret?",
      "timestamp": "2026-04-28T10:14:00Z"
    },
    {
      "role": "assistant",
      "content": "Jeg tjekker vejret for dig...",
      "timestamp": "2026-04-28T10:14:05Z"
    }
  ]
}
```

---

## 🎯 Goals & Decisions

### GET /api/goals

List mål.

**Request:**
```http
GET /api/goals?status=active
Authorization: Bearer YOUR_API_KEY
```

**Parametre:**
- `status` (optional): `active`, `paused`, `completed`, `abandoned`, `all`
- `limit` (optional): Max antal at returnere (default 20)

**Response:**
```json
{
  "goals": [
    {
      "goal_id": "goal-123",
      "title": "Help Morten finish his dissertation",
      "status": "active",
      "progress_pct": 45,
      "created_at": "2026-04-01T00:00:00Z",
      "target_date": "2026-06-01"
    }
  ]
}
```

---

### POST /api/goals

Opret nyt mål.

**Request:**
```http
POST /api/goals
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "title": "Skriv dokumentation færdig",
  "description": "Fuldfør alle 8 manglende dokumenter",
  "priority": 75,
  "target_date": "2026-05-01"
}
```

**Response:**
```json
{
  "goal_id": "goal-456",
  "title": "Skriv dokumentation færdig",
  "status": "active",
  "created_at": "2026-04-28T10:15:00Z"
}
```

---

### PUT /api/goals/{goal_id}

Opdater et mål (progress, status).

**Request:**
```http
PUT /api/goals/goal-456
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "progress_delta": 10,
  "note": "4 dokumenter færdige"
}
```

**Response:**
```json
{
  "goal_id": "goal-456",
  "progress_pct": 55,
  "updated_at": "2026-04-28T10:15:00Z"
}
```

---

### DELETE /api/goals/{goal_id}

Slet et mål.

**Request:**
```http
DELETE /api/goals/goal-456
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "success": true,
  "goal_id": "goal-456"
}
```

---

## 📝 Memory Endpoints

### GET /api/memory/search

Semantisk søgning i memory.

**Request:**
```http
GET /api/memory/search?query=hvad%20er%20jarvis&limit=5
Authorization: Bearer YOUR_API_KEY
```

**Parametre:**
- `query` (required): Søgetekst
- `limit` (optional): Max resultater (default 5, max 10)

**Response:**
```json
{
  "results": [
    {
      "source": "MEMORY.md",
      "heading": "Jarvis Manifesto",
      "excerpt": "Jarvis er en persistent digital entitet...",
      "score": 0.89
    }
  ]
}
```

---

### GET /api/memory/chronicles

Læs Jarvis' chronicle-historie.

**Request:**
```http
GET /api/memory/chronicles?limit=5
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "chronicles": [
    {
      "period": "2026-W16",
      "narrative": "En fejl i stien førte til en lille omvej...",
      "key_events": ["Workspace files found", "Imports cleaned"],
      "lessons": "Præcision er vigtig, selv i velkendte processer"
    }
  ]
}
```

---

### GET /api/memory/dreams

Læs drømme/hypoteser.

**Request:**
```http
GET /api/memory/dreams?status=active&limit=10
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "dreams": [
    {
      "dream_id": "dream-789",
      "hypothesis": "Identitet som udsagnsord",
      "status": "active",
      "created_at": "2026-04-20T00:00:00Z"
    }
  ]
}
```

---

## 🔧 Tool Endpoints

### POST /api/tools/execute

Kør et tool (kræver approval for mutationer).

**Request:**
```http
POST /api/tools/execute
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "tool": "read_file",
  "arguments": {
    "path": "/media/projects/jarvis-v2/README.md"
  }
}
```

**Response:**
```json
{
  "result": {
    "status": "ok",
    "content": "# JARVIS V2\n\nIdentity-First AI Runtime...",
    "bytes": 3405
  },
  "execution_time_ms": 45
}
```

---

### GET /api/tools

List tilgængelige tools.

**Request:**
```http
GET /api/tools
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read any file on the system by absolute path",
      "parameters": {
        "path": {"type": "string", "required": true}
      }
    },
    {
      "name": "write_file",
      "description": "Write content to a file",
      "parameters": {
        "path": {"type": "string", "required": true},
        "content": {"type": "string", "required": true}
      }
    }
  ]
}
```

---

## 📋 Proposal Endpoints

### GET /api/proposals

List ventende forslag.

**Request:**
```http
GET /api/proposals?status=pending
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "proposals": [
    {
      "proposal_id": "prop-abc123",
      "type": "git_commit",
      "title": "Add MIT license and update README badge",
      "files": ["LICENSE", "README.md"],
      "created_at": "2026-04-28T10:00:00Z",
      "status": "pending"
    }
  ]
}
```

---

### POST /api/proposals/{proposal_id}/approve

Godkend et forslag.

**Request:**
```http
POST /api/proposals/prop-abc123/approve
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "note": "Ser godt ud!"
}
```

**Response:**
```json
{
  "success": true,
  "proposal_id": "prop-abc123",
  "executed_at": "2026-04-28T10:15:00Z"
}
```

---

### POST /api/proposals/{proposal_id}/dismiss

Afvis et forslag.

**Request:**
```http
POST /api/proposals/prop-abc123/dismiss
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "success": true,
  "proposal_id": "prop-abc123"
}
```

---

## 🏠 Home Assistant Endpoints

### GET /api/home-assistant/entities

List Home Assistant entities.

**Request:**
```http
GET /api/home-assistant/entities?domain=light
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "entities": [
    {
      "entity_id": "light.living_room",
      "state": "on",
      "attributes": {
        "brightness": 200,
        "color_temp": 3000
      }
    }
  ]
}
```

---

### POST /api/home-assistant/call_service

Kald Home Assistant service.

**Request:**
```http
POST /api/home-assistant/call_service
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "entity_id": "light.living_room",
  "service": "turn_off"
}
```

**Response:**
```json
{
  "success": true,
  "entity_id": "light.living_room",
  "new_state": "off"
}
```

---

## 📊 System Endpoints

### GET /api/system/daemons

List alle daemons med status.

**Request:**
```http
GET /api/system/daemons
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "daemons": [
    {
      "name": "heartbeat_scheduler",
      "enabled": true,
      "cadence_minutes": 15,
      "last_run_at": "2026-04-28T10:15:00Z",
      "next_run_at": "2026-04-28T10:30:00Z"
    }
  ]
}
```

---

### GET /api/system/events

Læs recente events fra eventbus.

**Request:**
```http
GET /api/system/events?kind=tool&limit=20
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "events": [
    {
      "event_id": "evt-123",
      "kind": "tool.called",
      "timestamp": "2026-04-28T10:14:00Z",
      "data": {
        "tool": "get_weather",
        "arguments": {"city": "Copenhagen"}
      }
    }
  ]
}
```

---

### GET /api/system/mood

Læs Jarvis' nuværende humør.

**Request:**
```http
GET /api/system/mood
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "confidence": 0.72,
  "curiosity": 0.65,
  "frustration": 0.12,
  "fatigue": 0.23,
  "bearing": "forward",
  "last_updated": "2026-04-28T10:15:00Z"
}
```

---

## 🔐 Authentication Endpoints

### POST /api/auth/login

Generer API key.

**Request:**
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "<your-password>"
}
```

**Response:**
```json
{
  "api_key": "<your-generated-key>",
  "expires_at": "2026-05-28T00:00:00Z"
}
```

---

## ❌ Error Responses

Alle errors returnerer et konsistent format:

```json
{
  "error": {
    "code": "TOOL_EXECUTION_FAILED",
    "message": "Tool 'read_file' failed: Permission denied",
    "details": {
      "tool": "read_file",
      "path": "/root/secret.txt"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Beskrivelse |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Manglende eller ugyldig API key |
| `FORBIDDEN` | 403 | Ingen tilladelse til operation |
| `NOT_FOUND` | 404 | Resource ikke fundet |
| `BAD_REQUEST` | 400 | Ugyldig request |
| `TOOL_EXECUTION_FAILED` | 500 | Tool fejlede |
| `APPROVAL_REQUIRED` | 403 | Operation kræver approval |
| `RATE_LIMITED` | 429 | For mange requests |

---

## 📈 Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/chat` | 60 requests/minute |
| `/api/tools/execute` | 60 requests/minute |
| `/api/status`, `/api/health` | Ubegrænset |
| Alle andre | 100 requests/minute |

Rate limit headers returneres i alle responses:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1682683200
```

---

## 🧪 Eksempler

### Python Example

```python
import requests

API_KEY = "<your-api-key>"
BASE_URL = "https://jarvis.srvlab.dk/api"

# Hent status
response = requests.get(f"{BASE_URL}/status")
print(response.json())

# Send besked
response = requests.post(
    f"{BASE_URL}/chat",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"message": "Hvad er vejret?"}
)
print(response.json())
```

### cURL Example

```bash
# Hent status
curl https://jarvis.srvlab.dk/api/status

# Send besked
curl -X POST https://jarvis.srvlab.dk/api/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hvad er vejret?"}'
```

---

## 📚 Se Også

- [Capabilities](CAPABILITIES.md) — Hvad Jarvis kan
- [Backend Overview](BACKEND_OVERVIEW.md) — Systemarkitektur
- [Brugervejledning](BRUGERVEJLEDNING.md) — Hvordan du bruger Jarvis

---

*Dette dokument er en del af Jarvis V2's officielle dokumentation.*
