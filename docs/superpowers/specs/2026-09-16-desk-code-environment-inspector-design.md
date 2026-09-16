---
status: godkendt-design
created: 2026-09-16
owner: bjorn
implementation: ikke startet
---

# Desk Code-miljø og samlet inspector

## 1. Formål

Code-visningens Miljø-felt skal være en brugbar, levende oversigt over både
det aktive workspace og Jarvis' arbejde. Brugeren skal kunne aflæse status uden
at forlade samtalen og gå fra oversigt til dokumentation for det konkrete
arbejde med et enkelt klik.

Leverancen har fire brugerrettede resultater:

1. Workspace-delen starter med en tydelig ændringsstatus i formen
   **Ændringer +xx -xx**, hvor tilføjelser er grønne og sletninger røde.
2. Kilder er de faktiske URL'er, Jarvis brugte, ligesom kilderne under hans
   beskeder i chatview. Et klik viser først kilde og provenance i inspector.
3. Agenter kan åbnes og inspiceres. Brugeren kan se nuværende og tidligere
   arbejde og sende en besked til en aktiv agent fra en composer i panelet.
4. Tool-kald kan åbnes og viser deres rigtige input, status og resultat frem
   for kun en afkortet label.

Løsningen skal udvide Desk-appens eksisterende højre panel til en samlet
inspector. Den må ikke indføre parallelle drawers for artifacts, agenter,
kilder og tools.

## 2. Ikke-mål

- Der bygges ikke en ny agent-runtime eller beskedtransport.
- Der bygges ikke en ny kildeautoritet ved siden af samtalens content blocks.
- Miljø-feltet bliver ikke et nyt Mission Control-dashboard.
- Skjult chain-of-thought vises ikke. Agentens mål, status, synlige
  aktivitet, tool-kald, beskeder og resultater er tilladt.
- En agent må ikke identificeres ved at gætte ud fra tool-navn, rolle eller
  tekst. Interaktion kræver et autoritativt `agent_id`.
- Commit og pull request redesignes ikke funktionelt i denne leverance.
- Panelet skal ikke vise en fuld diff-editor. Eksisterende review-/filflader
  er fortsat ansvarlige for selve diffen og filindholdet.

## 3. Nuværende sandhed

### 3.1 Miljø-feltet mister data

`CodeView.tsx` flader sessionens og den aktive streams `tool_use`-blokke ud til
`ToolInvocation` med navn, input og i nogle tilfælde status. ID og resultat
bevares ikke. `EnvironmentPanel.tsx` kan derfor kun:

- genkende agentværktøjer via en hardcoded navneliste;
- vise generiske kildeetiketter som `Websøgning` og `Web-hentning`;
- vise afkortede tool-labels uden adgang til resultatet;
- samle afsluttede agenter efter tool-navn, selv om flere forskellige agenter
  kan have brugt samme dispatch-tool.

Denne fladning er ikke egnet som autoritet for inspector-navigation.

### 3.2 Faktiske kilder findes allerede

`lib/kilder.ts` udleder URL'er fra både tool-input, tool-resultat og
svarteksten. `Kilder.tsx` bruger dem under Jarvis' beskeder i chatview. Den
eksisterende `Kilde`-type bevarer dog kun URL og domæne; den bevarer ikke den
tool-blok, der fandt URL'en. Miljø-inspectoren skal genbruge udledningen, men
udvide den med provenance.

### 3.3 Agentdetaljer og kommunikation findes allerede

Agent Pool har API'er til agentens kørsler og beskeder samt handlingen
`sendTilAgent`. `AgentPoolPanel.tsx` har også en fungerende detaljevisning og
composer. Denne UI og dens datahentning skal trækkes ud som en delt komponent,
ikke kopieres ind i Code-visningen.

### 3.4 Højre panel er artifact-specifikt

`PanelContext` og `ArtifactPanel` accepterer kun artifacts. Code-visningen
skjuler Miljø-feltet, når artifact-panelet er åbent. Den eksisterende plads,
breddehåndtering og gensidige eksklusivitet er det rigtige fundament, men
kontrakten skal generaliseres til en typed inspector-target.

### 3.5 Git-status er kun en summering

`/chat/git-status` leverer branch, antal dirty filer samt samlet `added` og
`removed`. Det er nok til den ønskede topstatus. En opdelt liste over staged,
unstaged og untracked kræver et udvidet respons eller et separat eksisterende
workspace-endpoint og må ikke fabrikeres i klienten.

## 4. Produktstruktur

### 4.1 Miljø-feltets rækkefølge

Miljø-feltet vises som en kompakt statusflade i denne faste rækkefølge:

1. **Workspace**
2. **Aktivitet og kontekst**
3. **Agenter**
4. **Kilder**
5. **Seneste tools**

Der bruges sektioner og rækker, ikke kort inde i kort. Lange værdier afkortes
visuelt, men hele værdien er tilgængelig som tooltip eller i inspector.

### 4.2 Workspace-header

Første indholdsrække er altid ændringsstatus:

```text
Ændringer                         +146  -13
```

Krav:

- `+146` er grøn og `-13` er rød.
- Farve er ikke eneste signal; fortegn og tekst bevares.
- Et rent repository viser `Ingen ændringer` i neutral stil.
- Et ikke-git workspace viser `Git ikke aktivt` og skjuler git-handlinger.
- Branch, workspace-type, workspace-root og eventuel ahead/behind vises lige
  under status, når data findes.
- Refresh, terminal, review, commit og pull request bruger eksisterende
  handlers eller navigationsflader. Der oprettes ikke dobbelte workflows.
- Loading må ikke nulstille sidste kendte status til nul; en diskret
  opdateringstilstand vises oven på den seneste sandhed.

Hvis staged/unstaged/untracked tilføjes, skal backend levere de faktiske
kategorier og filstier. Klienten må ikke udlede dem fra `dirty`-tallet.

### 4.3 Aktivitet og kontekst

Sektionen samler den eksisterende `RunHealth`, nuværende arbejdsstatus,
sessionens tool-antal og tokenforbrug. Den er status, ikke en navigation til en
ny diagnostikside. Aktivt arbejde har en stabil liveness-indikator uden at
genmontere hele Miljø-feltet ved hvert stream-event.

### 4.4 Agenter

Hver agentrække viser:

- rolle eller menneskelæselig agenttype;
- en kort version af opgaven;
- status som `kører`, `venter`, `færdig` eller `fejlet`;
- en stabil farvemarkering, der ikke ændres ved rerender;
- seneste synlige aktivitet, hvis den findes.

Kun poster med et autoritativt `agent_id` er agentlinks. Et dispatch-tool uden
ID kan stadig åbnes som tool-resultat, men må ikke åbne agent-composeren.

Klik åbner agent-targetet i den fælles inspector. Aktive agentvisninger
opdaterer kørsler og beskeder med moderat polling. Polling stopper, når
targetet skjules, agenten afsluttes, appen går i baggrunden eller komponenten
unmountes.

### 4.5 Kilder

Kilderne er de samme faktiske URL'er som under Jarvis' beskeder. Miljø-feltet
viser domæne og eventuelt en kort titel; generiske labels som `Websøgning`
fjernes.

Første klik åbner en source-target i inspector med:

- fuld URL og domæne;
- hvilken søgning eller hentning der introducerede kilden;
- tool-navn, status og relevant input;
- det tilgængelige tool-resultat eller et afgrænset uddrag;
- en eksplicit `Åbn kilde`-handling, der åbner URL'en eksternt.

Kilder deduplikeres fortsat efter URL i brugsrækkefølge. Flere URL'er fra
samme domæne kan vises i inspector, selv om oversigten vælger at gruppere dem.
Interne runtime-adresser filtreres som i dag.

### 4.6 Tool-kald

De seneste tools vises som klikbare rækker med ikon, normaliseret label, kort
summary og status. Inspector viser:

- tool-navn og registry-label;
- `tool_use_id`;
- status og eventuel fejl;
- struktureret input;
- det foldede resultat;
- kilder fundet i netop dette kald;
- tidsdata, hvis protokollen leverer dem.

Input og output rendres struktureret, når de er JSON, og som preformatted text
ellers. Store resultater foldes progressivt i UI'et; de kopieres ikke ind i ny
global state.

## 5. Fælles inspector

### 5.1 Typed target

Den nuværende artifact-kontrakt generaliseres til en diskrimineret union:

```ts
type InspectorTarget =
  | { type: 'artifact'; artifact: Artifact }
  | { type: 'agent'; agentId: string; summary?: AgentSummary }
  | { type: 'source'; source: SourceEvidence }
  | { type: 'tool'; tool: ToolEvidence }
```

`PanelContext` ejer fortsat åben/lukket tilstand og bredde, men eksponerer et
`target` frem for kun `artifact`. Eksisterende artifact-call-sites skal kunne
migreres mekanisk via en kompatibel helper som `openArtifact`; de må ikke hver
især konstruere unionen.

Panelet renderer targetet gennem én `InspectorPanel`. Artifact-renderingen
beholder sin nuværende komponent og adfærd. Agent-, source- og tool-renderere
er isolerede komponenter med egne loading- og fejltilstande.

### 5.2 Navigation

Når et target er åbent fra Miljø, overtager inspectoren den eksisterende
højre panelplads. Headeren viser en tilbage-knap med label `Miljø` og en
luk-knap. Tilbage lukker targetet og genåbner Miljø-feltet uden at nulstille
dets collapse-state eller seneste git-status.

Der er kun ét inspector-target ad gangen. Klik på en kilde fra et tool-resultat
erstatter tool-targetet og gemmer et enkelt tilbage-link til tool-targetet.
Løsningen behøver ikke en generel browserhistorik i første version.

### 5.3 Agent-composer

Agent-inspectoren genbruger Agent Pools beskedfunktion. Composeren:

- vises kun for en autoritativ agent;
- sender med den eksisterende `sendTilAgent`-transport;
- deaktiveres under afsendelse og ved tom tekst;
- bevarer teksten ved fejl og viser fejlen lokalt;
- rydder først draftet efter bekræftet afsendelse;
- refresher beskedlisten efter succes;
- forklarer tydeligt, når en afsluttet agent ikke længere kan modtage beskeder.

Stop, suspend, resume og expire er ikke en del af den kompakte composer. Hvis de
bevares i detaljevisningen, skal deres eksisterende betydning og rettighedstjek
genbruges ordret; `suspend` må fortsat ikke fremstilles som et fysisk stop.

## 6. Datakontrakter

### 6.1 ToolEvidence

Miljø-feltet skal modtage evidensrige poster frem for den nuværende flade
`ToolInvocation`:

```ts
interface ToolEvidence {
  id: string
  name: string
  input: Record<string, unknown>
  status: 'running' | 'done' | 'error'
  result?: string
  runId?: string
  startedAt?: string
  finishedAt?: string
}
```

Live data kommer direkte fra foldede content blocks. Persisterede data bygges
fra beskedernes `content_json`. Sessionakkumulering må ikke kassere `id`,
`result` eller agentrelationer. LocalStorage er højst en cache; den er ikke
autoritet og skal versionsmærkes ved schemaændringen.

### 6.2 SourceEvidence

Kildeudledningen udvides uden at bryde `Kilde`-forbrugerne:

```ts
interface SourceEvidence extends Kilde {
  toolUseId?: string
  toolName?: string
  input?: Record<string, unknown>
  resultExcerpt?: string
  origin: 'tool_input' | 'tool_result' | 'assistant_text'
}
```

En ny helper returnerer provenance, mens `kilderFraBlokke` kan fortsat mappe
resultatet ned til den eksisterende `Kilde`-type for chatview. Dermed har
chatview og Miljø samme URL-regler og deduplikering.

### 6.3 Agentrelation

Agent-tools har ikke en dokumenteret fælles inputform for `agent_id`.
Implementeringen skal først kortlægge de faktiske tool-resultater for
`explore`, `task`, council og dispatch-tools. Derefter normaliseres relationen
ved stream-/content-block-grænsen eller i en dedikeret parser:

```ts
interface AgentReference {
  agentId: string
  role?: string
  goal?: string
  dispatchToolUseId: string
}
```

Hvis backend ikke returnerer `agent_id` for et dispatch, er det et
protokolhul. Den korrekte rettelse er at tilføje ID'et til tool-resultatet eller
et typed system-event. Klienten må ikke matche på måltekst eller den senest
oprettede agent.

## 7. Dataflow

```text
SSE / persisterede content blocks
              |
              v
      foldede tool_use-blokke
              |
      +-------+---------+
      |                 |
      v                 v
 ToolEvidence     SourceEvidence
      |
      v
 autoritativ AgentReference
      |
      v
 Miljø-oversigt --klik--> PanelContext<InspectorTarget>
                              |
                  +-----------+-----------+
                  |           |           |
               Agent       Source       Tool
                  |
                  v
       eksisterende Agent Pool API
```

Oversigten må gerne aflede korte labels, men inspector-targetet skal altid
bære eller kunne hente den bagvedliggende autoritative post.

## 8. Fejl- og tomtilstande

- Git utilgængelig: workspace-information vises stadig; git-handlinger skjules.
- Ingen ændringer: neutral `Ingen ændringer`, ikke en tom sektion.
- Ingen agenter/kilder/tools: sektionen skjules frem for at vise tomme kort.
- Ukendt agent-ID: posten åbnes som tool, ikke agent.
- Agent API fejler: seneste kendte summary bevares og retry tilbydes.
- Kilde uden tool-provenance: URL og `Fra svartekst` vises eksplicit.
- Tool uden resultat: `Kører` eller `Intet resultat gemt` vises; tom output må
  ikke ligne en vellykket, dokumenteret handling.
- Store eller ugyldige resultater må aldrig crashe panelet; fallback er rå
  tekst med en afgrænset første rendering.

## 9. Performance og tilgængelighed

- Miljø-feltet må ikke parse hele samtalehistorikken ved hvert token. Evidens
  udledes, når beskeder eller afsluttede tool-blokke ændres, og memoiseres.
- Agent polling er lazy, visibility-aware og scoped til åbent target.
- Lister har stabile keys baseret på tool- eller agent-ID, aldrig array-index.
- Klikbare rækker er rigtige buttons eller links med keyboard-focus.
- Status kommunikeres med tekst/ikon ud over farve.
- Inspector-header, tilbage-knap og luk-knap har entydige accessibility labels.
- Composerens input og send-knap kan bruges fuldt med tastatur.
- Panelets eksisterende responsive breddegrænser bevares. Tekst må ikke
  skubbe statuskolonnen eller ændre kontrollernes dimensioner.

## 10. Komponentgrænser

Forventede ejerskaber:

- `EnvironmentPanel`: kompakt oversigt og åbning af targets.
- `environmentEvidence`: normalisering af tools, kilder og agentreferencer.
- `PanelContext`: target, bredde og navigation.
- `InspectorPanel`: target-router og fælles chrome.
- `ArtifactInspector`: eksisterende artifact-rendering.
- `AgentInspector`: delt agentdetalje, historik og composer.
- `SourceInspector`: provenance og ekstern åbning.
- `ToolInspector`: struktureret input/resultat.
- `AgentPoolPanel`: liste og handlinger; bruger den delte `AgentInspector`.

Den nuværende `AgentDetalje` udtrækkes før den udvides, så Agent Pool og
Code-visningen ikke får to versioner af agentkommunikation.

## 11. Verifikation

Fokuserede tests skal mindst dække:

1. Workspace-header viser `+added` og `-removed` med separate semantiske
   klasser og en neutral clean-state.
2. Source-evidence binder hver URL til korrekt tool-input eller tool-resultat,
   filtrerer interne URL'er og bevarer chatviews eksisterende resultat.
3. To dispatches med samme tool-navn forbliver to poster, når de har
   forskellige ID'er.
4. En agent er kun klikbar med et autoritativt `agent_id`; ellers åbnes tool.
5. Panel-reduceren kan åbne, erstatte, gå tilbage og lukke alle targettyper
   uden at bryde artifacts.
6. Agent-inspectoren henter data lazy, sender besked, bevarer draft ved fejl og
   stopper polling ved unmount eller afsluttet agent.
7. Source-inspectoren åbner ikke URL'en ved rækkeklik; kun `Åbn kilde`
   udfører ekstern navigation.
8. Tool-inspectoren viser input, resultat, fejl og relaterede kilder.
9. CodeView-integrationen skjuler Miljø, mens inspector er åben, og vender
   tilbage til Miljø med bevaret status.
10. En tool-tung stream rerenderer ikke hele workspace-/git-delen pr. token.

Efter komponenttests verificeres Code-visningen visuelt i smal og bred desktop:

- ingen overlap med transcript, header, liveness eller composer;
- lange paths, agentmål og URL'er bryder ikke layoutet;
- sidepanelet kan resize;
- aktiv agent opdateres uden at flytte scroll eller composer.

Den fulde test-suite er ikke påkrævet. Der køres de berørte Desk-tests,
TypeScript-check og den relevante build.

## 12. Leverancerækkefølge

Implementeringen skal kunne deles i reviewbare faser:

1. Evidensmodel og provenance-tests.
2. Typed PanelContext og artifact-kompatibilitet.
3. Source- og tool-inspectorer.
4. Delt agent-inspector og autoritativ agentrelation.
5. Miljø-layout, workspace-header og CodeView-integration.
6. Fokuseret regressionstest, visuelt review og build.

En fase må ikke gøre agentrækker interaktive, før agent-ID-kontrakten er
verificeret. Det er den vigtigste korrekthedsgrænse i designet.
