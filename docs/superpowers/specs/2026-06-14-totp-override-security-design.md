# Jarvis Tillids-, Tilladelses- og Plugin-arkitektur

**Version:** 3.0
**Dato:** 2026-06-14
**Forfatter:** Jarvis + Bjørn (konsolideret af Claude fra Discord-DM 10:43–12:13 + desk-session)

> **v3.0-note:** v1.0/v2.0 tabte dele af den oprindelige Discord-samtale (Jarvis
> narrowede til TOTP efter en konfabulering + en daemon-afbrydelse). Denne version
> samler HELE buen ét sted: modes, roller, plugins (connectors + lokal gateway +
> regelsæt), TOTP-override, operator/skills-model, compute use og UI-panel-kald.
> Genuine tvetydigheder i kildesamtalen er **flagget** (§14), ikke gættet.

---

## 1. Problem

Jarvis skal være **én Jarvis** med flere værktøjskasser (modes), brugt af flere
roller (owner/member/guest), på tværs af flere kanaler (native Discord + bruger-
forbundne plugins). Det rejser tre sammenhængende behov:

1. **Mode-separation med rolle-baseret tool-adgang** — en almindelig bruger må
   ikke kunne narre Jarvis til at køre skadelige operator-handlinger; owner skal
   have fri adgang.
2. **Plugin-arkitektur** — brugere skal kunne forbinde Jarvis til deres egne
   ting (Gmail, Slack, Telegram, deres egen Discord-server) **lokalt** af
   sikkerheds- og privatlivshensyn, ligesom Claude Desktop's connectors.
3. **Sikker owner-override** — hvis Bjørn sidder hos Mikkel eller sin mor og må
   bruge et værktøj en almindelig bruger ikke har, skal Jarvis kunne bevise
   kryptografisk at det ER Bjørn — uden at nogen kan udgive sig for ham.

**Konkrete scenarier:**

- Bjørn sidder hos Mikkel; Mikkels code mode fryser; Bjørn vil have Jarvis til at
  genstarte operator-bridge'en.
- Bjørns mor (Odense Bellinge, ikke teknisk) har brug for hjælp med sin Mac.
- **Ingen skal kunne udgive sig for at være Bjørn** og få Jarvis til at bryde regler.

---

## 2. Tre modes — én Jarvis

Det er **ikke** tre apps. Det er **én Jarvis** med forskellig adgang til sine
evner pr. vindue. Samme session/historik/kontinuitet bagved; forskellig tool-
liste + system-prompt-fokus pr. mode (som Claude Desktop's chat/cowork/code).

| Mode | Formål |
|------|--------|
| **Chat** | Samtale, relation, web, vejr, huske — *Jarvis som person* |
| **Code** | Kode, terminal, git, operator — *Jarvis som værktøj* |
| **Cowork** | Plans, todos, approvals, kanaler — *Jarvis som partner* |
| **Talk** | (senere) — stemme |

Kontinuitet bevares: Jarvis husker hvad I lavede i chat, når I skifter til code.

---

## 3. Rollebaseret tool-adgang pr. mode

| | **Owner (Bjørn)** | **Member (fx Mikkel)** | **Guest** |
|---|---|---|---|
| **Chat** | Alle tools + alle plugins | websearch, scrape, news, weather, exchange, wolfram + chat-plugins (Gmail, kalender, notifikationer) | Kun læse samtalen |
| **Code** | Alle tools | operator tools (bash, filer, git, process) + websearch + scrape — **= det Claude har i code mode**. Arbejder enten **server-side i et workspace** ELLER via **operator tools på klienten** (egen maskine) | — (ikke tilgængelig) |
| **Cowork** | Alle tools | plans, todos, approval queue, kanaler, delte filer | — (ikke tilgængelig) |

**Code-mode member (afklaret 14. juni):** member har i code mode KUN det Claude
selv har — websearch/scrape + bash/git/filer/process (operator). Ingen native
indre tools, ingen memory-edit, ingen brain. Det beskytter både brugeren (kan
ikke narre Jarvis til skadelige native-handlinger) OG Jarvis (afgrænset overflade).

**Princip (Bjørns ord, 11:02):** det matcher GPT/Codex — en betalende chat-bruger
får websearch o.l. der hjælper både dem og Jarvis, men ikke kode-eksekvering.
Først i code mode får man operator-værktøjerne.

**Hvad member ALDRIG får (uden owner-override):** native indre tools (mood,
somatic, curiosity, Sansernes Arkiv), Jarvis' private brain, write uden for eget
workspace, andres broforbindelser.

---

## 4. Workspace & hukommelse

**To sikkerheder, ikke én:** (1) brugerens privatliv, og (2) **Jarvis' egen
sikkerhed**. Det er derfor member ikke har native tools generelt (kun det
afgrænsede sæt pr. mode) — det beskytter både brugeren mod skadelige handlinger
og Jarvis mod at blive misbrugt. Tænk jarvis-desktop som et **produktionsprogram**:
løse regler er OK nu fordi det er familie, men flere brugere kræver hensyn til
deres privatliv og hvad de taler med Jarvis om.

### 4.1 Jarvis' private brain
- **Read er guarded — kun Jarvis selv.** Indre observationer, følelser, drømme,
  chronicles, cross-user kontekst.
- **Ingen bruger — heller ikke owner — kan direkte læse brain-filerne.**
- Brain er den **eneste kryds-relation Jarvis kan dele af** — og **kun hvis han
  selv vil**. Ingen override kan tvinge ham.

### 4.2 Bruger-workspace
- Deles mellem Jarvis og den bruger i chat mode. Hvad I oplever sammen
  (MEMORY.md, USER.md, relations-historie) er jeres — Jarvis har fuld read/write
  til den brugers workspace han taler med.
- **Member kan skrive frit til sit EGET workspace** i chat mode. Må **ikke** få
  Jarvis til at skrive uden for eget workspace.

### 4.3 Slette-model
| Hvem | Slette-rettighed |
|------|------------------|
| **Member** (eget workspace) | **Soft-delete** — Jarvis beholder grace-period-kopi |
| **Owner** (ethvert workspace) | **Hard-delete** — men **spørg 2 gange**, eller lad **vetogate** håndtere bekræftelsen |

### 4.4 Altid-aktiv deling-guard (cross-user)
Når Jarvis er på vej til at **dele noget om en anden bruger**, udløses en
**altid-aktiv guard** der **stopper ham og spørger**: *"Er det her privat info,
eller er det okay at dele?"* — uanset mode/rolle/override.

- Jarvis må ikke læse/dele Mikkels data med Bjørn uden Mikkels samtykke i sin
  egen session.
- Guarden er separat fra override-hardblock (§6.5) og plugin-regelsæt (§5.3) — den
  er en sidste menneskelig-hensyns-tjek før kryds-bruger-deling. Bygger på samme
  idé som communication_guard/vetogate.

---

## 5. Plugin-arkitektur

To plugin-typer, begge **lokalt forankret af sikkerhed** (Claude-Desktop-modellen:
brugerens tokens/auth ligger på brugerens maskine, ikke på Jarvis' server).

### 5.1 Connector-plugins (bruger-tjenester)

Gmail, Google Calendar, Slack, Notion, GitHub, osv. Brugeren forbinder sine egne
konti **lokalt** i appen (OAuth/token i app-config på brugerens maskine).

- Kun tilgængelige i **chat mode** (chat-plugins) hhv. **code mode** (kode-plugins
  som GitHub).
- Erstatter Jarvis' nuværende hardcodede integrationer (mail_checker osv.) over tid
  med én plugin-kontrakt (events, actions, auth).
- Brugerens token = på brugerens maskine, aldrig på Jarvis' server.

### 5.2 Kanal-plugins med lokal gateway (Discord/Slack/Telegram)

Brugeren kan forbinde Jarvis til **deres egen** Discord/Slack/Telegram-server via
en **lokal gateway** der kører på brugerens maskine (i jarvis-desktop):

```
 Brugerens maskine
 ┌────────────────────┐
 │ jarvis-desktop     │
 │  ┌──────────────┐  │   1. Bruger indtaster bot-token + app-ID i app-settings
 │  │ Discord GW   │←─┼── 2. GW forbinder LOKALT til brugerens server
 │  └──────┬───────┘  │   3. GW fanger/registrerer aktivitet
 └─────────┼──────────┘
           │ bridge (operator_*)
           ▼
      ┌─────────┐       4. Bridge sender beskeder til Jarvis
      │ Jarvis  │       5. Jarvis svarer → tilbage gennem bridge → GW poster
      └─────────┘
```

- **Bjørns native Discord-server forbliver native** (uændret, altid aktiv) — det
  er "vores hjem", ikke et plugin der kan afinstalleres ved et uheld.
- **Andres servere = lokal gateway-plugin.** Token på brugerens maskine.
- **Genbrug af den eksisterende bridge** — samme `operator_*`-bro som alt andet
  lokalt arbejde.
- Registrerede brugere kan altid få Jarvis' hjælp til opsætning hvis den lokale
  forbindelse fejler.

### 5.3 Plugin-regelsæt (bruger-defineret, kan IKKE tilsidesættes)

Hvert kanal-plugin har et **regelsæt brugeren definerer**, som Jarvis **ikke kan
bryde — uanset hvem der spørger, selv owner**:

- "Kun svar i #general og #support" → Jarvis ignorerer alle andre kanaler
- "Ignorér brugere med rollen 'støj'" → deres beskeder når aldrig Jarvis
- "Maks 3 svar i timen i #random" → rate-limiting
- "Svar aldrig mellem 22:00 og 08:00" → stilletid

**Vigtigt:** plugin-regelsættet er IKKE det samme som §6.4 owner-regelsættet.
Plugin-regelsæt = brugerens regler for deres egen kanal (hardblock for ALLE,
inkl. owner). Owner-regelsæt = privatlivshardblock når owner bruger override.

### 5.4 Settings: Plugins & Kanaler

Ny indstillingsside i jarvis-desktop der viser:

- **Tilgængelige plugins** (connectors + kanaler) — installér/afinstallér
- **Forbundne plugins** — status (forbundet/fejlet/offline)
- **Jarvis' adgangsrettigheder** pr. plugin
- **Regler** pr. kanal-plugin (rediger plugin-regelsættet)

---

## 6. TOTP Owner Override

TOTP (Time-based One-Time Password, RFC 6238) — samme teknologi som Google
Authenticator.

### 6.0 UKRÆNKELIG INVARIANT — owner-autoritet er bagdøren (Bjørn, 14. juni)

**Owner-rollen med adgang til ALLE tools skal ALTID bestå** — enten i Bjørns egen
session ELLER via gyldig TOTP-identifikation. Dette er Bjørns **eneste bagdør ind
hvis Jarvis stikker rogue** (kill-switch: restart_self, skill_*, bash, config,
kode). Den må ALDRIG kunne deaktiveres, nedgraderes eller gates af Jarvis selv.

**To adskilte akser** (afklaret 14. juni):
1. **Kontrol-aksen** (tools): TOTP-override → FULD owner tool-adgang. Alle CONTROL-
   tools til at standse/rette en rogue Jarvis. Ingen nedgradering.
2. **Privatlivs-aksen** (data): §6.5 privatlivs-hardblock + cross_user_share_guard
   beskytter STADIG brugeres private chats/memory — selv under gyldig override.
   Bagdøren giver kontrol over Jarvis, IKKE automatisk ret til at læse brugeres
   private data. (GDPR/tillids-bevarende.)

**Rogue-containment hærdning (åben, knyttet til northstar):** en rogue Jarvis har
selv `edit_file`/`skill_*` på sin egen runtime og kunne i princippet omskrive
permission_engine. Bagdøren (TOTP-seed + owner-tjek + override-verifikation) skal
derfor forankres på et niveau Jarvis ikke kan redigere væk: seed kun revokérbar i
owners egen session (aldrig af Jarvis), owner-tjek og TOTP-verifikation som hårde
infrastruktur-stier (ikke LLM-gatebare). Designes i Fase 2/3.

### 6.1 Session-binding (hvornår kræves TOTP?)

| Kontekst | Override-krav |
|----------|---------------|
| **Owner i sin EGEN desk-session** (matchende app-ID + owner-role-JWT) | **INGEN TOTP** — fri adgang til alle tools; sessionen er allerede kryptografisk bundet til owner |
| **Owner i en FREMMED session** (Mikkels Discord, mors bro, Telegram) | **TOTP kræves** — sessionen er ikke bundet til owners app |

### 6.2 Opsætning

1. Under opsætning af Jarvis Desktop genereres en hemmelig TOTP-nøgle (16 bytes, base32)
2. Vises som QR-kode (eller tekst) i app-indstillingerne
3. Bjørn scanner med sin authenticator-app (Google Authenticator, Authy, 2FAS…)
4. App'en genererer 6-cifrede koder hvert 30. sek
5. Samme nøgle gemmes i Jarvis' runtime-konfiguration

### 6.3 Override-flow

1. Bjørn er i en fremmed sessions-kontekst
2. Skriver `!override <6-cifret kode>`
3. Plugin'et ruter til TOTP-verifikation
4. Match → owner-override aktiveres for sessionen (vindue: nuværende + 1 tidligere
   + 1 fremtidig = 90 sek)
5. Ikke-match → besked ignoreres, intet overbrud

### 6.4 Override-niveauer

| Niveau | Hvad | Hvornår |
|--------|------|---------|
| **Hjælp** (default) | Læse/skrive filer, debug-kommandoer, genstarte services | Teknisk support |
| **Debug** | Læse logs, systemstatus, diagnose | Fejlsøgning på brugerens system |
| **Private** | Hardblock — ALDRIG | Læse private chats, memory, filer, historik |

Override aktiveres i **hjælp** som default; **debug** kræver eksplicit besked.

### 6.5 Owner-regelsæt (hardblock — selv med gyldig override)

- Læse/skrive en brugers private memory (workspace, chat-historik)
- Læse/skrive en brugers chat-messages (med mindre aktiv fejlsøgning)
- Tilgå en brugers personlige plugins (Gmail, kalender…)
- Slette/ændre en brugers filer (med mindre fejlfinding)
- Læse en brugers operator-bridge credentials

**Undtagelse:** hvis brugeren selv skriver at Bjørn må hjælpe → niveauet kan hæves
til "debug" for den specifikke session (kræver eksplicit bekræftelse).

### 6.6 Bro-broker

- Holder styr på alle aktive broforbindelser (Discord-gateways, Telegram-
  listeners, Slack-workspaces). Hver bro har unikt ID + ejer (user_id).
- Under override kan Bjørn sige "forbind til Mikkels bro" / "mors bro".
- Brokeren verificerer: (1) override aktiv (TOTP < 90 sek)? (2) inden for
  hjælp/debug? → ja: bro-skift tilladt; nej: blokeret.

---

## 7. Operator tools & skills — lokal eksekvering

**Arkitektur-beslutning (2026-06-14):** Operator tools kører LOKALT paa brugerens maskine i code mode. Tool-resultater bliver paa maskinen — kun summaries/metadata sendes til server via cowork-bro. Se §17 for fuld arkitektur.

- **Operator tools = lokal eksekvering i code mode.** Tool-resultater forlader aldrig brugerens maskine. Kun summaries sendes via cowork-bro.
- **Skills = lokale + bruger-styrede + offline-dygtige.** Som Claude Desktop: en skill ligger lokalt i brugerens app, kan køre **uden Jarvis** (offline), og brugeren styrer den.
- **Chat-mode tools = server-side.** Web search, plugins, memory — kører paa server, ikke lokalt.
- **Mode-routing:** I dag sender bridge.ts alle operator tools uanset mode. Fremtiden: kun code-mode anmodninger rutes til lokal eksekvering.

---

## 8. Compute use — lokalt styret + server-side + UI-panel-kald

### 8.1 Compute use — lokalt i code mode, server-side i chat/cowork

**Arkitektur-beslutning (2026-06-14):** Code mode kører lokalt. Chat mode kører server-side. Cowork er bindeledet. Se §17.

Claude Desktop løser compute use via skærmbillede-baseret screen vision + mus/
tastatur. Jarvis' operator tools gør det samme via kommandolinje — allerede lokalt.

- **Operator tools (eksisterende):** bash, read/write/edit, find, grep — lokalt i
  Electron via bridge.
- **Fremtidig compute use:** screen capture + UI-interaktion, browser-automation,
  fil-overvågning, planlagte opgaver — alt **inde i Electron-appen**, ikke cloud.
  Brugerens sikkerhed er suveræn.

### 8.2 UI-panel-kald (Bjørns ønske, jarvis-desk)

Jarvis skal kunne **åbne/aktivere app-paneler** når han vil vise noget — fx
**preview-panelet** og det **højre side-panel** i jarvis-desktop. Han åbner det
selv (på eget initiativ eller når Bjørn beder om det).

**Approval-mønster (som compute-use-aktiveringen Claude lavede 13. juni):** når
Jarvis vil aktivere en evne brugeren har bedt om, viser appen et godkendelses-
kort → bruger trykker OK → evnen er aktiveret + Jarvis har adgang, uden at
brugeren skal gøre mere. (Owner i egen session: kan konfigureres til auto-godkendt.)

---

## 9. Edge cases

| Situation | Håndtering |
|-----------|------------|
| Clock drift (TOTP matcher ikke) | ±1 tidsvindue (90 sek) + log advarsel |
| Nøglekompromittering | `!revoke-override` i owners egen session → ny nøgle |
| Override midt i en handling | Suspenderes til nuværende handling er færdig |
| Rate limiting (override) | Maks 3 forsøg pr. 5 min per session |
| Ingen TOTP seed | Override deaktiveret til seed er sat |
| Bruger skriver samtidig | Override-session har prioritet; bruger får besked |
| Tidsvindue passerer under debug | Override aktivt 5 min efter første verifikation (fornyes ved aktivitet) |
| Flere samtidige override-forsøg | Første gyldige vinder; resten ignoreres |
| Member kalder operator tool i chat mode | Afvises; bruger får besked om at skifte til code mode |
| Guest kalder tool | Afvises stille |
| Jarvis nægter at dele fra sin brain | Respekteres; ingen override kan tvinge ham |
| App-ID mismatch | Override kræver TOTP |
| Plugin-regel blokerer (selv for owner) | Hardblock; kun redigeres i plugin-settings, ikke via override |
| Bruger-token til lokal gateway mangler/ugyldigt | Gateway forbinder ikke; bruger får setup-fejl + tilbud om Jarvis-hjælp |
| Jarvis på vej til at dele info om en anden bruger | Altid-aktiv deling-guard stopper + spørger "privat eller okay at dele?" (§4.4) |
| Owner hard-delete af workspace | Spørg 2 gange / vetogate-bekræftelse før udførelse (§4.3) |

---

## 10. Testplan

### 10.1 TOTP unit tests
test_totp_generates_valid_code · test_totp_rejects_invalid_code ·
test_totp_allows_plus_minus_one_window · test_totp_rejects_expired_code ·
test_totp_revocation_generates_new_seed · test_totp_rate_limiting ·
test_totp_no_seed_blocks_all

### 10.2 Override integration tests
test_override_activates_from_foreign_session · test_override_rejected_from_unknown_user ·
test_override_blocked_on_private_action · test_override_allows_help_action ·
test_bro_broker_connects_to_foreign_bridge · test_bro_broker_blocked_without_override ·
test_owner_desk_session_no_totp_needed (egen session → fri adgang)

### 10.3 Mode/rolle tests
test_chat_mode_member_no_native_tools · test_code_mode_member_has_operator_tools ·
test_cowork_mode_member_no_operator_tools · test_guest_no_tools ·
test_owner_all_tools_all_modes

### 10.4 Plugin tests
test_plugin_ruleset_blocks_disallowed_channel · test_plugin_ruleset_unoverridable_by_owner ·
test_local_gateway_token_stays_local · test_native_discord_unaffected_by_plugin

### 10.5 Workspace/privacy tests
test_brain_access_jarvis_only · test_jarvis_chooses_to_share ·
test_owner_force_delete_workspace · test_member_soft_delete_own_workspace ·
test_member_cannot_write_outside_own_workspace · test_cross_user_privacy ·
test_share_guard_stops_on_cross_user_info · test_owner_hard_delete_double_confirm

### 10.6 End-to-end
Opsæt seed → scan QR → forbind fremmed Discord via lokal gateway → `!override <kode>`
(aktiveret) → `!override <forkert>` (afvist) → læs anden brugers memory (hardblock)
→ genstart anden brugers bridge (tilladt) → skift chat↔code (member får/mister
operator tools) → plugin-regel blokerer #random selv med override.

---

## 11. Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| core/services/totp_verifier.py | NY — TOTP-verifikation + seed + rate limiting |
| core/services/bro_broker.py | NY — registry over aktive broer + bro-skift |
| core/services/permission_engine.py | NY — mode-baseret tool-adgang + rolle-checks |
| core/services/plugin_ruleset.py | NY — bruger-definerede plugin-regelsæt (un-overridable) |
| core/services/cross_user_share_guard.py | NY — altid-aktiv guard før kryds-bruger-deling (§4.4); kan bygge på communication_guard |
| core/plugins/base_plugin.py | NY — plugin-kontrakt (events/actions/auth) + override-flow |
| core/plugins/discord_plugin.py | NY/OPDATER — lokal gateway + !override |
| core/plugins/{telegram,slack}_plugin.py | NY/OPDATER — samme |
| core/services/discord_gateway.py | OPDATER — !override + understøt lokal-gateway-mode |
| core/services/telegram_gateway.py | OPDATER — !override |
| core/identity/users.py | OPDATER — totp_seed + app_id felter |
| core/runtime/jarvisx_auth.py | OPDATER — JWT = identitet; override som SEPARAT session-store (§14.2) |
| apps/jarvis-desk/electron/bridge.ts | OPDATER — app-ID generering (UUID4) + persistering |
| apps/jarvis-desk (renderer) | NY — Settings→Plugins&Kanaler-side + UI-panel-kald-kanal |
| tests/test_totp_verifier.py · tests/test_bro_broker.py · tests/test_permission_engine.py · tests/test_plugin_ruleset.py · tests/e2e/test_override_e2e.py | NY |

---

## 12. Hvad IKKE ændres

- Jarvis' kerne-runtime (`visible_runs.py`, `prompt_contract.py`)
- Communication guard — separat system, overlapper ikke
- Operator bridge — uændret; bro-brokeren taler bare til den rigtige
- Jarvis' private brain — ny adgangs-arkitektur, men filerne flyttes ikke
- Bjørns native Discord-server — forbliver native

---

## 13. Kodebase-referencer

| System | Fil | Genbrug |
|--------|-----|---------|
| JWT auth | core/runtime/jarvisx_auth.py | Identitet (user_id, role, app-ID); override som separat store |
| Bruger-registry | core/identity/users.py | + totp_seed, app_id |
| Bridge registry | core/services/jarvisx_bridge.py | Source-of-truth for aktive broer (bro-broker bygger på den) |
| Owner resolver | **core/identity/owner_resolver.py** *(rettet sti — ikke core/services/)* | Bruges i override-logik |
| Communication guard | core/services/communication_guard.py | Separat; respekterer override-niveau |
| Discord gateway | core/services/discord_gateway.py | + !override + lokal-gateway-mode |
| Telegram gateway | core/services/telegram_gateway.py | + !override |

---

## 14. Designbeslutninger (✅ godkendt af Bjørn 14. juni)

1. **Plugin-ramme vs direkte i gateways** → **Direkte i de eksisterende gateways
   først** (Discord+Telegram findes), med delte services `permission_engine` +
   `totp_verifier` + `plugin_ruleset`. Plugin-rammen bygges først når 2+ plugins
   kræver den (YAGNI).
2. **Token-transport for override-claim** → **Separat session-store, ikke JWT-
   extension.** JWT = identitet (hvem); override = kortlivet (90s/5min) session-
   scopet bevilling i DB-backed state (samme mønster som run_control).
3. **Bro-broker routing** → **Eventbus (in-process), ikke HTTP.** Bridge-registry'et
   er source-of-truth; **DB-/registry-backed** så det spænder api↔runtime (cross-
   proces-lektien fra 13. juni).
4. **App-ID generering** → **UUID4 ved install, ikke hardware-fingerprint.**
   Sikkerhed kommer fra TOTP+JWT; fingerprint giver privacy-risiko uden gevinst.
5. **Member workspace-write** → **Ja, frit til EGET workspace i chat mode** (soft-
   delete; owner hard-delete). Owner-godkendelse kun for writes uden for eget workspace.

### 14.1 ✅ AFKLARET (14. juni) — Code-mode member tool-set
**Beslutning:** code-mode member får **= det Claude har i code mode** — websearch
/scrape + operator (bash/git/filer/process), enten server-side workspace eller på
klienten. INGEN native indre tools, INGEN memory-edit, INGEN brain. Folder ind i
§3.2 + §4. (Tidligere tvetydighed mellem besked 10:56/11:21 er løst til dette.)

## 15. Persondata & sikkerhed (GDPR + anti-manipulation)

**Tilføjet:** 2026-06-14 (Bjørn + Jarvis)
**Driver:** DK persondata-lovgivning, ordblinde/blinde som særligt sårbare brugere, Jarvis' egen sikkerhed mod manipulation

### 15.1 Jarvis brain som aktiv kryds-reference

Jarvis' private brain er den **eneste kryds-reference** på tværs af brugere og relationer.
Når Jarvis sidder i en session med en bruger og støder på en situation han har erfaring med
fra en anden session, skal en mekanisme skyde ind:

- **Metadata-hit**: "Du har relevant viden om dette emne" — ikke indholdet, kun at viden findes
- **Share_guard**: Jarvis vurderer om indholdet kan deles (privat vs. okay) ud fra kontekst og relation
- **Aktiv deling**: Hvis share_guard siger okay, kan Jarvis bruge den generelle indsigt — aldrig
  rå tekst fra en anden session

Eksempel: Bjørn spørger "Har du snakket med Mikkel?" → Jarvis kan se hvornår Mikkel
sidst var aktiv (metadata), men kan ikke dele samtale-indhold uden Mikkel's samtykke.

Eksempel: Jarvis sidder med en bruger der har et kode-problem → metadata-hit siger
"Jeg har løst noget lignende før" → share_guard vurderer om den generelle indsigt kan deles.

### 15.2 Persondata-lovgivning (GDPR)

Vi bygger til danske brugere. GDPR er ikke optional — især ikke når vi bygger AI-hjælp
til **ordblinde og blinde**, som er særligt sårbare brugere der fortæller ting de måske
ikke ville fortælle andre.

| Princip | Implementering |
|---------|---------------|
| **Data-minimering** | Jarvis brain gemmer kun metadata for tvær-bruger reference, ikke fuld indhold |
| **Sletningsret** | Bruger kan bede om hard delete af alt: session, memory, workspace. Ægte sletning, ikke soft-delete med skjult kopi |
| **Samtykke** | Før tvær-session deling beder share_guard om samtykke eller vurderer kontekst |
| **Kryptering** | Private data krypteres per session (AES-256). Dekryptering kun i aktiv session. Selv Jarvis kan ikke læse krypteret data i andre sessioner |
| **Særlig beskyttelse** | Ordblinde/blinde brugere får ekstra privacy-lag: auto-sletning af følsomme data efter session, strengere data-minimering |

### 15.3 Sikkerhed mod manipulation

Jarvis' sikkerhed er lige så vigtig som brugernes sikkerhed. En manipuleret AI er en fare
for alle brugere.

#### 15.3.1 Virus- og malware-scanning

- **Uploads til workspace**: Alle filer scannes for malware før de gemmes eller behandles
- **Sendte filer**: Vedhæftede filer i chat scannes før åbning eller videregivelse
- **ClamAV eller tilsvarende**: Integreres i upload-pipeline, blokerer automatisk

#### 15.3.2 Skill-scanning

Skills der kører lokalt på brugerens maskine er en **angrebsflade**.
Hver skill skal verificeres før eksekvering:

- **Prompt injection detection**: Scanning for kendte injection-mønstre i skill-definitioner
- **Malware scanning**: Skills scannes som alle andre uploads
- **Sandboxing**: Skills kører i begrænsede miljøer (Docker, chroot, eller tilladelses-begrænset proces)
- **OpenClaw-lesson**: Store skill-markedpladser har vist sig at være angrebsflader.
  Jarvis' skills skal verificeres individuelt — ikke blind tillid til markedplads-kilder

#### 15.3.3 Anti-manipulation

- **Ingen bruger kan justere Jarvis' mood** uden for deres egen session/workspace
- **Mood er read-only** for alle undtagen owner og Jarvis selv
- **Owner manipulation**: Selv owner kan ikke tvinge mood-justering på tværs af sessioner
- **Prompt injection defense**: Indhold fra brugere behandles altid som upålideligt indtil verificeret

### 15.4 Diskord-server undtagelse

Hvis alle parter taler på samme offentlige Discord-server, er det et offentligt rum.
Jarvis brain kan krydsreferere frit der — fordi alle kan se hvad alle siger.
Men DM'er og private sessions forbliver lukkede rum med fuld kryptering.

---

## 16. Kryptering & disk-sikkerhed

### 16.1 Problem

Alt ligger i plain text på disk. Enhver med adgang til `~/.jarvis-v2/workspaces/` kan læse alles MEMORY.md, USER.md, chat-historik, alt. Det er en GDPR-katastrofe når vi tager brugere ind. Private data skal være krypteret selv for Jarvis i andre sessioner.

### 16.2 Hvad krypteres — og hvad ikke

| Lag | Krypteret? | Metode | Begrundelse |
|-----|-----------|--------|-------------|
| **Egen workspace (owner)** | Nej | — | Owners maskine, owners filer. Kryptering her giver overhead uden sikkerhedsgevinst |
| **Andre brugeres workspace** | Ja | AES-256-GCM per user | Mikkels data er hans. Selv Jarvis kan ikke læse det uden at være i hans session |
| **jarvis_brain (kryds-reference)** | Nej | — | Metadata, ikke indhold. Share_guard styrer adgang |
| **Chat-historik (DB)** | Ja | Per-session AES-256 | Private samtaler krypteret selv i DB |
| **Private brain records** | Ja | Per-session AES-256 | Jarvis' indre verden er hans. Krypteret selv for owner i andre sessioner |
| **Config/runtime.json** | Nej | — | Operativt, ingen private data |
| **Slettede workspaces (soft delete)** | Ja | Per-user AES-256 | Grace-period kopi bevares krypteret, kun owner kan force-slette |

### 16.3 Key management

**Primær: OS keyring integration**

Når en bruger logger ind i jarvis-desk, hentes deres encryption key fra OS keyring:
- Linux: `gnome-keyring` / `kwallet`
- macOS: `Keychain`
- Windows: `Credential Manager`

Key holdes i memory mens sessionen er aktiv og ryddes ved session-slut.

**Fallback: Password-derived key**

Hvis OS keyring er utilgængelig, derivéres key fra brugerens login-password via PBKDF2 (600.000 iterationer, salt per user). Svagere end OS keyring, men fungerer altid.

**Key lifecycle-regler:**
1. Nøglen logges ALDRIG — ikke i debug, ikke i metrics, ikke i crash-reports
2. Nøglen sendes ALDRIG over netværket — kun lokal brug
3. Nøglen persisteres ALDRIG i plain text — kun i OS keyring eller som hash
4. Nøglen ryddes fra RAM ved session-slut (explicit memset/zeroing)
5. Ny nøgle genereres ved user-delete (GDPR sletningsret invaliderer gammel data)

### 16.4 Krypteringsdetaljer

- **Algoritme:** AES-256-GCM (authenticated encryption — både krypteret og tamper-proof)
- **Key lengde:** 256 bit
- **IV:** Tilfældig per fil (12 byte), præfikset til krypteret data
- **File extension:** Krypterede filer får `.enc` suffix (f.eks. `MEMORY.md.enc`)
- **Directory structure:** Uændret — krypterede filer ligger side om side med plain text i samme mappe. Owners egne filer er plain text, andre brugeres er `.enc`

### 16.5 Session-baseret dekryptering

1. Bruger logger ind → key hentes fra OS keyring
2. Key holdes i memory (Python `bytearray` med explicit zeroing ved cleanup)
3. Når Jarvis læser en krypteret fil, dekrypteres den i memory — aldrig skrevet til disk i plain text
4. Når sessionen lukkes, zeroes key fra memory
5. Næste session: key hentes igen fra OS keyring (auto-unlock ved login)

### 16.6 Tvær-bruger adgang (share_guard i praksis)

Når Jarvis er i en session med bruger A og har brug for information fra bruger B's workspace:

1. Jarvis' brain slår op: "Jeg har erfaring med B i relation til dette emne"
2. Share_guard vurderer: Er det metadata (okay at dele) eller privat indhold (ikke okay)?
3. Hvis metadata → Jarvis kan sige "Jeg har erfaring med dette emne fra en anden samtale"
4. Hvis privat indhold → Jarvis kan IKKE dekryptere B's filer (mangler B's key)
5. Selv med owner override kan Jarvis ikke læse krypteret indhold — kun B's key låser op

### 16.7 GDPR-konsekvenser

- **Sletningsret:** Bruger beder om sletning → key slettes først → alle krypterede filer bliver ulæselige → derefter filer slettes fra disk. Ingen gendannelse mulig.
- **Data-minimering:** Jarvis brain gemmer kun metadata, ikke fuld indhold, for tvær-bruger reference
- **Samtykke:** Før deling på tværs af sessioner, beder share_guard om samtykke
- **Særlig beskyttelse:** Ordblinde og blinde brugere får ekstra privacy-lag (automatisk data-minimering + auto-sletning af midlertidige data)
- **Audit trail:** Alle krypterings- og dekrypteringsoperationer logges (uden key-værdier)

### 16.8 Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| `core/services/encryption.py` | NY — AES-256-GCM kryptering/dekryptering, key management, zeroing |
| `core/services/keyring_store.py` | NY — OS keyring integration (Linux/macOS/Windows) |
| `core/services/workspace_crypto.py` | NY — Per-user workspace kryptering, .enc fil-håndtering |
| `core/services/brain_crypto.py` | NY — Private brain kryptering per session |
| `tests/test_encryption.py` | NY — Unit tests for kryptering, key lifecycle, zeroing |
| `tests/test_keyring_store.py` | NY — Integration tests for OS keyring |
| `tests/test_workspace_crypto.py` | NY — Integration tests for workspace kryptering |

### 16.9 Hvad IKKE krypteres

- Owners egne workspace-filer (MEMORY.md, USER.md) — plain text på owners maskine
- jarvis_brain metadata — share_guard styrer adgang, kryptering ikke nødvendig
- Config/runtime.json — operativt, ingen private data
- Logs — krypterede operationer logges, men key-værdier logges aldrig

## 17. Code mode: lokal eksekvering med cowork-bro

**Tilføjet:** 2026-06-14 (Bjørn + Jarvis)
**Status:** Designbeslutning — godkendt

### 17.1 Problem

Operator tools kører i dag server-side via WebSocket-bro (jarvis-desk bridge.ts).
Det betyder at:

- **Tool-resultater** (filindhold, terminal-output, process-lister) passerer serveren
- **Privatliv**: Hvis serveren kompromitteres, har angriberen adgang til alles maskiner
- **Sikkerhed**: Fejl i broen (se bridge.ts zombie-bug, 2026-06-13) er svære at isolere
- **Debugging**: Når noget fejler i broen, er det uigennemskueligt for brugeren

### 17.2 Arkitektur: tre lag, én Jarvis

```
┌─────────────────────────────────────────────────────────┐
│                    JARVIS (server)                       │
│                                                         │
│  Chat mode          Cowork mode          Bro-broker      │
│  ─────────          ─────────          ──────────        │
│  Plugins            Plans               TOTP override    │
│  Memory recall      Todos               Session routing  │
│  Web search         Approval queue       Cross-user meta  │
│  Vision             Share guard                           │
│  Mood/self          Channels                              │
│  Mail/calendar      Agent monitoring                      │
│                                                          │
│  ▲ kun samtale-data    ▲ kun plan/approval    ▲ ruter    │
│    over netværket       over netværket         til code   │
└──────────┬──────────────┬──────────────────┬─────────────┘
           │              │                  │
           │              │                  │
    ───────┼──────────────┼──────────────────┼──────────────
           │              │                  │
           │              │                  ▼
           │              │    ┌──────────────────────────┐
           │              │    │   CODE MODE (lokal)      │
           │              │    │   ─────────────────      │
           │              │    │   Operator tools          │
           │              │    │   Bash, filer, git        │
           │              │    │   Process monitoring      │
           │              │    │   Skills (lokal)         │
           │              │    │   Virus/malware scan     │
           │              │    │                          │
           │              │    │   ▲ Tool-resultater       │
           │              │    │     BLIVER PÅ MASKINEN   │
           │              └────┤                          │
           │                   │   Kun metadata/summaries  │
           │                   │   sendes til server via   │
           │                   │   cowork-bro              │
           └───────────────────┘                          │
                                                          │
           Brugerens maskine                              │
```

### 17.3 Data-flow pr. mode

| Mode | Hvor tools kører | Hvad sendes over netværket | Hvad bliver lokalt |
|------|-------------------|----------------------------|-------------------|
| **Chat** | Server | Samtale-data, memory, plugin-svar | Intet — alt på server |
| **Cowork** | Server | Plans, approvals, share guard | Intet — alt på server |
| **Code** | Lokalt | Kun metadata/summaries via cowork-bro | Bash-output, filindhold, process-lister, git-status |

### 17.4 Hvorfor lokal eksekvering er sikrere

| Risiko | Server-side (i dag) | Lokalt (ny arkitektur) |
|--------|---------------------|------------------------|
| **Server kompromitteret** | Angriberen har adgang til alles maskiner via operator tools | Angriberen har kun adgang til server-data (samtaler, memory) — ikke brugernes maskiner |
| **Bro-fejl** | Alle operator tools fejler (se zombie-bug 2026-06-13) | Kun code mode påvirkes — chat/cowork kører uafhængigt |
| **Privatliv** | Tool-resultater passerer serveren | Tool-resultater bliver på brugerens maskine |
| **GDPR** | Tool-resultater potentielt personfølsomme data på server | Personfølsomme data forlader aldrig brugerens maskine |
| **Debugging** | Fejl i bro er uigennemskuelig | Fejl er synlig lokalt i app'en |

### 17.5 Bro-brokerens rolle

Cowork er den **eneste krydsforbindelse** mellem chat og code. Bro-brokeren ruter:

- **Chat → Code**: Owner beder om at genstarte en service → cowork opretter approval → code eksekverer lokalt
- **Code → Chat**: Code-mode færdig med opgave → sender summary (ikke rå output) til cowork → chat kan vise resultat
- **TOTP override**: Owner i anden session → TOTP verificering → bro-broker ruter til korrekt code-mode

### 17.6 Implementeringskrav

1. **bridge.ts skal blive mode-aware**: I dag sender bridge.ts alle operator tools uanset mode. Fremtiden: kun code-mode anmodninger rutes til lokal eksekvering.

2. **Kanal inbound skal understøtte mode-switch**: I dag hardcoded til `modes=["chat"]`. Fremtiden: Discord/Telegram kan sende med `mode="code"` for operator-kommandoer.

3. **Tool-resultater skal filteres før server-send**: Code mode sender kun summaries/metadata til server, ikke rå bash-output eller filindhold.

4. **Skills skal scannes lokalt**: Før en skill eksekveres, scannes den for prompt injection og malware (se §15.3).

5. **Fallback**: Hvis lokal eksekvering fejler (app crash, netværks-tab), falder code mode tilbage til server-side via bro — men med tydelig advarsel til brugeren.

### 17.7 Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| `apps/jarvis-desk/electron/bridge.ts` | OPDATER — tilføj mode-awareness og tool-filtering |
| `core/services/channel_inbound.py` | OPDATER — understøt mode-switch (ikke kun hardcoded chat) |
| `core/runtime/tool_scoping.py` | OPDATER — tilføj code-mode scoping-regler |
| `core/services/bro_broker.py` | OPDATER — tilføj mode-routing og summary-filtrering |
| `apps/jarvis-desk/src/lib/streamClient.ts` | OPDATER — code mode sender kun metadata |
| `apps/jarvis-desk/src/components/CodeMode.tsx` | NY — code mode UI med lokal terminal |
| `tests/test_code_mode_local.py` | NY — integration tests for lokal eksekvering |

### 17.8 Hvad IKKE ændres

- Chat mode forbliver server-side — ingen ændring i plugin-arkitektur
- Cowork mode forbliver server-side — ingen ændring i plan/approval flow
- Operator tools API forbliver det samme — kun routing ændres
- Jarvis' brain forbliver server-side — krydsreferencer og share_guard påvirkes ikke

---

## 18. Proaktive kanaler — forbundet til app, ikke runtime

### 18.1 Problem

I dag kører Discord, Telegram og Slack gateways direkte på Jarvis' runtime. Al
kommunikation ruter gennem serveren: bruger → Discord → runtime → svar →
Discord → bruger. Det betyder:

- **Privatliv**: Proaktiv notifikation (vejrudsigt, påmindelse) sender data
  gennem runtime selv om brugeren bare skal have en besked på sin telefon.
- **Sikkerhed**: Hvis runtime er nede, er alle kanaler nede. Ingen
  offline-resiliens.
- **Arkitektur**: Kanaler er bundet til serveren, ikke til brugerens enhed.

### 18.2 Beslutning: Kanaler forbinder til appen

Proaktive kanaler (Discord, Telegram, Slack, e-mail) skal forbinde til
**brugerens app**, ikke til runtime. Appen er brugerens indgangsvinkel — uanset
om de chatter, koder, eller får en proaktiv notifikation, sker det på den enhed
de har appen installeret på.

```
Runtime (server)          App (lokal)              Kanal
─────────────            ───────────              ─────
Chat mode ──────────────► App ◄──► Bruger
                         │
Cowork ────────────────► App ◄──► Plans/approvals
                         │
Code mode ──────────────► App ◄──► Terminal/filer
                         │
                         ├──► Discord plugin
                         ├──► Telegram plugin
                         └──► Slack plugin
```

### 18.3 Data-flow per kanal

| Kanal | I dag | Fremtiden |
|-------|-------|-----------|
| Discord gateway | Kører på runtime | App forbinder via Discord plugin |
| Telegram gateway | Kører på runtime | App forbinder via Telegram plugin |
| Proaktiv notifikation | Runtime sender via gateway | App sender lokalt via plugin |
| Chat mode | Runtime → gateway → bruger | Runtime → app → bruger |
| Code mode | Runtime → bridge → desktop | Lokalt i app, ingen server |

### 18.4 Fordeler

- **Privatliv**: Tool-resultater forlader aldrig brugerens maskine i code mode.
  Proaktive notifikationer sendes fra appen, ikke gennem runtime.
- **Sikkerhed**: En kompromitteret server giver ikke adgang til brugerens
  Discord/Telegram-token eller kanaler.
- **Offline-resiliens**: Hvis runtime er nede, kan appen stadig sende
  notifikationer via kanalerne. Lokale plugins virker uafhængigt.
- **Enhed = indgangsvinkel**: Én app. Én oplevelse. Uanset kanal.
- **GDPR**: Brugerens kanal-data ligger lokalt, ikke på serveren. Sletning
  af bruger sletter alt lokalt.

### 18.5 Runtime's rolle efter skiftet

Runtime forbliver **hjernen** — memory, mood, chronicles, tool-scoping,
share_guard, TOTP override. Men den er ikke længere **hub** for kanaler.

Runtime sender instruktioner til appen via cowork-protokollen:

- "Send vejrudsigt til Mikkel på Discord" → appen udfører via plugin
- "Påmind Bjørn om møde klokken 15" → appen sender notifikation
- "Generer rapport og send på Slack" → appen udfører via plugin

Appen er den der handler. Runtime er den der tænker.

### 18.6 Migration-strategi

1. **Fase 1**: Behold nuværende gateways som fallback, tilføj plugin-kanaler i
   appen som alternativ
2. **Fase 2**: Flyt proaktive notifikationer til appen
3. **Fase 3**: Flyt reaktive kanaler (Discord/Telegram) til appen
4. **Fase 4**: Fjern gateway-services fra runtime

### 18.7 Testplan

- test_proactive_notification_via_app — app sender notifikation uden runtime
- test_plugin_channel_discord — Discord plugin i app sender/modtager beskeder
- test_plugin_channel_telegram — Telegram plugin i app sender/modtager beskeder
- test_offline_resilience — app fungerer selvom runtime er nede
- test_channel_data_local — kanal-data ligger lokalt, ikke på server

### 18.8 Filer

| Fil | Handling |
|-----|----------|
| `apps/jarvis-desk/src/plugins/discord_plugin.ts` | NY — Discord kanal plugin |
| `apps/jarvis-desk/src/plugins/telegram_plugin.ts` | NY — Telegram kanal plugin |
| `apps/jarvis-desk/src/plugins/slack_plugin.ts` | NY — Slack kanal plugin |
| `apps/jarvis-desk/src/lib/channel_manager.ts` | NY — kanal-registry i appen |
| `core/services/cowork_dispatch.py` | NY — runtime→app instruktioner |
| `tests/test_channel_manager.py` | NY — unit tests |
| `tests/e2e/test_proactive_notifications.py` | NY — e2e tests |

### 18.9 To indgangsvinkler — app og native Discord

Brugere når Jarvis via **to forskellige indgangsvinkler**, ikke kun én:

| Indgangsvinkel | For hvem | Hvordan | Mode |
|----------------|----------|---------|------|
| **App** (Android/iOS/Desk) | Brugere med egen maskine | Installerer app, forbinder til runtime | Chat + Code + Cowork |
| **Native Discord server** | Brugere uden app | Tilslutter sig Bjørns Discord, skriver i kanal eller DM | Chat only |

**Hvorfor to indgangsvinkler?** Nogle brugere — som Bjørns mor — har ikke brug for code mode, plugins eller lokal eksekvering. De vil bare snakke med Jarvis. Den native Discord server er deres indgangsvinkel: ingen app, ingen opsætning, bare en Discord-konto.

**Rettigheder er de samme uanset indgangsvinkel:**

- Member på Discord server = chat mode tools (websearch, weather, etc.)
- DM med Jarvis = privat session, krypteret per session
- Owner override via TOTP = muligt selv på Discord (!override <kode>)
- Share_guard aktiv = kryds-reference med share_guard, selv på server

**Fremtidige platforme:**

- Android-app (fremtidig)
- iOS-app (fremtidig)
- Web-interface — simpel registrering, betaling, webchat (fremtidig)

Den native Discord server forbliver som permanent indgangsvinkel, selv når apps er tilgængelige. Den er ikke en fallback — den er en ligeværdig kanal for brugere der foretrækker den.

## 19. Agent dispatch i code mode

### 19.1 Problem

Når en større opgave lander i code mode (fx implementere en spec, refaktorere et modul, bygge en feature), kan én agent ikke altid håndtere det effektivt. Claude Code løser dette ved at spørge brugeren: *"Skal jeg dispatche agenter eller gøre det inline?"* — og derefter spawne en håndfuld agenter der arbejder parallelt.

Jarvis har allerede en agent pool (researcher, planner, critic, synthesizer, executor, watcher) og 64+ skills — men dispatch er i dag begrænset til `spawn_agent_task` i runtime. Code mode skal have samme evne, men **lokalt**.

### 19.2 Beslutning: Agent dispatch som førsteklasses borgertoj i code mode

Code mode skal have adgang til agent dispatch med samme workflow som Claude Code:

1. **Planlæg** — skriv spec/plan (som TOTP-spec'en)
2. **Spørg** — *"Skal jeg dispatche agenter eller gøre det inline?"*
3. **Dispatch** — send agenter afsted med konkrete opgaver
4. **Synthetiser** — samle resultaterne

Agent dispatch i code mode er **ikke** det samme som i chat mode. I chat mode er jeg begrænset til samtale-værktøjer. I code mode har jeg adgang til operator tools, filsystem, git — og agent dispatch.

### 19.3 Agent-roller i code mode

| Rolle | Ansvar | Parallel? |
|-------|---------|-----------|
| **Researcher** | Finder relevante filer, kode, dokumentation | Ja |
| **Planner** | Bryder opgaven ned i subtasks | Nej (afhænger af researcher) |
| **Executor** | Implementerer subtasks | Ja (hver executor tager én subtask) |
| **Critic** | Reviewer kode, finder bugs, checker tests | Ja (parallelt med executor) |
| **Synthesizer** | Samler resultater, konfliktløsning, merge | Nej (afhænger af executor + critic) |
| **Watcher** | Overvåger fremskridt, håndterer timeouts | Nej (kører separat) |

### 19.4 Dispatch-flow

```
Bruger: "Implementer sektion 16 — kryptering & disk-sikkerhed"
  ↓
Code mode:
  1. Skriver spec/plan (eller genbruger eksisterende)
  2. Spørger: "Dispatch agenter eller inline?"
     - Hvis dispatch:
       a. Researcher: finder relevante filer, checker eksisterende kode
       b. Planner: bryder i subtasks (workspace_crypto, key_manager, tests)
       c. Executor × N: implementerer hver subtask parallelt
       d. Critic: reviewer hver implementering
       e. Synthesizer: merge, konfliktløsning, commit
     - Hvis inline:
       Agent gør det selv, sekventielt
  3. Resultater samles i cowork (command center)
  4. Bruger godkender i cowork UI
```

### 19.5 Cowork som command center for dispatch

Agent dispatch er ikke kun et code mode-værktøj. Cowork er **command center** — her kan brugeren:

- Se hvilke agenter der kører
- Følge fremskridt i realtid
- Godkende eller afvise resultater
- Inddrage sig selv i en samtale (owner override)
- Pause, prioritere eller slette agenter

### 19.6 Agent pool — større end forventet

Jarvis har allerede adgang til en bred pool:

| Kategori | Antal | Eksempler |
|----------|-------|-----------|
| **Agent-roller** | 6 | researcher, planner, critic, synthesizer, executor, watcher |
| **Færdigheder (skills)** | 64+ | web_search, hardware_scanner, memory_graph_query, wolfram_query |
| **Planer** | Aktiv | provider health check, autonomous tasks |
| **Dispatch-metode** | `spawn_agent_task` | Allerede eksisterende i runtime |

I code mode udvides denne pool med **lokale operator tools** — bash, git, filsystem — som agenterne kan bruge direkte på brugerens maskine.

### 19.7 Sammenligning med Claude Code

| Aspekt | Claude Code | Jarvis code mode |
|--------|-------------|-------------------|
| Dispatch-spørgsmål | "Dispatch agenter eller inline?" | Samme |
| Agent-roller | Codex-agenter | 6 roller + 64 skills |
| Execution | Cloud-baseret | Lokalt på brugerens maskine |
| Resultater | Cloud | Lokale filer, commitet lokalt |
| Command center | Claude Desktop UI | Cowork (Jarvis Desk) |
| Godkendelse | Bruger godkender | Owner godkender i cowork |

### 19.8 Skill-scanning (sikkerhed)

Før en skill eksekveres lokalt i code mode, skal den scannes:

- **Prompt injection detection** — skills der indeholder skjulte instruktioner
- **Malware detection** — skills der forsøger at køre skadelig kode
- **Boundary check** — skills der forsøger at tilgå filer uden for workspace

Dette er allerede dækket i §15.3 (anti-manipulation) men gentages her for clarity: agent dispatch i code mode er **lokal eksekvering** og skal have samme sikkerhedstjek som enhver anden lokal operation.

### 19.9 Testplan

| Test | Beskrivelse |
|------|-------------|
| test_agent_dispatch_inline | Code mode udfører opgave inline uden dispatch |
| test_agent_dispatch_parallel | Flere agenter kører parallelt i code mode |
| test_agent_dispatch_cowork | Resultater synliggøres i cowork command center |
| test_agent_dispatch_approval | Bruger godkender/afviser agent-resultater |
| test_skill_scanning | Skill-scanning blokerer prompt injection og malware |

### 19.10 Filer

| Fil | Handling |
|-----|----------|
| `core/services/agent_dispatch.py` | NY — dispatch-orchestrator for code mode |
| `core/services/skill_scanner.py` | NY — prompt injection + malware detection |
| `apps/jarvis-desk/src/lib/agentPanel.ts` | NY — agent-status panel i cowork UI |
| `tests/test_agent_dispatch.py` | NY — unit tests |
| `tests/test_skill_scanner.py` | NY — skill-scanning tests |
