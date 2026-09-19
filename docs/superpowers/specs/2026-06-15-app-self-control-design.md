---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# App-Self-Control — Jarvis styrer jarvis-desk indefra (med samtykke)

**Dato:** 2026-06-15
**Status:** Design — afventer implementerings-plan
**Forfatter:** Claude Code (på Bjørns anmodning)

## Problem

jarvis-desk har to akser af "kapacitet" som brugeren styrer manuelt i UI'et:

1. **Mode** (`StreamContext`): `chat` | `cowork` | `code`. Kun code mode giver
   Jarvis operator-tools (terminal, fil-læsning/skrivning).
2. **Permission** (`Composer`, kun code mode): `ask` | `trust`. `trust` = "fuld
   adgang" — tools kører uden per-kald-godkendelse.

I dag skal brugeren huske at sætte disse selv. Den hyppige friktion: Bjørn beder
Jarvis om noget i **chat mode** der kræver terminal/filer, men har glemt at skifte
til code mode efter en app-genstart. Jarvis kan mærke at opgaven kræver mere, men
har ingen måde at gøre noget ved det — han kan kun sige "skift selv til code mode".

Samme mønster for nye brugere der kører med `ask`-permission: en krævende opgave
ville gå glattere med fuld adgang, men brugeren ved ikke at de skal slå det til.

**Mål:** Jarvis skal kunne *foreslå* et mode-/permission-skift indefra appen, og
appen skifter automatisk når brugeren godkender — så appen føles som **én
sammenhængende Jarvis**, ikke en samling adskilte tilstande brugeren skal jonglere.

## Ukrænkelig grænse

Jarvis **skifter aldrig noget selv**. Tool'et kan kun *anmode*; kun brugerens
klik på godkendelseskortet ændrer mode eller permission. Det er håndhævet
strukturelt (ikke via LLM-instruktion): backend-tool'et har ingen evne til at
mutere desk-state — det emitterer kun en anmodning som desk renderer.

Dette er også en **sikkerhedsfeature**: et mode-/permission-skift ændrer kun hvad
Jarvis *anmoder om*. Backend'ens permission_engine + tool-scoping håndhæver stadig
hvad en konkret bruger faktisk må — en member får member-scopede tools selv i code
mode med `trust`. Eskaleringen åbner ikke en bagdør; den skruer kun op for det
brugeren allerede har lov til. ([[project_multiuser_security_northstar]])

## Tilgang (valgt: A — in-band stream-event)

Jarvis kalder et generisk tool `request_app_action`. Når tool'et kaldes,
emitterer visible-run-streamen et `system_event kind="app_action_request"` i selve
SSE-streamen. Desk renderer et godkendelseskort **inline i samtalen** — præcis hvor
Jarvis spurgte. Brugeren godkender → desk skifter mode/permission + gen-sender den
oprindelige besked → Jarvis fortsætter sømløst i den nye tilstand.

Fravalgte alternativer:
- **B) Store + polling** (spejl `ui_panel_store`): mere afkoblet, men kortet er
  ikke inline med samtalen, og det tilføjer polling-infrastruktur vi ikke behøver.
  *(Fravalget gælder mutations-retningen. 19/9 blev B alligevel valgt for den
  læsende retning — se opdateringen nederst.)*
- **C) Ren prompt-instruktion** (Jarvis skriver "skift til code mode?" som tekst,
  desk tekst-matcher): skrøbeligt, ingen struktureret kontrakt. Afvist.

## Beslutninger (afklaret med Bjørn)

- **Scope:** Generisk ramme + de to konkrete eskaleringer. Vi bygger ét
  `request_app_action`-mekanisme der kan udvides (panel-åbning, agent-dispatch
  senere) UDEN ny infrastruktur, og leverer de to handlinger nu:
  `switch_to_code_mode` + `request_full_access`.
- **Kontinuitet:** Auto-fortsæt. Efter godkendelse skifter appen mode/permission
  OG gen-sender brugerens oprindelige besked automatisk, så Jarvis fortsætter i den
  nye tilstand uden at brugeren skal skrive igen.
- **Detektion:** Jarvis selv-bedømmer. Han kalder tool'et når HAN vurderer at
  opgaven kræver mere end den nuværende mode/permission. Ingen separat heuristik.

## Arkitektur

```
┌─ Jarvis (visible run, chat mode) ─────────────────────────────┐
│  bruger: "ret bug i db.py"                                     │
│  Jarvis vurderer: kræver filer+terminal → kalder tool         │
│    request_app_action("switch_to_code_mode", reason=...)      │
│    → tool returnerer "anmodet, afventer godkendelse"          │
│    → Jarvis afslutter turen: "Det kræver code mode —          │
│       godkend ovenfor, så fortsætter jeg."                   │
└───────────────────────────────────────────────────────────────┘
            │ visible_runs emitterer:
            ▼
   system_event kind="app_action_request"
     { action, reason, original_message }
            │ SSE → desk translator
            ▼
┌─ jarvis-desk ─────────────────────────────────────────────────┐
│  AppActionCard (inline i chat-tråden)                         │
│    "Skift til code mode? [Ja] [Nej]"                          │
│    Ja → 1. skift mode (chat→code) / permission (ask→trust)    │
│          2. gen-send original_message i ny tilstand          │
│          3. (kortet markeres "godkendt")                     │
│    Nej → kort lukkes; Jarvis' tur var allerede slut          │
└───────────────────────────────────────────────────────────────┘
```

## Komponenter

### 1. Backend-tool: `request_app_action`

**Fil:** `core/tools/` (ny tool-fil, fx `app_control_tool.py`) + registrering i
tool-registry.

- **Signatur:** `request_app_action(action: str, reason: str)`
  - `action`: enum — `"switch_to_code_mode"` | `"request_full_access"`.
    Ukendt action → tool-fejl (afvises, ikke emitteret).
  - `reason`: kort menneskelig forklaring vist på kortet ("Det kræver terminal og
    fil-adgang").
- **Returnerer:** struktureret resultat, fx
  `{"status": "requested", "action": ..., "note": "Afventer brugerens godkendelse i appen."}`
  så Jarvis ved det er pending og afslutter turen pænt.
- **Sideeffekt:** ingen direkte state-mutation. Tool'et signalerer kun at en
  app-action er ønsket; selve emissionen sker i visible_runs (se §2).
- **Tilgængelighed:** owner + member (begge styrer deres egen app). Backend
  permission_engine afgør stadig hvad der faktisk må køre efter skiftet.

### 2. Stream-emission i visible_runs

**Fil:** `core/services/visible_runs.py` (+ v2 SSE-translator).

Når et `request_app_action`-tool-kald udføres i runet, emitteres et
`system_event` med `kind="app_action_request"` og payload:

```json
{
  "kind": "app_action_request",
  "action": "switch_to_code_mode",
  "reason": "Det kræver terminal og fil-adgang",
  "original_message": "<brugerens oprindelige besked i dette run>"
}
```

`original_message` hentes fra run-konteksten (`run.user_message`) — desk skal ikke
selv gætte hvad der skal gen-sendes.

### 3. Desk: AppActionCard + handler

**Filer:** `apps/jarvis-desk/src/` — ny `AppActionCard.tsx` (genbruger
`ApprovalCard`-stil), event-håndtering i SSE-translatoren, mode/permission-mutation
via `StreamContext` + `Composer`-state.

- Translatoren mapper `system_event kind="app_action_request"` → render et
  AppActionCard inline i tråden.
- Kortet viser `reason` + en handlings-specifik tekst:
  - `switch_to_code_mode` → "Skift til code mode?"
  - `request_full_access` → "Slå fuld adgang til?"
- **Ja:**
  1. Udfør handlingen: `switch_to_code_mode` sætter mode = `code`;
     `request_full_access` sætter permission = `trust` (persisteres i
     `localStorage` PERM_KEY som i dag).
  2. **Auto-fortsæt:** gen-send `original_message` via normal send-sti i den nye
     tilstand → nyt run med de rigtige tools.
  3. Markér kortet som godkendt (disabled).
- **Nej:** luk kortet. Ingen besked til backend nødvendig — Jarvis' tur var slut.

### 4. De to konkrete handlinger

| Action | Hvad sker | Hvornår kalder Jarvis det |
|--------|-----------|---------------------------|
| `switch_to_code_mode` | mode `chat`/`cowork` → `code` | Opgaven kræver terminal/filer, men appen er i chat/cowork |
| `request_full_access` | permission `ask` → `trust` (i code mode) | Allerede i code mode med `ask`, men en krævende opgave ville gå glattere med fuld adgang |

## Dataflow (auto-fortsæt)

1. Bruger sender besked (chat mode).
2. Jarvis vurderer behov → kalder `request_app_action`.
3. visible_runs emitterer `app_action_request` med `original_message`.
4. Jarvis afslutter turen med en kort note.
5. Desk renderer AppActionCard inline.
6. Bruger klikker **Ja** → desk skifter tilstand + gen-sender `original_message`.
7. Nyt run starter i den nye tilstand; Jarvis fortsætter opgaven sømløst.

## Fejlhåndtering

- **Ukendt action:** tool returnerer fejl; intet kort emitteres.
- **Allerede i mål-tilstand:** hvis appen allerede er i code mode (for
  `switch_to_code_mode`) eller allerede `trust` (for `request_full_access`), bør
  Jarvis ikke kalde tool'et — men hvis han gør, no-op'er desk handlingen og
  gen-sender stadig (idempotent). Kortet kan vise "allerede i code mode".
- **Bruger afviser:** ingen state ændres; ingen gen-send. Jarvis' allerede-sendte
  note står som hans svar.
- **Tool-emission fejler:** fail-open — runet fortsætter uden kort (Jarvis' note
  alene). Aldrig crash af runet.
- **Member-restriktion:** backend permission_engine afviser stadig tools brugeren
  ikke må; eskaleringen giver ikke ekstra rettigheder.

## Testning

- **Backend:** `tests/test_app_control_tool.py` — tool returnerer korrekt
  struktur for hver action; ukendt action fejler; emission-payload indeholder
  `action`/`reason`/`original_message`.
- **Frontend:** `AppActionCard` render-test (begge actions); Ja-klik kalder
  mode/permission-setter + gen-send; Nej-klik lukker uden sideeffekt; idempotent
  ved allerede-i-mål-tilstand.

## Udvidelighed (YAGNI — ikke bygget nu)

Den generiske `request_app_action`-ramme kan senere bære flere actions UDEN ny
infrastruktur: `open_ui_panel` (findes allerede separat), `dispatch_agent`,
`switch_provider/model`. Disse bygges først når der er et konkret behov.

## Afgrænsning

- Ikke i scope: silent auto-switch (eksplicit afvist af Bjørn — altid spørg).
- Ikke i scope: nye permission-niveauer udover `ask`/`trust`.
- Ikke i scope: cross-device/remote app-styring (kun den lokale desk-session).

## Opdatering 19/9-2026 — B blev alligevel valgt, for den læsende retning

Fravalget af B ovenfor gælder stadig **mutations-retningen**: et mode- eller
permission-skift kræver brugerens klik, og kortet skal stå inline i samtalen.
Men da Jarvis skulle kunne *se* og *navigere* appen indefra, blev B valgt — og
det var et valg, ikke en glidning, af to grunde:

1. **Svaret bærer indhold.** `ui_panel_store` er fire-and-forget: den kan kun
   kvittere «åbnet». De nye værktøjer skal vide *hvad der står på skærmen* og
   *hvilke paneler der er åbne* — og når noget ikke kan lade sig gøre, give en
   fejltekst der siger hvad der mangler. Det kræver en returvej.
2. **Der er intet at give samtykke til.** Værktøjerne ændrer hvad der *vises*,
   ikke hvad Jarvis *må*. Den ukrænkelige grænse ovenfor — at Jarvis aldrig selv
   skifter mode eller permission — er urørt.

Bygget som:

| Del | Fil |
|---|---|
| Forespørgsels-protokollen (DB-backed, korreleret på request-id) | `core/runtime/db_view_requests.py` |
| Værktøjerne: `desk_get_layout` · `desk_show_pane` · `desk_close_pane` | `core/tools/desk_view_tools.py` |
| API-ruterne | `apps/api/jarvis_api/routes/ui_view_requests.py` |
| Desk's svarer (`POLL_MS = 1500`) | `apps/jarvis-desk/src/components/ViewRequestWatcher.tsx` |

Tre detaljer der er værd at kende:

- **Den der spørger, venter.** `vent_paa_svar` poller i op til 5 s. En
  forespørgsel ældre end 30 s regnes som forældet, så desk ikke udfører et
  «vis diff» Jarvis for længst har opgivet.
- **Et vindue der ikke viser samtalen, svarer ikke.** Med desk åben på to
  maskiner kunne det forkerte vindue ellers melde «ikke åben» først. Værktøjets
  frist siger så ærligt at samtalen ikke er på skærmen.
- **Pollen kører kun når vinduet er synligt** (`document.visibilityState`), og
  et tick kan ikke overlappe det næste — ét kald pr. 1,5 s i praksis, ikke i
  teorien.

Den polling-infrastruktur vi i juni kaldte «ikke nødvendig» er altså kommet til.
Den er afgrænset til desk og koster ét kald pr. 1,5 s — og den købte os evnen
til at svare med *indhold* i stedet for et kvitterings-flag.
