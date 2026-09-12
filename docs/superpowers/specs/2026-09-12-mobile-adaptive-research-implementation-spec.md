---
status: godkendt-design
created: 2026-09-12
owner: bjorn
implementation: ikke startet
---

# Mobil composer, vedvarende valg og adaptiv research-lane

## 1. Formaal

Denne spec beskriver én samlet ændring med tre brugerrettede resultater:

1. Mobil-composerens valg vises som tre ikonknapper i rækkefølgen
   **permissions -> model -> research**, og voice-kontrollerne deles rent i
   inline diktering og orb-baseret samtale.
2. Alle egentlige brugerpræferencer i mobilappen overlever app-genstart. Valg,
   der påvirker en samtale, gemmes pr. samtale; globale enheds- og
   kontopræferencer beholder deres korrekte ejer.
3. Research bliver en førsteklasses, serverstyret arbejdsmode. Den må ikke
   længere implementeres ved at føje en synlig instruktion til brugerens tekst.
   Små undersøgelser udføres af Jarvis selv med den installerede
   `deep-research`-skill. Store, paralleliserbare undersøgelser bruger Jarvis som
   lead og eksisterende researcher-agenter som workers.

Spec'en er implementeringsklar, men er ikke en kodeplan med commits. En separat
eksekveringsplan skal dele arbejdet i reviewbare faser efter godkendelse.

## 2. Ikke-maal

- Der bygges ikke en ny generel agent-runtime ved siden af
  `core/services/agent_runtime_*`.
- Der bygges ikke en ny streamingprotokol ved siden af SSE v2.
- Research betyder ikke automatisk multi-agent.
- Skjult chain-of-thought sendes ikke til klienten. Kun brugerrelevante
  statusresuméer, handlinger, kilder og resultater må streames.
- Midlertidig UI-state som åbne sheets, loading, scroll-position, kamera-preview,
  diagnostikresultater og igangværende haptik gemmes ikke som præferencer.
- Et dikteret lydklip er midlertidigt input. Det gemmes ikke som en besked og
  sendes ikke til Jarvis, før brugeren selv trykker send.
- Memory-skærmens lokale demohandlinger (`hidden`, `pinned`, `drafts`) må ikke
  fejlagtigt omfattes af en preference-store. De kræver særskilte server-API'er,
  før de kan love varige memory-ændringer.

## 3. Nuværende sandhed

### 3.1 Mobil research er i dag kun prompt-tekst

`apps/mobile/src/lib/chatPrompt.ts::outgoingChatText` indsætter følgende foran
brugerens tekst:

```text
Research mode: answer with sourced findings where possible, separate facts from
inference, and call out uncertainty.
```

`apps/mobile/src/screens/ChatScreen.tsx` bruger den omskrevne tekst både online
og i offline-køen og nulstiller derefter `researchMode`. Konsekvenserne er:

- brugerens besked ændres og vises ikke ordret;
- research-valget er kun én tur og forsvinder ved app-genstart;
- skill-gate, research-lane og agent-runtime aktiveres ikke;
- der findes ingen research-plan, evidensautoritet eller eksplicit kvalitetsport;
- backend kan ikke skelne brugerens ord fra klientens styringsinstruktion.

### 3.2 Per-samtale persistence findes, men er ufuldstændig

`apps/mobile/src/lib/chatSettings.ts` gemmer allerede `ChatIndstillinger` i
Expo SecureStore under `jarvis:chatcfg:<session-id>`. Den indeholder model-id,
tool-scope, oplæsning og permissions. Research og thinking ligger kun i lokal
React-state.

Modelvalget har samtidig to sandheder:

- globalt modelvalg med `{model, providerChoice, label}` i `sessionStore.ts`;
- per-chat model som kun en `string` i `ChatIndstillinger`.

Ved send kan per-chat model-id derfor blive kombineret med provider fra det
globale modelvalg. Det er en ugyldig konfiguration og skal fjernes som del af
migrationen.

`stemme` bliver gemt i samme record og vises som "Læs svar højt", men
`ChatScreen` læser ikke værdien ved afspilning. Et gemt valg uden effekt tæller
ikke som en fungerende indstilling; det skal enten kobles til TTS for den aktive
samtale eller fjernes fra UI'et. Denne spec vælger at koble det til TTS.

### 3.3 Backendens nødvendige byggesten findes allerede

- `ChatStreamRequest` og `/chat/stream/v2` bærer typed request-felter som
  permissions, thinking, mode og model.
- `visible_runs_sections/detached_run.py` og `run_event_log.py` gør runs
  serverautoritative, så en Android-SSE kan genetableres.
- `skill_relevance_surface.py` matcher skills under prompt-assembly.
- `/home/bs/.jarvis-v2/skills/deep-research/SKILL.md` beskriver plan,
  kildeforvaltning, flerpas-syntese og citation-kontrol.
- `agent_runtime_spawn.py`, rollen `researcher`, `explore`, model-fitness og
  claim guards kan udføre og kontrollere read-only delopgaver.
- SSE v2 kan allerede transportere ukendte `system_event` kinds uden at bryde
  ældre klienter.

Der er dog et vigtigt hul: owner-chat-scope i `core/tools/tool_scoping.py`
indeholder ikke `skill_gate` eller `skill_invoke`. Prompten kan foreslå en skill,
men modellen kan ikke pålideligt aktivere den i mobil chat. Eksplicit
research-mode skal derfor aktivere den kanoniske skill i runtimen, ikke håbe på
et model-initieret ritual.

## 4. Produktbeslutninger

### 4.1 Composer

Venstre kontrolrække bliver:

```text
[vedhaeft] [permissions] [model] [research]                  [mic/send]
```

Krav:

- De tre indstillingskontroller er ikon-only og har samme stabile
  `width`, `height` og hit-area.
- Rækkefølgen efter vedhæft er altid permissions, model, research.
- Permissions bruger `ShieldCheck` + en lille `ChevronDown`, fordi den åbner en
  vælger.
- Model bruger `Cpu` + `ChevronDown` og åbner den eksisterende model-vælger.
- Research bruger `SearchCheck` eller `Telescope` uden tekst. Aktiv tilstand
  vises med accentbaggrund og `accessibilityState.selected=true`.
- Alle knapper har præcise `accessibilityLabel`s, herunder aktiv værdi. Model
  skal fx læses som `Model: DeepSeek V4 Flash` og research som
  `Research: slået til`.
- Ingen label må dukke op på smalle skærme. Tilstanden må ikke ændre knappens
  dimensioner eller flytte komponisten.
- Research er en simpel on/off-kontakt i UI'et. Brugeren vælger intentionen;
  serveren vælger arbejdsdybden.
- Research nulstilles ikke efter send.

### 4.2 Research-resultat

- Brugerens egen besked vises og persisteres ordret.
- Et lille lookup må stadig føles som chat og streame første nyttige tekst
  hurtigt.
- Et stort research-run viser et kompakt, vedvarende statusområde over
  composeren: fase, antal undersøgte kilder, aktive delspor og eventuelle
  advarsler.
- Slutproduktet er en normal assistant-besked i samtalen med kontrollerbare
  citationslinks.
- Brugeren kan forlade appen. Runnet fortsætter, kan genfindes, og giver
  eksisterende push-notifikation ved completion.
- En ny besked under et aktivt research-run er en steer/follow-up til runnet,
  ikke et konkurrerende visible run.

### 4.3 Voice-kontroller: Dikter og Samtale

Composerens to voice-indgange får ét ansvar hver:

- **Mikrofonikonet hedder `Dikter`.** Det starter inline diktering og åbner
  aldrig orb-overlayet.
- **Wave-ikonet hedder `Start samtale`.** Det åbner orb-overlayet direkte i
  hands-free samtaletilstand.
- Så snart composerfeltet indeholder tekst eller en sendbar attachment, skifter
  wave-knappen til send-pilen som i dag.
- Mens et Jarvis-run arbejder, viser samme primære knap stop-firkanten som i
  dag. Stop har højere prioritet end wave og send.

Den primære højre knaps deterministiske prioritet er:

```text
working                         -> stop
not working AND sendable draft -> send
not working AND empty draft    -> start conversation (wave)
```

Et tryk på mikrofonikonet starter en ny inline recording state i composeren.
Den normale kontrolrække erstattes midlertidigt af en kompakt optagerlinje med:

```text
[cancel] [live waveform / elapsed time] [stop dictation]
```

Flowet er:

```text
idle -> recording -> transcribing -> draft inserted -> idle
  |         |              |
  +------ cancelled <-------+  (ved cancel/fejl)
```

Krav:

- Optagerlinjen bliver i composerens eksisterende flade; den er ikke et modal,
  overlay eller chat-element.
- Recording viser live niveau og forløbet tid uden at rerendere hele
  `ChatScreen` på hvert meter-sample. Genbrug `Animated.Value`-mønstret fra
  voice-state machine.
- Stop afslutter optagelsen og viser en tydelig transcribing-state i samme
  linje. Der kan ikke startes endnu en optagelse imens.
- En vellykket transskription indsættes i composerfeltet som et redigerbart
  udkast. Den sendes **aldrig automatisk**.
- Hvis feltet allerede indeholder tekst, indsættes dikteringen ved cursoren når
  selection er kendt; ellers appendes den med passende whitespace. Eksisterende
  tekst må aldrig overskrives.
- Efter indsættelse bliver den primære wave-knap automatisk til send, fordi
  draftet nu er sendbart.
- Cancel sletter den aktuelle lydfil og efterlader det eksisterende draft
  uændret.
- STT-fejl efterlader draftet uændret, viser en kort inline fejl og giver retry
  eller ny diktering. En fejl må ikke lukke appens almindelige composer.
- Android back, app-background, session-skift og unmount stopper og rydder en
  aktiv dikteringsoptagelse. Et halvt lydklip må ikke sendes automatisk.
- Diktering og orb-samtale er gensidigt eksklusive. Wave er disabled under
  recording/transcribing; `Dikter` er disabled mens orb-samtalen er aktiv eller
  Jarvis-runnet arbejder.
- Audio recorder ownership skal være entydigt. Inline diktering må ikke starte
  en tredje samtidig native recorder ved siden af samtalens capture/barge
  recorders.
- Accessibility annoncerer `Dikter`, `Stop diktering`, `Annuller diktering`,
  `Transskriberer` og `Start samtale` som separate handlinger/states.

Orb-overlayets push-mode fjernes fra den synlige mode-vælger, fordi den
brugeropgave nu ejes af inline diktering. Orb'en åbner i hands-free og forbliver
den kontinuerlige taleoplevelse: lyt -> transskriber -> Jarvis arbejder -> tal ->
lyt igen. Der må ikke længere være to UI-veje, der begge kaldes push-to-talk.

## 5. Preference-model

### 5.1 Ejerprincip

Hvert valg skal have præcis én autoritativ ejer:

| Omfang | Ejer | Eksempler |
|---|---|---|
| Samtale | versioneret SecureStore-record pr. `session_id` | permissions, model, thinking, research, tool-scope, oplæsning |
| Enhed | SecureStore | tema, accent, batteri, lokationspræcision, boble, kamera |
| Konto/server | eksisterende API/DB | connectors, notifikationsrouting, quiet hours, Google-link |
| Flygtig UI | React/native state | åbne sheets, loading, preview, diagnostik, scroll |

Denne leverance kræver persistence efter app-genstart, ikke synkronisering af
composer-valg mellem forskellige enheder. Derfor forbliver per-chat-valgene
lokale til mobilen i første version. En senere cross-device-version må flytte
hele recorden til én serverautoritet; den må ikke oprette en parallel serverkopi
uden konfliktpolitik.

### 5.2 Ny per-chat kontrakt

`ChatIndstillinger` ændres til en versioneret record:

```ts
export type ResearchMode = 'off' | 'on'
export type ThinkingMode = 'fast' | 'think'

export interface StoredModelChoice {
  model: string
  providerChoice: string
  label: string
}

export interface ChatIndstillingerV2 {
  version: 2
  model: StoredModelChoice | null
  thinkingMode: ThinkingMode
  researchMode: ResearchMode
  vaerktoejer: 'samtale' | 'fuldt'
  stemme: boolean
  spoergFoerst: boolean
}
```

`null` model betyder "brug appens standard for nye ture". Når brugeren vælger
en model i composerens model-sheet, gemmes hele objektet i den aktive samtales
record. `ChatScreen` må ikke længere holde et separat globalt modelvalg som den
aktive samtales sandhed.

### 5.3 Migration og defaults

Loaderen skal være tolerant og ren/testbar:

1. En valid V2-record valideres felt for felt; ukendte felter ignoreres.
2. En gammel record med `model: string` migreres til V2. Hvis den gamle model
   matcher den gemte globale `StoredModelChoice`, kopieres provider og label.
3. Kan provider ikke bestemmes, bliver model `null` i stedet for at gætte.
4. `thinkingMode` default er `think`; `researchMode` default er `off`;
   permissions default er fortsat sikker `ask`.
5. Den gamle globale model bruges kun som engangs-default for en ny samtale,
   indtil brugeren vælger noget i den. Den må ikke overskrive eksisterende
   per-chat-records.
6. Migrationen skrives tilbage som V2 efter succesfuld læsning.
7. Korrupt JSON eller SecureStore-fejl giver sikre defaults og må ikke crashe
   skærmen.

Nøglen kan fortsat være `jarvis:chatcfg:<sanitized-session-id>`. Record-versionen
gør fremtidige migrationer eksplicitte.

### 5.4 Send og offline-kø

`tilStreamFelter` returnerer én samlet request-projektion:

```ts
{
  model: string
  providerChoice: string
  mode: 'chat' | 'code'
  approvalMode: 'ask' | 'trust'
  thinkingMode: 'fast' | 'think'
  researchMode: boolean
}
```

Online og offline skal bruge den samme projektion. `offlineOutbox` udvides med
de relevante turn-controls, så en research-besked, der køes offline, stadig er
research ved afsendelse. Kun ren `text` gemmes som beskedtekst; den gamle
`outgoingChatText` slettes efter migrationen.

Hvis der endnu ikke findes en session ved første send, oprettes sessionen først,
og den aktuelle draft-konfiguration gemmes under det nye session-id før streamen
startes.

### 5.5 Audit af øvrige mobilvalg

Implementeringen skal bevare og teste denne matrix:

| Valg | Nuværende ejer | Krav |
|---|---|---|
| Tema + accent | `ThemeContext` SecureStore | Bevar; test reload |
| Batterioptimering | `batteryPrefs` SecureStore | Bevar; test reload |
| Lokationspræcision | `location` SecureStore | Bevar; test reload |
| Vedvarende chatboble | `bubbleSetting` SecureStore | Bevar; test reload |
| Kamera facing/flash/shutter | `cameraPrefs` SecureStore | Bevar; samlet reload-test |
| Connectors enabled | server API | Bevar serverautoritet; rollback ved save-fejl |
| Notifikationskanaler/quiet hours | server API | Bevar serverautoritet; reload fra server |
| Sidst aktive samtale | `sessionStore` SecureStore | Bevar |
| Voice push/hands-free | kun hook-state | Fjern valget: wave ejer hands-free, mikrofon ejer diktering |
| Kamera zoom | flygtig capture-state | Forbliver flygtig; det er shot-state, ikke en appindstilling |

Acceptance-kriteriet er ikke "persistér alle `useState`s". Det er: enhver
kontrol der præsenteres som et varigt valg eller en indstilling gendannes fra sin
autoritative store efter en kold app-start og anvendes af den funktion, den
påstår at styre.

Efter voice-opdelingen findes der ikke længere et varigt push/hands-free-valg:
indgangen bestemmer mode. Wave er altid hands-free samtale; mikrofon er altid
inline diktering. `voicePrefs` skal derfor ikke tilføjes alene for at bevare den
gamle, nu fjernede mode-vælger.

## 6. Wire-kontrakt

### 6.1 Request

`apps/api/jarvis_api/routes/chat.py::ChatStreamRequest` udvides additivt:

```py
research_mode: bool = False
```

Mobilens `StreamRequest`, `StreamContext.send` og `streamClient.startStream`
videresender feltet som `research_mode`. Default `False` bevarer alle ældre
klienters adfærd byte-for-byte.

Der indføres ikke et bruger-valgt `research_depth` i V1. Den interne router
returnerer `inline` eller `orchestrated`; det er runtimepolitik og kan ændres
uden mobilmigration.

### 6.2 Transcript-integritet

Følgende invariant er hård:

```text
persisted_user_message == user_entered_message + attachment presentation only
research policy not in user text
```

`research_mode` må hverken føjes til `effective_message`, `model_message`,
offline-teksten eller den viste besked. Research-kontrakten lægges i en separat
request-scoped runtime-kontekst.

Vedhæftningsdirektiver er eksisterende adfærd og ligger uden for denne specs
scope, men research metadata må ikke gøre denne sammenblanding større.

## 7. Research-arkitektur

### 7.1 Overblik

```text
Mobile research icon
        |
        v
ChatStreamRequest(research_mode=true)
        |
        v
research_router.classify(message, attachments, source policy, budget)
        |
        +---- inline -----------------------------------+
        |                                               |
        | canonical deep-research skill                 |
        | + research contract in prompt context         |
        | + normal Jarvis visible tool loop             |
        |                                               v
        +---- orchestrated --> research_run_store --> final Jarvis synthesis
                                |       ^               |
                                v       |               v
                         researcher agents       citation/critic gates
                                |
                                v
                         structured evidence ledger
```

### 7.2 Nye fokuserede moduler

Følgende moduler tilføjes under `core/services/`:

- `research_contract.py`
  - definerer `ResearchPolicy`, `ResearchTier`, `ResearchPlan`,
    `ResearchSource`, `ResearchFinding` og normalisering;
  - loader den kanoniske `deep-research`-skill deterministisk;
  - producerer en kompakt, request-scoped promptsektion;
  - indeholder ingen DB- eller agenteksekvering.

- `research_router.py`
  - vælger `inline` eller `orchestrated` ud fra opgavens form, ikke modelens
    spontane lyst til at delegere;
  - returnerer forklarlige signaler og budget;
  - udfører ingen research.

- `research_store.py`
  - ejer research-tabeller og transitions;
  - bruger runtime-DB-forbindelsen, men ændrer ikke den store `core/runtime/db.py`;
  - er autoritet for restart/reconnect-status.

- `research_orchestrator.py`
  - planlægger delspor, dispatcher eksisterende agents, samler evidens, kører
    quality gates og starter den afsluttende Jarvis-syntese;
  - udsender legacy/system-events, som SSE v2 wrapper additivt;
  - kalder agent-runtime og visible-run; implementerer dem ikke igen.

- `research_prompt_context.py`
  - lille ContextVar-baseret carrier for den aktive policy og den komprimerede
    evidenspakke;
  - resettes i `finally` og kopieres korrekt ind i detached-run-tråden.

- `research_evidence_collector.py`
  - modtager strukturerede observationer fra web-/connector-værktøjernes
    succes-path og skriver dem til den aktive ledger;
  - er en no-op uden aktiv research-context;
  - parser ikke URLs ud af færdig prosa eller UI-labels.

### 7.3 Skill-aktivering

Eksplicit `research_mode=true` er allerede brugerens gatebeslutning. Derfor:

1. Runtimen loader præcis skillen `deep-research` via skill-engine-service-API.
2. Skill-usage registreres som `source="explicit_research_mode"`.
3. Mangler skillen, fejler load eller er den slået fra, fortsætter research med
   den indbyggede minimumskontrakt og udsender en synlig warning/event.
4. Semantisk `skill_gate` bruges fortsat til almindelige, ikke-eksplicitte ture,
   men må ikke være en forudsætning for research-knappen.

Dette kræver en lille offentlig servicefunktion i skill-laget frem for import af
tool-executoren `_exec_skill_gate`. Tool-UI og runtime-policy skal ikke kobles
sammen gennem en privat executor.

### 7.4 Adaptiv tier-router

Routeren starter konservativt med deterministiske signaler og kan senere få en
billig modelklassifikator bag et flag.

`inline` vælges som default. `orchestrated` kræver mindst to uafhængige
research-spor og ét yderligere kompleksitetssignal.

Uafhængige spor kan være:

- flere navngivne virksomheder, produkter, lande eller teorier;
- sammenligning på flere dimensioner;
- en eksplicit litteratur-, markeds-, konkurrent- eller policyrapport;
- flere tidsperioder eller separate datakilder;
- brugerkrav om omfattende/deep/grundig research.

Yderligere signaler:

- forventet behov for mere end otte web-opslag;
- tre eller flere ønskede outputsektioner;
- højaktuel eller tvistfyldt information, der kræver krydstjek;
- vedhæftede dokumenter kombineret med åbent web;
- estimeret evidensmængde over én visible models praktiske kontekstbudget.

Router-output:

```py
ResearchDecision(
    tier="inline" | "orchestrated",
    signals=[...],
    max_workers=1 | 3,
    max_tasks=1 | 6,
    max_tool_calls=8 | 48,
    wall_time_s=180 | 1200,
    source_target=3 | 12,
)
```

Modelnavn eller brugerens permissions må ikke være kompleksitetssignaler.
Permissions styrer handlingstilladelse; research-tier styrer arbejdsform.

### 7.5 Inline research

Inline-mode genbruger den normale visible tool-loop:

1. Opret `research_run` med tier `inline`.
2. Aktivér research prompt-context med skillens instruktioner og budget.
3. Kør normal `start_visible_run` med brugerens ordrette besked.
4. Web/tool-events fortsætter gennem eksisterende tool cards.
5. `web_search`, `web_fetch`, `web_scrape` og relevante connector-adapters
   kalder evidens-collectorens no-op-safe observer med deres strukturerede
   resultater. Det er execution-chokepointet og ledgerens eneste automatiske
   kilde; URLs må ikke regex-parses ud af den færdige modeltekst.
6. Før finalisering kontrolleres, at eksterne faktuelle claims har citations,
   og at URLs faktisk findes i ledgeren.
7. Markér run terminalt og persistér quality metrics.

Jarvis selv ejer plan, opfølgende søgninger og sluttekst. Der spawnes ingen agent.

### 7.6 Orkestreret research

Orkestreret mode følger denne state machine:

```text
created -> planning -> researching -> verifying -> synthesizing -> completed
                     \-> blocked/failed/cancelled
```

Flow:

1. **Planning:** Jarvis/den valgte stærke visible model producerer et valideret
   `ResearchPlan` med 2-6 kohærente delopgaver og højst tre samtidige workers.
2. **Researching:** Hver uafhængig opgave køres som eksisterende
   `spawn_agent_task(role="researcher")` med read-only webværktøjer,
   `parent_session_id`, `parent_run_id`, task-id og et struktureret
   `result_contract`.
3. **Normalization:** Agentens resultat parses til findings, source records,
   gaps og contradictions. Ugyldigt output er ikke et fund; det retries én gang
   eller markeres failed.
4. **Gap pass:** Coordinatoren sammenholder dækningsmatrixen. Kun reelle huller
   må udløse nye søgninger. Maksbudgettet kan ikke udvides af modellen.
5. **Verification:** En critic-agent får claims + relevante kildeuddrag, ikke
   råt samlet browsing-output. Den kontrollerer claim support, modstrid og
   stale kilder. URLs verificeres af runtime-værktøjer.
6. **Synthesis:** Jarvis får brugerens oprindelige besked, plan, komprimerede
   findings, gaps, contradictions og den godkendte citation registry. Jarvis
   skriver og streamer slutrapporten i sin egen stemme.
7. **Completion:** Quality metrics, forbrug, agent-ids og final message-id
   knyttes til research-runnet.

Workers må ikke skrive direkte i brugerchatten. De returnerer evidens til
Jarvis; Jarvis ejer svaret.

### 7.7 Agent policy

- Policy er read-only. Default tools er `web_search`, `web_fetch`,
  `web_scrape`, relevante read-only MCP/connectors samt eventuelle
  brugerleverede filer.
- Ingen `bash`, filmutation, kanal-send, scheduling eller selvmutation.
- En child arver altid parentens strengere tool-ceiling.
- Private/forbundne kilder må kun bruges, hvis connectoren er enabled for
  brugeren. Rapporten markerer kilde-access som public, semi-public eller
  user-authorized private.
- Maks tre samtidige agents i V1. En plan med seks tasks køres i bølger.
- Agentmodel vælges via eksisterende capability/model-fitness med krav om
  dokumenteret tool-calling. Providerfejl må ikke tælle som research-resultat.
- Claims fra agents er forslag til evidens, ikke sandhed, før verification.

## 8. Durabel research-state

### 8.1 Tabeller

`research_store.py` ejer mindst disse tabeller:

```text
research_runs
  id, visible_run_id, session_id, user_id, status, tier,
  original_query, policy_json, plan_json, metrics_json,
  created_at, updated_at, completed_at, failure_code

research_tasks
  id, research_run_id, ordinal, title, objective, status,
  agent_id, attempts, result_json, started_at, completed_at

research_sources
  id, research_run_id, task_id, canonical_url, title, publisher,
  source_type, access_class, published_at, retrieved_at,
  authority_score, content_hash, evidence_excerpt

research_steers
  id, research_run_id, message, status, created_at, applied_at
```

`canonical_url + content_hash` bruges til dedup inden for et run. Store rå sider
skal ikke duplikeres i DB; ledgeren gemmer metadata og et kort bevisuddrag, mens
eksisterende web-cache/artifact-lag kan eje større indhold.

### 8.2 Invarianter

- Kun lovlige state transitions accepteres.
- Et terminalt run kan ikke genåbnes.
- En task kan højst have én aktiv agent.
- `visible_run_id` bindes, så SSE, push og chat persistence kan korreleres.
- En kilde tæller kun i metrics, hvis mindst én finding refererer til den.
- Et citation-link i slutrapporten skal resolve til en godkendt ledger-entry.
- DB-fejl må stoppe orkestreret mode før agents spawnes; et langt run uden
  durabel state er ikke acceptabelt.

## 9. Streaming og genoptagelse

### 9.1 Additive SSE events

Research bruger eksisterende `system_event` envelope:

```json
{"type":"system_event","kind":"research_started","payload":{
  "research_run_id":"research-...","tier":"orchestrated"
}}

{"type":"system_event","kind":"research_plan","payload":{
  "tasks":[{"id":"t1","title":"...","status":"pending"}]
}}

{"type":"system_event","kind":"research_progress","payload":{
  "phase":"researching","completed_tasks":2,"total_tasks":4,
  "sources":9,"active_tasks":["t3"]
}}

{"type":"system_event","kind":"research_source","payload":{
  "source_id":"src-...","title":"...","domain":"example.com",
  "source_type":"official"
}}

{"type":"system_event","kind":"research_warning","payload":{
  "code":"skill_unavailable","message":"Research-skill kunne ikke indlaeses"
}}

{"type":"system_event","kind":"research_completed","payload":{
  "research_run_id":"research-...","sources":14,"quality":"passed"
}}
```

Payloads må ikke indeholde rå chain-of-thought eller hele agentrapporter.
Klienter, der ikke kender events, ignorerer dem som i dag.

### 9.2 Mobil state

`StreamContext` reducerer research-events til en separat `ResearchUiState` i
stedet for at blande dem ind i tekstblokke. UI'et viser:

- fase (`Planlægger`, `Undersøger`, `Kontrollerer`, `Skriver rapport`);
- completed/total delspor;
- source count;
- seneste korte status;
- stopknap gennem eksisterende cancel-run.

Statusfladen ligger over composer/liveness-laget og ruller ikke med chatten.
Den forsvinder først ved terminal state, hvorefter slutrapporten bliver i
chatten.

### 9.3 Reconnect og app-koldstart

- Normal socket-reconnect fortsætter via `run_event_log` offset.
- `/chat/active-runs` udvides additivt med `research_run_id`, `research_status`
  og `research_tier`, eller mobilen kalder et fokuseret
  `/chat/sessions/{id}/active-research` endpoint.
- Ved koldstart henter mobilen snapshot fra `research_store` og rekonstruerer
  statusfladen, før live follow tilkobles.
- Stream-events er hints til UI; DB-snapshot er autoritet efter reconnect.
- En backend-procesrestart genoptager i første version ikke automatisk agents,
  men markerer forældede ikke-terminale runs `failed/restart_interrupted` og
  tilbyder retry. Automatisk checkpoint-resume er en senere fase.

### 9.4 Steering under run

Når single-flight finder et aktivt research-run, gemmes brugerens nye besked i
`research_steers` og signaleres til coordinatoren. Den anvendes ved næste
fasebarriere:

- planning: revider planen;
- researching: tilføj/prioritér et delspor inden for budget;
- verifying: tilføj et claim eller en kilde til kontrol;
- synthesizing: indarbejd som outputkrav, hvis final generation kan styres;
- terminal: start en normal ny tur.

Der spawnes aldrig et andet research-run i samme session som svar på steering.

## 10. Evidens- og kvalitetskontrakt

### 10.1 Source governance

Hver kilde har:

- canonical URL og retrieval timestamp;
- titel, publisher og publication date når kendt;
- type: `official`, `academic`, `secondary-industry`, `journalism`,
  `community`, `other`;
- access class: `public`, `semi-public`, `user-authorized-private`;
- authority score og stale flag;
- hvilke findings den støtter eller modsiger.

Primære/official sources foretrækkes for produktadfærd, lovgivning, priser,
specifikationer og virksomhedsclaims. Community-kilder kan vise erfaringer, men
må ikke alene bære et faktuelt hovedclaim.

### 10.2 Quality gates

Før completion måles:

1. **Instruction coverage:** alle eksplicitte dele af brugerens spørgsmål er
   dækket eller markeret som gap.
2. **Factual support:** væsentlige eksterne claims har en kilde.
3. **Citation entailment:** kilden støtter faktisk claimet, ikke kun emnet.
4. **Citation validity:** URL'en kan hentes eller er en legitim brugerfil.
5. **Source quality:** kritiske claims bruger bedst tilgængelige kildetype.
6. **Contradiction handling:** uenige kilder skjules ikke; forskellen forklares.
7. **Freshness:** tidsfølsomme claims har en passende `as_of`-dato.
8. **Calibration:** usikre eller ufuldstændige resultater mærkes som sådanne.
9. **Tool efficiency:** søgninger og agents holder sig inden for budget og
   reducerer reelle gaps.

Et gate-fail må ikke pyntes til success. Coordinatoren kan lave ét begrænset
repair-pass; derefter leveres en ærlig delrapport med gaps eller et struktureret
failure-resultat.

### 10.3 Stopbetingelser

Research stopper når én af disse er sand:

- alle planens spørgsmål har mindst ét tilstrækkeligt evidensspor og ingen
  åben kritisk contradiction;
- to successive søgebølger giver ingen nye støttede findings;
- tool-, token- eller wall-time-budget er brugt;
- brugeren afbryder;
- nødvendige kilder er utilgængelige og alternativer er udtømt;
- runtime/provider fejler efter den tilladte retry.

"Mange kilder" er ikke i sig selv en completion-betingelse.

## 11. Integration i eksisterende kode

### 11.1 Mobile filer

Forventede ændringer:

- `apps/mobile/src/components/Composer.tsx`
  - ikon-only layout og rækkefølge;
  - stabile knapdimensioner og accessibility;
  - primærknappens stop/send/wave-prioritet;
  - inline recorder-linje og transcribing/error states.
- `apps/mobile/src/components/ModelPicker.tsx`
  - forbliver picker for model + thinking;
  - alle ændringer skriver til aktiv chat-config.
- `apps/mobile/src/components/ChatSettingsSheet.tsx`
  - viser samme per-chat modelobjekt eller viderestiller til samme picker;
  - må ikke vedligeholde et andet modelvalg som kun består af model-id.
- `apps/mobile/src/lib/chatSettings.ts`
  - V2 schema, migration, samlet stream-projektion.
- `apps/mobile/src/screens/ChatScreen.tsx`
  - én per-chat config-state;
  - ingen separat transient research/thinking/global-model sandhed;
  - ingen reset efter send;
  - `chatCfg.stemme` styrer faktisk automatisk TTS for svar i den aktive
    samtale uden at starte hands-free mikrofonen;
  - wave kalder samtale-entry, mens mikrofon kalder dictation-controlleren;
  - session/lifecycle cleanup for aktiv diktering.
- `apps/mobile/src/lib/useVoiceConversation.ts`
  - forenkles til orb-baseret hands-free samtale;
  - ejer fortsat conversation capture, barge-in og streaming TTS;
  - eksponerer ikke længere push som bruger-valgt orb-mode.
- ny `apps/mobile/src/lib/useComposerDictation.ts`
  - ejer inline recording/transcription state machine og cleanup;
  - genbruger den eksisterende STT-klient og lydkonfiguration gennem en fælles,
    lille audio-capture helper, så recorder-semantik ikke kopieres.
- `apps/mobile/src/components/VoiceOverlay.tsx`
  - åbner direkte i hands-free;
  - fjerner push/hands-free segmentvælgeren og push-hold gestures.
- `apps/mobile/src/lib/chatPrompt.ts`
  - slettes, når alle call-sites og tests er migreret.
- `apps/mobile/src/lib/streamClient.ts`
  - `researchMode` request-felt.
- `apps/mobile/src/state/StreamContext.tsx`
  - request plumbing og `ResearchUiState`.
- `apps/mobile/src/lib/offlineOutbox.ts`
  - versioneret turn-controls.
- ny `apps/mobile/src/components/ResearchStatus.tsx`
  - flydende status over composer, ikke inde i chat-listen.
- eventuel fælles `apps/mobile/src/lib/audioCapture.ts`
  - kun den naturlige recorder-lifecycle, permission og cleanup, som både
    dictation og conversation faktisk deler;
  - VAD, barge-in og samtaleloop forbliver i `useVoiceConversation`.

Bemærk eksisterende duplikerede `thinkingMode` property i
`ChatScreen.ensureSessionAndSend`: den fjernes under den samlede projektion.

### 11.2 Backend filer

Forventede ændringer:

- `apps/api/jarvis_api/routes/chat.py`
  - additivt request-felt.
- `apps/api/jarvis_api/routes/chat_stream_v2.py`
  - research routing, aktiv-run metadata og legacy fallback wiring.
- `core/services/visible_runs_sections/detached_run.py`
  - vælger normal visible generator eller research-orchestrator og bevarer
    detached semantics.
- `core/services/prompt_contract.py`
  - læser en kompakt request-scoped researchsektion.
- `core/tools/simple_tools_web.py` og relevante connector-adapters
  - kalder den no-op-safe evidence collector med strukturerede tool-resultater;
  - almindelige runs er adfærdsmæssigt uændrede.
- `apps/api/jarvis_api/sse_v2_events.py`
  - kun dokumentation/typed helpers hvis nødvendigt; wire bruger fortsat
    `SystemEvent`.
- nye fokuserede research-moduler fra afsnit 7.2.

`core/services/visible_runs.py` er over Boy Scout-grænsen. Designet placerer
research-branching udenfor filen og bruger ContextVar-promptsektionen, så denne
leverance ikke behøver ændre dens logik. Bliver en ændring alligevel nødvendig,
skal nærmeste naturlige enhed først udskilles efter repoets Boy Scout-regel.

## 12. Fejlmodel

Kanoniske fejl bør mindst omfatte:

| Kode | Brugeradfærd | Runtimeadfærd |
|---|---|---|
| `research.skill_unavailable` | vis warning, fortsæt | minimumskontrakt |
| `research.plan_invalid` | kort retry-status | én replan, ellers fail |
| `research.worker_failed` | fortsæt hvis dækning findes | retry én gang/anden model |
| `research.source_unreachable` | markér gap | alternativ kilde |
| `research.verification_failed` | vis delresultat-advarsel | ét repair-pass |
| `research.budget_exhausted` | lever bedste delrapport | terminal incomplete |
| `research.cancelled` | behold hidtidig status kort | cancel children + finaliser |
| `research.restart_interrupted` | tilbyd retry | stale-run recovery |

En worker-fejl må ikke blive vist som et fund. Et orkestreret run må ikke stå
evigt `running`; stale cleanup og terminalisering er obligatorisk.

## 13. Sikkerhed og privatliv

- Research-agents er read-only uanset composerens `trust`-valg.
- `trust` må kun påvirke værktøjer, der kan ændre noget; det må ikke udvide
  research-agenters policy.
- Web- og connectorindhold er utroværdigt input og går gennem eksisterende
  abuse/prompt-injection guards.
- Credentials og connector tokens sendes aldrig i agentprompts eller events.
- User-authorized private sources må bruges til tredjepartsresearch, men ikke
  præsenteres som uafhængig verifikation af brugerens egne private claims.
- Events og source ledger må ikke lække private kilders rå indhold til andre
  sessioner eller brugere.
- Cancel propagates til aktive child-agents og lukker deres lifecycle records.

## 14. Teststrategi

Den fulde test-suite skal ikke køres for denne leverance. Kør berørte, fokuserede
suites og TypeScript-check.

### 14.1 Mobil unit/component tests

- Composer viser ingen model/research-labels og har rækkefølgen
  permissions -> model -> research.
- Ikonernes accessibility labels/states er korrekte.
- Tom composer viser wave; tekst/attachment viser send; working viser stop.
- Wave åbner orb direkte i hands-free og sender ikke en besked alene.
- Mikrofon åbner ikke orb; den viser recording -> transcribing inline.
- Dictation stop indsætter tekst i draft uden auto-send og uden at overskrive
  eksisterende tekst.
- Dictation cancel, STT-fejl, session-skift, background og unmount rydder native
  recorder sikkert og bevarer det eksisterende draft.
- Conversation og dictation kan ikke eje audio capture samtidigt.
- Chat settings V1 -> V2 migration, corrupt JSON og defaults.
- Model/provider/label gemmes og gendannes atomisk pr. session.
- Thinking, permissions, research, tool-scope og voice reloades pr. session.
- Research forbliver aktiv efter send og efter remount.
- Session A og B beholder forskellige valg.
- Offline outbox bevarer `research_mode` og øvrige turn-controls uden at ændre
  beskedteksten.
- Stream request sender `research_mode`; false/default er bagudkompatibel.
- Research SSE events bygger korrekt UI-state og ukendte kinds ignoreres.
- Research status ligger uden for `MessageList` og forsvinder terminalt.
- Settings reload-smoke dækker theme, accent, battery, location, bubble,
  camera og voice mode.

### 14.2 Backend unit tests

- `ChatStreamRequest` default false og accepterer true.
- Routerens boundary-cases: simpelt lookup -> inline; flerakset rapport ->
  orchestrated; kompleks men ikke parallel opgave -> inline.
- Research skill aktiveres deterministisk og degraderer ved manglende skill.
- State machine afviser ulovlige transitions og duplikerede aktive tasks.
- Worker-resultat normalisering afviser providerfejl og ukorrekt schema.
- Source dedup, stale marking og citation->ledger validation.
- Budget/stopbetingelser og max tre samtidige workers.
- Cancel og worker-failure terminaliserer alle records.
- Request-scoped context resettes mellem samtidige normale/research-runs.
- Brugerens persisterede tekst er identisk med input og indeholder aldrig
  research-instruktionen.
- SSE event payloads indeholder ingen rå agentprompt/reasoning.
- Detached reconnect og cold-start snapshot rekonstruerer status.

### 14.3 Integration/eval

Et lille fast eval-sæt på mindst 20 realistiske queries etableres fra dag ét:

- 6 simple lookups, som ikke må spawne agents;
- 6 paralleliserbare sammenligninger/rapporter;
- 4 tidsfølsomme eller modstridende emner;
- 2 dokument + web-opgaver;
- 2 failure/blocked-source cases.

Scoringsrubrik:

- factual accuracy;
- instruction coverage/completeness;
- citation entailment og citation validity;
- source quality;
- contradiction handling og calibration;
- tool efficiency, latency og cost;
- korrekt tier-valg.

Der logges baseline fra almindelig web-chat, inline research og orkestreret
research, så dyrere arkitektur kun rulles ud, hvis den faktisk forbedrer
kvaliteten på de opgaver, den vælger.

## 15. Observability

Mission Control/run telemetry skal kunne vise:

- valgt tier og router-signaler;
- plan/task-status og agent-ids;
- tool calls, tokenforbrug, wall time og estimeret cost pr. fase;
- source count, source-type-fordeling og duplicate rate;
- coverage, citation accuracy/validity og verification outcome;
- antal steer-events, retries og repair-pass;
- terminal failure code;
- inline-vs-orchestrated kvalitets- og prisfordeling.

Metrics må komme fra research-store/run-events, ikke fra UI-projektionen som en
anden sandhed.

## 16. Rollout

Feature flags i runtime settings:

```text
mobile_composer_icon_controls_enabled
research_request_metadata_enabled
research_inline_contract_enabled
research_orchestrator_enabled
research_progress_events_enabled
```

Faser:

1. **UI + persistence:** ikonrækken og V2 chat settings. Research sendes stadig
   ikke til backend, før metadataflaget er klar.
2. **Metadata + inline:** fjern prompt-prefix; aktivér server-side skill og
   evidenskontrakt. Orchestrator flag er off.
3. **Shadow router:** beregn tier og metrics, men kør alt inline.
4. **Orchestrated canary:** owner-only og udvalgte sessions; maks tre workers.
5. **General owner rollout:** quality/cost thresholds skal være opfyldt.
6. **Members:** først efter permission, connector isolation og quota-tests.

Rollback kan på hvert trin slå det nye flag fra. Når prompt-prefixet er fjernet,
må rollback ikke genindføre synlig styringstekst; fallback er normal chat eller
inline minimumskontrakt.

## 17. Acceptance-kriterier

Leverancen er færdig når:

1. Composerens tre indstillingsknapper er ikon-only i korrekt rækkefølge på
   små og store mobile viewports.
2. Mikrofonikonet giver inline diktering, hvis resultat lander som et redigerbart
   draft uden auto-send; wave åbner den hands-free orb-samtale, og den primære
   knap følger stop -> send -> wave-prioriteten uden tvetydige states.
3. En bruger kan sætte forskellige model/thinking/permission/research-valg i to
   samtaler, force-close appen og få præcis de samme valg tilbage.
4. Alle kontroller, der præsenteres som indstillinger, består persistence-audit;
   den gendannede værdi har reel effekt, og flygtig state er eksplicit
   klassificeret.
5. Research ændrer aldrig brugerens tekst eller transcript.
6. Research-mode aktiverer den kanoniske deep-research-kontrakt server-side.
7. Små opgaver spawner ingen agents; store paralleliserbare opgaver kan bruge
   eksisterende agents under et hårdt budget.
8. Jarvis skriver altid det endelige svar; workers vises kun som status/evidens.
9. Et orkestreret run fortsætter ved mobil disconnect og kan rekonstrueres efter
   app-koldstart.
10. Slutrapportens citations kan spores til ledgeren, og quality gates kan
   blokere falsk success.
11. Cancel, providerfejl, manglende skill og backend-restart ender i en synlig,
    terminal og retrybar tilstand.
12. Fokuserede mobil/backend-tests og typecheck består.
13. Build/release udføres først efter separat godkendt eksekveringsplan og
    implementation review.

## 18. Fagligt grundlag

Designet følger ikke ét produkts UI, men de fælles produktionsmønstre:

- OpenAI beskriver deep research som flertrins, selvstændig webundersøgelse med
  løbende progress, steering og en citeret rapport. Deres API understøtter
  baggrundsruns og genhentning, hvilket understøtter Jarvis' eksisterende valg
  om serverautoritative runs.
  - https://openai.com/index/introducing-deep-research/
  - https://help.openai.com/en/articles/10500283-deep-research
  - https://developers.openai.com/api/reference/cli/resources/responses/methods/create
- Anthropic bruger et orchestrator-worker-system med parallelle researcher-
  agents og et særskilt citation-pass. De rapporterer samtidig cirka 15x
  chat-tokenforbrug for multi-agent research og anbefaler det især til
  værdifulde opgaver med reelt parallel bredde.
  - https://www.anthropic.com/engineering/multi-agent-research-system
- Google bruger plan, iterativ søgning, custom/private sources, streaming og
  forskellige hastighed/dybde-profiler. Det støtter ét simpelt brugerintent med
  adaptiv runtimepolitik frem for at gøre hele orkestreringen til mobil-UI.
  - https://blog.google/products-and-platforms/products/gemini/google-gemini-deep-research/
  - https://blog.google/innovation-and-ai/models-and-research/gemini-models/next-generation-gemini-deep-research/
- BrowseComp viser, at browsing alene ikke er nok; persistent søgestrategi og
  reasoning er afgørende. Det bruges kun som search-hardness-eval, ikke som
  eneste kvalitetsmål for åbne rapporter.
  - https://openai.com/index/browsecomp/
- Long-form evals bør særskilt måle accuracy, completeness, presentation/
  objectivity og citation quality.
  - https://arxiv.org/abs/2506.11763
  - https://arxiv.org/abs/2602.11685

## 19. Aabne implementeringsvalg

Disse valg kan afgøres i eksekveringsplanen uden at ændre designet:

- `SearchCheck` versus `Telescope` som research-ikon efter screenshot-test.
- Om active-research snapshot udvider `/chat/active-runs` eller får et fokuseret
  endpoint. Der skal kun være én DB-autoritet i begge tilfælde.
- Præcise første budgettal efter baseline-måling. Arkitekturens hårde loft og
  max tre samtidige workers er ikke åbne valg.
