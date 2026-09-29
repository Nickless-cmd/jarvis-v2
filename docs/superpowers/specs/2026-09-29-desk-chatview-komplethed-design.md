# Opgave 2 til Codex — chatview-komplethed, scroll-ejerskab og delte primitiver

> ⏸ **PARKERET indtil efter 3. oktober 2026 (Bjørn 29/9-2026).**
> Codex' kvote er opbrugt indtil da. Filen er færdig-redigeret og verificeret —
> den må **ikke** gives videre til codex før det. Den venter kun på kvoten.

Kopiér alt nedenfor ind i Codex.

> **Forudsætning:** Opgave 1 (streaming-ydelse og fence-korrekthed) er afsluttet. Denne opgave bygger ovenpå og gentager ikke dens punkter. Hvis et af punkterne her viser sig at være løst af Opgave 1, så sig det i stedet for at lave det om.

---

## Opgave

Repo: `/media/projects/jarvis-v2`
App: `apps/jarvis-desk` (Electron + React 19 + Vite, TypeScript, vitest)

Formålet er at lukke de huller der gør chatviewet ufærdigt sammenlignet med en moden agent-klient, og at fjerne de strukturelle årsager til at rendering og scrollning glider. Kildegrundlaget er en gennemgang af DeepSeek Harness (DSH) — 289 pakker i `~/.npm/_npx/ed2e730009a84a04/node_modules/@deepseek-ai/` — holdt op mod denne kodebase.

### Regler for arbejdet

1. Kør `npm test` i `apps/jarvis-desk` efter hver ændring. Alle eksisterende tests skal blive ved med at bestå.
2. Ingen nye npm-dependencies. Det gælder også virtuelle lister — byg det selv hvis det er nødvendigt.
3. Bevar kommentarstilen: dansk, med dato og begrundelse, der forklarer *hvorfor* — ikke hvad. Flere af kommentarerne i denne kodebase er bedre end hvad man finder i sammenlignelige projekter; skriv i samme ånd.
4. Tag én sektion ad gangen og commit separat.
5. Ved hver adfærdsændring der rører synligt output: afklar med Bjørn før merge, og hold det som separat commit.
6. Hvis et punkt viser sig forkert, umuligt eller allerede løst — sig det. Gennemtving det ikke.

### Test-disciplin — det her er ikke boilerplate

Reglen «alle tests skal blive ved at bestå» siger intet om hvorvidt de måler
noget. Fire tests skrevet i denne kodebase 29/9-2026 bestod uden at måle
noget som helst:

- én sammenlignede `sum(lens[:k])` med `sum(lens[:2])` mens `k == 2` — sand
  uanset hvad koden gjorde
- én kaldte en stub som fixturen havde sat i stedet for den rigtige funktion,
  og rapporterede «hentet 0 gange» om noget der aldrig blev kaldt
- to asserterede på ét felt af et resultat, så en mutation der ændrede alt
  andet gik igennem

Ingen af dem blev fanget af test-suiten. Alle fire blev fanget af
mutationskørsel. Derfor:

7. **Mutationsprøv hver test du skriver.** Slå den adfærd fra som testen
   påstår at måle, og se testen fejle. Gør den ikke det, måler den ingenting
   — uanset hvor grøn den er. Skriv i commit-beskeden hvilke mutationer du
   prøvede, og hvad de gjorde.
8. **Assertér hele det observerbare resultat**, ikke ét felt. Et objekt
   asserteres som objekt; relaterede fejltilstande som en tabel. Reglen står i
   `CLAUDE.md` under Code Rules med de to eksempler som begrundelse.
9. **Test den kolde sti.** Modul-niveau cache, singleton eller lazy init
   opfører sig anderledes ved første kald. 577 grønne tests missede to fejl
   som fem minutter på telefonen fandt, fordi forskellen var kold mod varm.
   Rammer din ændring en cache eller en `useRef`, så test tilstanden FØR den
   er varmet op.
10. **En måling der giver 0 % eller 100 % er næsten altid et brækket
    instrument, ikke et resultat.** Det skete fire gange på ét døgn i denne
    kodebase, hver gang på en dato- eller tidssammenligning. Kontrollér
    instrumentet før du tror på tallet: tæl hvad der kom med OG hvad der blev
    filtreret fra.
11. **En mutation der brækker filen syntaktisk måler ingenting.** Sker det —
    testen kører slet ikke i stedet for at fejle — så lav mutationen om så den
    ændrer *adfærd*. Det skete her samme dag: 4 af 14 tests kørte, og det lignede
    et bestået mutations-forsøg.

### Omfang og rækkefølge

Punkt 1 er den største enkeltgevinst og bør tages først — den er også forudsætningen for at punkt 2 kan testes ordentligt. Punkt 7 og 8 er rent visuelle og kan tages løbende.

**Tag ikke hele punkt 2 i én omgang.** Det er en fler-uges refaktorering. Start med `Button` og `Modal`, mål effekten, og beslut derefter. Begynd gerne først når en konkret fejl tvinger det frem — et halvt primitiv-lag er værre end intet, for så har du to måder at gøre alt på.

**Prioritering efter gennemlæsning mod koden (Jarvis, 29/9-2026):**

1. **Punkt 1a først** — en bug Bjørn har mærket, og forudsætningen for resten. Tag 1b separat.
2. **Punkt 3 bygges i den eksisterende skinne**, ikke som et nyt rail — se punkt 3.
3. **Punkt 9 er i praksis løst** af Opgave 1. Det er nu «verificér», ikke «byg».
4. **Punkt 2 udskydes** til en konkret udløser.
5. **Punkt 3, 4 og 5 er Bjørns kald** — produktbeslutninger, ikke huller som sammenligningen kan afgøre.
6. **To server-afhængigheder skal afklares FØR arbejdet starter:** punkt 3's turn-outline og punkt 5's locator for fuld tekst. Ellers bygges en halv feature der går i stå.

---

## Punkt 1 — Scroll-ejerskab som arkitektur, ikke som patches

**Filer:** `src/views/ChatView.tsx`, `src/views/CodeView.tsx`, `src/lib/useFastholdBund.ts`, `src/hooks/usePinVedStart.ts`, `src/styles/transcript-ydelse.css`

Der skrives til `scrollTop` **otte** steder i follow-stien, og de har hver sin opfattelse af hvem der bestemmer. En **niende** skriver — `components/rich/useFoldPosition.ts:19` — bevarer læsepositionen ved fold og er en anden slags; tag stilling til om den hører under koordinatoren:

| fil:linje | hvornår |
|---|---|
| `ChatView.tsx:396` | efter send |
| `ChatView.tsx:414` | ved ny besked |
| `ChatView.tsx:419` | `if (atBottom)` på besked-antal |
| `ChatView.tsx:450` | `ResizeObserver` på containeren |
| `useFastholdBund.ts:45` | hvert 250 ms mens der arbejdes |
| `usePinVedStart.ts:19` | ved overgang til "working" |
| `CodeView.tsx:598` | `scrollToBottom` — CodeViews egen, ikke delt |
| `CodeView.tsx:914` | `if (el && atBottom)` på besked-antal |

**Rettet 29/9-2026 (Jarvis, målt mod `main` `448b4fc1a`):** der stod «seks steder», og de to `CodeView`-skrivninger var ikke nævnt — `CodeView.tsx` manglede også i Filer-linjen. `useFastholdBund`-skrivningen står på `:45`, ikke `:39` (`:39` er `const el = ref.current`).

**Besluttet 29/9-2026 (Bjørn + Jarvis): `CodeView` er MED i denne opgave.** Den renderer den samme transcript-maskine — `CompactionNotice`, `KoeChip`, `JumpToLatest`, `NyeBeskederLinje`, `StickyPrompt`, `transcript-ydelse.css` — og dens egne kommentarer siger det: «samme som ChatView», «porteret 1:1 fra ChatView». Den har sin egen `atBottom`-state (`CodeView.tsx:517`) og kalder `usePinVedStart` med **samme** `onBund`-callback (`:602`).

Scopingen er ikke kosmetik. `usePinVedStart` er **delt** mellem de to views (`ChatView.tsx:432`, `CodeView.tsx:602`). Bygges koordinatoren kun for `ChatView`, skal ét hook-instans melde intent til **to forskellige koordinatorer** — præcis «et halvt lag er værre end intet», som punkt 2 selv advarer mod. Og `CodeView` har to `scrollTop`-skrivninger som dokumentet oprindeligt slet ikke nævnte (`:598`, `:914`).

Dertil CSS-ankeret i `transcript-ydelse.css:52-53`. `useFastholdBund.ts:1-22` dokumenterer selv hvorfor intervallet findes (Bjørn 17/9-2026): et svar kan lande ad en vej hvor hverken `stream.blocks`, `followState.blocks` eller besked-antallet ændrer sig, og `ResizeObserver` ser det ikke, fordi den kigger på containeren og ikke indholdet. **Det problem skal løses, ikke fjernes.**

DSH løser det ved at adskille **follow-intent** fra **DOM-skrivninger**. Seks controllere, én koordinator:

| controller | ejer |
|---|---|
| `useScrollFollow` | fælles bund-tærskler, follow-intent, native scrolling |
| `useProcessScroll` | gruppe-observation, initial placering, kant-fades |
| `useChatViewport` | turn-aware DOM-læsninger, clamped writes, ét paging-anker |
| `useChatReading` | follow-politik, samplet læser-input, semantisk hukommelse |
| `useChatNavigation` | turn-hop, anmoder viewport om bevarelse |
| `useChatScroll` | koordinerer deres committede inputs |

Kernen er: **præcis én controller skriver til DOM'en. De øvrige melder intent.** `useChatReading` beslutter *om* der skal følges; `useChatViewport` udfører den clamped skrivning.

### 1a — Indfør én scroll-koordinator

Byg `src/lib/useChatScroll.ts` (eller tilsvarende) med denne ansvarsdeling:

- **Læser** ejer `atBottom`/follow-intent og sampler brugerens input.
- **Viewport** er den eneste der skriver `scrollTop`.
- Alt andet — interval, resize, ny besked, stream-start — kalder en intent-funktion i stedet for at skrive selv.

Verificér at `useFastholdBund`s dækkede tilfælde stadig er dækket. Skriv en test der reproducerer 17/9-tilfældet: indhold vokser uden at blok-listen eller besked-antallet ændrer sig, og ruden skal følge med.

**Testen for 17/9-tilfældet er hele beviset — den skal mutationsprøves.**
Fjern nettet og se den fejle. Gør den ikke det, har du ikke reproduceret
tilfældet, og koordinatoren kan afskaffe beskyttelsen uden at nogen opdager
det. Kør samme test mod **begge** views (se 1c).

Kant-tilfælde der skal dækkes, hver med sin mutation:

| tilfælde | mutation der skal få testen til at fejle |
|---|---|
| indhold vokser, blok-liste og besked-antal uændret | fjern intervallet |
| brugeren har scrollet op mens der arbejdes | lad viewport skrive alligevel |
| læser-input præcis i bunden | udskyd follow-ejerskabet til næste sample |
| to skrivere vil skrive i samme frame | lad begge skrive |
| container resizes uden at indhold ændrer sig | fjern `ResizeObserver`-intent |

Den fjerde er den vigtige for arkitekturen: det er dén der beviser at der er
**én** skriver. Uden den test kan koordinatoren indføres uden at fjerne
problemet den findes for.

### 1b — Fire kant-tilfælde fra DSH der er værd at kopiere

**Læser-input der rammer præcis bunden opdaterer follow-ejerskabet med det samme.** Alt andet forbliver *pending* til sample-intervallet eller `scrollend` — også inden for tærsklen. Begrundelsen er vigtig: ellers kan layout-vækst spise en lille scroll-bevægelse, og brugeren oplever at ruden "stjæler" scrollen tilbage. Det er sandsynligvis den slags Bjørn har mærket.

**Semantisk anker ved historik-indskydning.** Ved "hent ældre" markeres ét anker i transcript-rækkefølge — den første ikke-tomme, ikke-skjulte markør, uden hit-testing eller geometri-søgning. Ankerets element måles, og forskydningen kompenseres: den cappede gruppe først, resten til transcript-scrollporten. En gen-monteret række findes via samme semantiske nøgle. `stickyPrompt`/`NyeBeskederLinje` kan levere markørerne.

**`overflow-y: clip` på transcript-roden, ikke `auto`.** Så roden *ikke* er en scroll-container. Det betyder at sticky kodebannere og udvidede headers refererer til den faktiske samtale-scrollport i stedet for en nærmere liggende ancestor. Verificér hvad der ændrer sig visuelt før du gør det.

**To uafhængige follow-tilstande.** Det ydre transcript og en åben capped gruppe følger hver for sig:

| Ydre følger | Gruppe følger | Til-bund-knap | Nyt indhold |
|---|---|---|---|
| Ja | Ja | skjult | hver scrollport følger sit eget gulv |
| Ja | Nej | skjult | ydre følger, gruppen holder position |
| Nej | Ja | synlig | gruppen følger, ydre holder læseposition |
| Nej | Nej | synlig | begge holder |

**Afklar med Bjørn** om 1b skal med i denne omgang eller udskydes. 1a er forudsætningen; 1b er forfinelsen.

---

### 1c — 17/9-nettet mangler helt i CodeView

**Selvstændig bug, ikke en flytning.** Målt mod `main` `448b4fc1a`:

`ChatView` har **to** værn mod 17/9-tilfældet:
- `usePinVedStart` (`ChatView.tsx:432`) — pin ved overgang til «working»
- `useFastholdBund` (`ChatView.tsx:434`) — **interval-nettet**, hvert 250 ms

`CodeView` har **kun den første** (`CodeView.tsx:602`). `useFastholdBund` kaldes ingen andre steder i `src` — den optræder kun i `ChatView.tsx` og sin egen test.

Konsekvensen er konkret: 17/9-scenariet — et svar der lander ad en vej hvor hverken `stream.blocks`, `followState.blocks` eller besked-antallet ændrer sig, og `ResizeObserver` ikke ser det fordi den kigger på containeren og ikke indholdet — har **intet net i code-mode**. Det er samme bug Bjørn mærkede i chat, og den står stadig åben i code.

**Skal løses, ikke bare dokumenteres.** Enten kalder `CodeView` `useFastholdBund` med samme kontrakt, eller koordinatoren fra 1a bærer nettet for **begge** views. Det sidste er at foretrække — to kald til ét hook er stadig to ejere.

---

## Punkt 2 — Delt primitiv-lag (start småt)

**Filer:** `src/components/shell/` (30 filer), `src/components/settings/` (21 filer), `src/components/` (13 filer)

Målt i kodebasen:

- **354** `<button>`-elementer (genmålt 29/9-2026 sent mod serverens main;
  gik 343 → 336 → 354 inden for ét døgn — tallet forfalder hurtigt)
- **10** komponenter der definerer en modal eller overlay (`aria-modal` / `role="dialog"`)
- **15** filer med deres egen `Escape`-håndtering
- **0** delte kontroller — der findes ingen fælles `Button`, `Modal`, `Menu`, `Tooltip` eller `Switch`

DSH's regel, citeret fra `client-ui-primitives`:

> *"A plugin cannot import another plugin's component, so this package is the only place a control can be shared: reuse what fits, and lift a deliberate visual difference into a prop rather than starting a second copy. […] What is not fine is copying a control that already exists here."*

**Vigtig korrektion til min tidligere vurdering:** `src/styles/tokens.css` findes og definerer **71 tokens** (`--bg-*`, `--fg-*`, `--radius-*`, `--accent`, `--danger`, `--warn` osv.). Token-laget er altså på plads. Det er **komponent-laget** der mangler. Det ændrer opgaven: du skal ikke indføre et designsystem, du skal løfte de kontroller der allerede findes som CSS-klasser op til komponenter der bruger de tokens.

**Start med to:**

1. **`Button`** med `variant` (`primary` | `ghost` | `outline` | `toolbar`). Ref skal pege på det native `<button>` så fokus og overlay-ankring virker. Find de mest brugte inline-mønstre og erstat dem — ikke alle 354 på én gang.
2. **`Modal`** der samler: overlay, Escape, fokusfælde, fokus-genoprettelse, `aria-modal`. DSH har `useModalLayer` til dette, inkl. fokus-genoprettelse efter Escape og app-luk, og `focusWithoutRing` så outline først vender tilbage ved Tab. Dine 14 spredte Escape-handlere er præcis hvad denne skal erstatte.

**Mål og rapportér:** antal `scrollTop`-skrivninger, antal Escape-handlere, antal `<button>`-elementer før og efter. Sæt ikke et mål for "alle" — sæt et mål for "de næste ti kaldesteder".

**Kant-tilfælde for `Modal`** — det er dem de 14 spredte handlere hver især
har løst halvt, og de er grunden til at et fælles lag betaler sig:

| tilfælde | mutation |
|---|---|
| Escape lukker ØVERSTE modal, ikke dem under | lad eventet boble |
| fokus vender tilbage til det element der åbnede | fokusér `body` i stedet |
| fokus-genoprettelse når elementet er unmountet imens | antag at det findes |
| fokusfælden slipper ikke ud med Tab/Shift+Tab | fjern wrap-around |
| `focusWithoutRing` — ring først ved Tab, ikke ved klik | vis ring altid |
| en menu inde i en modal spiser sin egen Escape først | lad modalen lukke |

Den sidste er DSH's eksplicitte regel og den letteste at tabe: trykker man
Escape i en åben `/`-menu (punkt 4), skal menuen lukke — ikke hele modalen
bagved.

**Kant for `Button`:** `ref` skal pege på det native `<button>`. Mutation:
returnér en wrapper-div. Fokus og overlay-ankring brækker stille, og intet
visuelt afslører det.

**Gør ikke:** indfør ikke et `Label`-krav på hver primitiv. DSH tvinger det igennem fordi deres pakker ikke kan nå `ctx.locale`; du er dansk-only, og det ville være ren friktion.

---

## Punkt 3 — Turn-navigation i den eksisterende skinne

**Skinnen findes allerede.** `src/components/chat/MessageRail.tsx` er en lodret navigations-skinne i **venstre kant** af chatviewet, monteret i `ChatView.tsx:988` og `CodeView.tsx:1129` som søskende til transcriptet. Den tegner `RailAnchor { id, label, fejl?, slags? }` som knapper, scroller til `[data-rail-id]`, lader markeringen følge scroll-positionen og folder titlerne ud ved hover. En tur der endte i fejl får en rød streg.

**Der skal ikke bygges et nyt rail.** Alt i dette punkt skal ind i `MessageRail` + `lib/railAnkre.ts` — ét rail, to kaldere (chat og code). DSH's `TurnNavigator` er en *anden* slags skinne (højre side, rent turn-baseret); den er kilde til **adfærd**, ikke til en ny komponent.

**Udseendet bevares (Bjørn 29/9-2026).** Skinnen skal se ud som den gør i dag — rækkeafstanden og tætheden ændres ikke. Vores nuværende afstand er `min-height: 10px` + `gap: 1px` (`app.css:3436` + `:3442` — panelet bærer `gap`, rækken `min-height`; linjetallene er flyttet siden 448b4fc1a), altså allerede tæt; den må **ikke** gøres større. DSH's pitch er kilden til *adfærd* (antallet af turns må ikke styre skinnens højde), **ikke** til et nyt visuelt design. Ingen ny luft mellem leddene. Ændringen i dette punkt er hvad skinnen *kan* og *hvornår* den følger — ikke hvordan den ser ud.

**Hvad skinnen har i dag** — verificeret i `lib/railAnkre.ts`:

- **Kapitler** fra serveren (`anchor_id`, `title`) via `useRailAnkre`.
- **Komprimeringer**, altid, som deres egen slags — de steder konteksten blev skåret over.
- **Fastgjorte** — brugerens egne pins; den eneste markering han selv har sat.
- Regel (Bjørn 16/9-2026): kort session (≤ `KORT_SESSION`) viser **én streg pr. tur**; lang session viser **kun serverens kapitler**. 147 streger var støj — den regel må ikke rives ned for at få «ét turn pr. streg» igen.

**Hvad der mangler — det er her DSH's model er kilden:**

1. **Tur-navigation også i en lang session.** I dag falder tur-stregerne væk når sessionen vokser. Støjen var ægte, så løsningen er ikke at vise alle igen. DSH's greb er **fast pitch**: hvert mærke har en fast højde uanset preview, og en stige højere end rammen scroller internt med gradient-fades. Det gør antallet af turns ligegyldigt for skinnens højde. **Højden er dog vores nuværende** — `min-height: 10px` + `gap: 1px` — ikke DSH's; det er princippet der lånes, ikke målene.
2. **Preview der kan læses uden hover.** I dag er labelen én linje, ≤72 tegn (`railLabel`). DSH viser én prompt-linje (50 tegn) og op til tre svarlinjer (120), og lader et turn der endnu ikke er indlæst vise kun sin prompt — eller blot sit nummer.
3. **Hop til et turn der ikke er i det indlæste vindue.** Det er den egentlige forskel: navigation skal være bredere end det indlæste vindue. DSH aktiverer et ikke-indlæst mærke ved at sidde historik gennem turn'ets `turn/start`-seq og lande på rækken.
4. **Kun synlige mærker monteres** — plus overscan og den aktive marks naboer. Fast pitch + observeret viewport-størrelse bestemmer offsets uden at læse DOM'ens scroll-udstrækning. Uden dette bliver en lang session dyr at tegne.
5. **Skjules når transcriptets tilgængelige bredde — ekskl. horisontal padding — er ≤900px.** Viewport-bredden er ikke kriteriet. Tjek om `msg-rail` allerede har en sådan regel; hvis ikke, er det den rigtige.
6. **Auto-follow:** hold skinnen stille mens den aktive marks centrum er inden for det fade-frie bånd, og centrér den når den forlader båndet. Previews følger pointer/fokus — mærker der scroller under en stillestående pointer skifter ikke preview.

**Server-siden skal afklares FØR du bygger.** En outline for *alle* startede turns — ikke kun de indlæste — findes ikke i dag: `useRailAnkre` henter `getSessionMilestones`, som er kapitler. Afklar om `/live` eller session-endpointet kan udvides med en turn-outline, eller om `turn/start`-sekvenser kan læses fra den gemte log. **Kan det ikke lade sig gøre uden server-ændringer, så byg kun punkterne 1, 2, 4, 5 og 6 over det indlæste vindue, og markér historik-navigationen (punkt 3) som udskudt i en kommentar.** Byg ikke en klient-side gætning på hvilke turns der findes.

**Afklar med Bjørn** før merge: det er en synlig flade, og skinnen er allerede hans.

---

## Punkt 4 — `/`-kommando- og reference-menu i komponisten

**Delvist bygget — rettet 29/9-2026 (Jarvis).** Dokumentet sagde «findes ikke i dag», men `@`-filreferencen **er** bygget: `lib/fileMention.ts` (`findAktivMention`, `indsætMention`, `rangerFiler`), `hooks/useFileMention.ts` (indekset hentes først når brugeren skriver `@`) og `components/shell/ComposerMention.test.tsx` (4 tests). Den tegner `.mention-liste` **over** feltet med filnavn i fed og stien klippet fra venstre (`direction: rtl`), så halen altid er synlig.

`/` findes derimod **kun som rå tekst**: `CodeView.tsx:460` og `ChatView.tsx:547` opfanger `/compact` med et regex og kører det — ingen menu, ingen forslag, ingen synlighed.

Det der reelt mangler er at **løfte `@`-mekanikken til at tage flere kilder**, så `/` og `@` deler samme komponent og forskellen kun er hvilke kilder der er tændt. `Composer.tsx` har desuden `forslag` — auto-forslag til *næste besked*, en tredje og uafhængig funktion.

DSH's `client-ui-input-trigger`: når brugeren skriver `/` eller `@` ved markøren, åbnes en **grupperet menu** for slash-kommandoer, fil-referencer og session-referencer. Den understøtter tastatur og pointer, inkl. drill-down og launchers der åbner én kandidatgruppe oven på den aktuelle markering. Et valg kalder enten et kommando-flow eller indsætter en reference som inputfladen håndterer.

Rangeringen er specificeret præcist (`rankByName`): forespørgslen skal være en **case-insensitiv ordnet delsekvens** af navnet. Prefix-hits rangerer først, derefter alignment-score, derefter kilde-rækkefølge.

Menyen skal lukke sig korrekt: Escape lukker menuen og *ikke* noget bagvedliggende — DSH har en eksplicit regel om at menuer konsumerer deres lokale Escape før modal-dismissal.

**Opgave:** byg trigger-detektion i `Composer` (tegn ved caret, kun i starten af et ord), en grupperet menu, og `rankByName` med DSH's rangering. Kilder i første omgang: kommandoer (findes de i API'et?) og filer (`@`). Brug den kommende `Modal`/`Menu`-primitiv fra punkt 2 hvis den er klar.

---

## Punkt 5 — Spill-lager og output-begrænsning

**Findes ikke i dag.** Verificeret: ingen `spill`-mekanisme i render-stien. Store tool-resultater lever i DOM'en.

DSH løser det i to lag:

**`output-retention`** — capper det en tool returnerer til modellen og *rapporterer hvad der blev udeladt*. `ItemRetainer` beholder et ordnet head-vindue og kan rapportere et eksakt antal udeladte elementer. `TextRetainer` beholder head-, tail- eller head-og-tail-bytevinduer uden at returnere ugyldig UTF-8 ved klippet. `formatRetentionNotice` tilføjer en ensartet udeladelses-klausul, mens hver tool leverer sin egen genopretnings-vejledning.

**`spill`** — et resultat over `maxInlineTokens` bliver til et *preview plus en locator*. Modellen ser en afgrænset preview; den fulde tekst er stadig hentbar via locatoren. `spill-policy` bestemmer hvornår der spilles, og `spill-local` er backenden.

**Opgave:**
- Implementér `TextRetainer`-mønstret (head+tail uden at splitte et surrogate-pair) i den danske kodebase. Brug det i `raekkeKroppe.tsx` hvor tool-output i dag vises råt.
- Tilføj en udeladelses-notits i samme stil som `formatRetentionNotice`, så brugeren kan se at noget er klippet.
- Undersøg om serveren kan levere en locator for fuld tekst. Hvis ikke, så implementér retention-laget nu og notér spill-laget som afhængigt af server-arbejde.

**Bemærk:** `truncateWithoutSplittingSurrogatePair` er ikke pynt. Et naivt
klip midt i et emoji giver et ødelagt tegn — men det farlige er ikke tegnet.
Ugyldig UTF-8 kan brække **serialiseringen** af hele beskeden længere nede,
og så er det ikke ét tegn der mangler, det er svaret.

DSH's `TextRetainer` arbejder på **bytes**, ikke tegn. Afklar hvilken du
bygger: JavaScript-strenge er UTF-16, så et `slice()` splitter surrogat-par,
mens et byte-vindue splitter multi-byte-sekvenser. De to fejl ser forskellige
ud og kræver hver sin test.

Kant-tilfælde, hver med sin mutation:

| tilfælde | mutation |
|---|---|
| klip præcis mellem to surrogater (emoji) | brug rå `slice()` |
| klip midt i en kombineret grapheme (flag, hudfarve) | klip på code point i stedet for grapheme |
| head+tail hvor de to vinduer overlapper | fjern overlap-tjekket |
| input kortere end vinduet | klip alligevel |
| tom streng | klip alligevel |
| udeladelses-notitsen selv | fjern tallet for hvad der blev udeladt |

**Tjek den klipper der allerede kører.** `core/services/tool_result_aging.py`
aldrer tool-resultater i produktion. Rettet 29/9-2026 (Jarvis): den klipper **ikke** på tegn — den aldrer på **udvekslinger** (`exchanges[:cut]`) og sender indhold over `_AGING_COMPRESS_MIN_CHARS = 2000` tegn til en `compress_fn` (i dag `_compact_llm_for_run`, `core/services/visible_runs.py:4971` — en LLM-komprimering, ikke et slice). Surrogat-risikoen ligger derfor i komprimeringen, ikke i et naivt klip. Den blev
rettet 28/9 (mærke på komprimerede resultater), men surrogat-spørgsmålet blev
ikke stillet. Mens du alligevel er i emnet: har den samme hul?

---

## Punkt 6 — Fælles geometri-model for output-kort

**Fil:** `src/components/rich/raekkeKroppe.tsx`

DSH's output-kort deler én geometri-model:

- `white-space: pre` med **horisontal scrollning**, så kolonnejusteret indhold beholder sin justering.
- Et **head-plus-tail-snit bag en expand-knap** når `maxLines` (standard **16**) overskrides, så en lang krop aldrig strækker kortet.
- `TerminalBlock` parser ANSI til React-spans med en **per-linje kolonnebuffer** for markørflytning, og respekterer erase-in-line, tabulatorstop og tegnbredde.
- Hosts kan fravælge geometrien per flade via CSS-variabler: `--dsl-terminal-command-whitespace`, `--dsl-terminal-line-whitespace`, `--dsl-terminal-output-max-height`, `--dsl-terminal-gutter`.
- Skillelinjen følger den *rendrede* krop, så et kørende kort der streamer live-output skiller kommando fra tekst ligesom et afsluttet kort.

I din kodebase har `Terminal` (`raekkeKroppe.tsx:359`) en `visHele`-udvidelse, men den gælder kun hele kommandoen, og der er ingen delt model — `Diff`, `Fil`, `Minde` og `Raadata` har hver sin.

**Opgave:** indfør `maxLines: 16` med head+tail-snit som delt mønster på tværs af output-kortene, med udvidelsesknap. Bevar horisontal scrollning for kolonnejusteret indhold. Verificér ANSI-parseren (`ansiStykker`, `raekkeKroppe.tsx:286`) håndterer
per-linje kolonnebuffer korrekt — sammenlign med DSH's beskrivelse og tilføj
test for markørflytning hvis det mangler.

Kant-tilfælde for parseren, hver med sin mutation:

| tilfælde | mutation |
|---|---|
| `\r` uden `\n` (progressbar der overskriver sig selv) | behandl `\r` som linjeskift |
| erase-in-line midt i en linje | ignorér erase-sekvensen |
| tabulatorstop | brug fast 8 kolonner uanset stop |
| dobbeltbrede tegn (CJK, emoji) | tæl dem som én kolonne |
| en sekvens der er delt over to bidder under streaming | parse hver bid isoleret |
| head+tail-snit midt i en aktiv farve | luk ikke farven ved snittet |

Den sidste er let at overse: klipper du 16-linjers-snittet midt i en åben
farvesekvens, farves resten af kortet. Og den femte er den der kun rammer
under streaming — den findes ikke i en test der fodrer hele teksten på én
gang.

**Afklar med Bjørn:** ændrer hvordan lange tool-resultater ser ud.

---

## Punkt 7 — Form-tallene

**Filer:** `src/styles/tokens.css`, `src/styles/app.css`, `src/styles/raekkevisning.css`

> **Verificeret mod koden 29/9-2026 (Jarvis).** Opgaven står ved magt — der
> findes **nul** afstands-tokens. Målt: `tokens.css` har **71** tokens
> (16 `--bg-*`, 13 `--fg-*`, 3 `--radius-*`, 2 bredder) og `--space`/`--gap`/
> `--pad` har **aldrig** eksisteret i nogen af de 10 CSS-filer.
> Spredningen er målt: **1.261** spacing-deklarationer i alt (`app.css` 982,
> `cheap-lane.css` 82, `raekkevisning.css` 57, `environment-inspector.css` 50,
> `desk-settings.css` 40, `cowork-categories.css` 37, `side-tasks.css` 13) med
> ~25 unikke px-værdier i `app.css` alene.
>
> **Men tabellen nedenfor er DSH's, og fire af de otte elementer findes ikke
> her.** Samme fejlklasse som punkt 8 — se den rettede tabel.

DSH's mål. Brug dem som udgangspunkt og tilpas til din visuelle identitet — men vælg *ét* tal pr. element frem for at lade hver skærm bestemme:

| element | DSH's mål | hvad der faktisk er her (målt 29/9-2026) |
|---|---|---|
| `Switch` | 36×20 | **ingen `Switch`-komponent.** Nærmeste er `.toggle` (`app.css:2339`) — **32×18**, radius 9 |
| `StateDot` | 10px slot; `ongoing` 14px | **findes ikke** (0 filer). Nærmeste er `PresenceDot` + `.liveness-dot` |
| `DisclosureRow` | fast 24px højde, titel og indhold side om side | **ikke en komponent her** — nævnes kun i `RaekkeTranskript.tsx` som reference til *forlægget* (`DisclosureRow.tsx:68`) |
| `Tag` | 11px kapsel | **ingen `.tag`-regel** i nogen CSS-fil |
| `Pill` på tekstlinje | 24px | findes, men **scoped**: `.connector-actions .pill` — 11px tekst, `padding: 3px 9px`, radius 999px |
| Output-kort fold | `maxLines` 16, head+tail | `maxLines` findes **ikke** i koden (se punkt 6) |
| `HoverCard` preview | ankerbredde −48px, 24px sideindvendig, max 420px højde | **findes ikke** (0 filer) |
| `Modal` | min. 24px viewport-margin | `.pv-bekraeft`: `inset: 0; margin: auto; width: min(460px, 92vw)` — ingen fast margin; under ~600px vindue falder sideafstanden under 24px |

**Afstande:**

| mellem | DSH's px | hvad der bruges i dag (målt 29/9-2026) |
|---|---|---|
| tool- og process-rækker | 6 | `raekkevisning.css` kører **fem** gap-værdier: 8 (3×), 9 (2×), 12 (5×), 16 (1×), 10 (2×) |
| udvidet gruppetitel → indhold | 8 | — |
| assistentsvar ↔ tilstødende process-rækker | 12 | — |
| turn-afslutning: varighed/status-kontroller | 16 | — |

**To tal DSH ikke har:** rækkevisningen bruger **9** og **10** som gap, og
**11px** som side-padding (~20 steder). De er ikke i nogen tabel.

**Tallene er ikke bundet til en betydning i dag.** `gap: 6px` står 63 steder i
`app.css` + `raekkevisning.css`, `gap: 8px` 82 steder, `gap: 12px` 21, `gap: 16px` 2.
Som padding: 6px 79 steder, 8px 106, 12px 52, 16px 21. At «6» er «tool- og
process-rækker» kan man ikke se nogen steder i kilden — det er præcis dét punkt
7 skal rette.

Skjulte og tomme rækker — inkl. bevarede tomme slot-ankre — tilføjer **ingen** afstand.

**Opgave:** saml disse i `tokens.css` som navngivne tokens og brug dem. Målet er ikke at ramme DSH's tal, men at der findes *ét* sted hvor hver afstand er bestemt. Dokumentér i en kommentar hvilke tal der er valgt og hvorfor de afviger.

**Vælg ud fra hvad der faktisk er der, ikke fra tabellen ovenfor.** Rækkevisningen
har allerede fem gap-værdier og en 11px side-padding; beslutningen er hvilke af
dem der er *betydning* og hvilke der er tilfældige.

**To vogtere du skal holde dig inden for (målt 29/9-2026):**
- `styles/tokens.test.ts` — «bruger ingen tokens der ikke er defineret». En ny
  `--space-*` skal **både** defineres i `tokens.css` og bruges med `var()`; et
  brug uden definition fejler testen.
- `styles/kaskade.test.ts` — en regel i én fil kan tabe til en anden fil med
  samme specificitet (den fejl kostede en hel runde 26/9). Samler du afstande i
  `tokens.css`, så verificér hvilken regel der vinder for elementer der bærer
  klasser fra to filer.

---

## Punkt 8 — Bevægelse

**Filer:** `src/styles/app.css`, `src/components/shell/` (eksisterende shimmer-komponenter)

**`TextShimmer`** — rettet 29/9-2026 (Jarvis): der findes **ingen** `TextShimmer`-komponent. Der er en `.shimmer`-CSS-klasse (`styles/liveness.css:25`) sat inline på et `<span>` — `.linje-titel`, `.rv-sumT`, `.rv-turTekst`, `.rv-arbejdsfortaelling` (`SkillLine.tsx:44`, `ThinkingLine.tsx:88`, `RaekkeTranskript.tsx:164/318/368`, `ToolGroupCard.tsx:94`). Dens animation er `shimmer-sweep 2.25s linear infinite` (`LabelSkift.test.tsx:169`) — altså **en anden rytme** end DSH's 1s sweep + 500ms hvile. Afklar om DSH-rytmen skal indføres, eller om 2.25s er den valgte identitet. Resten af kravene herunder står uændret:

- 300ms initial forsinkelse, **1s sweep**, 500ms hvile.
- Masken spænder over **indholdsbredden**, capes af den synlige række, og er **tiltet 15° fra lodret**, med flad top og bløde kanter.
- Den bevægende dekoration forbliver klippet til rækken **uden at forstørre dens scrollbare areal**. (Vigtigt — en shimmer der giver en scrollbar er en klassisk fejl.)
- Basis-teksten arver kalderens farve, inkl. hover-skift; temaet leverer det gennemsigtige highlight.
- **Ikoner og chevrons placeres uden for** shimmeren, så kun tekst og separatorer får highlight. Separatorer markeres med `data-shimmer-decoration`.
- Sammensatte børn rendres **to gange** mens den er aktiv og må derfor ikke have effekter eller element-ids.
- Reduced-motion beholder den statiske basis.

**`StateDot`** — rettet 29/9-2026 (Jarvis): der findes **ingen** `StateDot`. Den nærmeste er `components/shell/PresenceDot.tsx` (bruger `JarvisRing`, `size={22}`, `spinning` når `status === 'working'`) og `.liveness-dot` (`styles/liveness.css:38`). Princippet står: alle synlige loaders skal **pinnes til dokument-tid nul**, så de roterer i fase. Fire loaders der roterer forskudt ser forkert ud på en måde der er svær at pege på. Lille ændring, stor effekt.

**`ConnectionIndicator`** — rettet 29/9-2026 (Jarvis): komponenten hedder `components/shell/ConnectionPill.tsx` (grøn/rød `connection-dot` + host + ping-ms via `hooks/useConnection`). Verificér mod den: fader den ud over **150ms før unmount**, størrelser den sig til den aktuelle label, og skrider prikkerne frem **hver 500ms uafhængigt af retry-timingen**? Den bærer i dag en `title` på wrapperen — afklar om den native tooltip skal væk.

**`Tooltip`** — rettet 29/9-2026 (Jarvis): der findes **ingen** delt `Tooltip`-komponent. `title`-attributter og ad-hoc bobler bruges i bl.a. `CodeView.tsx`, `EditedFilesCard.tsx`, `CheapLaneChart.tsx`, `StickyPrompt.tsx`, `Composer.tsx` og `JobsPanel.tsx`. Bygges den, skal den flippe over/under kun når den modsatte side passer; ikke måle boblen synkront; genbruge anker-koordinater ved label- og viewport-ændringer.

---

## Punkt 9 — Streaming: verificér at Opgave 1's arbejde holder

**Nedgraderet 29/9-2026 — fra «byg» til «verificér».** Codex leverede det meste af dette som del af Opgave 1 samme dag: `fenceScanner.ts` + `c95025e65` (åben fence avanceres linje for linje), `chatCodeHighlight.ts` + `1e0de8517` (færdige token-linjer i faste grupper), `MarkdownRenderer.tsx` (frossen blok beholder sin tekst). Opgaven er derfor: bekræft de tre akser nedenfor mod den faktiske kode, og skriv de to kendte begrænsninger ind som kommentarer. Holder en akse ikke, så sig det — gennemtving den ikke.

DSH gør **begge** de ting Opgave 1 indførte — blokfrysning *og* linjeforsegling — som to akser:

> *"it freezes completed blocks, advances a top-level open fence by completed lines, and highlights that fence from saved Shiki grammar state. Completed token lines enter fixed-size React groups, so later chunks reconcile only the growing group; an unchanged fence retains that DOM when the final full parse resolves cross-document syntax."*

Den anden akse er den Opgave 1's punkt 3d lagde grunden til. Verificér at følgende holder efter Opgave 1:

1. **En åben top-level fence avanceres linje for linje** — linjer vises efterhånden som de afsluttes, og den nuværende delvise linje kører gennem samme grammatik. En lukkende fence eller en tvetydig parse falder tilbage til den almindelige hale-vej.
2. **Færdige token-linjer kommer i faste React-grupper**, så senere bidder kun rekoncilierer den voksende gruppe. En uændret fence beholder sit DOM når den endelige fulde parse løser syntaks på tværs af dokumentet.
3. **Den afsluttende fulde parse løser stadig referencer der krydsede freeze-grænsen.**

**Kendte begrænsninger DSH selv skriver højt** — accepter dem, prøv ikke at løse dem:
- En reference-link eller fodnote hvis definition ligger på den anden side af freeze-grænsen vises som **rå tekst** mens svaret streamer, og løses ved finalize.
- **En lang highlightet fence beholder hele sit token-DOM.** Streaming undgår re-parse og re-tokenize, men smider ikke gamle farver væk og virtualiserer ikke spans. Endelig DOM-størrelse følger stadig token-antallet. En patologisk enkelt lang linje falder tilbage til den almindelige hale-vej.

Skriv begge dele ind som kommentarer ved den relevante kode, så de ikke bliver "opført" som fejl senere.

**«Verificér» betyder ikke «læs koden og sig ja».** For hver af de tre akser:
find den test der beviser den, og mutationsprøv den. Findes der ingen test,
så er aksen ikke verificeret — den er antaget. Sig hvilke af de tre der havde
en test, og hvilke du måtte skrive.

Kant-tilfælde for fence-streamingen:

| tilfælde | mutation |
|---|---|
| en bid der slutter midt i en fence-markør (to af tre backticks) | behandl den som lukket |
| en fence der aldrig lukkes | frys den alligevel |
| indlejret fence i en liste eller citat | behandl som top-level |
| sproget angives efter at fencen er åbnet | lås sproget ved åbning |
| en enkelt patologisk lang linje | frys i stedet for at falde til hale-vejen |

Den sidste står allerede som en kendt begrænsning. Verificér at
fallback'en faktisk udløses — en dokumenteret begrænsning der ikke virker er
værre end en udokumenteret, fordi ingen leder efter den.

---

## Punkt 10 — Hvad du IKKE skal kopiere

**289 pakker er ikke et mål.** DSH er bygget til at tredjeparter kan udvide den via `cordis.yml`, og størstedelen af de 289 pakker findes fordi *en plugin ikke kan importere en anden plugins komponent*. Du har ét produkt og ét repo. Tag lektionen — del kontrollerne (punkt 2) — men ikke strukturen.

**Ingen lokaliseringstvang.** DSH kræver komplette labels på hver primitiv og lader udeladelse fejle i typechecker. Du er dansk-only. Ren friktion.

**Ingen pakke-grænser i koden.** DSH's `client-ui-*`-opdeling følger deres plugin-grænseflade, ikke et domæne. I én applikation er mapper nok.

**Kopier ikke `chunked-list`** med mindre du får et konkret behov for versionsbevarende lister. Det er løst for et problem du ikke har beskrevet.

---

## Definition of done

- `npm test` grøn i `apps/jarvis-desk` — og **hver ny test mutationsprøvet**.
  Grøn alene er ikke en accept: rapportér for hvert punkt hvilke mutationer du
  prøvede, og at de fik testen til at fejle. En mutation der ikke fik nogen
  test til at fejle er et hul du skal nævne, ikke skjule.
- Punkt 1a: én funktion skriver `scrollTop` i **både** `ChatView` og `CodeView`. En test reproducerer 17/9-tilfældet og består.
- Punkt 1c: 17/9-nettet dækker `CodeView`, ikke kun `ChatView` — testen fra 1a skal kunne køres mod begge views.
- Punkt 2: `Button` og `Modal` findes og er taget i brug på mindst ti kaldesteder hver. Antal spredte Escape-handlere er faldet.
- Punkt 3: turn-navigation bygget **ind i det eksisterende `MessageRail`** — ikke som et nyt rail. Skinnens **udseende og rækkeafstand er uændret** (`min-height: 10px` + `gap: 1px`; ingen ny luft). Server-outline afklaret først; afklaret med Bjørn før merge.
- Punkt 4: bygget hvis afklaret med Bjørn, ellers dokumenteret som udskudt med en begrundelse.
- Punkt 5: retention-laget findes med test for surrogate-pair-klippet.
- Punkt 6–8: de valgte tal og specs står ét sted, med kommentar om afvigelser.
- Punkt 9: de tre akser verificeret mod koden, og de to kendte begrænsninger står som kommentarer.
- Ingen nye dependencies.
- **Tallene i dette dokument er fra `448b4fc1a` (29/9-2026) og forfalder.**
  Genmålt mod serverens `main` 29/9-2026 sent (Jarvis): `<button>` gik
  343 → 336 → **354**, modaler 9 → **10**, Escape-filer 14 → **15**. Stigningen
  er ægte — panelet fik nye menuer samme dag. Stemmer et tal ikke, så sig det
  og brug dit eget.

**Rapportér tilbage:** for hvert punkt — hvad du gjorde, hvilke tal du målte før/efter, hvad du valgte ikke at gøre og hvorfor. Sig det hvis et punkt er forkert, allerede løst, eller ikke kan lade sig gøre. Målingerne bag denne opgave er taget mod `main` `448b4fc1a` (29/9-2026, app `apps/jarvis-desk`, rent træ); hvis koden er ændret siden, er de forældede. Enkelte tal er efterprøvet og rettet samme dag — se punkt 1 og punkt 2.
