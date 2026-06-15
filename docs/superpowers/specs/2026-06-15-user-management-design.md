# User Management — Design

**Version:** 1.0
**Dato:** 2026-06-15
**Forfatter:** Jarvis + Bjørn

---

## 1. Problem

Vi har tre brugere i `users.json` (Bjørn, Michelle, Mikkel) med manuelle tilføjelser og ingen rigtig brugerstyring. Når vi tager betalende brugere ind med GDPR, ordblinde/blinde, og persondata-lovgivning, er filer ikke nok.

---

## 2. Eksisterende kodebase — hvad vi har

| Fil | Linjer | Funktion |
|-----|--------|----------|
| `core/identity/users.py` | 210 | User dataclass, load/save, find_by_discord_id/name/workspace, add_user, remove_user |
| `core/identity/workspace_bootstrap.py` | 80 | Opretter workspace-mappe for ny bruger |
| `core/services/quota_store.py` | 140 | check_quota, consume_quota (chat/code/agent) |
| `core/services/delete_policy.py` | 65 | Soft delete (member) / hard delete (owner) |
| `core/services/share_guard_store.py` | 71 | Aktive delings-beslutninger |
| `core/services/permission_engine.py` | 136 | Tool-adgang pr. (rolle, mode) |
| `core/services/totp_verifier.py` | 135 | RFC 6238, rate-limit, seed |
| `core/services/keyring_store.py` | 160 | OS keyring integration, per-user encryption keys |
| `core/runtime/jarvisx_auth.py` | 295 | JWT HS256, bearer tokens, /auth/issue, /auth/refresh |
| `core/services/bro_broker.py` | 111 | Bro-registrering, override routing |
| `core/services/override_command.py` | 65 | !override command handler |

### Hvad vi har
- ✅ `add_user()` — tilføj bruger med discord_id, name, role, workspace
- ✅ `remove_user()` — fjern bruger via discord_id
- ✅ `find_user_by_discord_id/name/workspace()` — lookup
- ✅ `quota_store` — kvote-tjek (chat, code, agent)
- ✅ `delete_policy` — soft/hard delete
- ✅ `keyring_store` — per-user encryption keys
- ✅ `permission_engine` — mode/rolle adgang
- ✅ `totp_verifier` — owner override
- ✅ `jarvisx_auth` — JWT tokens, refresh

### Hvad vi mangler
- ❌ `register_user()` — selvregistrering via email med verifikation
- ❌ `load_user_info()` — komplet brugerprofil med alle felter
- ❌ `mute_user()` / `unmute_user()` — dæmp/aktiver bruger
- ❌ `set_user_quota()` — sæt/ændr kvote pr. bruger
- ❌ Email-verifikation flow (send, verify, activate)
- ❌ Bruger-db migration (fil → SQLite med kryptering)
- ❌ GDPR-endpoints (slet bruger, eksporter data, samtykke)

---

## 3. Arkitektur — SQLite med krypterede kolonner

### 3.1 Hvorfor SQLite
- Allerede i brug (`jarvis.db` findes)
- Ingen ekstern dependency
- Fil-baseret (let backup)
- WAL-mode for concurrent adgang
- SQLCipher eller application-level AES-256-GCM for krypterede kolonner

### 3.2 Bruger-tabel

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,              -- UUID
    email TEXT UNIQUE NOT NULL,       -- Login-identifikator
    email_verified INTEGER DEFAULT 0, -- 0=ikke verificeret, 1=verificeret
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',  -- owner/member/guest
    workspace TEXT UNIQUE NOT NULL,
    discord_id TEXT,                 -- Optional, for Discord integration
    totp_seed TEXT,                 -- Encrypted TOTP seed
    quota_chat INTEGER DEFAULT 20,  -- Free tier: 20 messages/day
    quota_code INTEGER DEFAULT 0,    -- Free tier: no code access
    quota_cowork INTEGER DEFAULT 0,  -- Free tier: no cowork access
    muted INTEGER DEFAULT 0,        -- 0=active, 1=muted
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,                -- Soft delete timestamp (NULL = active)
    encryption_key_id TEXT,         -- Reference to keyring key
    consent_data_processing INTEGER DEFAULT 0,
    consent_marketing INTEGER DEFAULT 0,
    consent_blind_access INTEGER DEFAULT 0  -- Ordblinde/blinde features
);
```

### 3.3 Krypterede kolonner

Følgende kolonner krypteres med AES-256-GCM per-user key (fra keyring_store):
- `totp_seed` — selv owner kan ikke læse uden aktiv session
- `email` — krypteret for GDPR compliance
- `discord_id` — krypteret for privacy

### 3.4 Workspace-filer

Workspace-filer (MEMORY.md, USER.md, etc.) krypteres per-user med samme key.
Se spec §16 for detaljer om krypteringsimplementering.

---

## 4. Brugerfunktioner

### 4.1 add_user() — manuel tilføjelse (owner/admin)

```python
def add_user(
    *,
    email: str,
    name: str,
    role: str = "member",
    workspace: str | None = None,
    discord_id: str | None = None,
) -> User:
```

Eksisterer allerede. Udvidet med email og kryptering.

### 4.2 register_user() — selvregistrering via email

```python
def register_user(
    *,
    email: str,
    name: str,
    password: str,  -- hashed med bcrypt
) -> tuple[User, str]:
    # Returns (user, verification_token)
    # 1. Valider email (ikke allerede registreret)
    # 2. Generer UUID og workspace
    # 3. Hash password med bcrypt
    # 4. Opret user med email_verified=0
    # 5. Send verifikations-email
    # 6. Returner (user, token)
```

**Flow:**
1. Bruger udfylder registreringsformular
2. Jarvis opretter konto med `email_verified=0`
3. Bruger klikker link i email
4. Konto aktiveres med `email_verified=1`
5. Bruger kan logge ind

### 4.3 load_user_info() — komplet brugerprofil

```python
def load_user_info(user_id: str) -> dict:
    # Returns:
    # - Alle user-felter (inkl. krypterede, dekrypteret i aktiv session)
    # - Kvote-status (chat, code, cowork)
    # - Workspace-sti
    # - TOTP-status
    # - Consent-status
    # - Mute-status
```

### 4.4 mute_user() / unmute_user()

```python
def mute_user(user_id: str, reason: str | None = None) -> bool:
    # Sætter muted=1, deaktiverer alle notifications
    # Brugeren kan stadig logge ind, men kan ikke sende beskeder

def unmute_user(user_id: str) -> bool:
    # Sætter muted=0, genaktiverer notifications
```

### 4.5 set_user_quota()

```python
def set_user_quota(
    user_id: str,
    *,
    chat: int | None = None,
    code: int | None = None,
    cowork: int | None = None,
    agent: int | None = None,
) -> dict:
    # Opdaterer kvote for bruger
    # Owner kan sætte ubegrænset (-1)
    # Member får standard kvoter
    # Ordblinde/blinde får Plus-kvoter gratis
```

### 4.6 del_user() — GDPR-sletning

```python
def del_user(user_id: str, mode: str = "soft") -> bool:
    # mode="soft": Sætter deleted_at timestamp, deaktiverer konto
    # mode="hard": Sletter alle data permanent (GDPR right to erasure)
    # Hard delete kræver owner TOTP override
    # Hard delete sletter:
    #   - User row
    #   - Workspace files (encrypted)
    #   - Chat history
    #   - Memory files
    #   - Session data
```

---

## 5. Email-verifikation

### 5.1 Registreringsflow

1. Bruger indtaster email + password på jarvis.srvlab.dk
2. Jarvis opretter konto med `email_verified=0`
3. Jarvis sender verifikations-email med token (24h TTL)
4. Bruger klikker link
5. Token verificeres → `email_verified=1`
6. Bruger kan nu logge ind

### 5.2 Sikkerhed
- Token er en kryptografisk UUID, ikke gættelig
- Token udløber efter 24 timer
- Max 3 registreringsforsøg pr. email pr. dag
- Password hashes med bcrypt (cost factor 12)

---

## 6. GDPR-compliance

### 6.1 Data-minimering
- Vi gemmer kun nødvendige data: email, name, role, workspace
- Discord_id er optional
- TOTP seed krypteres per-user

### 6.2 Sletningsret
- Soft delete: deaktiverer konto, beholder data i grace-period (30 dage)
- Hard delete: permanent sletning af alle data (GDPR right to erasure)
- Hard delete kræver owner TOTP override for andres data

### 6.3 Samtykke
- `consent_data_processing`: samtykke til at behandle persondata
- `consent_marketing`: samtykke til marketing-kommunikation
- `consent_blind_access`: samtykke til ordblinde/blinde features

### 6.4 Audit trail
- Alle ændringer til user-data logges med timestamp og actor
- Sletning logges særskilt

---

## 7. Kvote-tiers

| Tier | Chat | Code | Cowork | Agent | Pris |
|------|------|------|--------|-------|------|
| Free | 20 beskeder/dag | Ingen | Ingen | Ingen | 0 kr |
| Plus | Ubegrænset | 3 timer/dag | 10 approvals/dag | 2/dag | 99 kr/md |
| Pro | Ubegrænset | 5 timer/dag | 50 approvals/dag | 5/dag | 199 kr/md |
| Owner | Ubegrænset | Ubegrænset | Ubegrænset | Ubegrænset | — |
| Ordblinde/blinde | Ubegrænset | Plus-kvoter | Plus-kvoter | Plus-kvoter | Gratis |

---

## 8. Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| `core/identity/users.py` | OPDATER — tilføj email, kryptering, register_user, load_user_info, mute, quota |
| `core/identity/user_db.py` | NY — SQLite database adapter med krypterede kolonner |
| `core/identity/email_verify.py` | NY — Email-verifikation flow (send, verify, activate) |
| `core/services/quota_store.py` | OPDATER — tilføj set_user_quota |
| `core/services/delete_policy.py` | OPDATER — tilføj hard delete med GDPR-log |
| `apps/api/jarvis_api/routes/auth.py` | OPDATER — tilføj /auth/register, /auth/verify, /auth/user-info |
| `apps/api/jarvis_api/routes/users.py` | NY — CRUD endpoints for user management |
| `tests/test_user_management.py` | NY — unit tests for all user functions |
| `tests/test_email_verify.py` | NY — unit tests for email verification |
| `tests/test_gdpr_endpoints.py` | NY — integration tests for GDPR endpoints |

---

## 9. Hvad IKKE ændres

- Jarvis' kerne-runtime (visible_runs, prompt_contract)
- Communication guard
- Eksisterende plugins (Discord, Telegram)
- Operator bridge
- Workspace-filstruktur (kun kryptering tilføjes)
