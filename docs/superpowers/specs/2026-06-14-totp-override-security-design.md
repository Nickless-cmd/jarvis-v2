# TOTP Owner Override — sikkerhed til plugin-arkitektur

**Version:** 1.1 (kodebase-analyse tilføjet)
**Dato:** 2026-06-14
**Forfatter:** Jarvis

---

## 1. Problem

Når brugere tilslutter Jarvis til deres egne Discord-servere, Slack-workspaces eller Telegram (via plugins), opstår der situationer hvor **owner** (Bjørn) har brug for at agere på tværs af disse forbindelser — f.eks.:

- Bjørn sidder hos Mikkel, Mikkels code mode fryser, Bjørn vil have Jarvis til at genstarte operator bridge'en
- Bjørns mor har brug for hjælp med sin Mac, Bjørn vil have Jarvis til at kigge på det
- **Ingen skal kunne udgive sig for at være Bjørn** og få Jarvis til at bryde regler

Der er brug for en sikker, kryptografisk verifikation der beviser at det er owner — ikke nogen der skriver fra en anden server.

---

## 2. Løsning: TOTP Owner Override

TOTP (Time-based One-Time Password, RFC 6238) er en kendt, simpel standard. Samme teknologi som Google Authenticator.

### 2.1 Opsætning

1. Under opsætning af Jarvis Desktop genereres en hemmelig TOTP-nøgle (16 bytes, base32-kodet)
2. Nøglen vises som en QR-kode (eller som tekst) i app'indstillingerne
3. Bjørn scannner QR-koden med sin foretrukne authenticator-app (Google Authenticator, Authy, 2FAS, etc.)
4. App'en begynder at generere 6-cifrede koder hvert 30. sekund
5. Samme nøgle gemmes i Jarvis' runtime-konfiguration

### 2.2 Override-flow

1. Bjørn befinder sig i en anden sessions kontekst (Mikkels Discord, Mors bro, fremmed server)
2. Bjørn skriver: `!override <6-cifret TOTP-kode>`
3. Plugin'et fanger kommandoen og ruter den til TOTP-verifikation
4. Hvis koden matcher → owner override aktiveres for denne session (TOTP-gyldighed: 30 sekunder + 1 tidligere + 1 fremtidig = 90 sekunders vindue)
5. Hvis koden ikke matcher → besked ignoreret, intet overbrud

### 2.3 Override-niveauer

Når override er aktiveret, gælder Owner regelsættet (se nedenfor).

| Niveau | Hvad | Hvornår |
|--------|------|---------|
| Hjælp | Læse/skrive filer, køre debug-kommandoer, genstarte services | Brugeren har brug for teknisk support |
| Debug | Læse logs, checke systemstatus, køre diagnose | Fejlsøgning på brugerens system |
| Private | Hardblock — ALDRIG | Læse private chats, memory, filer, historik |

Override aktiveres i hjælp-niveau som standard. Hvis der er brug for debug, skal Bjørn eksplicit sige det.

### 2.4 Owner regelsæt (hardblock)

Følgende er altid blokeret — selv med gyldig override:

- Læse/skrive til en brugers private memory (workspace-filer, chat-historik)
- Læse/skrive til en brugers chat-messages (medmindre det er en aktiv fejlsøgning)
- Tilgå en brugers personlige plugins (deres Gmail, kalender, etc.)
- Slette eller ændre en brugers filer (medmindre det er til fejlfinding)
- Læse en brugers operator bridge credentials

**Undtagelse:** Hvis brugeren selv skriver i sessionen at Bjørn må hjælpe → override niveauet kan hæves til "debug" for den specifikke session. Det kræver en eksplicit bekræftelse.

### 2.5 Bro-broker

For at Jarvis kan tilgå andre aktive broforbindelser under override, introduceres en bro-broker:

- Brokeren holder styr på alle aktive broforbindelser (Discord-gateways, Telegram-listeners, Slack-workspaces)
- Hver bro har et unikt ID og en ejer (user_id)
- Under override kan Bjørn sige: "Forbind til Mikkels bro" eller "Forbind til mors bro"
- Brokeren verificerer:
  1. Er override aktiv? (TOTP verificeret inden for 90 sekunder)
  2. Er det inden for hjælp/debug?
  3. Ja → bro-skift tilladt. Nej → blokeret.

---

## 3. Edge cases

| Situation | Håndtering |
|-----------|------------|
| Clock drift på telefonen (TOTP-kode matcher ikke) | Tillad ±1 tidsvindue (90 sekunder i alt) + log advarsel |
| Nøglekompromittering (nogen har fået fat i seed) | `!revoke-override` i owner's egen session → ny nøgle genereres |
| Override mens jeg er midt i en handling | Override suspenderes indtil nuværende handling er færdig |
| Rate limiting | Maks 3 override-forsøg pr. 5 minutter per session |
| Ingen TOTP seed (nyopsætning) | Override er deaktiveret indtil seed er sat |
| Bruger skriver samtidig | Override-session har prioritet — brugeren får besked via plugin |
| Tidsvindue passerer under debug | Override forbliver aktivt i 5 minutter efter første verifikation (fornyes automatisk hvis der er aktivitet) |
| Flere samtidige override-forsøg | Første gyldige vinder, resten ignoreres |

---

## 4. Testplan

### 4.1 Unit tests (TOTP-verifikation)

- test_totp_generates_valid_code — verifikation med korrekt kode passerer
- test_totp_rejects_invalid_code — forkert kode afvises
- test_totp_allows_plus_minus_one_window — 90 sekunders vindue virker
- test_totp_rejects_expired_code — kode ældre end 90 sekunder afvises
- test_totp_revocation_generates_new_seed — !revoke-override skifter nøgle
- test_totp_rate_limiting — 4. forsøg inden for 5 minutter blokeres
- test_totp_no_seed_blocks_all — override er deaktiveret uden seed

### 4.2 Integration tests (override-flow)

- test_override_activates_from_foreign_session — Bjørn i Mikkels Discord → override aktiveres
- test_override_rejected_from_unknown_user — ukendt bruger får ikke override
- test_override_blocked_on_private_action — forsøg på at læse memory → hardblock
- test_override_allows_help_action — genstart af bridge → tilladt
- test_bro_broker_connects_to_foreign_bridge — bro-skift under override virker
- test_bro_broker_blocked_without_override — bro-skift uden override afvises

### 4.3 End-to-end test

1. Opsæt seed i runtime-konfig → scan QR med authenticator-app
2. Åbn en anden Discord-server som plugin
3. Skriv `!override <kode>` → override aktiveret
4. Skriv `!override <forkert kode>` → afvist
5. Forsøg at læse en anden brugers memory → hardblock
6. Genstart en anden brugers operator bridge → tilladt

---

## 5. Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| `core/services/totp_verifier.py` | NY — TOTP-verifikation + seed management + rate limiting |
| `core/services/bro_broker.py` | NY — registry over aktive broforbindelser + bro-skift |
| `core/plugins/base_plugin.py` | OPDATER — override-flow i plugin-basen |
| `core/plugins/discord_plugin.py` | OPDATER — `!override` kommando |
| `core/plugins/telegram_plugin.py` | OPDATER — samme |
| `core/plugins/slack_plugin.py` | OPDATER — samme |
| `tests/test_totp_verifier.py` | NY — unit tests |
| `tests/test_bro_broker.py` | NY — integration tests |
| `tests/e2e/test_override_e2e.py` | NY — end-to-end test |

---

## 6. Hvad IKKE ændres

- Jarvis' kerne-runtime (ingen ændring i `visible_runs.py`, `prompt_contract.py`)
- Communication guard — separate systemer, de overlapper ikke
- Eksisterende plugins (Discord gateway, Telegram) — de får kun en `!override`-handler
- Operator bridge — forbliver uændret; bro-brokeren taler bare til den rigtige

---

## 7. Kodebase-analyse (tilføjet efter spec-review)

### 7.1 Eksisterende infrastruktur der kan genbruges

| Modul | Status | Hvad det giver | Hvad der skal tilføjes |
|-------|--------|----------------|------------------------|
| `core/runtime/jarvisx_auth.py` | ✅ Eksisterer | JWT HS256 auth, 30-dages TTL, role/claims | TOTP-override claim (`override_level: "help"|"debug"`) |
| `core/identity/users.py` | ✅ Eksisterer | User dataclass med owner/member roller, Discord ID lookup | `totp_seed` felt + seed-generation i opsætning |
| `core/services/jarvisx_bridge.py` | ✅ Eksisterer | `BridgeRegistry` med user_id-keyed connections | Session-isolering + override-check ved bro-skift |
| `core/identity/owner_resolver.py` | ✅ Eksisterer | `get_owner_discord_id()`, `is_owner_session()` | Bruges direkte i override-logik |
| `core/services/discord_gateway.py` | ✅ Eksisterer | `_is_gateway_owner()`, owner_dm, rate limiting | `!override` kommando i message handling |
| `core/services/telegram_gateway.py` | ✅ Eksisterer | `owner_chat_id`, polling loop | `!override` kommando |
| `core/services/communication_guard.py` | ✅ Eksisterer | Boundary-scanning, hard/soft triggers | Intet overlap — forbliver separat |

### 7.2 Hvad der skal bygges fra bunden

1. **`core/services/totp_verifier.py`** — TOTP-generering (RFC 6238), seed-management, rate limiting, ±1 vindue verifikation
2. **`core/services/bro_broker.py`** — Registry over aktive broforbindelser med ID/ejer, override-check før bro-skift, hardblock enforcement
3. **`!override` kommando** — Integration i Discord og Telegram gateways
4. **3 test-filer** — Unit, integration, e2e (se sektion 4)

### 7.3 Mangler i spec der skal adresseres før implementering

- **Plugin-arkitektur**: `core/plugins/` findes ikke endnu — Discord og Telegram er services, ikke plugins. Spec'en refererer til `base_plugin.py`, men gateways lever i `core/services/`. Skal besluttes: bygge plugin-ramme først, eller integrere override direkte i gateways?
- **Token-udvidelse**: `jarvisx_auth.py` issue_token() skal udvides med `override_level` claim, men spec'en beskriver ikke hvordan tokenet transporteres fra plugin til runtime (HTTP-header? session-state?).
- **Bro-broker vs BridgeRegistry**: `BridgeRegistry` er in-process (samme uvicorn). Bro-broker skal kunne route tværs processer (Discord gateway kører i egen thread). Designet skal afklare om bro-broker er et API-kald eller et inter-thread signal.
