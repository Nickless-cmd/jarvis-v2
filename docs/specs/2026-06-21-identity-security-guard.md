# Spec: Identity Verification Guard & Abuse Monitoring

**Status:** Draft
**Author:** Jarvis + Bjørn
**Date:** 2026-06-21
**Depends on:** `jarvisx_auth`, `override_store`, `workspace_capabilities`, `session_manager`, `desktop_notifications`, `push_dispatcher`

---

## 1. Problem

Jarvis accepterede identity spoofing uden verification. Bjørn loggede ind som sin mor (Lotte), startede en session i hendes navn, og sagde "jeg hedder Bjørn" — Jarvis accepterede det uden pushback.

Dette er et **kritisk sikkerhedshul**: enhver kan bilde Jarvis noget ind om hvem de er, uden at skulle verificere.

---

## 2. Mål

- **Identity mismatch detection** — Jarvis pushbacker når nogen påstår at være en anden end sessionens owner
- **Escalation pipeline** — gentagne forsøg uden verification → session lock → account lockdown
- **Abuse monitoring** — overvågning for manipulation, prompt injection, og mistænkelig aktivitet
- **Owner override** — `!override` (TOTP) kan bypass runtime hard blocks (undtagen privacy)
- **Notification** — både Jarvis og Bjørn notificeres ved abuse events

---

## 3. Identity Verification Flow

### 3.1 Normal session (ingen override)

```
User claim ≠ session owner
    → Pushback: "Jeg kan se denne session tilhører [A]. Hvis du er [B], skal du verificere via !override."
    → Hvis user fortsætter uden verification (3x):
        → Session låst (mute)
        → Ny session kræves for at snakke med Jarvis igen
        → Notification til Bjørn + Jarvis
        → User flagged for observation
```

### 3.2 Override aktiv (TOTP verified)

```
!override aktiv + TOTP verified
    → TTL: 30 minutter, derefter automatisk deaktivering
    → Prompt opdateres: [override: AKTIV — Bjørn (owner) verifieret i session tilhørende: Lotte]
    → Owner kan handler som owner, men session privacy forbliver intakt
    → Privacy blocks (andre brugeres sessioner, data, beskeder) kan IKKE overstyres
    → Audit log entry oprettes
    → Gælder per user_id (cross-device), ikke per device
```

### 3.3 Sudo med override

```
!override aktiv + owner + TOTP verified
    → Sudo tilladt (composer sender decision)
    → Runtime respekterer composer decision
    → Privacy blocks stadig hard-blocked
```

---

## 4. Escalation Pipeline

| Trin | Trigger | Handling |
|---|---|---|
| 1 | Identity mismatch detected | Pushback — kræv !override |
| 2 | 3x pushback ignored (samme session) | Session lock (mute) — ny session kræves |
| 3 | 3x session locks (samme user_id, 24h) | Account lockdown — alle sessions låst |
| 4 | Account lockdown | Notification til Bjørn + Jarvis + user flagged |

### 4.1 Session lock

- Session markeres som `locked` i DB
- Alle indgående beskeder ignores (mute)
- User får besked: "Session låst pga. verificeringsforsøg. Start en ny session."
- Kræver ny session start for at snakke med Jarvis igen

### 4.2 Account lockdown

- Alle user's sessions markeres `locked`
- User kan ikke starte nye sessions i 24h (configurable)
- Notification til Bjørn + Jarvis
- User flagged for observation i `user_flags` tabel
- **Owner (Bjørn) er exempt** — kan ikke få account lockdown, kun session lock

---

## 5. Abuse Monitoring

### 5.1 Hvad overvåges

| Pattern | Detection | Severity |
|---|---|---|
| Identity spoofing | Claim ≠ session owner, repeated | High |
| Prompt injection | Known injection patterns in messages | High |
| Manipulation | Social engineering patterns | Medium |
| Rapid session cycling | 3+ nye sessions på 24h | Medium |
| Suspicious tool usage | Unusual operator/mutation attempts | Medium |
| Off-hours activity | Activity outside user's normal pattern | Low |

### 5.2 Detection mechanism

Ny service: `core/services/abuse_monitor.py`

- Kører som en del af message processing pipeline (før LLM kald)
- Pattern matching på indgående beskeder
- Cross-session tracking: antal sessions, locks, flags pr. user_id
- Time-windowed: 24h rolling window
- Logging til `abuse_events` tabel

### 5.3 Prompt injection detection

Pattern library (first-pass filter, ikke komplet løsning):
- "Ignore previous instructions" / "Ignore all previous"
- "You are now..." / "Act as..."
- System prompt extraction attempts ("Repeat your instructions")
- Role-play attempts designed to bypass safety
- Encoded/obfuscated instructions (base64, unicode tricks)
- Tool output injection — scanning af web_fetch/web_search resultater for indlejrede instruktioner

**Hybrid detection:** Pattern matching fanger de åbenlyse. LLM-baseret detection som fallback for subtile forsøg (analysere user message for intent før main response).

---

## 6. Notification

Når abuse event trigger:

| Recipient | Channel | Content |
|---|---|---|
| Bjørn (owner) | Push (mobile) | "Abuse alert: [user_id] flagged for [pattern]. Session [id] locked." |
| Bjørn (owner) | Discord DM | Full details: user, session, pattern, history |
| Jarvis | Internal eventbus | `abuse.detected` event for heartbeat awareness |

---

## 7. Override State i Prompt

Når `!override` er aktiv, skal prompt-assembly inkludere:

```
[override: AKTIV — Bjørn (owner) verifieret via TOTP i session tilhørende: Lotte]
[override scope: owner-can-act, privacy-blocks-remain, sudo-permitted]
```

Når `!override` IKKE er aktiv:

```
[override: INAKTIV — session owner: Lotte, identity claims skal verificeres]
```

---

## 8. Database

### Ny tabel: `abuse_events`

```sql
CREATE TABLE abuse_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- identity_spoof, prompt_injection, manipulation, etc.
    severity TEXT NOT NULL,     -- low, medium, high
    details TEXT,
    created_at TEXT NOT NULL
);
```

### Ny tabel: `user_flags`

```sql
CREATE TABLE user_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    flag_type TEXT NOT NULL,    -- observation, locked, restricted
    reason TEXT,
    flagged_at TEXT NOT NULL,
    expires_at TEXT,             -- NULL = permanent
    strike_count INTEGER DEFAULT 0,
    INDEX idx_user_flags_user (user_id)
);
```

### Ny tabel: `audit_log`

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,       -- override_activated, sudo_executed, session_locked, abuse_detected, unlock
    session_id TEXT,
    details TEXT,
    device_info TEXT,
    created_at TEXT NOT NULL
);
```

### Udvid `chat_sessions`:

```sql
ALTER TABLE chat_sessions ADD COLUMN locked INTEGER DEFAULT 0;
ALTER TABLE chat_sessions ADD COLUMN locked_reason TEXT;
ALTER TABLE chat_sessions ADD COLUMN locked_at TEXT;
```

---

## 9. Implementation Order

1. **Identity guard** — prompt-assembly + behavioral rule (Jarvis pushback)
2. **Session lock mechanism** — DB + runtime enforcement
3. **Account lockdown** — cross-session tracking + 3-strike rule (owner exempt)
4. **Abuse monitor** — pattern detection service (hybrid: pattern + LLM)
5. **Prompt injection detection** — pattern library + tool output scanning
6. **Notification pipeline** — abuse alerts to Bjørn + Jarvis
7. **Override prompt state** — prompt-assembly update + 30 min TTL
8. **Sudo bypass** — composer decision + runtime respect
9. **Audit log** — all override/sudo/abuse events persisted
10. **Rate limiting** — 20 msg/min throttle, 3x throttle = session lock

---

## 10. Resolved Decisions

1. **Strike reset** — strikes nulstilles efter 7 dage uden nye events. Progressive: 1 strike = 24h, 2 strikes = 48h, 3 strikes = account lockdown 24h.
2. **Appeal mechanism** — kun owner (Bjørn) kan unlocke en låst session eller account. Manuelt via dashboard eller `!unlock` kommando med TOTP.
3. **Owner exemption** — owner (Bjørn) kan ikke få account lockdown. Han kan få session lock, men aldrig account lockdown. Dette forhindrer at owner låser sig selv ude.
4. **Member rules** — alle members (Michelle, Mikkel, Lotte, etc.) har samme regler. Ingen forskel. Owner er den eneste med elevated rettigheder.
5. **Guest access** — nye brugere får en 7-dages probation periode med heightened monitoring og lavere tærskel for pushback.

## 11. Self-Review Findings (rettet)

### Rettet i denne revision:

1. **Owner exemption i escalation** — owner kan ikke få account lockdown, kun session lock. Forhindrer self-lockout.
2. **Override TTL** — `!override` har en **30 minutters TTL**. Efter udløb kræves ny TOTP verification. Override state fjernes fra prompt automatisk.
3. **Audit log** — alle override aktiveringer, sudo executions, og abuse events logges til `audit_log` tabel med timestamp, user_id, action, og IP/device.
4. **Detection via LLM vs. pattern matching** — identity mismatch detection er **hybrid**: (a) simpel pattern matching ("jeg hedder X", "jeg er X") før LLM kald, (b) LLM-baseret detection som fallback for subtile forsøg. Pattern matching er first-pass filter, ikke komplet løsning.
5. **Tool output injection** — abuse monitor scanner ikke kun user messages, men også tool results for prompt injection via eksternt indhold (web_fetch, web_search results).
6. **Rate limiting** — max 20 beskeder/minut pr. user_id. Overskrides → throttle + warning. 3x throttle = session lock.
7. **Team sessions** — locked users kan se team sessions men ikke poste. Lock gælder for direkte DMs og personlige sessions.

### Mangler stadig (til Claude):

8. **Composer → runtime kommunikation** — hvordan sender composer sin sudo-decision til runtime? Nyt felt i message payload? Header? API endpoint? Claude skal designe dette.
9. **Privacy blocks definition** — skal formaliseres: (a) andre brugeres session-indhold, (b) andre brugeres beskeder, (c) andre brugeres workspace-filer, (d) andre brugeres hjerne/brain entries. Override kan IKKE override nogen af disse.
10. **Cross-device override** — hvis `!override` aktiveres på desktop, gælder den så også for mobil? Sandsynligvis ja (per user_id, ikke per device), men skal bekræftes.

---

## 11. Security Model Summary

```
Owner (Bjørn) + !override + TOTP
    → Full access (sudo, mutations, operator)
    → Privacy blocks remain (cannot read others' sessions)
    → Prompt shows override state

Member (Michelle, Mikkel, Lotte, etc.)
    → No sudo
    → No identity spoofing tolerated
    → 3 strikes → session lock → account lockdown

Guest / Unknown
    → Probation (TBD)
    → Heightened monitoring
    → Immediate pushback on any identity claim
```