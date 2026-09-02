# Jarvis Mobile Companion V2 — Remote-paritet

Date: 2026-09-02
Status: gennemgået + beslutninger taget — fase 1-plan klar til eksternt review
Fase 1-plan: `docs/superpowers/plans/2026-09-02-jarvis-mobile-companion-v2-remote-phase1.md`
Branch for implementering: `codex/jarvis-mobile-companion-v1` (apps/mobile)
Forrige design: `2026-06-17-jarvis-mobile-companion-design.md` (V1, færdig)

## Purpose

V1 byggede en pålidelig chat-companion: SSE-streaming, approvals inline i
chatten, presence, QR-pairing, push. Det den mangler er **det andet rum**:
et Arbejde-rum der viser alt det arbejde Jarvis laver — også når chatten er
lukket — og lader Bjørn godkende, inspicere og styre fra mobilen.

V2 løfter appen til paritet med OpenAI's Codex-Remote-mønster i ChatGPT-
mobilappen: chat som base, arbejde som kontrollerbart rum. Vi kopierer ikke
kode — vi genbruger arkitektur-mønsteret: **kontrol- og eksekveringsplanet er
adskilt; state bor på serveren, telefonen er en observer/godkend-flade.**

For os er mønsteret endda enklere end hos OpenAI: Jarvis kører allerede
døgnet rundt i sin container. Der er ingen "connected computer" at sætte op —
Arbejde-rummet kigger bare på det arbejde der allerede findes.

## Design-principper

1. **State bor hos Jarvis, aldrig i appen.** Appen ejer ikke runs; den
   abonnerer på serverens mission-control state. Taber telefonen forbindelsen,
   dør intet — det er sådan "et run aldrig dør" løses arkitektonisk.
2. **Chat er base, Remote er rum.** Én app, to bevidste tilstande af samme
   forhold til Jarvis. Ikke to apps, ikke et monster med to hoveder.
3. **Én run-model på tværs.** Chat-sessioner (A), autonome runs (B) og
   agent-arbejde på andre maskiner (C) er alle *runs* med samme livscyklus:
   status, trin, godkendelser, resultater. Arbejde-tab viser dem samlet.
4. **Genbrug serveren.** Mission-control API'et findes allerede
   (`/mc/runs`, `/mc/approvals`, `/mc/overview`, `/mc/events` med 3s-cache).
   Appen skal begynde at *bruge* det — ikke få bygget et nyt. Undtagelsen er
   push: der kræves ét nyt server-stykke (se Server-verifikation).
5. **Godkendelse er ikke en chat-besked.** Når noget kræver Bjørn, skal det
   ligge i en kø der overlever app-lukning og bliver til en notifikation.

## Research — hvad OpenAI faktisk gør (2026-09-02)

Før fase 1-skitsen: hvad OpenAI's egne engineering-posts og docs beskriver
om Codex' arkitektur. Kilder: "Unlocking the Codex harness" (OpenAI eng.,
2026-02-04), Codex Remote docs (learn.chatgpt.com/docs/remote), SWE Quiz'
gennemgang af agent-loop-posts. Ingen gæt — kun det de selv dokumenterer.

### Arkitektur: én harness, mange overflader

Alle Codex-overflader (CLI, web, VS Code, macOS-app) kører samme "Codex
harness" (Rust-biblioteket Codex core: agent loop, thread-lifecycle, config,
auth, sandboxet tool-eksekvering). Mellemleddet er **Codex App Server**: en
langlivet proces der hoster core-threads og eksponerer dem via et
**bidirektionalt JSON-RPC-protokol** (JSONL over stdio). Processen har fire
komponenter: stdio-reader (transport), message-processor (oversætter klient-
JSON-RPC → core-operationer og core's low-level events → stabile UI-ready
notifikationer), thread-manager (én core-session pr. thread), og core-threads.

Vigtig indsigt: de valgte JSON-RPC frem for MCP, fordi MCP ikke kunne
repræsentere rig session-state (diffs, streaming-progress). Protokollen er
designet bagudkompatibel, så klient og server kan opdateres uafhængigt.

### Tre konversations-primitiver: Item, Turn, Thread

1. **Item** — den atomiske I/O-enhed. Typet (user message, agent message,
   tool execution, approval request, diff) med eksplicit livscyklus:
   `item/started` → valgfri `item/*/delta` (streaming) → `item/completed`
   med terminal payload. Klienten kan begynde at rendere på `started`,
   streame på `delta`, finalisere på `completed`.
2. **Turn** — én enhed agent-arbejde: starter når klienten sender input,
   slutter når agenten er færdig med outputs. En turn = en sekvens af items.
3. **Thread** — den durable container for en session: flere turns, kan
   oprettes/fortsættes/forgrenaes/arkiveres, event-history persisteres så
   klienter kan reconnecte og rendere en konsistent timeline.

Serveren kan **pause en turn midt-eksekvering** ved at sende en
approval-request til klienten — agenten venter på allow/deny før den
fortsætter. (Dét er modellen for interruptible agenter.)

### Robusthed: state bor på serveren, aldrig i klienten

OpenAI's egen begrundelse for web-varianten: browser-tabs er flygtige
(tabs lukkes, netværk falder), så web-appen kan ikke være source of truth for
langtidige opgaver. Løsningen: en worker provisionerer en container med
workspace, kører App Server i containeren, browseren taler HTTP+SSE til
backend. "Work continues even if the tab disappears"; en ny session kan
reconnecte, fortsætte og catch up "without rebuilding state in the client."
Samme mønster planlægges for TUI: connecte til en remote server, agenten
holder sig tæt på compute, arbejdet fortsætter selv hvis laptoppen sover.

**Det er svaret på "hvordan sørger de for at et run aldrig dør":** ikke ved
streaming-magi, men ved at eksekvering og state er på et stabilt plan og
klienten kun er et øje/et sæt hænder der kan tabe forbindelsen uden konsekvens.

### Streaming-format

Én klient-anmodning → mange event-notifikationer. Web-laget: HTTP + SSE
(typed response events). App-laget: JSON-RPC-notifikationer. Livscyklus-
markørerne (started/delta/completed) gør delvis rendering, fejl-genopretning
og audit-logging nemme. Før arbejdet: et `initialize`-handshake hvor klient
og server aftaler protokol-version, capabilities og feature-flags.

### Approval-mønstre (bekræfter R7 + R8)

To lag, begge dokumenteret i OpenAI's Remote-docs:
- **Tilladelses-spektrum pr. forbindelse** (R7): sandbox → auto-review →
  read-only → fuld adgang. Kun dét der krydser niveauet bliver en approval.
- **Transaktions-approval** (R8) i docs' ordlyd: "Permission requested — Do
  you want to allow Codex to run this command? `pnpm test -- StatusBadge`" med
  knapperne **Approve / Always approve / Tell Codex what to do / Deny** —
  præcis det tre-graduerede mønster vi målte, inkl. "Always approve" der
  gemmer en præfiks-regel, og et fjerde verb "Tell Codex what to do"
  (svar med instruks i stedet for ja/nej).

### Remote-fladens struktur (nuancerer R5)

OpenAI's egen docs-mockup viser Remote-skærmen med **tabs øverst:
`Tasks | Approve | Review | New task`**, og over dem et maskine-filter
("All / MacBook / Studio / Devbox") og en opgaveliste med Pinned/Today-
gruppering. R5-screenshot'et (maskine + projekter + seneste) er altså
**Tasks-tabben i opgavevisning**, ikke hele fladen. Review viser "Changes:
2 files changed +38 −12" med fil-liste og linje-diffs; New task er en guide
(maskine → projekt → branch → "Work on {machine}").

Konsekvens: vores tidligere "Remote er IKKE en tab-liste" (R5) var forhastet —
konkluderet fra ét screenshot uden docs. Det korrekte billede: **Tasks/
Approve/Review som tabs på Remote-niveau, med opgavedetalje (R6) som
dykke-niveau hvor godkendelser/diffs er inline.** Fase 1-skitsen tegnes efter
dette.

## De tre rum i appen

Navigation følger ChatGPT-appens faktiske mønster (målt fra Bjørns
reference-screenshots, 2026-09-02): **top-segmented control — ikke bund-tabs.**

```
┌─────────────────────────────────┐
│ (≡)   [ Snak | Arbejde ]   (⟳)  │  ← top-bar: menu, segmented control, sync
├─────────────────────────────────┤
│                                 │
│        (indhold pr. tab)        │
│                                 │
├─────────────────────────────────┤
│  (+  Spørg Jarvis…   🎤  ◍ )    │  ← pille-komponist (kun i Snak)
└─────────────────────────────────┘
```

- **Venstre cirkel-knap:** menu (profil, indstillinger, QR-pairing, historik).
- **Midten — segmented control:** `Snak | Arbejde` — de to bevidste tilstande.
- **Højre cirkel-knap:** sync/refresh (manuelt poll af mission-control state).

### Snak (ubevæget fra V1)
Den flydende samtale. Voice, billeder, streaming. Uændret oplevelse.

### Arbejde (nyt; spejler ChatGPT-appens "Work"-tab = Codex-Remote)
Tre sektioner i samme visuelle stil som Codex-Remote:

- **Tasks** — alle aktive runs på tværs af A/B/C: chat-sessioner der kører,
  autonome jobs, agent-arbejde på maskinerne. Hvert kort: titel, maskine,
  status, alder, sidste trin. Tryk → detaljevisning med trin-tidslinje.
- **Approve** — godkendelseskøen. Kort der beder om ja/nej på en konkret
  handling (kør kommando, skriv fil, send besked). Den findes allerede som
  ApprovalCard i V1 — den flyttes *ud* af chat-flowet og ind i en overlevende
  kø. Push-notifikation når noget nyt lander her.
- **Review** — diffs, ændrede filer, testresultater fra agent-runs.
  Read-only inspection på mobilen; "åbn i editor" som deep-link.
- **Ny opgave** — start et run: vælg maskine (jarvis-container, desktop via
  bro, PVE-host), skriv instruksen. (Fase 3.)

Menu-knappen (≡) rummer Indstillinger (ubevæget fra V1): QR-pairing,
forbindelser, tema.

## UI-paritet — 1:1 med ChatGPT-appen

Bjørns krav: companion-appen skal se ud og føles som ChatGPT/Codex-appen —
samme layout-rytme, komponent-sprog og interaktions-mønstre — men med Jarvis
bagved.

Det betyder, vi efterligner det **visuelle sprog**, ikke kopierer assets:

- **Samtale-skærmen:** besked-liste med bruger-bobler i accent-farve og
  AI-svar i neutral flade; forslag-chips over komponisten; komponist-felt
  nederst med mikrofon- og vedhæft-knap; streaming med glidende tekst og
  animeret status-markør (ikke statisk spinner).
- **Arbejde-skærmen:** sektioner øverst (Tasks/Approve/Review) i samme
  visuelle stil som Codex-Remote; opgave-kort med status-farve, maskine-tag
  og alder; godkendelses-kort med tydelig ja/nej og diff-forsmag.
- **Navigation og overflade:** top-segmented control (`Snak | Arbejde`) — som
  målt i ChatGPT-appen — mørk/lys-tema med samme kontrast- og
  overflade-hierarki (baggrund → kort → hævet element), afrundede hjørner,
  diskret typografi-skala, ikoner i samme vægt-stil.
- **Mikro-interaktioner:** haptisk feedback ved godkendelse, tilstandsskift
  uden "hoppen" (layout-anchoring), optimistisk UI med diskret validering.

### Målt fra Bjørns reference-screenshots (2026-09-02)

Otte skærmbilleder fra ChatGPT-appen (dark mode) er analyseret og lagt i
reference-pakken (R1–R3: samtale/hovedskærm, R4: sidebar, R5: Remote-hjem,
R6: opgave-tråd, R7: adgangsniveau-modal, R8: transaktions-approval-kort).
De konkrete mål vi designer efter:

- **Baggrund:** solid sort (`#000000`). Sekundære elementer (cirkel-knapper,
  segmented control-beholder, input-pille): mørkegrå/antracit (~`#2F2F2F`).
  Aktivt tab i segmented control: lysere grå pille. Tekst/ikoner: hvid.
- **Top-bar:** venstre cirkel-knap = menu (to hvide linjer); midten =
  pilleformet segmented control med to lige brede tabs; højre cirkel-knap =
  sync/refresh-ikon.
- **Komponist (Snak):** pilleformet, mørkegrå med subtil kant. Placeholder
  tekst (hos os: "Spørg Jarvis…"). Venstre: `+` (vedhæft). Højre: mikrofon +
  separat cirkulær voice-knap med **lilla/blå gradient** og hvid
  lydbølge-ikon (voice mode). Aktiv voice-tilstand viser lydbølge-indikator.
- **AI-boble:** mørk lilla pille i højre side (ChatGPTs "Hej Bjørn"-hilsen),
  efterfulgt af hvid tekst uden boble. Under AI-svar: værktøjsrække med små
  lysegrå ikoner (kopi, like/dislike, TTS, del, menu).
- **Statusbar/navigation:** Android-standard; systemindhold i toppen.

### Reference #4 — Sidebar/menu (målt 2026-09-02)

ChatGPT-appens hamburger-menu, dansk lokalisering. Vigtigst: OpenAI's egne
danske destinationer og deres hierarki — dem matcher vi 1:1 i sproget:

- **Menu-top:** "ChatGPT"-titel + søgeknap (cirkel) + kebab-menu.
- **Primær navigation** (line-art ikoner): Billeder · Bibliotek · **Projekter**
  · **Fjernbetjening** · **Planlagt** · Plugins.
- **Fastgjort-sektion** (📌): fastgjorte chats (hos Bjørn: "Jarvis-agent").
- **Seneste-sektion:** chat-liste; aktiv chat får mørkegrå highlight
  (8–12px radius).
- **Bund:** pille-FAB "✏️ Chat" med **lilla→blå gradient** (samme accent som
  voice-knappen), profil-cirkel "BS", separat lilla voice-knap med waveform.
- **Terminologi vi overtager (dansk, 1:1):** Fjernbetjening (Remote) ·
  Planlagt (Scheduled) · Projekter · Fastgjort · Seneste · Bibliotek.

### Reference #5 — Remote-skærmen (målt 2026-09-02) ★ vigtigste for Arbejde-tab

Selve Codex-Remote-fladen i ChatGPT-appen — det vi bygger som Arbejde-tab:

- **Top-bar:** tilbage-pil (venstre, cirkel), titel **"Remote"** centreret,
  kebab-menu (højre, cirkel).
- **Forbundet maskine-sektion** (øverst, under top-bar): grøn
  online-statusprik (`~#4CAF50`) + laptop-ikon + maskinnavn (hos Bjørn:
  "CheifOne"). Viser hvilken computer der eksekverer arbejdet.
- **"Projekter"-sektion:** liste over tilgængelige projekter på maskinen.
  Første række = laptop-ikon ("Chats"), øvrige = folder-ikoner
  ("jarvis-v2", "observer-sessions"). Generøs vertikal padding (16–20px).
- **"Seneste"-sektion:** tidligere opgaver, to-kolonne justeret:
  venstre = opgavebeskrivelse ("Say hello", "Vurder Jarvis AI-arkitektur"),
  højre = relativ tidsstempel i grå (`#B0B0B0`, "2d", "2mdr").
- **Floating bottom-lag:** pilleformet søgefelt ("Søg i chats", mørkegrå
  `~#222222`) + to cirkulære gradient-knapper: voice (lydbølge) og
  compose (blyant/papir).

Konsekvens for vores Arbejde-tab: dette er **Tasks-tabben i opgavevisning**
(maskine + projekter + seneste opgaver). OpenAI's egne docs viser Remote-
fladen med tabs ovenpå — Tasks | Approve | Review | New task — se
Research-sektionen. Vores tre sektioner (Tasks/Approve/Review) er altså
forenelige med det faktiske mønster; R5 dokumenterer hvordan Tasks-listen
ser ud.

### Reference #6 — Opgave-tråd (detaljevisning, målt 2026-09-02) ★ niveau 2

Det man lander i efter at trykke på en opgave/projekt i Remote-hjemmet — en
Codex-chat på CheifOne i projekt jarvis-v2 ("Say hello"). Viser hvordan en
agent-konversation ser ud på Remote-niveau:

- **Top-bar:** tilbage-pil i cirkel (venstre). Midten: en **kontekst-pille**
  der bærer hele trådens identitet — chat-bobbel-ikon + trådnavn ("Say
  hello"), robot-ikon + projekt ("jarvis-v2"), computer-ikon + maskine
  ("CheifOne"). Højre: halvmåne-ikon (tema) + kebab-menu, begge i cirkler.
- **Besked-flow:** agent-svar er **venstrejusteret tekst uden boble**
  (rapport-stil); bruger-beskeder er **mørke lilla/blå piller, højrejusteret**
  ("Du stoppede?", "du stoppede?"). Kode/commits i monospace
  (`917f27dd`, `main`, `--no-verify`). Under agent-tekst: kopiér-ikon (venstre).
- **Inline trin/tidslinje-elementer** i tråden (ikke en separat fane):
  navigationslink ("Designing standalone hook wrapper for worktrees >") og
  tidsstempel-link ("Arbejdede i 10 min. 57 sek. >"). Agenten rapporterer med
  commit-info, bullet-lister og verifikations-afsnit i almindelig tekst.
- **Komponist (Remote-form):** placeholder = **"Arbejd på {maskine}"**
  ("Arbejd på CheifOne") — komponisten i en opgave-tråd er *steer-input* til
  agenten, ikke en chat-besked til Jarvis. `+` venstre, mikrofon højre.
- **Ingen tabs, ingen sektioner** — ren tråd. Godkendelser og diffs må
  således dukke op *inde i* dette flow (inline-kort), ikke som faner ovenpå.

Konsekvens: R6 er **dykke-niveauet** — det man lander i efter at trykke på
en opgave fra Tasks-listen. Her er der ingen tabs; godkendelser og diffs
dukker op **inline i tråden** som kort (R8). Tabs (Tasks/Approve/Review)
hører til på Remote-niveauet ovenover; dykke-niveauet er en ren tråd med
kontekst-pille + steer-komponist. (Fase 1-skitse tegnes efter dette.)

### Reference #7 — Adgangsniveau-modal (målt 2026-09-02)

Bjørn sendte den som "approval cards", men den viser noget vigtigere og
anderledes: en **modal hvor man vælger tilladelses-niveau** — ikke et
transaktions-approval på én kommando. Centreret kort (~#212121, radius
24–28px) over dæmpet/blurret baggrund (~60–80% sort), 4 radio-lignende
valgmuligheder, hver med ikon (venstre) + titel/desc (midten) + checkmark
ved aktivt valg (højre):

- **Standardtilladelser** — "Kører kommandoer i en sandbox" (hånd-ikon)
- **Automatisk gennemgang** — "Gennemgår automatisk anmodninger om udvidede
  rettigheder" (cirkel-check-ikon)
- **Kun læsning** — "Kræver godkendelse for at redigere filer eller køre
  kommandoer" (hængelås-ikon)
- **Fuld adgang** (aktiv) — "Fuld computeradgang (øget risiko)" (ambra
  advarselstrekant ~#FFB347)

Baggrunden er selve opgave-tråden (samme kontekst-pille øverst som R6:
"Say hello" / jarvis-v2 / CheifOne) med komponisten "Arbejd på CheifOne".

Konsekvens for vores design: OpenAI konfigurerer **magt pr. forbindelse/
run på et spektrum** (sandbox → auto-review → read-only → fuld adgang)
frem for et binært ja/nej på hver enkelt handling. Det giver os et mønster
for vores egen sikkerhedsmodel: i stedet for at Approve-køen drukner i
små godkendelser, kan et run have et **tilladelses-niveau der filtrerer hvad
der overhovedet kræver Bjørn**. Kortet der så dukker op (når noget krydser
niveauet) er fase 1's Approve-kort — og dette er skærmen *før*: vælg niveau
når et run starter. (Tilføres fase 1-skitse som konfigurations-skærm;
checkmark-radiogruppe + advarselsmarkering for det højeste niveau.)

### Reference #8 — Transaktions-approval-kort i tråden (målt 2026-09-02)

Det faktiske godkendelses-øjeblik — svaret på "hvordan ser en approval ud":
et **inline kort der popper op midt i opgave-tråden** (samme R6-kontekst:
"Say hello" / jarvis-v2 / CheifOne — billedet er endda Bjørns egen test af
approval-flowet mod en Jarvis-agent):

- **Anledningstekst** over kortet i almindelig tråd-tekst: "Vil du godkende,
  at jeg læser de første fem linjer af /root/.profile for at teste det
  manuelle approval-kort?" — agenten forklarer *hvorfor* i klart sprog.
- **Kortet:** mørkegrå flade (~#2F2F2F, afrundet 12–16px), venstrejusteret.
  Indeholder en **"Kommandoudførelse"-tag** (lille etiket med
  kommandolinje-ikon) + selve kommandoen i monospace-kodeblok
  (`/bin/bash -lc 'sudo head -n 5 /root/.profile'`).
- **Tre handlinger under kommandoen** (lodret stak, ikke knap-række):
  1. **"Godkend"** (primær, hvid/lys) — godkend denne én gang.
  2. **"Godkend altid"** (sekundær) — med en undertitel der viser *præcis*
     hvilken regel der gemmes: "Kommandoer, der starter med
     `sudo head -n 5 /root/.profile`". (Mønsteret for vores "Godkend altid":
     en præfiks-regel, ikke en blind tilladelse.)
  3. **"Spring over"** (tertiær, neutral) — afvis denne én gang.
- **Design-signal:** ingen rød/grøn ja-nej-knas — tre graduerede valg hvor
  "altid" bærer sin egen gennemsigtige regel. Kortet forstyrrer ikke
  tråd-flowet: det er ét element i strømmen, ikke en fuldskærms-modal.

Konsekvens for vores design: fase 1's Approve-kort skal følge dette mønster
(anledningstekst → kort med tag+kodeblok → Godkend / Godkend altid med
præfiks-regel / Spring over) — og det skal kunne vises **både** i
Arbejde-tabets godkendelses-kø *og* inline i en opgave-tråd. V1's
ApprovalCard er udgangspunktet, men skal udvides med "Godkend altid"-
præfiks-reglen og den forklarende anledningstekst for at matche 1:1.

Alt visuelt design verificeres mod faktiske screenshots af ChatGPT-appen,
side-for-side, før implementering af hver skærm. Bjørn leverer reference-
skærmbilleder; vi designer vores egne assets efter samme DNA — ingen kopierede
ikoner, logoer eller kode fra OpenAI's app.

## Run-model (A/B/C)

| Type | Eksempel | Starter fra | Kræver godkendelse? |
|------|----------|-------------|---------------------|
| A — chat-session | Samtale med Bjørn | Snak | Trinvist, inline |
| B — autonom | Morgenvejr, PVE-overvågning | Scheduler/daemon | Sjældent, kun ved dømmekraft |
| C — agent-arbejde | Opgave på desktop via bro | Remote → Ny opgave | Ja, ved handlinger |

Alle tre eksponeres som runs af mission-control (`/mc/runs`). Forskellen er
kun synlig i kilden (`source`-felt) og i hvilke verber der er tilgængelige
(cancel/approve/steer).

## Server-verifikation (self-review, 2026-09-02)

Designet byggede på to server-antagelser. Begge er nu verificeret i koden:

1. **Overlever godkendelser en lukket session? — Ja, på data-niveau.**
   Capability-approvals ligger i DB-tabellen `capability_approval_requests`
   (oprettet i `core/runtime/db_capability_approval.py`) med livscyklus
   pending → approved → executed. Flowet er **to-faset og asynkront**:
   `workspace_capabilities` filer forespørgslen med kontekst (inkl.
   indholds-fingerprint) og run'et *fortsætter* — det venter ikke. Bjørns
   svar kan komme minutter eller timer senere; ved eksekvering matcher
   serveren fingerprintet, så forslaget kun udføres hvis indholdet ikke har
   ændret sig undervejs. Det betyder: **ingen timeout-mekanisme findes — og
   ingen er nødvendig.** (Besvarer åbent spørgsmål 2.)
2. **Push ved nye godkendelser? — Findes IKKE endnu.**
   `core/services/push_dispatcher.py` har kun tre kinds: `answer_ready`,
   `initiative`, `reminder`. Der er ingen `approval_requested`. Fase 1's
   leverance-kriterie ("få push når en godkendelse venter") kræver derfor ét
   server-stykke: en ny kind + et hook der fyres når en
   capability-approval-request files (naturligt sted:
   `_persist_capability_approval_request` i `workspace_capabilities.py`,
   linje ~468/515). Chat-approvals (A-runs) får *ikke* push i fase 1 — de
   sker mens appen er åben i Snak; push der er fase 2-arbejde.

Desuden verificeret: `/mc/approvals` læser den samme overflade (recent
approval-requests) som appen skal vise, og eksisterende approve/execute-
endpoints findes under `/mc/capability-approval-requests/{id}/...`.

## Data-flow

- **Polling:** Arbejde-tab poller `/mc/overview` hvert 3–5s (serveren cacher
  allerede i 3s). Ingen websocket i fase 1 — polling er robust nok og undgår
  forbindelses-hjørner på ustabilt mobildata.
- **Push:** FCM (findes allerede) bruges til *events*, ikke state: "ny
  godkendelse venter" (ny kind, se ovenfor), "run færdigt", "run fejlede".
  Tryk på notifikation → deep-link til det relevante kort.
- **Optimistisk UI:** godkendelse sendes straks, UI bekræfter, server-svar
  validerer. Fejl → ErrorBanner (findes).
- **Offline:** appen viser sidst kendte state + "forbindelse tabt" (findes
  som ConnectionPill). Intet korrupt — state er serverens.

## Faser

### Fase 1 — Remote read-only + Approve (kernen)
- Navigation: tilføj `Arbejde`-sektion i segmented control med Tasks +
  Approve (UI efter ChatGPT-appens Remote-visuelle sprog — se UI-paritet).
- Tasks: læs `/mc/runs` + `/mc/overview`, vis aktive runs A/B/C samlet
  (+ nyligt afsluttede, se Beslutninger).
- Approve: ApprovalCard-køen fra serverens `/mc/approvals`; ja/nej sender til
  eksisterende approve-endpoint.
- Server-arbejde: `approval_requested`-kind i push_dispatcher + hook ved
  filing af capability-approval-request.
- Fælles kort-komponent (status, maskine, alder) efter Codex-Remote-stil.
- **Leverance-kriterie:** Bjørn kan lukke appen, få en notifikation om en
  godkendelse, åbne, godkende — og run'et fortsætter.

### Fase 2 — Review + push for chat-approvals
- Detaljevisning pr. run: trin-tidslinje, terminal-output/screenshots.
- Diff-visning for C-runs (ændrede filer, patch-view).
- Push for A-run chat-approvals (hook i visible-runs approvallag).
- Deep-link "åbn i editor" på desktop.

### Fase 3 — Fuld paritet
- "Ny opgave"-flow: vælg maskine + instruks → spawn agent-run.
- Steer: send instruks til et kørende run.
- Live terminal-feed (når polling ikke slår til).

## Beslutninger (fra gennemgang, 2026-09-02)

De fire åbne spørgsmål er besvaret og lukket:

1. **Tasks-visning: aktive + nyligt afsluttede (24t), grupperet.**
   Codex viser kun aktive, men C-runs (agent-arbejde) har ingen chat-historik
   at falde tilbage på — uden de nyligt afsluttede kan Bjørn ikke se hvad en
   agent lavede efter det blev færdigt. Aktive øverst, "afsluttet i dag"
   under, kollapsbart.
2. **Ingen auto-timeout på godkendelser.** Serveren har ingen
   timeout-mekanisme, og behøver ingen: capability-approvals er asynkrone og
   fingerprint-beskyttede (forslaget kan overleve timevis af grubleri). UI'et
   viser kortets alder; hvis det run der bad om godkendelsen er dødt, markeres
   kortet med run-status, men svaret behandles stadig korrekt.
3. **B- og C-runs kan afbrydes fra mobilen** (cancel-knap med bekræftelse på
   runs der understøtter det — agents-runs har spawn/execute/cancel i
   mission-control). **A-runs (aktiv chat) kan ikke afbrydes fra Remote** —
   den afbrydes i Snak, hvor den hører hjemme.
4. **Tasks + Approve er nok til fase 1.** Review er fase 2 — ikke en
   forudsætning for at levere "godkend fra lommen" (det er leverance-
   kriteriet). Review tilføjes når fase 1 kører på telefonen.
