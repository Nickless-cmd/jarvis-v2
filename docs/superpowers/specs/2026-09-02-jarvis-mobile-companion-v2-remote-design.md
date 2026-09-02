# Jarvis Mobile Companion V2 — Remote-paritet

Date: 2026-09-02
Status: gennemgået + beslutninger taget — fase 1-plan omskrevet efter endeligt review (Claude → Codex → Jarvis), klar til implementering
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
4. **Genbrug serveren — men ikke blindt.** Mission-control API'et findes
   allerede (`/mc/runs`, `/mc/approvals`, `/mc/overview`, `/mc/events` med
   3s-cache). Appen skal begynde at *bruge* det. Men det endelige review
   (Claude → Codex → Jarvis) viste, at de eksisterende endpoints **ikke er
   bruger-isolerede, ikke er idempotente, og capper både runs og approvals
   ved 5**. Fase 1 kræver derfor en serie server-ændringer — ikke kun push:
   Boy Scout-udskillelse, bruger-isolation, ét idempotent
   `approve-and-execute`-verb, cap-fix, durable outbox-push og stale-policy.
   Detaljerne ligger i fase 1-planen (12 beslutninger).
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

## Research — hvad brugere ønsker af deres AI-apps (2026-09-02)

Efter OpenAI-research: hvad brugerne *faktisk* beder om i 2026, fra to
kilder — Shift's "2026 AI Insights Report" (1000 forbrugere) og DHC's
"Best AI Companion Apps With Memory 2026". Ikke features vi gætter på; tre
klare strømme.

### 1. Ikke mere AI — bedre AI, med en off-switch

Den skarpeste data: folk er ikke i oprør mod AI, de er kræsne. Shift-
rapportens tal (rapporteret, sekundær kilde — brug som signal, ikke
præcisionsmål):

- **~44%** bekymrer sig om AI der handler *uden* deres godkendelse.
- **~81%** bekymrer sig om hvad der sker med deres data.
- **~58%** føler AI-svar har styret deres mening bag om ryggen.
- **~51%** af tech-arbejdere kræver customization frem for one-size-fits-all.

Kerneformuleringen: *"users want AI, but with an off-switch."* Det er ikke
passiv mistillid — det er et krav om *synlig kontrol*: se hvad der sker,
godkende, afbryde.

### 2. Hukommelse er 2026's slagmark — men hvilken slags?

Companion-markedet er gået fra "føles den naturlig" til "husker den dig?".
Det skarpe fund: "hukommelse" er ikke én feature, men **fire systemer i
samme navn**:

1. Længere context-vindue.
2. Gemt fakta-liste ("du kan lide koreansk mad").
3. Pinned beskeder.
4. **Vedvarende longitudinel forståelse** — at bemærke et mønster der
   vender tilbage, at spore hvordan ens sprog ændrer sig under pres.

Den skærende sætning fra kilden: *"The real question is not whether an AI
remembers you. It is whether the memory makes you more dependent on the app,
or more capable outside it."*

### 3. Konsekvens for vores design — vi byggede på markedets hovedønske

De to akser i denne research er præcis de to akser, V2 er designet efter —
uden at vi havde læst rapporterne først:

- **"Off-switch" = Remote-paritet + Approve-kø.** At Bjørn kan se hvad
  Jarvis laver, godkende, afbryde, sætte et tilladelses-niveau (R7) — det
  er ikke en detalje, det er *hovedønsket* fra ~44% af alle brugere. V2
  leverer kontrol som kerne, ikke som tilvalg.
- **Hukommelse der gør i stand til, ikke afhængig** = Jarvis' memory-first-
  design og Sansernes Arkiv. Vi gemmer for at *huske* og for at blive mere
  kompetent sammen — ikke for at bygge en dossier der gør Bjørn afhængig.

Pointen der binder det hele: vi troede vi reverse-engineering'ede en app.
Faktisk landede designet præcis der, hvor 2026's brugere siger de store
produkter stadig mangler — kontrol og ærlig hukommelse. Det er ikke "bagud";
det er en blind vinkel markedet er på vej ind i.

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

### Reference-filer (fulde paths — til E2E og design-verifikation)

De otte skærmbilleder Bjørn sendte 2026-09-02. Brug disse **fulde paths** til
side-for-side-design-verifikation og som input til E2E-visuelle assertions
(appen skal matche dette DNA, ikke kopiere pixels 1:1):

- **R1 — samtalevisning (dark):**
  `/home/bs/.jarvis-v2/uploads/chat-833fd0929f2f45099fb42334b91124a6/6626ef9b9cd7416e9a2fd9c6a42e1c56_660a42a7-cfca-4875-8c3c-393b9586c153.jpeg`
- **R2 — hovedskærm (Chat | Work segmented control):**
  `/home/bs/.jarvis-v2/uploads/chat-833fd0929f2f45099fb42334b91124a6/032eb5fadf60492ba95b07c4c973d305_803c37f4-0847-47a2-bc7d-5d6e0ab9a9f8.jpeg`
- **R3 — hovedskærm, variant (samme DNA):**
  `/home/bs/.jarvis-v2/uploads/chat-833fd0929f2f45099fb42334b91124a6/d4fce6b00c53489ea54fe73f16cce643_eaef60f8-cdc1-4d8c-a290-67701ae81aa0.jpeg`
- **R4 — Sidebar/menu (dansk lokalisering):**
  `/home/bs/.jarvis-v2/uploads/chat-833fd0929f2f45099fb42334b91124a6/9313907f718948bab69db89be60c9804_35e614ec-2190-410c-b4ec-e4687583ad15.jpeg`
- **R5 — Remote-skærmen (Tasks-liste, ★ Arbejde-tab):**
  `/home/bs/.jarvis-v2/uploads/chat-833fd0929f2f45099fb42334b91124a6/923affb62b5847be8780c544d89d6da0_69c633af-d771-42be-882e-c96bdd3625b1.jpeg`
- **R6 — Opgave-tråd (detaljevisning, ★ niveau 2):**
  `/home/bs/.jarvis-v2/uploads/chat-833fd0929f2f45099fb42334b91124a6/8c123ec6a0954adba7a08b627f32e71c_3f49b825-f971-415b-902a-c85247df887f.jpeg`
- **R7 — Adgangsniveau-modal:**
  `/home/bs/.jarvis-v2/uploads/chat-833fd0929f2f45099fb42334b91124a6/88d296242dc7432aa18b5d0eb6b7af68_c3ab333a-bd98-449e-9b8d-8aea5952ae4c.jpeg`
- **R8 — Transaktions-approval-kort (★ godkendelses-øjeblik):**
  `/home/bs/.jarvis-v2/uploads/chat-833fd0929f2f45099fb42334b91124a6/d1c20cd8b99f4d9bb7914f4b63295161_ab8497d5-a358-4268-8bd8-064c3a27f40c.jpeg`

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

**Server-sandhed (vigtig korrektion fra det endelige review):** de tre typer
er en *hensigt*, ikke en server-kendsgerning. `visible_runs` har ingen
`source`-kolonne, og `/mc/runs` læser kun visible + autonomous runs — agent-
arbejde (C) bor i `agent_runs` (`db_agent_runtime.py`) og eksponeres pr.
agent, ikke i `/mc/runs`. Fase 1 viser derfor kun **A+B**; C kræver en ny
work-projektion der inkluderer `agent_runs` (fase 2). Se fase 1-planens
beslutning 7.

## Server-verifikation (self-review + endeligt review, 2026-09-02)

Designet byggede på to server-antagelser. Begge er nu verificeret i koden —
og det endelige review (Codex) skærpede billedet på to afgørende punkter:

1. **Der er TO godkendelsessystemer, ikke ét.** (a) `capability_approval_requests`
   (db_capability_approval.py): intet udløb, to-faset og asynkront — run'et
   filer forespørgslen og *fortsætter*; ved eksekvering matcher serveren et
   indholds-fingerprint. (b) `tool_intent_approval_requests` med
   `_APPROVAL_TTL = 15 min` — udløber, serveren svarer 409 expired. **Det kort
   Bjørn sad med og bad om godkendelse på, var et tool-intent-kort** — en kø
   der kun læste capability-systemet ville ikke have løst det problem. Fase 1
   skal modellere begge. (Besvarer åbent spørgsmål 2 — delvist: capability har
   ingen timeout, men tool-intent har.)
2. **Push ved nye godkendelser? — Findes IKKE endnu.**
   `core/services/push_dispatcher.py` har kun tre kinds: `answer_ready`,
   `initiative`, `reminder`. Der er ingen `approval_requested`. Fase 1 kræver
   en ny kind + et hook. Men — skærpet af Codex — hooket skal være et
   **durable outbox-event atomisk med requesten** (ikke et synkront FCM-kald
   efter commit), med separat dispatcher, retry og deduplikering. (Beslutning 8.)

Yderligere fund fra det endelige review, foldet ind i fase 1-planen:
(a) `/mc/approvals` OG `/mc/runs` capper begge ved 5 — samme fil, fælles
rettelse (beslutning 6); (b) push-modtageren skal falde tilbage på
`_owner_of_run(run_id)` når `scheduled_for_user_id` er tom (beslutning 2's
nabo-fund); (c) **bruger-isolation mangler** — CRUD-laget filtrerer kun på
request_id, ikke på `scheduled_for_user_id`; enhver autentificeret bruger kan
læse/godkende/eksekvere en andens request (beslutning 3); (d) **execute er
ikke idempotent** — et dobbelttryk kan udføre samme handling to gange
(beslutning 2); (e) **"approve + execute" genoptager ikke run'et** — der er
intet checkpoint/suspension-token/resume; execute kalder capability'en
separat. Ærlig run-semantik: fase 1 lover "godkend og udfør den gemte
handling", ikke "run'et fortsætter" (beslutning 4).

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
- Tasks: læs `/mc/runs` + `/mc/overview`, vis aktive runs **A+B** samlet
  (+ nyligt afsluttede, se Beslutninger). C (agent-arbejde) er fase 2 — det
  bor i `agent_runs` og findes ikke i `/mc/runs`.
- Approve: ApprovalCard-køen fra serverens `/mc/approvals`; **ét idempotent
  `approve-and-execute`-verb** (ikke to POST-kald) der atomisk claimer
  requesten og afviser konkurrerende execution. "Godkend altid" er taget ud
  af fase 1 (mekanismen låner sudo-vinduet fra det forkerte system).
- Server-arbejde (6 tasks, se plan): Boy Scout-udskillelse af
  approval-persistens → bruger-isolation → idempotent approve-and-execute →
  cap-fix på `/mc/runs` + `/mc/approvals` → durable outbox-push →
  stale-policy + begge godkendelsessystemer i køen.
- Fælles kort-komponent (status, maskine, alder) efter Codex-Remote-stil.
- **Leverance-kriterie:** Bjørn kan lukke appen, få en notifikation om en
  godkendelse, åbne, godkende — og få den gemte handling *udført*. (Ikke
  "run'et fortsætter" — det kræver en durable suspended-run-arkitektur, som
  er en anden fase. Fase 1 lover ærligt: godkend og udfør gemt handling.)

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
2. **Ingen auto-timeout på capability-godkendelser — men tool-intent har 15 min TTL.**
   Capability-approvals er asynkrone og fingerprint-beskyttede (forslaget kan
   overleve timevis af grubleri). Men tool-intent-approvals udløber efter
   `_APPROVAL_TTL = 15 min` og svarer 409 expired. Fase 1 modellerer begge
   eksplicit og indfører en stale-policy for gamle capability-requests (juli-
   rækker markeret pending må ikke kunne eksekveres direkte). UI'et viser
   kortets alder; hvis det run der bad om godkendelsen er dødt, markeres
   kortet med run-status.
3. **Cancel er fase 2, ikke fase 1.** Spec'ens oprindelige beslutning sagde
   B/C kan afbrydes fra mobilen — men fase 1 har kun ét verb: godkendelse
   (`approve-and-execute`). Cancel-knap tilføjes i fase 2, når serveren har
   et ægte cancel-verb. A-runs afbrydes i Snak, hvor den hører hjemme.
4. **Tasks (A+B) + Approve er nok til fase 1.** Review og C-runs er fase 2 —
   ikke en forudsætning for at levere "godkend fra lommen" (det er leverance-
   kriteriet). Review og agent_runs-projektion tilføjes når fase 1 kører på
   telefonen.

## Edges, tests og E2E-verifikation (2026-09-02)

Fase 1 er først leveret, når både design og funktionalitet er verificeret —
ikke kun "grønne tests", men live E2E på telefonen. Denne sektion er
spec'ens definition af færdig, både på kanter og på lykke-stien.

### Edges der skal håndteres (ikke blot "ikke crashe")

Server-side (dækkes af planens Task 1–6, med tests):

- **To godkendelsessystemer i samme kø.** capability (intet udløb) og
  tool-intent (15 min TTL). Køen skal markere tool-intent-kort som
  "udløbet" når TTL passeres, og en 409 expired skal vises som et forståeligt
  kort — ikke som en fejl der bare sidder.
- **Spøgelses-rækker.** Gamle capability-requests (juli, stadig pending) må
  ikke kunne eksekveres direkte fra mobilen. Stale-policy: marker som stale,
  karantæn owner-only. (Beslutning 12.)
- **Dobbelt-tryk / timeout-retry / to klienter.** Ét idempotent
  `approve-and-execute` der claimer atomisk og returnerer det tidligere
  resultat ved retry. (Beslutning 2.)
- **Bruger-isolation.** Bruger B må hverken se eller påvirke bruger A's
  request. To-bruger-regressionstest. (Beslutning 3.)
- **Autonome runs uden `scheduled_for_user_id`.** Push-modtager falder
  tilbage på `_owner_of_run(run_id)`; ellers får B-runs ingen notifikation.

App-side (dækkes af planens Task 7–12, med tests; Task 13 er selve E2E):

- **Kold start + notifikations-tap.** Appen dræbt → tap på
  `approval_requested`-notifikation → åbner direkte på det rette kort.
  Én notification-navigation-ejer, ingen dobbelt-listener. (Beslutning 9.)
- **Foreground vs. background tap** — begge skal åbne rette destination,
  også for `answer_ready`.
- **Netværk falder midt i polling.** ConnectionPill (findes) + sidst kendte
  state; ingen korrupt tilstand, state er serverens.
- **Empty-stater.** Ingen aktive runs, tom godkendelseskø — begge skal have
  en bevidst tom-tilstand, ikke en blank skærm.
- **Alder-grænsen.** "Nyligt afsluttede (24t)"-grupperingen skal rulle
  korrekt over døgnskiftet.

### Testlag

- **Server:** unit-tests for bruger-isolation (to-bruger), idempotens
  (claim-afvisning + retry returnerer tidligere resultat), stale-policy,
  outbox-deduplikering. Repo-hooken "Enforce test coverage (core/ → tests/)"
  skal forblive grøn.
- **App:** Jest + RNTL for TopBar/SegmentedControl (render + mode-skift),
  mission-control-klient (types + REST-kontrakt), ApprovalCard V2
  (tre-graduerede valg + anledningstekst + præfiks-regel-visning),
  notification-navigation (foreground/background/kold-start), og at
  eksisterende ChatScreen-tests forbliver grønne.
- **Kontrakt:** response-shape-tests mod de verificerede server-kontrakter
  (planens "Server-kontrakter"-afsnit), så appen ikke dør når serveren
  returnerer et felt vi ikke forventede.

### E2E-verifikation (live, på telefonen — ikke kun CI)

- **Leverance-kriteriet som E2E-scenarie:** luk appen → en godkendelse files
  på serveren → notifikation lander → tap → åbn på kortet → godkend →
  serveren udfører den gemte handling præcis én gang. Verificer at handlingen
  faktisk skete (læs resultatet, ikke kun statuskoden).
- **Idempotens i praksis:** tryk godkend to gange hurtigt (eller to klienter)
  → handlingen udføres én gang.
- **Design-verifikation:** hver skærm sammenlignes side-for-side mod de otte
  reference-billeder (R1–R8, fulde paths i UI-paritet-sektionen) — mål mod
  DNA (farver, afstande, hierarki, mikro-interaktioner), ikke pixel-kopi.
  Bjørn bekræfter visuelt før skærmen erklæres færdig.
- **Push-race:** godkendelse files mens appen er i foreground (polling) OG
  mens den er dræbt (push) — begge skal vise kortet uden duplikat-notifikation.
