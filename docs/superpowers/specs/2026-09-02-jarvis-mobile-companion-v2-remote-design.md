# Jarvis Mobile Companion V2 — Remote-paritet

Date: 2026-09-02
Status: gennemgået + beslutninger taget — klar til fase 1-implementering
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

Tre skærmbilleder fra ChatGPT-appen (dark mode) er analyseret og lagt i
reference-pakken. De konkrete mål vi designer efter:

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
