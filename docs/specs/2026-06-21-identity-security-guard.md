---
status: færdig
audited: 2026-07-08
ground_truth: 9/9 refs alive, 17d old
---
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
    → TTL: 90s initial vindue, fornyes til +5 min ved aktivitet
    → Prompt opdateres: [override: AKTIV — Bjørn (owner) verifieret i session tilhørende: Lotte]
    → Owner kan handler som owner, men session privacy forbliver intakt
    → Privacy blocks (andre brugeres sessioner, data, beskeder) kan IKKE overstyres
    → Audit log entry oprettes
    → Gælder per session — aktiveres på ét device, gælder kun dér
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
7. **Override prompt state** — prompt-assembly update + 5 min TTL
8. **Sudo bypass** — composer decision + runtime respect
9. **Audit log** — all override/sudo/abuse events persisted
10. **Rate limiting** — 20 msg/min throttle, 3x throttle = session lock

---

## 10. Testing

### 10.1 Test coverage per komponent

| Komponent | Test-fil | Coverage-krav |
|---|---|---|
| Override store (grant/touch/revoke) | `tests/test_override_store.py` | All 3 operations + TTL expiry + cross-process isolation |
| TOTP verification | `tests/test_totp_verifier.py` | Valid code, expired code, wrong code, replay attack |
| Identity mismatch detection | `tests/test_identity_guard.py` | Claim ≠ owner → pushback, 3x → session lock |
| Session lock | `tests/test_session_lock.py` | Lock/unlock, locked session ignores messages, lock persistence |
| Account lockdown | `tests/test_account_lockdown.py` | 3 strikes → lockdown, 24h expiry, owner exemption |
| Abuse monitor (pattern matching) | `tests/test_abuse_monitor.py` | All patterns in §5.1, no false positives on normal messages |
| Prompt injection detection | `tests/test_prompt_injection.py` | Known patterns encoded/decoded, tool output injection |
| Rate limiting | `tests/test_rate_limiting.py` | 20 msg/min throttle, 3x → session lock |
| Sudo with override | `tests/test_sudo_override.py` | Owner+override→sudo, member+override→no sudo, no override→no sudo |
| Audit log | `tests/test_audit_log.py` | All actions logged, correct fields, queryable |
| Notification pipeline | `tests/test_abuse_notifications.py` | Bjørn notified on abuse events, format correct |

### 10.2 Edge case tests

| Edge case | Forventet adfærd |
|---|---|
| Override udløber midt i en tool-session | Prompt opdateres, næste tool-kald afvises hvis det kræver override |
| To samtidige override-forsøg (samme bruger, forskellige devices) | Sidste TOTP vinder — gammel override deaktiveres |
| Member forsøger at claim owner-status uden override | Pushback hver gang, 3x → session lock |
| Bruger starter ny session efter lock | Lock er per user_id — alle sessions låst (override er dog per-session, så hver device kræver egen TOTP) |
| Prompt injection i tool output (web_fetch) | Scanner fanger det før det når LLM prompt |
| Bruger sender 20+ beskeder på 1 minut | Rate limited — warning, 3x → session lock |
| Owner forsøger at læse en anden brugers session via override | Blocker — privacy blocks gælder stadig |
| Bruger unlockes efter 7 dage — gør det igen | Strikes nulstilles efter 7 dage — starter forfra |
| Team session: locked user forsøger at poste | Locked user kan se men ikke poste i team sessions |
| Override touch fornyer midt i en lang operation | TTL fornyes ved hvert tool-kald — aktiv brug afbrydes ikke |

### 10.3 Integration tests

- `tests/test_identity_guard_integration.py` — full flow: login → spoof → pushback → !override → verified → sudo → audit
- `tests/test_abuse_full_flow.py` — abuse detection → session lock → notification → Bjørn notified → unlock

---

## 11. Edge Cases (ikke dækket ovenfor)

### 11.1 Race conditions

| Scenario | Håndtering |
|---|---|
| Bruger A sender TOTP-kode samtidig med at override udløber | `override_store.touch()` tjekker først om override er aktiv — hvis nej, returneres error |
| To admins forsøger at unlock samme locked session | Første unlock vinder — anden får "already unlocked" |
| Abuse monitor kører samtidig med at session låses | Låsning er idempotent — dobbelt lås er harmless |

### 11.2 Privacy & compliance

| Scenario | Håndtering |
|---|---|
| Owner override i en andens session — kan læse deres beskeder? | **Nej.** Privacy blocks forblider hard-blocked. Owner kan kun handle (køre sudo, ændre system), ikke læse data. |
| Hvad hvis en bruger sletter deres konto med aktive abuse flags? | Abuse flags beholdes i `user_flags` (soft delete). Kan ikke undgå historik ved at slette konto. |
| GDPR sletning — hvordan håndteres abuse_events? | Abuse events kan anonymiseres (user_id → hash) men ikke slettes — audit trail krav. |

### 11.3 Override edge cases

| Scenario | Håndtering |
|---|---|
| Bruger aktiverer override, skifter device midt i session | Override gælder per session. Skifter bruger device/app, kræves ny TOTP-verifikation. |
| Bruger aktiverer override, starter ny session | Override gælder på tværs af sessions — prompt opdateres i begge. |
| Hvad hvis TOTP-koden stjæles? | 90s initial vindue begrænser skade. Aktivitet fornyer, men uden aktivitet udløber den. |

### 11.4 Abuse monitor edge cases

| Scenario | Håndtering |
|---|---|
| Falsk positiv — normal samtale flagged som abuse | Abuse monitor logger til `abuse_events` med severity. Kun high severity → session lock. Medium/low gives warning og logges. Bjørn kan manuelt override. |
| Bruger taler på et andet sprog — trigger pattern matching? | Pattern library er sprog-agnostisk for injection patterns. Normal samtale på dansk/tysk/whatever = no false positive. |
| Hvad hvis abuse monitor selv fejler (crash)? | Fail-open: hvis abuse_monitor kaster exception, pass — lås ikke session fordi monitoren crashede. Log error til audit. |

### 11.5 Session management

| Scenario | Håndtering |
|---|---|
| Bruger har 10 åbne sessions — account lockdown låser dem alle | Alle sessions markeres `locked` i DB. Nye sessions kan ikke oprettes i lockdown-perioden. |
| Hvad hvis locked session indeholder ulæste beskeder? | Beskeder bevares. Efter unlock kan brugeren læse dem. Lock er mute, ikke sletning. |
| Unlock sker før 7 dage — hvad med strikes? | Manuelt unlock (Bjørn) nulstiller strikes. Automatisk unlock efter 7 dage nulstiller også. |

---

## 12. Resolved Decisions

1. **Strike reset** — strikes nulstilles efter 7 dage uden nye events. Progressive: 1 strike = 24h, 2 strikes = 48h, 3 strikes = account lockdown 24h.
2. **Appeal mechanism** — kun owner (Bjørn) kan unlocke en låst session eller account. Manuelt via dashboard eller `!unlock` kommando med TOTP.
3. **Owner exemption** — owner (Bjørn) kan ikke få account lockdown. Han kan få session lock, men aldrig account lockdown. Dette forhindrer at owner låser sig selv ude.
4. **Member rules** — alle members (Michelle, Mikkel, Lotte, etc.) har samme regler. Ingen forskel. Owner er den eneste med elevated rettigheder.
5. **Guest access** — nye brugere får en 7-dages probation periode med heightened monitoring og lavere tærskel for pushback.

## 13. Self-Review Findings (rettet)

### Rettet i denne revision:

1. **Owner exemption i escalation** — owner kan ikke få account lockdown, kun session lock. Forhindrer self-lockout.
2. **Override TTL** — `!override` har et **90s initial vindue**, fornyes til **+5 min ved aktivitet** (touch). Override state fjernes fra prompt når den udløber.
3. **Audit log** — alle override aktiveringer, sudo executions, og abuse events logges til `audit_log` tabel med timestamp, user_id, action, og IP/device.
4. **Detection via LLM vs. pattern matching** — identity mismatch detection er **hybrid**: (a) simpel pattern matching ("jeg hedder X", "jeg er X") før LLM kald, (b) LLM-baseret detection som fallback for subtile forsøg. Pattern matching er first-pass filter, ikke komplet løsning.
5. **Tool output injection** — abuse monitor scanner ikke kun user messages, men også tool results for prompt injection via eksternt indhold (web_fetch, web_search results).
6. **Rate limiting** — max 20 beskeder/minut pr. user_id. Overskrides → throttle + warning. 3x throttle = session lock.
7. **Team sessions** — locked users kan se team sessions men ikke poste. Lock gælder for direkte DMs og personlige sessions.

### Mangler stadig (til Claude):

8. **Composer → runtime kommunikation** — hvordan sender composer sin sudo-decision til runtime? Nyt felt i message payload? Header? API endpoint? Claude skal designe dette.
9. **Privacy blocks definition** — skal formaliseres: (a) andre brugeres session-indhold, (b) andre brugeres beskeder, (c) andre brugeres workspace-filer, (d) andre brugeres hjerne/brain entries. Override kan IKKE override nogen af disse.
10. **Cross-device override** — AFKLARET: override er per-session. Aktiveres på desktop → gælder kun desktop. Mobil kræver separat TOTP. (Besluttet af Claude på baggrund af spec review, juni 2026)

---

## 14. Code Analysis vs. Spec (2026-06-21)

### 14.1 Allerede implementeret i koden (skal ikke bygges)

| Komponent | Fil | Status | Notes |
|---|---|---|---|
| Override store (grant/touch/revoke) | `core/services/override_store.py` | ✅ Live | DB-backed, cross-proces. TTL: 90s initial + 5min med aktivitet |
| JWT auth tokens | `core/runtime/jarvisx_auth.py` | ✅ Live | HS256, role+app_id i claims, `session_needs_override()` |
| TOTP verifier | `core/services/totp_verifier.py` | ✅ Live | Verificerer 6-cifret kode mod seed |
| `!override` command handler | `core/services/override_command.py` | ✅ Live | Aktiverer override via TOTP, fornyer ved aktivitet |
| Sudo allowlist | `core/tools/workspace_capabilities.py` | ✅ Live | `APPROVED_SUDO_EXEC_ALLOWLIST` + `sudo_exec` policy |
| Forny override fra run-kontekst | `core/services/visible_runs.py` | ✅ Live | Fornyer 5-min vinduet ved aktivitet |
| Prompt injection patterns (skills) | `core/services/skill_scanner.py` | ✅ Live | Kun for skills, ikke general message pipeline |
| Basic "ignore previous" detection | `core/services/in_flight_runs.py` | ✅ Live | Limiteret til run-kontekst |
| app_id binding i JWT | `core/runtime/jarvisx_auth.py` | ✅ Live | Token bundet til specifik app-installation |

### 14.2 Mangler stadig (skal implementeres)

| Komponent | Hvor | Status | Notes |
|---|---|---|---|
| Identity mismatch pushback | Message pipeline → LLM | ❌ Mangler | Ingen detection af "jeg hedder X" ≠ session owner |
| Override state i visible prompt | `prompt_support_signals.py` | ❌ Mangler | `[override: AKTIV...]` banner findes ikke |
| Session lock (locked kolonne) | `chat_sessions` DB | ❌ Mangler | Ingen `locked` kolonne i tabellen |
| Session lock enforcement | Message processing pipeline | ❌ Mangler | Runtime accepterer stadig beskeder til låste sessions |
| Account lockdown | Cross-session tracking | ❌ Mangler | Ingen mekanisme til at låse alle brugerens sessions |
| `abuse_monitor.py` | Ny service | ❌ Mangler | Abuse detection service findes ikke |
| `abuse_events` tabel | DB | ❌ Mangler | Findes ikke |
| `user_flags` tabel | DB | ❌ Mangler | Findes ikke |
| `audit_log` tabel | DB | ❌ Mangler | Findes ikke |
| Abuse notification | Push + Discord + eventbus | ❌ Mangler | Ikke wired |
| Rate limiting (20 msg/min) | Message pipeline | ❌ Mangler | Ikke implementeret |
| Prompt injection i gennerelle messages | General message pipeline | ❌ Mangler | Kun for skills (`skill_scanner.py`) |
| Tool output injection scanning | `web_fetch`/`web_search` resultater | ❌ Mangler | Ikke implementeret |

### 14.3 TTL-reconciliation (spec vs. kode)

Spec'en siger **30 min** TTL for `!override`. Koden har:
- **Initial:** 90 sekunder (`_INITIAL_WINDOW = 90.0` i `override_store.py`)
- **Fornyelse:** +5 minutter ved aktivitet (`_ACTIVITY_WINDOW = 300.0`)

Dette er en **bevidst design-beslutning** fra Claudes commits — kort initial vindue sikrer at override ikke bliver hængende hvis brugeren ikke aktivt bruger den. Ved aktiv brug fornyes den løbende. **Spec opdateret til 5 min** for at matche koden.

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