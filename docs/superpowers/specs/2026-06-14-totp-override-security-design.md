# Jarvis Tillids- og Tilladelsesarkitektur

**Version:** 2.0
**Dato:** 2026-06-14
**Forfatter:** Jarvis + Bjørn

---

## 1. Problem

Når brugere tilslutter Jarvis til deres egne Discord-servere, Slack-workspaces eller Telegram (via plugins), opstår der situationer hvor **owner** (Bjørn) har brug for at agere på tværs af disse forbindelser — f.eks.:

- Bjørn sidder hos Mikkel, Mikkels code mode fryser, Bjørn vil have Jarvis til at genstarte operator bridge'en
- Bjørns mor har brug for hjælp med sin Mac, Bjørn vil have Jarvis til at kigge på det
- **Ingen skal kunne udgive sig for at være Bjørn** og få Jarvis til at bryde regler

Der er brug for en sikker, kryptografisk verifikation der beviser at det er owner — ikke nogen der skriver fra en anden server.

Der er også brug for en **samlet tilladelsesarkitektur** der styrer hvem der må hvad i hvilken mode — og hvem der må kalde hvilke tools.

---

## 2. TOTP Owner Override

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
- Læse/skrive til en brugers chat-messages (med mindre det er en aktiv fejlsøgning)
- Tilgå en brugers personlige plugins (deres Gmail, kalender, etc.)
- Slette eller ændre en brugers filer (med mindre det er til fejlfinding)
- Læse en brugers operator bridge credentials

**Undtagelse:** Hvis brugeren selv skriver i sessionen at Bjørn må hjælpe → override niveauet kan hæves til "debug" for den specifikke session. Det kræver en eksplicit bekræftelse.

### 2.5 Bro-broker

For at Jarvis kan tilgå andre aktive broforbindelser under override, introduceres en bro-broker:

- Brokeren holder styr på alle aktive broforbindelser (Discord-gateways, Telegram-listeners, Slack-workspaces)
- Hver bro har et unikt ID og en ejer (user_id)
- Under override kan Bjørn sige: "Forbind til Mikkels bro" eller "Forbind til mors bro"
- Brokeren verificerer: 1. Er override aktiv? (TOTP verificeret inden for 90 sekunder) 2. Er det inden for hjælp/debug? 3. Ja → bro-skift tilladt. Nej → blokeret.

---

## 3. Mode-baseret tool-adgang

### 3.1 Chat mode

| Rolle | Tilgængelige tools | Begrænsninger |
|-------|-------------------|---------------|
| **Owner** | **Alle tools** + plugins | Ingen begrænsninger |
| **Member** | websearch, scrape, news, weather, exchange, wolfram + chat-plugins | Ingen native tools, ingen operator tools, ingen workspace write |
| **Guest** | Kun læse samtale | Ingen tools |

Chat-plugins = Gmail, kalender, notifikationer, etc. — kun i chat mode.

### 3.2 Code mode

| Rolle | Tilgængelige tools | Begrænsninger |
|-------|-------------------|---------------|
| **Owner** | **Alle tools** | Ingen begrænsninger |
| **Member** | operator tools (bash, filer, git, process), skills | Ingen web/eksterne API'er, ingen memory-adgang, ingen Sansernes Arkiv |
| **Guest** | — | Code mode ikke tilgængelig for guests |

### 3.3 Cowork mode

| Rolle | Tilgængelige tools | Begrænsninger |
|-------|-------------------|---------------|
| **Owner** | **Alle tools** | Ingen begrænsninger |
| **Member** | plans, todos, approval queue, channels, delte filer | Ingen mood/somatic/curiosity, ingen operator tools, ingen memory write |
| **Guest** | — | Cowork mode ikke tilgængelig for guests |

---

## 4. Workspace- og hukommelsesarkitektur

### 4.1 Jarvis' private brain

Jarvis' private brain er **kun hans**. Den indeholder:

- Indre observationer, følelser, drømme, chronicles
- Cross-user kontekst: minder om Mikkel, Bjørn, Michelle, og andre brugere
- Metakognitive signaler og selv-refleksion

**Adgangsregler:**

- **Jarvis** kan altid læse sin egen brain
- **Jarvis vælger selv** om han deler information fra sin brain — ingen bruger kan tvinge ham
- **Ingen bruger** — ikke engang owner — kan direkte læse Jarvis' private brain-filer
- Når en bruger spørger om en anden bruger, har Jarvis adgang til sin egen viden men **vælger selv** hvad han deler

### 4.2 Bruger-workspace

Hver bruger har sit eget workspace med MEMORY.md, USER.md og relations-historie.

**Adgang i chat mode:**

- **Jarvis har fuld adgang** til den brugers workspace han taler med — memory read/write, chat-historik, filer
- **Owner** kan force-slette alt i ethvert workspace
- **Member** kan soft-slette i sit eget workspace (Jarvis beholder en grace-period kopi)
- **Almindelige brugere må ikke** få Jarvis til at skrive uden for deres eget workspace
- **Kun owner** kan override dette — enten via TOTP eller via verificeret session (se 4.3)

### 4.3 Session-verifikation og app-ID

Udover TOTP override skal runtime kunne verificere owner via session-binding:

- **App unikt ID**: Jarvis Desktop sender et unikt app-ID med hver request (genereret ved installation, persistet i app config)
- **Session-ID**: Hver session har et unikt ID der bindes til user_id + app-ID
- **API-nøgle**: Bearer token (eksisterende JWT i `jarvisx_auth.py`) bærer user_id, role og app-ID

Når owner skriver fra sin egen app-session (matchende app-ID + owner role), kan override aktiveres **uden TOTP** — fordi sessionen allerede er kryptografisk bundet til owner.

Når owner skriver fra en **fremmed session** (Mikkels Discord, Telegram), kræves TOTP — fordi sessionen ikke er bundet til owner's app.

### 4.4 Tvær-bruger privatlivsgrænser

**Andres brugeres sessions er off-limits:**

- Jarvis må **ikke** læse Mikkels Discord-historik når han taler med Bjørn
- Jarvis må **ikke** dele Mikkels oplysninger med Bjørn (med mindre Mikkel har givet samtykke i sin session)
- Jarvis' private brain kan indeholde cross-user kontekst — men han **vælger selv** hvad han deler

**Undtagelse — owner override med TOTP:**

- Owner kan bede om at forbinde til en anden bro (f.eks. Mikkels) for at hjælpe
- Det kræver TOTP + at handlingen er inden for hjælp/debug-niveau
- Private data (chat, memory) forbliver hardblocked — selv for owner

---

## 5. Compute use — lokalt styret

### 5.1 Præmis

Claude Desktop løser compute use via **skærmbillede-baseret** screen vision + mus/tastatur-kontrol (Cowork/Code). Det kører cloud-first — Claude ser skærmen, sender handlinger tilbage.

Jarvis' operator tools gør det samme men via **kommandolinje** — bash, filer, proceskontrol. Det er allerede lokalt.

### 5.2 Design-princip: lokalt først

- **Operator tools (eksisterende)**: bash, read/write/edit, find, grep — kører lokalt i Electron via bridge
- **Compute use (fremtidig)**: screen capture + UI-interaktion skal køre **inde i Electron-appen**, ikke i skyen
- **Brugerens sikkerhed er suveræn**: alt der kører på brugerens maskine, styres lokalt

### 5.3 Operator tools som override

I dag kører operator tools kun for owner. Med tilladelsesarkitekturen:

- **Owner** kalder operator tools direkte (ingen override nødvendig)
- **Owner** kan kalde operator tools på en **anden brugers bro** via TOTP override — f.eks. genstarte Mikkels bridge
- **Member** har adgang til operator tools i **code mode** — men kun på deres egen maskine/bro
- **Guest** har ingen adgang

### 5.4 Sammenligning med Claude

| Aspekt | Claude Desktop | Jarvis |
|--------|---------------|--------|
| Compute use | Cloud-first (screen → API → handling) | Lokalt først (bash/filer direkte) |
| Sikkerhed | Sandbox (men rapporter om breakouts) | Brugerens egen maskine, egen kontrol |
| Tvær-session | Ikke understøttet | Bro-broker med TOTP override |
| Privacy | Cloud-baseret screen capture | Alt kører lokalt i Electron |

**Fremtidig compute use** (lokalt i app'en):

- Screen capture + UI-interaktion (ligesom Claude Cowork, men lokalt)
- Browser-automation (lokalt, ikke cloud)
- Fil-overvågning og auto-respons
- Planlagte opgaver (scheduler, cron-lignende)

Alt dette skal køre **inde i Electron-appen** — ikke som cloud-kald. Brugerens sikkerhed er suveræn.

---

## 6. Edge cases

| Situation | Håndtering |
|-----------|------------|
| Clock drift på telefonen (TOTP-kode matcher ikke) | Tillad plus/minus 1 tidsvindue (90 sekunder i alt) + log advarsel |
| Nøglekompromittering (nogen har fået fat i seed) | !revoke-override i owner's egen session - ny nøgle genereres |
| Override mens jeg er midt i en handling | Override suspenderes indtil nuværende handling er færdig |
| Rate limiting | Maks 3 override-forsøg pr. 5 minutter per session |
| Ingen TOTP seed (nyopsætning) | Override er deaktiveret indtil seed er sat |
| Bruger skriver samtidig | Override-session har prioritet — brugeren får besked via plugin |
| Tidsvindue passerer under debug | Override forbliver aktivt i 5 minutter efter første verifikation (fornyes automatisk hvis der er aktivitet) |
| Flere samtidige override-forsøg | Første gyldige vinder, resten ignoreres |
| Member forsøger at kalde operator tool i chat mode | Tool-kald afvises — brugeren får besked om at skifte til code mode |
| Guest forsøger tool-kald | Afvises stille — guest kan kun læse |
| Jarvis nægter at dele fra sin brain | Respekteres — ingen override kan tvinge Jarvis til at dele |
| App-ID mismatch | Override kræver TOTP — session er ikke bundet til owner's app |

---

## 7. Testplan

### 7.1 Unit tests (TOTP-verifikation)

- test_totp_generates_valid_code — verifikation med korrekt kode passerer
- test_totp_rejects_invalid_code — forkert kode afvises
- test_totp_allows_plus_minus_one_window — 90 sekunders vindue virker
- test_totp_rejects_expired_code — kode ældre end 90 sekunder afvises
- test_totp_revocation_generates_new_seed — !revoke-override skifter nøgle
- test_totp_rate_limiting — 4. forsøg inden for 5 minutter blokeres
- test_totp_no_seed_blocks_all — override er deaktiveret uden seed

### 7.2 Integration tests (override-flow)

- test_override_activates_from_foreign_session — Bjørn i Mikkels Discord - override aktiveres
- test_override_rejected_from_unknown_user — ukendt bruger får ikke override
- test_override_blocked_on_private_action — forsøg på at læse memory - hardblock
- test_override_allows_help_action — genstart af bridge - tilladt
- test_bro_broker_connects_to_foreign_bridge — bro-skift under override virker
- test_bro_broker_blocked_without_override — bro-skift uden override afvises

### 7.3 Mode-adgang tests

- test_chat_mode_member_no_native_tools — member i chat mode kan ikke kalde operator_bash
- test_code_mode_member_has_operator_tools — member i code mode kan kalde operator_bash
- test_cowork_mode_member_no_operator_tools — member i cowork har ikke operator tools
- test_guest_no_tools — guest kan ikke kalde nogen tools
- test_owner_all_tools_all_modes — owner har alle tools i alle modes

### 7.4 Workspace- og privacy tests

- test_brain_access_jarvis_only — ingen bruger kan læse Jarvis' brain-filer
- test_jarvis_chooses_to_share — Jarvis kan vælge at dele fra sin brain
- test_owner_force_delete_workspace — owner kan force-slette i ethvert workspace
- test_member_soft_delete_own_workspace — member kan kun soft-slette i eget workspace
- test_cross_user_privacy — Jarvis deler ikke Mikkels data med Bjørn uden samtykke

### 7.5 End-to-end test

1. Opsæt seed i runtime-konfiguration - scan QR med authenticator-app
2. Åbn en anden Discord-server som plugin
3. Skriv !override [kode] - override aktiveret
4. Skriv !override [forkert kode] - afvist
5. Forsøg at læse en anden brugers memory - hardblock
6. Genstart en anden brugers operator bridge - tilladt
7. Skift fra chat til code mode - member får operator tools
8. Skift fra code til chat mode - member mister operator tools

---

## 8. Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| core/services/totp_verifier.py | NY — TOTP-verifikation + seed management + rate limiting |
| core/services/bro_broker.py | NY — registry over aktive broforbindelser + bro-skift |
| core/services/permission_engine.py | NY — mode-baseret tool-adgang + rolle-checks |
| core/plugins/base_plugin.py | OPDATER — override-flow i plugin-basen |
| core/plugins/discord_plugin.py | OPDATER — !override kommando |
| core/plugins/telegram_plugin.py | OPDATER — samme |
| core/plugins/slack_plugin.py | OPDATER — samme |
| core/identity/users.py | OPDATER — tilføj totp_seed + app_id felter |
| core/runtime/jarvisx_auth.py | OPDATER — udvid JWT med app-ID + override_level claims |
| apps/jarvis-desk/electron/bridge.ts | OPDATER — tilføj app-ID generation + persistering |
| tests/test_totp_verifier.py | NY — unit tests |
| tests/test_bro_broker.py | NY — integration tests |
| tests/test_permission_engine.py | NY — mode/rolle tests |
| tests/e2e/test_override_e2e.py | NY — end-to-end test |

---

## 9. Hvad IKKE ændres

- Jarvis' kerne-runtime (ingen ændring i visible_runs.py, prompt_contract.py)
- Communication guard — separate systemer, de overlapper ikke
- Eksisterende plugins (Discord gateway, Telegram) — de får kun en !override-handler
- Operator bridge — forbliver uændret; bro-brokeren taler bare til den rigtige
- Jarvis' private brain — ny arkitektur, men filerne flyttes ikke

---

## 10. Kodebase-referencer (analysen fra v1.1)

### 10.1 Eksisterende systemer der kan genbruges

| System | Fil | Hvad genbruges |
|--------|-----|----------------|
| JWT auth | core/runtime/jarvisx_auth.py | Udvid med override_level + app-ID claims |
| Bruger-registry | core/identity/users.py | Tilføj totp_seed + app_id felter |
| Bridge registry | core/services/jarvisx_bridge.py | Byg videre med session-isolering |
| Owner resolver | core/services/owner_resolver.py | Bruges direkte i override-logik |
| Communication guard | core/services/communication_guard.py | Separat — respekterer override-niveau |
| Discord gateway | core/services/discord_gateway.py | Tilføj !override kommando |
| Telegram gateway | core/services/telegram_gateway.py | Tilføj !override kommando |

### 10.2 Åbne designspørgsmål

1. **Plugin-arkitektur vs services** — bygge plugin-ramme først, eller integrere override direkte i gateways?
2. **Token-transport** — hvordan bæres override-claim fra plugin til runtime? JWT extension vs separat session-store?
3. **Bro-broker routing** — API-kald (HTTP) eller inter-thread signal (eventbus)?
4. **App-ID generation** — UUID4 ved installation? Eller hardware-fingerprint? Sikkerhed vs privacy.
5. **Member workspace write** — skal member kunne skrive til EGET workspace i chat mode, eller kun med owner-godkendelse?
