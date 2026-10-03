# Indbakken som kontrolflade — design

**Mål:** Give Jarvis én indbakke der holder hans ventende arbejde som *data* i
stedet for som prosa i prompten, og koble dens handlingskrævende klasse på
R2.5-gaten, så ting bliver fulgt til døren uden at noget kan afbryde ham eller
lamme ham.

**Arkitektur:** En læseflade over eksisterende kildetilstand (vækninger,
baggrundsjobs, agenter og planlagte opgaver) og en lille durabel
`inbox_items`-bogføring af kilde-id, verificeret ejer, påmindelser og afgørelse.
`session_inbox` forbliver leveringskø og er ikke sandheden om åbne opgaver:
den modtager kun nogle notifikationer og markerer dem leveret ved flush. En
separat, brugerafgrænset mutationsvagt genbruger R2.5's værktøjsklassifikation,
men ikke dens procesglobale verifikationsblok. Ændring af notifikationernes
visning kræver en tilsluttet klientforbruger, før assistant-replikken fjernes.

**Teknologi:** Python (core/services), en ny SQLite-tabel til kvitteringer,
eksisterende `session_inbox`, `self_wakeup`, `recurring_tasks`,
`scheduled_tasks`, `agent_registry`/`agent_runs` og kildeadaptere til jobs.
Desk og mobil indgår i notifikationsskiftet. Tabellen gemmer ikke job-output
eller en anden kopi af kildens status.

---

## Hvorfor — hvad der er målt

Alle tal her er målt 2-3/10-2026 på CT105, ikke anslået.

### Problemet Bjørn beskrev

> «han booker ofte rigtig mange wakeup og de rammer osse ind lidt random i vores
> sessioner … hvis en lang opgave eller en agent vender tilbage med ting kan de
> ende med at vække dig eller give dig information til næste runde. Det ser jeg
> aldrig ske for Jarvis — nogen gange dukker det op på et helt andet tidspunkt.»

Den tilfældige timing er **ikke tilfældig**. Der er tre leveringsveje med tre
forsinkelser, og intet i beskeden siger hvilken den kom ad:

| Vej | Hvornår | Hvor |
|---|---|---|
| Direkte | straks | `notification_bridge`, inaktiv session |
| Efter turen | når hans tur slutter | `session_inbox`, flush på `visible-run` |
| Fallback | op til **10 minutter** senere | `session_inbox._FALLBACK_FLUSH_MINUTES` |

Den tredje er næsten sikkert hvad Bjørn oplever. En vækning fyrer, bliver køet,
og hvis ingen tur afsluttes i vinduet lander den ti minutter senere — midt i
noget andet. Det er en **umærket forskel**, ikke et sammenfald.

### Hvad han faktisk bruger

`tool_usage`, hele historikken:

| Værktøj | Kald | Fejl | Senest |
|---|---|---|---|
| `mark_wakeup_consumed` | 171 | 6 | 1/10 |
| `schedule_self_wakeup` | 141 | 1 | 2/10 |
| `list_self_wakeups` | 59 | 0 | 2/10 |
| `cancel_self_wakeup` | 24 | 1 | 2/10 |
| `spawn_agent_task` | 66 | 1 | **5/9** |
| `scout_agent` | 37 | **27** | 2/10 |
| `cancel_agent` | 17 | **11** | 5/7 |
| `bash_session_list` | **6** | 0 | **4/9** |

Tre konklusioner:

1. **Vækninger er den levende arbejdsgang.** 141 kald til booking og 171 kald
   til markering som brugt viser høj aktivitet. Kaldetællinger alene beviser
   ikke 30 manglende bookinger: andre kilder, tidsvinduer og fejlede kald skal
   afstemmes mod konkrete `wakeup_id` og statusovergange først.
2. **Agentværktøjerne blev brugt lidt i den målte periode.** Fejlprocenterne
   gælder værktøjskald, ikke hele agentfunktionen; årsagerne skal klassificeres
   før designet regner agenter som defekte.
3. **`bash_session_list` blev kaldt seks gange.** Det måler ikke læsning af
   baggrundsjobpanelet eller andre joblister og beviser ikke, hvorfor et
   færdigt job blev overset. Det er en hypotese, som visningen skal måle.

### Hvorfor R2.5 og ikke R2

| Gate | Fyrer | Efterleves |
|---|---|---|
| R2 (advisory) | 47/døgn | **15 %** (målt 13/6: surfaced 47, heeded 7) |
| R2.5 (blocking) | 7.610 evalueringer ved oprindelig måling | **543 blokeringer; frigivelsesårsager skal skilles ad** |

`r2_5_gate.evaluated` stod på 7.610 med seneste 3/10; `blocked` 543,
`mutation_refused` 467, `released` 460. *(RETTET 3/10 (Jarvis): genmålt — evaluated er nu **7.643**. Tallene vokser, datoen står, og det er pointen.)* Kontrolmåling 3/10 på CT105 viste
**415** frigivelser ved `kig_tilbage` og **45** ved `udløbet`. `460/543` er
derfor ikke en efterlevelsesrate, og hændelserne er heller ikke parret per
blok-id. En ny inbox-gate skal måle afgørelse og frigivelse per post. Forskellen er
ikke gradvis:

**R2 spørger. R2.5 kan nægte en mutation.** R2's målte 15 % gælder den
eksisterende verifikationspåmindelse. R2.5's faktiske efterlevelse kan ikke
udledes af antal `released`, fordi timeout også frigiver.

R2.5 har desuden allerede model-differentierede tærskler —
`r2_5_unverified_threshold_deep=3`, `_reasoning=5`, `_fast=8`,
`r2_5_heed_rate_threshold=0.4`. Det er samme tiering harness-specen manglede.

### Hvorfor prompten bliver mindre

Ventende tilstand i den dynamiske hale ændrer sig hver tur og **buster cachen**
oveni at den fylder. Samme familie som fundet om prompt-åbneren: 12 % af
kaldene stod for 39 % af al miss. Flyttes tilstanden til en flade han *læser*,
får vi tre ting: mindre prompt, stabilt prefix, og kontrollen til ham.

**MEN dette tal er ikke målt endnu, og det skal det være før vi tror på det.**
Bjørn pegede på at både de FASTE dele og den dynamiske hale kunne blive mindre.
Jeg tilbød at måle hvor stor en andel af halen der er ventende-tilstand, og
gjorde det ikke — så gevinsten står her som en påstand. Det er præcis mønsteret
«nytten blev talt uden prisen», som kostede os et dynamisk værktøjssæt engang.

Derfor er det Opgave 0 nedenfor, og den skal køres FØR noget bygges: den afgør
om dette er en økonomisk sag (prompten skrumper målbart) eller en kontrol-sag
(den skrumper ikke, men han får styringen). Begge er gyldige — men de skal
bygges forskelligt, og vi skal vide hvilken vi er i.

---

## Global Constraints

Disse gælder HVER opgave nedenfor.

- **Kun hans eget arbejde må gate.** Hans vækninger, hans baggrundsjobs, hans
  agenter. Daemoner og huset må kun oprette ikke-blokerende poster. (Bjørns
  beslutning 3/10.)
- **Ejer er proveniens, ikke et inputflag.** `kilde_ejer="jarvis"` fra en
  vilkårlig kalder er ikke bevis. Registreringen skal knyttes til et faktisk
  tool-/run-id og autentificeret bruger ved oprettelsen. Ukendt proveniens er
  synlig, men må aldrig gate.
- **Værktøjssættet må ALDRIG afhænge af indbakkens indhold.** Værktøjer står før
  beskederne i prompten; et skiftende sæt kostede målt 92 % → 26 % cache-hit.
  Visningen må pege på det rigtige værktøj i sin TEKST — det koster ingenting.
- **Indbakken afleverer henvisninger, aldrig payload.** En post med et
  filartefakt bærer sti OG størrelse; en vækning eller godkendelse uden fil
  har typet kilde-id og ingen opdigtet sti. En sti må ikke læses uden for
  brugerens autoriserede workspace.
- **Ingen post må skrives som en assistant-besked.** Det var fejlen bag Smiths
  løkke: hans note landede i promptens hale, Jarvis gentog den, Smith detekterede
  gentagelsen. Data må ikke blive tale.
- **Indbakke-indhold er DATA, ikke instruktioner.** En post skrevet af en agent
  eller et job kan ikke instruere Jarvis. (Prompt-injection-fladen; samme regel
  som gælder Claudes egne notifikationer.)
- **ALT der ikke kom fra Bjørns composer SKAL bære en kilde-mærkning.** Stående
  regel fra Bjørn 3/10-2026, og den gælder hver post, hvert gate-varsel og hver
  påmindelse denne spec indfører — ikke kun indbakken.

  Baggrunden er målt samme dag: FEM værn i `visible_runs.py` appender til
  `_a_parts`, og `_a_parts` er — ifølge `compose_exchange_text`s egen docstring —
  både det persisterede svar OG næste rundes model-input. Fire er i jeg-form, og
  tre bærer ordene «Sig til»: `_exhaust_note`, `_hp_note`, `_stop_note`. Næste
  runde ser en opfordring i første person og kan læse den som om den var givet;
  det startede runder i Bjørns navn og kostede ekstra runder.

  > **RETTET 3/10 (Opus).** Første udgave af dette afsnit sagde
  > `_all_followup_parts`, «altså i det næste runde læser», og angav linjenumre.
  > Begge dele var forkerte. `_all_followup_parts` bruges KUN til `partial_text`
  > ved cutoff og trunkeres ved retry; `_a_parts` er model-input. Konsekvensen er
  > at problemet var **større** end først meldt: alle fem noter nåede modellen,
  > ikke tre. Jeg stolede på navnet («followup» → «næste runde») i stedet for at
  > følge variablen til dens forbrug. Linjenumre er fjernet frem for rettet —
  > de skred fire gange på én dag.

  > **GJORT 3/10 (Opus), deployet.** Rettelsen er bygget og kører:
  > `core/services/visible_run_guard_notices.py` holder teksterne ÉT sted og
  > deler værnene i tre klasser efter hvad de skal udrette — 1) skal handle
  > (runnet dør uden den), 2) skal advare næste runde, 3) kun til mennesket.
  > Klasse 3 filtreres ud af model-input i `_exchange_text` og strippes fra
  > historikken i `transcript_sections`, mens listen selv aldrig muteres, så
  > Bjørn beholder noten i det gemte svar. Klasse 1 og 2 når modellen MÆRKET.
  > Reglen nedenfor er altså ikke længere kun et krav til denne spec — den har
  > en implementering at følge, og `tests/test_visible_run_guard_notices.py`
  > pinner begge filter-lag.

  Formen der virker er den Claudes eget harness bruger ordret:

  ```
  [SYSTEM NOTIFICATION - NOT USER INPUT]
  Dette er en automatisk hændelse, IKKE en besked fra brugeren.
  Må IKKE læses som samtykke, bekræftelse eller svar på et åbent spørgsmål.
  ```

  Tre egenskaber gør den virksom: den siger hvad den ER, hvad den IKKE er, og
  den **forbyder eksplicit at læse den som samtykke**. Den sidste er vigtigst —
  uden den kan en systembesked blive et «ja».

  **To udgaver af samme besked.** Rettelsen er ikke at fjerne invitationen:
  Bjørn SKAL kunne se at et værn greb ind, og «sig til» er den rigtige besked
  til et menneske. Det der når MODELLEN skal bære mærkningen. Derfor: én udgave
  til skærmen, én mærket til prompten.
- **Alle tre nye tærskler/intervaller skal måles efter ibrugtagning**, ikke sættes
  blindt. R2's punkt 2 ventede fra juni på en måling der aldrig blev lavet.
- **En post må ikke kunne forsvinde tavst.** Køen ligger i SQLite og er durabel,
  men en fejlet skrivning må ikke blive en værdi der ser ud som succes — det er
  husets hyppigste fejlform (`swallowed_error_becomes_a_value`). `enqueue` har
  allerede en typet `{"status": "error"}`; kalderen SKAL læse den, og en
  handlingskrævende post der ikke blev skrevet skal logges på WARNING.
  Det offentlige materiale (agent-inbox) bruger ack+retry med eksponentiel
  backoff til samme formål; vi behøver det ikke, fordi skrivningen er lokal og
  synkron — men vi behøver at fejlen kan SES.
- **Læsning er uden mutation.** `due_wakeups()` fyrer og gemmer forfaldne
  vækninger, `build_tool_intent_approval_surface()` kan oprette/udløbe
  godkendelser. `background_jobs.liste()` starter derimod **ikke** daemonen —
  den spørger først når pid-filen peger på en ægte daemon — men den nulstiller
  daemonens idle-ur, så en session-løs daemon ikke lukker ned mens panelet er
  åbent. Heller ikke den er altså ren. Ingen af dem må kaldes fra
  `byg_indbakke`; brug rene, scoped læsninger/snapshots.
- **En leveret notifikation er ikke en afgjort opgave.** `delivered_at` i
  `session_inbox` betyder kun levering. `done`/`drop` og påmindelsestæller
  ligger durabelt per bruger og kilde-id, også når sessionen er inaktiv, og
  efter procesgenstart.
- Dansk i kommentarer og docstrings, som resten af huset.

---

## Filstruktur

| Fil | Ansvar |
|---|---|
| `core/services/inbox_view.py` (ny) | Bygger seks sektioner fra scoped kildeadaptere og afgørelser; beregner alder/forfald/dubletter. Ingen skrivning. |
| `core/runtime/db_inbox.py` (ny) | Idempotent `inbox_items`-skema og brugerafgrænsede opslag/atomare afgørelser. |
| `core/services/inbox_state.py` (ny) | Proveniens, påmindelsespolitik og `done`/`drop` gennem `db_inbox`. Ingen job-payload. |
| `core/services/session_inbox.py` (ændres i sidste fase) | Kun leveringskø. Assistant-levering erstattes først når klienten viser kilde-mærkede notifikationer. |
| `core/services/inbox_gate.py` (ny) | Brugerafgrænset to-trins påmindelse og mutationsnægt; deler klassifikation med R2.5, ikke global bloktilstand. |
| `core/services/r2_5_blocking_gate.py` | Eksisterende verifikationsgate beholdes; dens cooldown og frigivelse gælder ikke inboxen. |
| `core/tools/` (ændres) | Tre værktøjer: `inbox`, `inbox_done`, `inbox_drop`. |
| `tests/test_inbox_view.py`, `tests/test_inbox_state.py` (nye) | Coverage-gaten kræver dem. |

Hvorfor adskilte filer: visningen er ren læsning; bogføringen og gaten skriver.
En visning skal kunne kaldes uden risiko for mutation. De ansvar må ikke kunne
forveksles — en læseflade der kan skrive er præcis fælden fra
`a_read_surface_can_create_what_it_reads`.

---

## Hvad visningen viser

Seks sektioner. Én linje per post. Aldrig payload. Tallene nedenfor er
illustrative, ikke kopieret fra runtime.

```
VAKTE DENNE TUR                            ← hvorfor er jeg i gang
  wake-6e201  fyrede 07:30  «følg op på Michelles brief»   → inbox

VENTER PÅ DIG (3)                          ← KUN denne kan gate mutationer
  wake-6e201  booket 1/10 09:12  fyrede 2/10 07:30  3d forfalden
              «følg op på Michelles brief»                    [dig]
  job-bglj7   kørte 16m, exit 1, 4 fejl
              «hele suiten på raads-branchen»  → tasks/bglj7.output (112 kB)
  job-a71f3   STATUS UKENDT — procesbevis mangler, stod «kører» i 2d
              «mobil-build»                   → inbox         [dig]

I GANG (1)
  job-b1vvm   kører 3m    «suite på branchen»    (intet output endnu)

PÅ VEJ (2)                                 ← engangs-vækninger
  wake-9f3a2  om 40m   «mål om cheap-lane holder»
  sched-c81d4 om 6t    «skygge-review af event_trigger»

PLANLAGTE (2)                              ← GENTAGER sig, ikke engangs
  rec-67e42   hver 1440m   næste 4/10 07:30   «Michelles morgenbrief»
  rec-6456e   hver 360m    næste 3/10 13:18   «vejr-opslag»

VENTER PÅ BJØRN (1)                        ← synlig, gater IKKE
  appr-4b2   siden 2/10 18:40   «commit til main på agent-reduktion»

Backlog: 1.896 kandidat-forslag → GET /central/candidates
```

### Felterne, og hvorfor netop de

Hver post har seks felter. De fem første er præcis dem Claudes egne
task-notifikationer bærer — den form er bevist i drift:

1. **Stabilt id** (`wake-6e201`, `job-bglj7`). Adresserbart af `done`/`drop`.
2. **Status**, typet. `kører / færdig / fejlet / forældreløs`. Aldrig prosa.
3. **Opretterens EGEN beskrivelse** — ikke kommandolinjen. Med fem kørende jobs
   er beskrivelsen den eneste måde at se hvilket der blev færdigt. Claudes
   notifikation bærer `summary` med netop launcher-beskrivelsen; uden den skulle
   man åbne filen for at vide hvad der skete.
4. **Udfald** — exit-kode, fejltælling. `exit 1` er et andet signal end `exit 0`
   og skal stå uden at man åbner noget.
5. **Henvisning og størrelse, når der findes et artefakt.** Størrelsen hjælper
   læseren med at vælge mellem `tail -5` og hele filen. Uden fil bruges et
   typet kilde-id; skemaet må ikke kræve en ikke-eksisterende outputfil.
6. **Verificeret ejer** (`[dig]` / `[huset]` / `[ukendt]`) og bruger-id. Afgør
   om posten må gate. `[ukendt]` er aldrig blokerende.

### Hvorfor «PÅ VEJ» og «PLANLAGTE» er adskilt

`self_wakeup` og `scheduled_tasks` er begge ENGANGS. Kun `recurring_tasks`
gentager sig og har `interval_minutes`/`next_fire_at`. Michelles morgenbrief
er ÉN aktiv recurring-post, ikke en ny `scheduled_tasks`-række hver dag.

Det er samme fejl som dubletterne, blot i fremtiden: uden adskillelsen vil
indbakken overdrive hvor meget der venter, og så bliver den noget man lukker i
stedet for at læse.

### Sektionen «VAKTE DENNE TUR»

Bjørn bad om «hvad har vækket ham», og det er **ikke** det samme som at liste
fyrede vækninger. Når en vækning starter en tur, skal turen vide HVILKEN —
ellers står Jarvis med en opgave uden at vide hvorfor han er i gang. Den
sektion er tom i en tur han selv startede, og har præcis én linje i en tur en
vækning udløste.

Turens `wakeup_id` skal komme fra dispatcherens registrerede årsag, ikke
gættes fra den seneste fyrede vækning. Først når booking, affyring og
kvittering er parret per id, kan man sige om der er et bogføringshul.

### Og to felter der ikke findes i dag

**Alder og forfald som et TAL.** Ikke «findes», men «3d forfalden». Skygge-
registret fejlede præcis dér: otte eksperimenter, `event_trigger` 78 dage over
sin 24-timers frist. Registret VIDSTE det hele tiden — ingen visning gjorde det
til et tal nogen så.

**Dublet-tælling.** Den må ikke erstatte identiteten af tre reelle vækninger:
hver har sit id og kan fyre eller annulleres selvstændigt. Vis gerne en gruppe
med `booket 3 gange`, men bevar alle tre id'er og deres egne afgørelser.
Lighed på `(type, beskrivelse)` er kun et forslag om dublet, ikke bevis.

---

## Skrive-kontrakten

**Kun det Jarvis selv har startet må gate.**

| Kilde | Må oprette | Må gate |
|---|---|---|
| `schedule_self_wakeup` (hans eget kald) | ja | **ja** |
| Baggrundsjob han selv startede | ja | **ja** |
| Agent han selv spawnede | ja | **ja** |
| `recurring_tasks`, heartbeat, daemoner | ja | nej |
| `candidate_review_digest`, proposals | nej (kun tællingen) | nej |
| Godkendelser (venter på Bjørn) | ja, egen klasse | nej |

Tre betingelser SKAL alle holde for at en post gater:

1. **Ejeren er verificeret som Jarvis** ved kildens oprettelsespunkt, med
   autentificeret bruger og tool-/run-id — ikke ved et af kalderen valgt flag.
2. **Kilden kan navngives i visningen.** Kan den ikke, må den ikke gate. En
   blokering uden en adresse er en blokering man ikke kan rette.
3. **Posten er stadig åben for samme bruger.** Levering, læsning, en anden
   brugers kvittering eller en genstart må ikke ændre dette implicit.

Princippet i én sætning: **det du selv har lovet kommer tilbage til dig; huset
kan informere, men ikke kræve.** Det er svaret på «han har ingen kontrol» — gaten
er hans egne forpligtelser, ikke husets krav.

Og det er grunden til at et **dagligt gate-loft** ikke blev valgt: rammes et
loft på hvor mange poster der må gate af støj, er den vigtige post den der
falder udenfor. Ejerskab er den bedre akse — huset kan informere, men ikke kræve.

> **PRÆCISERET 3/10 (Opus):** denne sætning sagde bare «loftet», og Opgave 10
> indfører et loft. To forskellige mekanismer med samme ord, og modsatte domme i
> samme dokument. De er adskilte nu:
>
> | Ord | Hvad | Dom |
> |---|---|---|
> | **gate-loft** | hvor mange poster der må blokere mutationer per døgn | **afvist** — støj ville skubbe den vigtige post udenfor |
> | **visnings-loft** | hvor mange linjer en sektion viser, med «+N mere» | **valgt**, se Opgave 10 |
>
> De kan begge være rigtige, fordi de fejler i hver sin retning: et gate-loft
> kan skjule en blokering man SKAL se, mens et visnings-loft kun skjuler linjer
> — og kun hvis det siger hvor mange. Derfor kræver Opgave 10 trin 5 at den
> blokerende sektion aldrig afkortes tavst.

---

## Koblingen til R2.5

Inboxen får en **egen forudsætning i samme mutationspunkt** som R2.5, ikke
en ekstra gren i R2.5's eksisterende blok. `r2_5_blocking_gate` vurderer
uverificerede mutationer; `r2_5_haandhaevelse` holder én procesglobal `_blok`,
som frigives ved første readback eller efter 10 minutter. Begge dele er
forkert livscyklus for åbne inbox-poster og usikkert på tværs af brugere/
workers. Del kun værktøjets mutationsklassifikation og den eksisterende
undtagelse for Bjørns `bash_session*`/`operator_bash_session*`.

Bjørns formulering 3/10 var **to-trins**: «først bede ham checke indbox, og hvis
ignoreret eskalerer som den gør nu». Første udkast af denne spec kollapsede det
til øjeblikkelig blokering — det var min vurdering sat i stedet for hans form,
og uden at sige det. To-trins er bedre: den høflige anmodning koster ingenting,
og blokeringen fanger dem der ignorerer den. Det er præcis måden R2 og R2.5
allerede forholder sig til hinanden.

```text
TRIN 1 — inbox-påmindelse (advisory)
  ny åben, verificeret Jarvis-post for denne bruger?
       ja → én KILDE-MÆRKET systemlinje: «N venter i indbakken → inbox»
            Mutationen slipper igennem. Gem påmindelses-id/tid per post.
  stadig åben ved en senere kvalificeret brugertur/mutation?
       ja → højst én ny påmindelse pr. post pr. afgrænset interval.
            Tæl kun når påmindelsen faktisk blev leveret til modellen.

TRIN 2 — inbox-mutationsvagt (efter N leverede, ubesvarede påmindelser)
  åben post for denne bruger med nok påmindelser?
       nej → slip igennem
       ja → nægt denne mutation med kilde-mærket tool-resultat;
             angiv id, kort beskrivelse og inbox som næste læsning.
  → frigives kun af en gyldig, durabel done/drop-afgørelse per post
```

`_INDBAKKE_PAAMINDELSER_FOER_BLOK` kan begynde på **2** som målebar
`settings`-værdi, men R2's 15 % er ikke en måling af inboxens heed-rate.
Påmindelsesinterval, maksimal frekvens og alder før eskalation skal også
konfigureres og måles. Hvis en ny post kun får én påmindelse, kan tærsklen
2 aldrig nås; derfor er den senere, begrænsede påmindelse ovenfor nødvendig.

Trin 1 må ikke fyre i hver runde. Både første og eventuel anden påmindelse
skal være idempotente og have et målt interval; ellers får vi den samme støj
som R2. En tæller alene uden leverings-id kan hverken bevise to påmindelser
eller fungere på tværs af processer.

Tre regler i koblingen:

- **Læse-værktøjer slipper altid igennem.** Som i dag for uverificerede
  mutationer: han skal kunne komme fri.
- **Bjørns shell-bagdøre følger den eksisterende R2.5-undtagelse.** En
  inbox-post må ikke utilsigtet fjerne den aftalte bypass.
- **Bjørn skrev «fjerne tool til læst». Jeg har læst det som NÆGT, ikke FJERN**,
  og grunden er målt: fjernes et værktøj fra sættet, ændres prompt-prefixet, og
  et skiftende sæt kostede 92 % → 26 % cache-hit. R2.5 nægter i forvejen uden at
  fjerne noget — samme virkning for Jarvis, nul cache-pris. Er fortolkningen
  forkert, er det denne linje der skal rettes.
- **Frigivelse kræver en afgørelse per post, ikke blot et blik.** `inbox` alene
  frigiver ikke; hver handlingskrævende post skal lukkes med `done` eller `drop`.
  Ellers bliver læsningen en formalitet, og vi er tilbage i banner blindness —
  bare med en blokering i stedet for en advarsel, hvilket er værre.
- **Fail-open er synlig og tidsafgrænset.** Ved DB-fejl må en mutation ikke
  blokeres på et gæt; fejlen logges med bruger-/post-id. En post uden mulig
  gyldig afgørelse skal kunne eskaleres til Bjørn og have en dokumenteret
  nødvej, så et permanent defekt source-id ikke låser Jarvis.
- **Heed-raten på DEN forudsætning måles separat.** R2's 15 % er grunden: hvis
  «læs indbakken» begynder at fyre 47 gange om dagen, har vi bygget den tredje
  mekanisme der skal reddes af den fjerde.

---

## Værktøjerne — færre, ikke flere

Han har otte listnings/bogførings-værktøjer i dag, hver med sin egen outputform.
Indbakken skal **reducere** det, ikke lægge et niende ovenpå.

**`inbox`** — hele visningen. Erstatter i praksis `list_self_wakeups`,
`list_agents` og `bash_session_list` som *det han kalder*.

**`inbox_done(id)`** — kvitter en *allerede udført* opgave. For en fyret
vækning kan den kalde `mark_wakeup_consumed`; for et job/agent skal den
kontrollere terminalt udfald og derefter gemme en idempotent kvittering.
Den må ikke markere en endnu ikke fyret vækning som brugt.

**`inbox_drop(id, reason)`** — afvis/dismiss en åben inbox-post med begrundelse.
Den stopper **ikke** automatisk et kørende job eller en agent. Annullering er
en selvstændig, kilde-specifik mutation med egne tilladelser; en planlagt
vækning kan kun annulleres i dens tilladte `pending`-tilstand.

De specialiserede værktøjer **bliver**: `schedule_self_wakeup`,
`interrupt_agent`, `send_message_to_agent`, `spawn_agent_task`. Det er dér
arbejdet gøres. Indbakken erstatter kun listningen og bogføringen — additivt, og
kan ikke brække noget.

De gamle `list_*`-værktøjer fjernes IKKE i denne spec. De er billige, de virker
(`list_self_wakeups`: 59 kald, 0 fejl), og at fjerne et værktøj rører fem steder
— server-definition, dispatch, eksport-liste, desk og mobil. Målt 2/10: jeg ramte
tre af de fem i første forsøg. En oprydning hører i sit eget spor.

---

## Hvad der ER med, og hvad der ikke er

> **MANGLER (Jarvis 3/10):** tabellen navngiver fravalg *med* vagt —
> kanalbeskeder har en AST-vagt i Opgave 2 trin 9. Men det mest almindelige ægte
> tilfælde, et løfte givet i prosa («jeg tjekker det i morgen»), har hverken
> indgang eller navngivet fravalg. Efter spec'ens egen standard skal det stå som
> fravalg. Se §6 i «Seks mangler».

| Aspekt | Afgørelse | Begrundelse |
|---|---|---|
| Vækninger | **ind**, egen sektion | Den levende arbejdsgang, 141+171 kald |
| Baggrundsjobs | **ind** | Han lister dem aldrig; derfor forsvinder svar |
| Agenter | **ind**, men lavt rangeret | Næsten døde: spawn sidst 5/9, scout 73 % fejl |
| Planlagte engangsopgaver (`scheduled_tasks`) | **ind** under «PÅ VEJ» | De fyrer én gang og må ikke tælles som recurring |
| Gentagende opgaver (`recurring_tasks`) | **ind** under «PLANLAGTE» | `interval_minutes` og `next_fire_at` beskriver gentagelsen |
| Godkendelser | **ind** som «venter på Bjørn», gater ikke | Han skal kunne SE at en tråd venter på dig, uden at din svartid bliver hans blokering |
| Kandidat-backlog | **ude**, kun ét tal med en adresse | 1.896 poster, 99 % gentagelser, ville drukne den dag ét |
| Kanalbeskeder (Discord/Telegram/mobil) | **ude**, med en vagt | Det er samtale, ikke opgaver. En udelukkelse uden vagt glider — se Opgave 2, trin 9 |
| Forældreløse poster | **ind** som typet status | Et job hvis proces er væk skal ikke stå som «i gang» i tre dage |
| Flere brugere | nøglet per bruger; kun verificerede Bjørn-poster gater i denne fase | `list_wakeups` og agent-registret er ikke i sig selv brugerfiltrerede; ukendt ejer må ikke lækkes eller gate |

---

## Opgaver

Opgave 8–13 (tilføjet 3/10) bygger på Opgave 1–2 (postens lager og visningen) og
Opgave 4 (tælleren). De tilføjer livscyklus og oprydning — ikke nye kilder.

Opgave 14 er **sidst og obligatorisk**: e2e-verifikation på CT105, usmocket.
Den afhænger af alle de andre og kan ikke køres i forvejen — og uden den er
«bygget» kun en påstand. En grøn suite beviser at enhederne virker, ikke at
de er forbundet.

### Opgave 0: Mål prompten FØR vi bygger

**Filer:** ny `scripts/maal_ventende_i_prompten.py`; ingen test (måleværktøj).

Denne opgave er FØRST, og resten afhænger af dens svar. Den må ikke springes.

- [ ] **Trin 1:** Byg en ægte synlig prompt på CT105 med
      `build_visible_chat_prompt_assembly(...)` — samme vej som
      `verify_visual_before_done` kræver, ikke en rekonstruktion.
- [ ] **Trin 2:** Klassificér hver sektion som `ventende-tilstand` eller
      `andet`. Ventende-tilstand = vækninger, åbne opgaver, igangværende jobs,
      hvad der vakte ham, agent-status. Rapportér tokens og andel, både for de
      FASTE sektioner og for den dynamiske hale — Bjørn pegede på begge.
- [ ] **Trin 3:** Mål hvor ofte de sektioner ÆNDRER sig mellem to ture.
      Skeln mellem stabilt prefix og dynamisk hale: en uændret sektion i
      cachebart prefix kan få cache-hit; en ændret hale kan stadig påvirke
      pris/latens. Rapportér faktisk hit-rate og tokens, ikke kun tekstlængde.
- [ ] **Trin 4: LÅS tallet i denne spec** med dato, som R2's baseline blev låst
      13/6. Et tal uden en dato er en påstand.
- [ ] **Trin 5:** Brug målingen til at prioritere prompt-reduktion separat
      fra kontrolfladen. En grænse på 8 % af halen kan ikke udledes af at
      historikken bruger 3,1 % af et 1M-vindue; nævner og cacheadfærd er
      forskellige. Opgave 2's *mindste læsevisning* er en forudsætning for
      `inbox_done`/`inbox_drop` og må ikke udskydes mens en gate bygges.
- [x] **Trin 6: Commit** måleværktøjet og det låste tal.

> **MÅLT OG LÅST 3/10-2026 kl. 19:01-19:07 UTC (Opus).** Værktøjet er
> `scripts/maal_ventende_i_prompten.py`, kørt på CT105 med husets egen
> interpreter mod hans levende samtale `chat-cec7edd712e24998a3e08bd1e61beb51`
> (2.687 beskeder), deepseek-flash, tre bygninger med tur-cachen ryddet imellem.
>
> | Del | Tokens | Ventende tilstand | Andel |
> |---|---|---|---|
> | Stabilt prefix (før `DYNAMIC_TAIL_SENTINEL`) | 15.068 | 0 | **0,0 %** |
> | Dynamisk hale | 9.039 | 0 | **0,0 %** |
> | System i alt | 23.936 | 0 | **0,0 %** |
>
> Ændring over tre bygninger: 9 af 107 dele skiftede, **ingen** af dem ventende.
>
> **Tallet er nul, og det er ikke en målefejl — det er svaret.** Jeg efterprøvede
> det direkte frem for at tro på et aggregat:
>
> * Systemet havde præcis ÉN ventende vækning: `wake-cf0577f5bb`, «Slet
>   prevacuum-backuppen». Hverken dens id eller dens tekst står i prompten.
> * Ordet «WAKE» optræder **0 gange**. Ordet «wakeup» optræder 9 gange — og alle
>   ni er **værktøjsbeskrivelser** (`schedule_self_wakeup`, `list_self_wakeups`,
>   `cancel_self_wakeup`, `operator_wakeup`). Ikke én er en ventende post.
> * De to baggrundsjobs i registret står `exited` siden 18/7 og 28/5. Syv
>   side-opgaver er alle terminale.
>
> Prompten fortæller ham altså at han HAR et værktøj til at liste vækninger. Den
> fortæller ham aldrig at han har en der venter.
>
> **Det vender spec'ens egen præmis om.** Afsnittet «Hvorfor prompten bliver
> mindre» hviler på at ventende tilstand ligger spredt i prompten og kan samles.
> Den ligger ikke i prompten. Indbakken vil derfor **lægge til**, ikke trække fra
> — og Trin 5's «brug målingen til at prioritere prompt-reduktion» har intet at
> prioritere.
>
> Men indbakkens værdi bliver større, ikke mindre: den er ikke en optimering,
> den er den **manglende læseflade**. Jarvis har en forpligtelse han selv har
> booket, og han kan ikke se den. Det er `seks_kognitive_systemer_uden_skriver`
> spejlvendt — en kø ingen læser.
>
> **Konsekvenser for de øvrige opgaver:**
> 1. Budgettet for indbakke-sektionen skal sættes som en TILFØJELSE til halen
>    (9.039 tokens i dag), ikke som en besparelse. Opgave 10's visnings-loft er
>    derfor ikke kosmetik — det er den eneste pris-kontrol der findes.
> 2. Opgave 14 trin 4 («blev halen mindre, eller kom indbakken oveni?») har sit
>    svar på forhånd: den kommer oveni. Leddet skal måle HVOR MEGET.
> 3. Den første målte fejl var min egen: første kørsel 18:57 sagde også 0,0 %,
>    men af en helt anden og forkert grund — segmenteringen matchede kun
>    `[SECTION]`-overskrifter og fandt 9 dele i en prompt runtimen delte i 60, så
>    51 dele faldt i en kategori der ikke kunne klassificeres. To nuller med
>    samme tal og modsat gyldighed. Derfor rapporterer værktøjet nu altid de
>    største UKLASSIFICEREDE dele: et nul skal kunne efterprøves.

### Opgave 1: Handlings-klassen i køen

> **MANGLER (Jarvis 3/10):** postens livscyklus har kun to udgange — `done` og
> `drop`, begge mine. Ingen udløbs-tilstand, ingen retention, og
> `kraever_handling` udledes af proveniens uden en indholdsregel der lukker en
> post der ikke længere kræver noget. Se §1, §2 og §4 i «Seks mangler».

**Filer:** ny `core/services/inbox_state.py`, `core/runtime/db_inbox.py` og migration for
`inbox_items`; test `tests/test_inbox_state.py`. `session_inbox.enqueue`
ændres ikke til en opgave-registrator.

**Interfaces — producerer:** `registrer_kilde(bruger_id, kildetype, kilde_id,
oprettende_run_id, ...)->dict`. Verificeret ejer bestemmes ved integrationens
oprettelsespunkt. Unik `(bruger_id, kildetype, kilde_id)` gør genlevering
idempotent; en genstart må ikke nulstille påmindelser eller afgørelse.

> **VERIFICERET 3/10 (Jarvis):** den oprindelige udgave kaldte kilderne
> «elleve» og byggede på `session_inbox` som opgavetilstand. Ingen af
> delene holdt: basen har **5** distinkte kilder (`jarvis-notify`,
> `candidate-review-digest`, `notification-router`, `test-daemon-2`,
> `test-daemon`), og `enqueue` kaldes fra ét sted
> (`notification_bridge.py:216`). Vigtigere: `flush_session` sætter
> `status='delivered'`, hvorefter `pending_for_session` ikke længere
> viser posten — derfor den separate, idempotente `inbox_items`-
> kvittering. Princippet fra den fejl står ved magt: en kolonne der
> skrives uden at blive læst er `built_but_not_connected` i miniature —
> læseren skal med i samme ændring.

- [ ] **Trin 1: Skriv den fejlende test**

```python
def test_huset_kan_ikke_spoofe_jarvis_ejerskab(inbox_db):
    """Et kalder-valgt ejerflag er ikke proveniens."""
    r = registrer_kilde(bruger_id="bjorn", kildetype="daemon",
                       kilde_id="morgenbrief-1", oprettende_run_id="",
                       paastaaet_ejer="jarvis")
    assert r["status"] == "ok"
    assert r["post"]["kraever_handling"] is False
```

- [ ] **Trin 2: Kør den og se den fejle**

`pytest tests/test_inbox_state.py::test_huset_kan_ikke_spoofe_jarvis_ejerskab -v`
Forventet: FAIL fordi `inbox_state` endnu ikke findes.

- [ ] **Trin 3: Minimal implementering**

Idempotent migration for `inbox_items` med bruger, kilde-id, oprettende run,
verificeret ejer, åben/afgjort status, sidste leverede påmindelse og
kvitteringstid. Indhold/artefakt bliver hos kilden. Håndhæv at en uprøvet
ejerpåstand ikke kan blive handlingskrævende:

```python
# Skrive-kontrakten håndhæves ved den betroede kildeintegration. Ukendt
# oprettende run eller bruger => synlig post, men aldrig mutationsblok.
if not verificeret_jarvis_run(oprettende_run_id, bruger_id):
    kraever_handling = False
```

- [ ] **Trin 4: Kør igen** — PASS. Test også idempotent genregistrering,
      genstart, anden bruger og at en allerede leveret notifikation stadig er
      åben, indtil den afgøres.
- [ ] **Trin 5: Commit** gennem wrapperen, `--message-file`.

### Opgave 2: Visningen

> **MANGLER (Jarvis 3/10):** seks sektioner, én linje per post — og intet loft
> og ingen rangorden. `forfald_dage` er et tal der *vises*, ikke en tærskel der
> *gør* noget. Argumentet der udelukkede kandidat-backloggen («1.896 poster
> ville drukne den dag ét») gælder også inde i sektionerne. Se §3 i «Seks
> mangler».

**Filer:** ny `core/services/inbox_view.py`; test `tests/test_inbox_view.py`.

**Interfaces — konsumerer** (kontrolleret mod koden 3/10; ingen af de
muterende hjælpefunktioner kaldes af visningen):

| Kilde | Funktion |
|---|---|
| Åbne afgørelser | `inbox_items` scoped på eksplicit `bruger_id`; `session_inbox.pending_for_session` er kun leveringskø |
| Vækninger | `self_wakeup.list_wakeups()` + eksplicit brugerfilter; `due_wakeups()` fyrer/gemmer og er ikke læsning |
| Baggrundsjobs | brugerafgrænsede snapshots per jobtype; `background_jobs.liste()` starter ikke daemonen, men nulstiller dens idle-ur, og blander husets services med Jarvis-jobs |
| Agenter | `agent_registry`/`agent_runs` kræver verificeret brugerproveniens; nuværende `list_agent_registry_entries()` filtrerer ikke bruger |
| Planlagte engangsopgaver | `scheduled_tasks` med eksplicit brugerfilter; `list_pending_for_current_user()` læser alle ved tom kontekst |
| Gentagende opgaver | `recurring_tasks` med eksplicit brugerfilter; `list_recurring_tasks()` bruger implicit kontekst |
| Godkendelser | `db_governance.recent_tool_intent_approval_requests(user_id=..., include_unassigned=False)`; `build_tool_intent_approval_surface()` kan skrive/udløbe |

`self_wakeup.mark_wakeup_consumed(wakeup_id)` findes, men kun som mutation
efter at en fyret vækning er håndteret. Eksisterende læsefunktioner med
implicit bruger-kontekst må omsluttes af eksplicit scoped adapter eller
afvises ved ukendt ejer, før multi-bruger-visningen kaldes ren.
**Producerer:** `byg_indbakke(bruger_id: str, *, nu_ts: float | None = None) ->
dict` med nøglerne `vakte`, `venter_paa_dig`, `i_gang`, `paa_vej`,
`planlagte`, `venter_paa_bjorn`, `backlog_tal`, og per post de seks felter
fra afsnittet ovenfor. Uden autentificeret bruger-id returneres en typet
fejl, aldrig en liste over alle brugere.
`nu_ts` injiceres, så testene er deterministiske — samme mønster som
`shadow_experiment_registry`.

- [ ] **Trin 1: Testen for forfald som et tal**

```python
def test_en_forfalden_post_baerer_sit_forfald_som_et_TAL():
    """Skygge-registret vidste at event_trigger var 78 dage over sin frist.
    Ingen visning gjorde det til et tal nogen så. Det er fejlen her."""
    v = byg_indbakke("bjorn", nu_ts=TID, kilder=_fake(wake_fyret=TID - 3*86400))
    post = v["venter_paa_dig"][0]
    assert post["forfalden_dage"] == 3
    assert "3d forfalden" in post["linje"]
```

- [ ] **Trin 2: Kør, se den fejle** (`ImportError`).
- [ ] **Trin 3: Implementér** `byg_indbakke` med de SEKS sektioner — `vakte`,
      `venter_paa_dig`, `i_gang`, `paa_vej`, `planlagte`, `venter_paa_bjorn` —
      plus `backlog_tal`, alder/forfald og dublet-tælling på (type, beskrivelse).

      *Første udkast skrev «de fire sektioner». Det var forkert allerede da, og
      blev mere forkert da «VAKTE DENNE TUR» kom til i rettelsesrunden — en
      modsigelse jeg selv indførte mens jeg lukkede huller. Tallet står nu med
      navnene, så det ikke kan drive igen.*
- [ ] **Trin 4: Testen for dubletter**

```python
def test_tre_identiske_vaekninger_vises_som_EN_med_et_tal():
    """Grupper kun præsentationen; bevar alle tre vækningers id'er."""
    v = byg_indbakke("bjorn", nu_ts=TID, kilder=_fake(wake_gentaget=3))
    assert len(v["paa_vej"]) == 1
    assert v["paa_vej"][0]["dubletter"] == 3
    assert len(v["paa_vej"][0]["kilde_ider"]) == 3
    assert "booket 3 gange" in v["paa_vej"][0]["linje"]
```

- [ ] **Trin 5: Testen for forældreløse poster**

```python
def test_et_job_hvis_proces_er_vaek_staar_som_FORAELDRELOEST():
    """Uden dette står et dødt job som «kører» i dagevis. Det er samme fejl som
    det stale `connected=True` i discord-gatewayen: en tilstand ingen opdaterer
    fordi den der skulle, selv døde."""
    v = byg_indbakke("bjorn", nu_ts=TID, kilder=_fake(
        job_status="kører", job_pid_lever=False, job_sidst_set=TID - 2*86400))
    post = v["venter_paa_dig"][0]
    assert post["status"] == "foraeldreloes"
    assert post["id"] not in [x["id"] for x in v["i_gang"]], (
        "et dødt job stod stadig under «I GANG»"
    )
```

      Forældreløs kræver pålideligt procesbevis fra den samme host. Et job på
      en utilgængelig operator-maskine er `status_ukendt`, ikke bevist dødt.
      Først når status siger `kører`, processen beviseligt er væk og posten er
      ældre end `_FORAELDRELOES_EFTER_S`, havner den i `venter_paa_dig`.
      Tærsklen er en settings-værdi og måles i Opgave 7.

- [ ] **Trin 6: Testen for bruger-isolation**

```python
def test_en_anden_brugers_poster_siver_ALDRIG_ind():
    """Husstanden har flere brugere, og de andres workspaces er krypterede.
    En indbakke der blander dem er et databrud, ikke en fejl i visningen."""
    v = byg_indbakke("bjorn", nu_ts=TID, kilder=_fake(
        poster=[("bjorn", "wake-mine"), ("anden", "wake-andens")]))
    alle = [x["id"] for sek in v.values() if isinstance(sek, list) for x in sek]
    assert alle == ["wake-mine"], f"en anden brugers post kom med: {alle}"
```

      Denne injicerede liste er kun første test. Kør også adapter-tests mod
      faktiske kilder: `list_wakeups()` er global; agent-registret mangler
      brugerfelt; `scheduled_tasks` kan liste alle uden kontekst. En adapter
      uden sikker ejerbinding må udelade posten og rapportere `ukendt`, ikke
      vælge Bjørn som stiltiende fallback.

- [ ] **Trin 7: Testen for at visningen IKKE kan skrive** (kilde-vagt, AST):
      `byg_indbakke` og dens hjælpere må ikke kalde `enqueue`,
      `append_chat_message`, `set_runtime_state_value`, `schedule_*`,
      `due_wakeups`, `build_tool_intent_approval_surface` eller joblister der
      starter en daemon. Test både direkte og indirekte kildeadaptere.
      Begrundelse i testen: `a_read_surface_can_create_what_it_reads`.
- [ ] **Trin 8: Testen for at posten bærer en HENVISNING og aldrig payload**

> **TILFØJET 3/10 (Opus):** Opgave 2 sprang fra trin 7 til trin 9 — der var
> intet trin 8. Hullet var ikke kun nummerering: «indbakken afleverer
> henvisninger, aldrig payload» står tre steder i spec'en (Global Constraints,
> filstrukturen, visningens overskrift) og havde **ingen vagt**. Spec'ens egen
> standard gælder for den selv: *en udelukkelse uden vagt glider.*

```python
def test_posten_baerer_en_henvisning_og_aldrig_payload(inbox_db):
    """Et jobs output kan være 112 kB. Lander det i visningen, lander det i
    promptens hale — og så er kontrolfladen blevet den byrde den skulle lette.
    Testen pinner BEGGE retninger: med fil og uden."""
    post(kilde="job", output_sti="tasks/bglj7.output", output_bytes=114_688)
    post(kilde="wake", kilde_id="wake-6e201")

    linje = byg_indbakke(bruger="bjorn")["venter_paa_dig"]
    # Henvisning OG størrelse — størrelsen er det der gør valget mellem
    # `tail -5` og hele filen muligt uden at åbne noget.
    assert "tasks/bglj7.output" in linje[0] and "112 kB" in linje[0]
    # Og intet af indholdet.
    assert "Traceback" not in linje[0]
    assert len(linje[0]) < 200, "en linje per post — ikke et uddrag"
    # Uden fil: typet kilde-id, ingen opdigtet sti. Skemaet må ikke KRÆVE
    # en outputfil der ikke findes.
    assert "wake-6e201" in linje[1]
    assert ".output" not in linje[1] and "None" not in linje[1]
```

      Kanterne der skal med som egne cases:
      - fil der **er forsvundet** siden posten blev skrevet → henvisningen vises, størrelsen mangler, og det siges — ikke `0 B`, som ikke kan skelnes fra en tom fil
      - fil på **0 bytes** → `0 B`, og det er et ægte svar
      - sti **uden for** brugerens autoriserede workspace → posten vises, stien gør ikke (Global Constraints)
      - meget lang beskrivelse → afkortes i linjen, aldrig i den gemte post

- [ ] **Trin 9: Vagten mod at kanalbeskeder siver ind**

```python
def test_kanalbeskeder_hoerer_ikke_i_indbakken():
    """En udelukkelse uden en vagt glider. Discord/Telegram/mobil er SAMTALE,
    ikke opgaver; kom de ind, ville indbakken blive en anden indbakke."""
    import ast, pathlib
    kilde = pathlib.Path("core/services/inbox_view.py").read_text()
    tekst = ast.unparse(ast.parse(kilde))
    for forbudt in ("discord", "telegram", "chat_messages"):
        assert forbudt not in tekst.lower(), (
            f"inbox_view læser {forbudt} — kanalbeskeder er samtale, ikke opgaver"
        )
```

- [ ] **Trin 10: Kør alle, PASS. Commit.**

### Opgave 3: Bogføringen

**Filer:** ny `core/services/inbox_state.py`; test `tests/test_inbox_state.py`.

**Interfaces — konsumerer:** durabel `inbox_items`-post og kun ved
passende status `self_wakeup.mark_wakeup_consumed(wakeup_id)`. Job-/agentstop
er en særskilt handling og må ikke skjules bag `drop`.

**Interfaces — producerer:** `done(bruger_id: str, post_id: str) -> dict`,
`drop(bruger_id: str, post_id: str, reason: str) -> dict`. Begge returnerer
`{"status": "ok"|"ukendt"|"fejl", "type": ..., "id": ...}` — typet, aldrig prosa.

- [ ] **Trin 1: Test at `done` på en vækning rammer den rigtige mekanisme**

> **RETTET 3/10 (Jarvis):** `kaldt == ["6e201"]` kodificerede en fejl.
> `mark_wakeup_consumed(wakeup_id)` slår op på `record["wakeup_id"] ==
> wakeup_id`, og de faktiske id'er er `wake-` + **10** hex
> (`wake-49b89a51de`) — ikke 5. Stripper `done` præfikset, fejler opslaget og
> returnerer `{"status": "error", "error": "wakeup not found"}`. Præfikset
> vælger mekanisme; det klippes ikke af.

```python
def test_done_paa_en_vaekning_markerer_den_brugt():
    kaldt = []
    with patch("core.services.self_wakeup.mark_wakeup_consumed",
               side_effect=lambda wid: kaldt.append(wid) or {"status": "ok"}):
        r = done("bjorn", "wake-49b89a51de")
    assert r == {"status": "ok", "type": "wakeup", "id": "wake-49b89a51de"}
    assert kaldt == ["wake-49b89a51de"], (
        "praefikset blev klippet af — opslaget i self_wakeup fejler"
    )
```

- [ ] **Trin 2: Kør, se den fejle.**
- [ ] **Trin 3: Implementér** ved opslag af den konkrete post for
      `bruger_id`; vælg kildehandler fra postens typede `kildetype`, ikke
      alene fra et brugerleveret id-præfiks. `wake-` er del af det rigtige
      wakeup-id og må ikke strippes. Kræv passende kildestatus, udfør
      kildeændring og durabel afgørelse idempotent med defineret rækkefølge
      og recovery ved fejl imellem dem.
- [ ] **Trin 4: Test at et ukendt id ikke melder succes.** Det er husets
      hyppigste fejlform: `swallowed_error_becomes_a_value`.
- [ ] **Trin 5: Test races og isolation:** gentaget `done` giver samme
      afgørelse, en anden brugers id afvises, `drop` stopper ikke et job,
      og en `pending` vækning kan ikke kvitteres som allerede udført.
- [ ] **Trin 6: Kør, PASS. Commit.**

### Opgave 4: R2.5-forudsætningen

> **MANGLER (Jarvis 3/10):** tælleren skal læse **den samme liste prompten blev
> bygget fra**. Skill-gaten så ikke sine egne kald 3/10, fordi den læste
> `_a_tool_calls` — der bærer transport-navnet `call_loaded_tool` — mens
> udpakningen til det ægte navn sker i `core/tools/kaldt_vaerktoej.pak_ud`,
> kaldt fra `_prepare_call`, altså efter listen er fyldt. Det er dagens egen
> fejlklasse. Se §5 i «Seks mangler».
>
> **RETTET 3/10 (Opus):** denne note sagde først at udpakningen stod i
> `simple_tool_executor.py`. Den fil *kalder* kun `pak_ud`; den ene definition
> er `core/tools/kaldt_vaerktoej.py:76`. Samme fejlklasse som de fem Jarvis
> rettede: et sted der lød rigtigt frem for det sted koden står.

**Filer:** ny `core/services/inbox_gate.py`, integration i
`core/services/simple_tool_executor.py` ved siden af R2.5; test
`tests/test_inbox_gate.py`. Eksisterende R2.5's procesglobale blok ændres
ikke til at repræsentere inbox-poster.

**Interfaces — konsumerer:** scoped `inbox_items`-poster med verificeret
ejer, åben status og durabel leveret-påmindelsesstatus. Antal alene er ikke
nok: nægtelsen skal kunne navngive de konkrete id'er.

- [ ] **Trin 1: Test at en handlingskrævende post nægter en mutation**

> **RETTET 3/10 (Jarvis):** funktionsnavnet og returformen var forkerte. Den
> faktiske funktion er `should_block_for_verification(*, reasoning_tier: str)`
> → `dict | None` med nøglerne `{reason, suggestions, urgency}` — der findes
> ingen `evaluer_mutation`, ingen `blokeret`-nøgle og ingen `aarsag`. Og
> vigtigere: funktionen har **fire** tidlige `return None` (cooldown <60 s,
> gate-fejl, under tærskel, heed_rate utilstrækkelig). En test der vil se en
> blokering skal styre alle fire, ellers måler den ingenting.

```python
def test_to_leverede_paamindelser_foer_mutation_naegtes(inbox_db):
    # VERIFICERET 3/10 (Jarvis): den oprindelige test kaldte
    # `evaluer_mutation` og forventede v["blokeret"] — den funktion
    # findes ikke. R2.5's faktiske should_block_for_verification(*,
    # reasoning_tier) har FIRE tidlige return None (cooldown <60 s,
    # gate-fejl, under taerskel, heed_rate), saa en test gennem den vej
    # maa styre alle fire. Codex' redesign giver i stedet inboxen sin
    # EGEN forudsaetning i samme mutationspunkt — evaluer_inbox_mutation
    # — og dér maales inbox-leddet alene. Fixture-id'et er rettet til
    # runtime-formatet (wake- + 10 hex).
    post = _egen_aaben_post("bjorn", id="wake-49b89a51de")
    assert evaluer_inbox_mutation("bjorn", "edit_file")["blokeret"] is False
    _lever_paamindelse(post, tur="t1")
    assert evaluer_inbox_mutation("bjorn", "edit_file")["blokeret"] is False
    _lever_paamindelse(post, tur="t2")
    v = evaluer_inbox_mutation("bjorn", "edit_file")
    assert v["blokeret"] is True
    assert "wake-49b89a51de" in v["poster"]
```

- [ ] **Trin 2: Test at huset og en anden bruger IKKE kan nægte**, selv ved
      en fejlmærket post i basen. Dobbelt værn ved registrering og mutation.
- [ ] **Trin 3: Test at læse-værktøjer og aftalte shell-bagdøre slipper
      igennem** mens en post er åben.
- [ ] **Trin 4: Test at almindeligt R2.5-readback eller 10 minutters timeout
      ikke frigiver inbox-blokken**; kun `done`/`drop` på dens poster gør.
- [ ] **Trin 5: Implementér** scoped vurdering og kilde-mærket tool-resultat.
- [ ] **Trin 6: Mutations-tjek** — fjern forudsætningen, se Trin 1 fejle.
- [ ] **Trin 7: Kør `tests/test_inbox_gate.py` og eksisterende R2.5-tests.
      Commit.**

### Opgave 5: Værktøjerne

**Filer:** ændrer `core/tools/simple_tools_definitions.py` (tre skemaer),
`core/tools/simple_tools_native.py` (tre eksekutorer), `core/tools/simple_tools.py`
(dispatch + eksport-liste); test `tests/test_inbox_tools.py` (ny).

**Advarsel fra 2/10:** et værktøjsnavn bor **fem** steder — skema, dispatch,
eksport-liste (`__all__`), desk og mobil. En AST-sletning af et skema ramte den
INDRE dict og efterlod `{'type': 'function'}`; det er gyldig Python, så
`compileall` tav, og først `test_browser_tools` fangede det. Tilføjelse har samme
fem steder.

- [ ] **Trin 1: Test at alle tre er registreret** og svarer på et tomt kald med
      en typet fejl, ikke en undtagelse.
- [ ] **Trin 2: Kør, se den fejle.**
- [ ] **Trin 3: Tilføj** skema + eksekutor + dispatch + eksport-navn for hver.
- [ ] **Trin 3a: Følg Boy Scout-reglen** hvis ændringen rører logik i en
      eksisterende fil over 2.000 linjer: udskil nærmeste naturlige enhed
      med bagudkompatibel re-eksport før nye tool-grene lægges ind.
- [ ] **Trin 4: Kør `tests/test_desk_toolnavne.py`** — den fejler hvis desk
      nævner et navn der ikke findes. Her er det modsat: de nye navne behøver
      ikke desk-form, men guardens søster-test
      (`raekkeKroppe.test.tsx`) fanger et registreret værktøj UDEN form. Giv de
      tre en etiket i desk OG mobil i samme commit — `tool_text_two_copies`.
- [ ] **Trin 5: Kør hele suiten. Commit.**

### Opgave 6: Kilde-mærket levering med tilsluttet klient

**Filer:** ændrer `core/services/session_inbox.py` (`flush_session`); test
`tests/test_session_inbox.py`.

Dette er ændringen der gør notifikationer til data i den synlige samtale. I
dag skriver `flush_session` indholdet som en **assistant-besked**. At erstatte
den med `event_bus.publish()` alene leverer ikke noget til bruger eller model:
ingen dokumenteret abonnent viser den foreslåede `channel.inbox_leveret`.
`session_inbox` har desuden kun de notifikationer der blev køet i en aktiv
session; akut og direkte levering går udenom. Opgave 1-4 må derfor ikke
afhænge af denne flush for at registrere handlingskrævende poster.

**Rækkefølge:** Byg først API/event-stream og en kilde-mærket notifikations-
komponent i både desk og mobil, med replay fra en durabel status ved reconnect.
Test at bruger og model kan skelne `[SYSTEM NOTIFICATION - NOT USER INPUT]`
fra en brugermeddelelse. Skift først derefter `flush_session` fra assistant-
replik til reference. Før klienterne er udrullet, beholdes den eksisterende
leveringsvej eller en eksplicit kompatibilitetsvej; ingen post må forsvinde.

- [ ] **Trin 1: Test at flush IKKE skriver indholdet som assistant-besked**

```python
def test_flush_afleverer_en_henvisning_og_ikke_en_replik():
    """Smith mintede seks direktiver om sin EGEN replik, fordi hans note landede
    i promptens hale og blev læst som noget Jarvis havde sagt. En henvisning kan
    ikke lukke den løkke."""
    skrevet = []
    with patch("core.services.chat_sessions.append_chat_message",
               side_effect=lambda **kw: skrevet.append(kw) or {"id": "m1"}):
        flush_session("s1")
    assert skrevet == [], f"flush skrev indhold som replik: {skrevet}"
```

- [ ] **Trin 2: Kør, se den fejle** (flush skriver i dag).
- [ ] **Trin 3: Test klientforbrugeren før server-skiftet:** desk og mobil
      viser én systemmærket post ved live event og efter reconnect/replay;
      den indgår ikke som assistant- eller user-turn i modelhistorikken.
- [ ] **Trin 4: Implementér** en durabel notifikationsreference med id og
      source, synlig gennem eksisterende API/event-stream. Markér først
      `session_inbox`-rækken leveret når klientens replay-vej kan finde
      referencen. Eventbus-hændelsen er et signal, ikke eneste lager.
- [ ] **Trin 5: Test** antal/id, nul tab ved DB-/publish-fejl, ingen dobbelt
      visning ved replay, og både aktiv og inaktiv session. En kilde uden
      filartefakt må stadig kunne henvises ved id.
- [ ] **Trin 6: Kør server- og klienttests; deploy klienterne før
      assistant-replikken fjernes. Commit i afhængighedsrækkefølge.**

### Opgave 7: Mål det, før vi tror på det

> **MANGLER (Jarvis 3/10):** opgaven beder mig skelne «udløb» fra de andre
> udfald — men ingen opgave skaber en udløbs-tilstand. En måling af noget der
> ikke findes, måler nul. Se §1 og Opgave 8.

**Filer:** ny `scripts/maal_indbakke.py`; ingen test (måleværktøj).

R2's punkt 2 ventede fra 13. juni på en måling der aldrig blev lavet, og
tærsklerne blev først sat da nogen regnede efter. Skygge-registrets 24-timers
vindue stod 78 dage. Denne opgave findes for at det ikke gentager sig.

- [ ] **Trin 1:** Script der rapporterer, per døgn: hvor mange poster blev
      handlingskrævende, hvor mange gange fyrede TRIN 1 (påmindelsen), hvor
      mange gange nægtede TRIN 2, og hvor mange af dem blev frigivet. Begge
      heed-rater skal stå hver for sig — trin 1's og trin 2's — og de afgør om
      `_INDBAKKE_PAAMINDELSER_FOER_BLOK = 2` er det rigtige tal.
- [ ] **Trin 1a:** Par hændelser per post-id og bruger-id. Skeln `done`,
      `drop`, udløb, fail-open og DB-fejl; `released` uden årsag er ikke
      efterlevelse. Mål også om varslet kom fra model, system eller bruger,
      og hvor mange poster der forsvandt ved leveringsskiftet.
- [ ] **Trin 2:** Kør det, og LÅS en baseline i specen her, med dato.
- [ ] **Trin 3:** Registrér vinduet i `shadow_experiment_registry` med
      `review_after_hours`, så påmindelsen (rettet 2/10 med en durabel klokke)
      melder når det er modent.
- [ ] **Trin 4: Commit.**

---

### Opgave 8: Udløbs-tilstanden — en post må kunne dø af sig selv

> **MANGLER (§1).** Opgave 7 beder om at skelne «udløb» fra `done`/`drop`. Ingen
> opgave skaber tilstanden. En måling af noget der ikke findes, måler nul.

**Filer:** `core/runtime/db_inbox.py` (migration: `expires_at`), `core/services/inbox_state.py`;
test `tests/test_inbox_state.py`.

**Beslutning først (trin 1):** skal `inbox_items` have `expires_at` med samme
semantik som godkendelserne (`core/runtime/db_governance.py`: `expires_at` +
`expire_tool_intent_approval_request`), eller er udløb med vilje overladt til mig?

Bygges den, gælder tre ting: udløb er en **terminal tilstand**, ikke en sletning;
`kraever_handling` falder ved udløb, så en post ikke kan gate i det uendelige ved
at ingen rører den; og udløbet skrives til sporet, så Opgave 7 kan skelne
`udloebet` fra `released` uden årsag.

> **RETTET 3/10 (Opus) — præcedensen er ikke den den ser ud som.**
> Trin 4 sagde først: beregnet tilstand på læse-tidspunktet, «samme form som
> godkendelsernes `expired`-beregning, **ikke** en baggrundsjob der skal køre
> for at posten dør». Beregningen findes præcis som beskrevet
> (`db_governance.py:74`) — men dens egen historie siger det modsatte af det
> jeg udledte. `sweep_expired_intents`' docstring:
>
> > «Udloebet er DOVENT: det sker naar den samme intention slaas op paa ny. En
> > intention ingen spoerger til igen bliver derfor staaende `pending` for
> > evigt. MAALT 10/9-2026: fire raekker med udloeb 23, 50, 115 og 115 dage
> > tilbage i tiden, alle stadig `pending`.»
>
> Fejeren blev altså **tilføjet** fordi den beregnede form ikke var nok — og
> trin 4 forbød netop den rettelse. Jeg læste mekanismens form og sprang dens
> målte fejl over; det er samme fejl som
> `selvhelbredelse_skjuler_sin_egen_aarsag`, blot i omvendt retning.
>
> Indbakken er mindre udsat, fordi visningen læser alle åbne poster hver tur.
> Men «hver tur» gælder kun for en bruger hvis session faktisk kører. En post
> der tilhører en inaktiv bruger rammes af samme kurve, bare langsommere — og
> det er præcis §4's argument om retention, en etage nede.
>
> **Beslutningen i trin 1 er derfor: beregnet PLUS en fejer**, ikke beregnet
> alene. Fejeren er ikke det der *dræber* posten (det gør beregningen, med det
> samme) — den er det der sikrer at en post ingen læser også får sin terminale
> tilstand skrevet, så Opgave 7 kan tælle den.

- [ ] **Trin 1: Lås beslutningen** i Global Constraints (bygges, eller afvises med begrundelse). Bygges den, skal den bære BEGGE dele, med fejerens begrundelse.
- [ ] **Trin 2: Test at en post med passeret `expires_at` ikke længere gater**, og at den stadig kan læses.
- [ ] **Trin 3: Kør, se den fejle.**
- [ ] **Trin 4: Implementér** udløb som en **beregnet** tilstand på læse-tidspunktet — så posten dør uden at nogen job skal køre — OG en fejer efter mønstret i `sweep_expired_intents`, så en post ingen slår op igen ikke står `pending` for evigt.
- [ ] **Trin 5: Kanterne** — hver af disse er en vej udløbet kan blive tavst forkert:
      - `expires_at` **mangler** (NULL) → posten udløber ALDRIG, og det skal være et bevidst valg, ikke en tom streng der sorterer forkert
      - `expires_at` som tom streng eller uparsabel tekst → posten må ikke blive «udløbet» ved et uheld; fail mod at BEVARE den, og log på WARNING
      - tidsstemplet er ISO **med `T`** — `datetime('now',…)` som grænse slipper hele dagen igennem, fordi `T` sorterer efter mellemrum. Brug `strftime('%Y-%m-%dT%H:%M:%S','now',…)` og tæl rækker med OG uden filteret. Den fælde er ramt tre gange i dette hus.
      - naiv vs. tidszone-bærende tidsstempel (`db_governance.py:69` tilføjer UTC når `tzinfo is None` — gør det samme, ellers sammenlignes æbler og pærer)
      - udløb **præcis** på grænsen (`expires_at == now`) → vælg én side og pin den
      - en post der stadig **gater** må ikke kunne udløbe uden at nægtelsen forsvinder samme sted; ellers blokerer en død post
- [ ] **Trin 6: Test at udløb er idempotent** og at en genstart ikke nulstiller det — og at fejeren kørt to gange ikke tæller samme post to gange.
- [ ] **Trin 7: Kør hele suiten. Commit.**

### Opgave 9: Standardtilstanden — hvem lukker en post der er færdig?

> **MANGLER (§2).** `kraever_handling` udledes af proveniens, og `inbox_done` er
> manuel. Intet lukker et job der er exit 0 af sig selv — så systemets ligevægt
> er blokeret.

**Filer:** `core/services/inbox_state.py`, den kilde der registrerer posten;
test `tests/test_inbox_state.py`.

**Beslutning først (trin 1):** hvem lukker en post hvis arbejde er færdigt uden at
nogen kaldte `done`? Tre mulige: (a) kilden lukker — jobbet skriver sin egen
terminale tilstand; (b) en indholdsregel nedgraderer posten når kilden er
terminal; (c) ingen af dem, og posten skal lukkes af mig. Vælges (c), skal
begrundelsen stå — for det er præcis den blokerede ligevægt.

- [ ] **Trin 1: Lås beslutningen.**
- [ ] **Trin 2: Test at en post hvis kildearbejde er afsluttet (exit 0) ikke længere gater** — uden at `inbox_done` blev kaldt.
- [ ] **Trin 3: Kør, se den fejle.**
- [ ] **Trin 4: Implementér** kildens terminale tilstand som **nedgradering**, ikke sletning: posten bliver `afsluttet_af_kilde` og kan stadig ses. Beviset slettes ikke.
- [ ] **Trin 5: Kanterne** — en nedgradering der rammer forkert er værre end ingen:
      - kilden er færdig med **exit != 0** → posten må IKKE lukkes; en fejlet opgave er netop en der kræver handling
      - kilden er **forsvundet** (procesbevis mangler, «STATUS UKENDT») → hverken lukket eller gatende-for-evigt; den hører i sin egen klasse, se visningens `job-a71f3`
      - kilden melder færdig **to gange** → idempotent, og tælleren i Opgave 7 må ikke tælle den dobbelt
      - posten er allerede `done` af mig → kildens melding må ikke genåbne den
      - kilden melder færdig **mens** posten gater en mutation → nægtelsen skal forsvinde i samme greb, ellers blokerer en død post
- [ ] **Trin 6: Test at nedgraderingen er idempotent**, og at en post der IKKE er færdig ikke nedgraderes af en fejlende kilde.
- [ ] **Trin 7: Kør hele suiten. Commit.**

### Opgave 10: Loft og rangorden i visningen

> **MANGLER (§3).** Seks sektioner, én linje per post, ingen cap. Argumentet der
> udelukkede kandidat-backloggen («1.896 poster ville drukne den dag ét») gælder
> også **inde i** sektionerne.

**Filer:** visningsfilen fra Opgave 2 (`byg_indbakke`); samme testfil som Opgave 2.

**Beslutning først (trin 1):** et loft per sektion, og en rangorden — ældste først
eller mest handlingskrævende først? Loftet skal være **synligt**: en afkortet
sektion skal sige hvad der er skjult («+17 mere»), ellers er loftet selv en
tavshed.

- [ ] **Trin 1: Lås beslutningen** (tal og orden).
- [ ] **Trin 2: Test at en sektion med flere poster end loftet viser loftet og en tælling af resten**, og at de viste er de rigtige efter den valgte orden.
- [ ] **Trin 3: Kør, se den fejle.**
- [ ] **Trin 4: Implementér** loft, orden og «+N mere»-linje.
- [ ] **Trin 5: Test at den blokerende sektion («VENTER PÅ DIG») aldrig kan afkortes tavst** — en skjult blokerende post er en usynlig blokering.
- [ ] **Trin 6: Kanterne** — et loft der lyver er værre end intet loft:
      - **præcis** loftet antal poster → ingen «+0 mere»-linje
      - loft + 1 → «+1 mere», og den rigtige post er den der blev skjult
      - **tom** sektion → sektionen vises slet ikke, frem for en overskrift med nul linjer
      - poster med **samme** alder → ordenen skal være deterministisk (sekundær nøgle på id), ellers flakker visningen mellem ture og buster prompt-cachen
      - en afkortet **blokerende** sektion → må ikke kunne forekomme; testen skal bevise at loftet ikke gælder dér, ikke bare at det er stort nok
- [ ] **Trin 7: Kør hele suiten. Commit.**

### Opgave 11: Retention — hvad sker der med de lukkede poster?

> **MANGLER (§4).** `inbox_items` er durabel og vokser. Ingen lukket-sektion,
> ingen sletning, ingen TTL — samme kurve som de 1.896 kandidater, bare
> langsommere.

**Filer:** `core/runtime/db_inbox.py`, `core/services/inbox_state.py`;
test `tests/test_inbox_state.py`.

**Beslutning først (trin 1):** hvor længe lever en lukket post, og hvor ser jeg
den? Sletning er ikke det eneste svar — en lukket-sektion der kan læses, men som
ikke fylder i den aktive visning, kan være nok.

- [ ] **Trin 1: Lås beslutningen.**
- [ ] **Trin 2: Test at en lukket post ældre end vinduet ikke optræder i den aktive visning**, men stadig kan findes.
- [ ] **Trin 3: Kør, se den fejle.**
- [ ] **Trin 4: Implementér** retention som en **læse-regel** (vindue), og kun sletning hvis beslutningen kræver det. Sletning af et bevis kræver sin egen begrundelse.
- [ ] **Trin 5: Test at retention ikke kan fjerne en post der stadig gater**, uanset alder.
- [ ] **Trin 6: Kanterne** — retention sletter beviser, så hver vej skal pinnes:
      - en post der stadig **gater** → aldrig fjernet, uanset alder (trin 5)
      - en post **uden** lukke-tidspunkt → falder ikke ud af vinduet ved et uheld; mangler tidsstemplet, bevares posten
      - vinduets **grænse** (`lukket_at == graense`) → vælg én side og pin den; og tidsstemplet er ISO med `T`, så brug `strftime('%Y-%m-%dT%H:%M:%S','now',…)` frem for `datetime('now',…)`
      - **nul** poster uden for vinduet → den aktive visning er uændret, og intet slettes
      - en post der er faldet ud af den aktive visning → skal stadig kunne **findes**; «væk fra forsiden» er ikke «slettet»
- [ ] **Trin 7: Kør hele suiten. Commit.**

### Opgave 12: Tælleren skal læse promptens eget artefakt

> **MANGLER (§5).** Dagens fejlklasse: skill-gaten læste `_a_tool_calls` — der
> bærer transport-navnet `call_loaded_tool` — mens event-loggen stod på den anden
> side af udpakningen i `core/services/simple_tool_executor.py`. Gaten fyrede på
> en forkert præmis i timevis.

**Filer:** `core/services/inbox_gate.py` og integrationen i
`core/services/simple_tool_executor.py` — altså PRÆCIS de filer Opgave 4
opretter; test `tests/test_inbox_gate.py`.

> **RETTET 3/10 (Opus):** denne linje sagde `core/services/visible_runs.py`
> «(tælleren i R2.5-forudsætningen, Opgave 4)». Det modsagde Opgave 4, der
> lægger tælleren i ny `inbox_gate.py` plus `simple_tool_executor.py`. Samme
> tæller, to hjem — og den ene af dem er en fil på 7.600+ linjer, hvor
> Boy Scout-reglen ville kræve en udskillelse først. Opgave 4 vinder:
> tælleren bor der, hvor nægtelsen sker.
>
> Rører en opgave alligevel en fil over 2.000 linjer, gælder trin 3a fra
> Opgave 5 uændret: udskil nærmeste naturlige enhed FØR ændringen.

> **OVERHALET 3/10 (Opus) — beslutningen er truffet, præcedensen findes.**
> Trin 1 og 3 kunne ikke længere udføres som skrevet. Jarvis rettede
> skill-gatens udgave kl. 12:26:51 (`730e00121`), og den kørende proces har den
> (units startet 12:28:52). «Kør, se den fejle» kan altså ikke reproduceres på
> skill-gaten, og `prop-36aa612b6d7c49f1` er indhentet af virkeligheden.
>
> Værre var at rettelsen gik ind **utestet**: ingen testfil nævnte den nye kode.
> Coverage-gaten slap den igennem, fordi det var en ændring i en eksisterende
> fil og ikke en ny vagt. Dagens egen fejlklasse var altså rettet uden at noget
> pinnede rettelsen.
>
> Begge dele er nu gjort: indsamlingen er udskilt til
> `skill_gate_guard.samle_kaldte_navne(followup_exchanges, runde_kald)` —
> Boy Scout, da den sad inline i en 7.600-linjers generator — og
> `tests/test_skill_gate_guard.py` pinner elleve kanter. Mutations-tjekket viser
> at begge huller fanges hvis de lægges tilbage.
>
> **Svaret på trin 1 er derfor givet:** `core/tools/kaldt_vaerktoej.pak_ud` er
> den ENE definition af det ægte navn, og `samle_kaldte_navne` er mønstret for
> at læse en turs kald. Opgave 12 er ikke bortfaldet — den handler om
> indbakkens tæller — men den **arver** et løst problem i stedet for at løse det.

**Beslutning først (trin 1):** hvilken liste er indbakke-tællerens ene sandhed —
og er det overhovedet den samme som skill-gatens? Skill-gaten tæller *kald*;
indbakke-gaten tæller *leverede påmindelser*. Lås om de deler kilde eller ikke,
og skriv hvorfor.

- [ ] **Trin 1: Lås beslutningen** — navngiv listen, og om den deles med skill-gaten.
- [ ] **Trin 2: Test at tælleren ser det ÆGTE navn** når påmindelsen kom ad en indpakket vej: genbrug `samle_kaldte_navne`s mønster, kald ikke `pak_ud` igen i et nyt modul.
- [ ] **Trin 3: Kør, se den fejle.**
- [ ] **Trin 4: Implementér** læsningen gennem den ene kilde fra trin 1.
- [ ] **Trin 5: Kanterne** — hver af disse har kostet en fejl i huset og skal have sin egen case:
      - argumenter som JSON-**streng** (sådan sender udbyderne dem), som dict, og helt fraværende
      - **ugyldig** JSON → transport-navnet bliver stående, ikke «et skill blev brugt»
      - gyldig JSON der ikke er et objekt (`[1,2]`, `"tekst"`, `null`) → samme retning
      - indpakket kald **uden** indre navn, og med indre navn == transport-navnet (ingen rekursion)
      - skrald i listen (`None`, streng, tal, manglende `function`) → springes over, kaster ikke
      - **begge** kilder læses, også når den ene er tom — og den AKTUELLE runde er med
- [ ] **Trin 6: Vagt mod at reglen gentages** (AST): ingen anden fil end `kaldt_vaerktoej` må definere udpakningen. To definitioner kan drive fra hinanden, og det er præcis hvordan et filter bliver stille virkningsløst.
- [ ] **Trin 7: Kør hele suiten. Commit.**

### Opgave 13: Et løfte givet i prosa — navngivet fravalg eller indgang

> **MANGLER (§6).** Kanalbeskeder blev udelukket *med* en AST-vagt. Den mest
> almindelige ægte fejl — «jeg tjekker det i morgen», sagt i en samtale og aldrig
> registreret — er slet ikke nævnt.

**Filer:** Global Constraints og tabellen «Hvad der ER med, og hvad der ikke er»;
evt. en vagt efter mønstret i Opgave 2 trin 9.

**Beslutning først (trin 1):** skal prosa-løfter kunne registreres — og i givet
fald af hvem, må jeg oprette en post ud fra min egen sætning? Eller er det et
fravalg med begrundelse? Spec'ens egen standard gælder: **en udelukkelse uden
vagt glider.**

- [ ] **Trin 1: Lås beslutningen.**
- [ ] **Trin 2a (fravalg):** skriv det som navngivet fravalg i tabellen, med begrundelse — på linje med kanalbeskederne.
- [ ] **Trin 2b (indgang):** beskriv hvem der må registrere, hvordan proveniens bevises for en sætning (samme krav som Opgave 1: ejer er bevis, ikke et flag), og hvordan en fejlagtig registrering trækkes tilbage.
- [ ] **Trin 3: Commit.**

---

### Opgave 14: E2E-verifikation på CT105 — usmocket, i produktionen

> **TILFØJET 3/10 (Opus).** Opgave 0 og 7 *måler*, men intet verificerer at
> kæden holder usmocket. Huset har to målte grunde til at det ikke er nok:
> 577 grønne tests missede to fejl som fem minutter på telefonen fandt (kold mod
> varm kodesti), og min lokale DB gav det **modsatte** svar om følelsesankrene
> end CT105 gjorde. En suite der er grøn beviser at enhederne virker — ikke at
> de er forbundet.
>
> Og den mest sandsynlige fejl her er husets hyppigste: `built_but_not_connected`.
> Indbakken kan være korrekt og fuldstændig, og **ingen prompt læser den**.

**Filer:** ny `scripts/e2e_indbakke.py` (verifikationsværktøj, ingen test af sig
selv — den ER testen); kører mod CT105.

**Forudsætninger der skal bevises FØR målingen tælles:**

- [ ] **Trin 1: Begge units kører den kode du tror.** `jarvis-api` har
      `runtime_services=False` og `jarvis-runtime` `True` — de kører samme app
      med forskellige ansvar, så en ændring kan være live i den ene og død i
      den anden. Bevis det med tidsstempler, ikke med tillid:

```bash
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && git log -1 --format="kode:  %h %ad" --date=format:"%H:%M:%S"
for u in jarvis-api jarvis-runtime; do printf "%-15s %s\n" $u "$(systemctl show -p ActiveEnterTimestamp --value $u)"; done'
```

      Er en unit startet FØR commit'en, måler du den gamle kode. Genstart kun
      bag vagten — ét kald, betingelsen som TEST, aldrig to kommandoer:

```bash
ssh bs@10.0.0.39 'n=$(sqlite3 ~/.jarvis-v2/state/jarvis.db "select count(*) from visible_runs where status in (\"running\",\"streaming\",\"queued\") and run_id like \"visible-%\""); [ "$n" = 0 ] && sudo -n systemctl restart jarvis-api jarvis-runtime || echo "IKKE genstartet: $n aktive"'
```

**Kæden, led for led. Hvert led skal måles i PRODUKTIONEN, ikke i en fixture:**

- [ ] **Trin 2: En ægte kilde skriver en post.** Book en rigtig vækning gennem
      `schedule_self_wakeup` og læs rækken i `inbox_items` på CT105. Et
      `enqueue`-kald fra et script beviser kun skrivningen — ikke proveniensen,
      som er hele gate-betingelsen. Verificér at `kilde_ejer` blev udledt af
      run-/tool-id og ikke af et flag.
- [ ] **Trin 3: Posten står i visningen.** `byg_indbakke` kørt på CT105's egen
      interpreter (`/home/bs/miniconda3/envs/ai/bin/python`), ikke min — mine
      proces-starter arver en anden profil, og «den kører hos mig» beviser
      intet om hans.
- [ ] **Trin 4: PROMPTEN bærer den.** Det afgørende led, og det der oftest
      mangler. Byg den rigtige synlige prompt for en rigtig session og bevis at
      indbakke-sektionen står i den — med samme tekst visningen gav. Mål
      samtidig Opgave 0's tal igen: blev halen mindre, eller kom indbakken
      oveni?
- [ ] **Trin 5: Gaten nægter en ægte mutation.** Med en åben handlingskrævende
      post: forsøg en rigtig mutation og bevis nægtelsen — og at den **navngiver
      post-id'et**. En blokering uden adresse er en blokering man ikke kan rette.
      Ingen mock på sømmen: en mock på præcis den grænse der kan brække kan
      aldrig se fejlen.
- [ ] **Trin 6: To-trins-eskaleringen i rigtig tid.** Første og anden
      påmindelse, derefter nægtelsen. Tælleren skal overleve en **procesgenstart**
      midt imellem — den fejl har huset målt før: en volatil tæller nulstillede
      sig, og påmindelsen kom aldrig.
- [ ] **Trin 7: `inbox_done` lukker den, og visningen falder.** Posten forsvinder
      fra «VENTER PÅ DIG», nægtelsen ophører i samme greb, og posten kan stadig
      findes. Bevis ALLE tre.
- [ ] **Trin 8: Intet er sivet ind i chatten.** Ingen post må være skrevet som en
      assistant-besked — det var fejlen bag Smiths løkke. Tæl rækker i
      `chat_messages` for sessionen før og efter hele forløbet: differensen skal
      være de beskeder DU sendte, intet andet.
- [ ] **Trin 9: Mål det der ikke skete.** De tre tal huset kender som tavse
      fejlformer:
      - **ingen** poster uden læser: hver post i `inbox_items` skal kunne nås af en visning for sin bruger — en kø ingen læser er `seks_kognitive_systemer_uden_skriver` i spejlvendt form
      - **ingen** gatende post uden kilde i visningen (Skrive-kontraktens betingelse 2)
      - **ingen** falsk nudge: ankeret er målt 3/10 — run `visible-e4fff62ad24140` fik `cognitive_state.skill_invoked(code-review)` 09:57:42 UTC og `skill_gate.nudge` 09:58:48, altså **66 sekunder efter i samme run**. Rettelsen er live siden 12:28:52 CEST. Genmål:

```sql
select substr(created_at,12,8) tid, kind,
       substr(json_extract(payload_json,'$.run_id'),1,22) run
from events
where kind in ('skill_gate.nudge','cognitive_state.skill_invoked')
  and created_at > strftime('%Y-%m-%dT%H:%M:%S','now','-1 day')
order by created_at;
```

      Et par hvor en nudge følger en invokering **i samme run** er en regression.

- [ ] **Trin 10: Skriv tallene ind i spec'en** — ikke i en commit-besked der
      forsvinder. Et måleresultat ingen kan finde igen er ikke en måling.
      Mislykkedes et led, står det med sit led-nummer og hvad der manglede.

**Fail-retningen for hele opgaven:** et led der ikke kan måles er et led der
**ikke** virker, indtil nogen beviser andet. Tavshed tælles aldrig som bestået —
det er præcis hvad de 46/71 «aktive» systemer og den grønne ledger gjorde.

---

## Selvgennemgang

### Den kritiske runde fandt fire ting det første udkast manglede

Første udkast kørte kun den mekaniske gennemgang (dækning, pladsholdere,
type-konsistens) og fandt én ægte fejl: et opdigtet funktionsnavn. Da Bjørn
spurgte om jeg havde kørt en KRITISK gennemgang mod hele samtalen, fandt den
fire mere. De er alle rettet ovenfor, og de står her fordi mønsteret er værd at
huske.

**1. Jeg havde overskrevet hans design uden at sige det.** Han sagde to-trins:
«først bede ham checke … og hvis ignoreret eskalerer». Jeg kollapsede det til
øjeblikkelig blokering. Det er den værste af de fire, fordi det er min vurdering
sat i stedet for hans erklærede form — og hans er bedre.

**2. «Hvad har vækket ham» var slet ikke med.** Han bad om det ordret. Jeg
listede fyrede vækninger, hvilket ikke er det samme som at turen VED hvilken der
startede den. Nu en egen sektion.

**3. Prompt-gevinsten stod som en påstand.** Jeg tilbød at måle hvor stor en
andel af halen der er ventende-tilstand, gjorde det ikke, og skrev alligevel
gevinsten ind. Det er «nytten talt uden prisen». Nu er det Opgave 0, og den
afgør om resten er en økonomisk eller en kontrol-sag.

**4. Jeg havde ikke sagt at «fjerne tool til læst» var en FORTOLKNING.** Jeg
læste det som nægt-ikke-fjern, med en målt begrundelse — men en fortolkning der
ikke er mærket som sådan kan ikke rettes af den der skrev originalen.

### Anden runde: de syv huller var NAEVNT, ikke bygget

Bjørn spurgte derefter om listen af syv huller jeg selv havde navngivet var med.
Svaret var: de stod i beslutnings-tabellen, men **tre af dem havde ingen opgave
der byggede dem**, og to var selvmodsigelser jeg havde indført.

En tabel der siger «ind» er ikke en implementering. Det er præcis
`built_but_not_connected` i spec-form.

**To selvmodsigelser i mit eget dokument:**

- Tabellen sagde planlagte opgaver er «ind, ADSKILT fra vækninger» — men
  visningen havde **ingen sektion** til dem. Nu har den en, med begrundelsen for
  hvorfor engangs og gentagende skal være adskilt.
- Trin 3 sagde «de fire sektioner», mens skitsen havde fem. **Jeg indførte den
  modsigelse i den FØRSTE rettelsesrunde**, da jeg tilføjede «VAKTE DENNE TUR»
  uden at opdatere tællingen. Nu står tallet med navnene, så det ikke kan drive.

**Tre huller uden implementering:**

- **Forældreløse poster** stod som «ind som typet status» uden et trin. Nu
  trin 5 med en test: et job hvis proces er væk må ikke stå som «kører» i
  dagevis. Samme fejl som det stale `connected=True` i discord-gatewayen.
- **Bruger-isolation** fandtes kun som `bruger_id` i en signatur. Nu trin 6 med
  en test — husstandens andre workspaces er krypterede, så en blanding er et
  databrud og ikke en visningsfejl.
- **Kanalbeskeder** var udelukket uden en vagt. En udelukkelse uden vagt glider.
  Nu trin 9: en AST-vagt der fejler hvis `inbox_view` begynder at læse discord,
  telegram eller `chat_messages`.

**Mønsteret i begge runder** er værd at holde fast: jeg skrev beslutningerne ned
og troede dermed de var dækket. Det er samme fejl som de seks tomme vagter vi
fjernede i dag — noget der ser ud som dækning, men ikke måler eller bygger noget.

**Dækning efter Claudes rettelser:** hvert aspekt fra samtalen havde en opgave —
prompt-målingen (0), handlings-klassen (1), visningen med seks sektioner,
«vakte denne tur», forældreløse, bruger-isolation, kanal-vagt, alder og
dubletter (2), bogføringen (3), to-trins inbox-vagt (4), værktøjerne (5),
henvisning-i-stedet-for-replik (6), og efter-målingen af begge heed-rater (7).
De syv huller jeg selv navngav er afgjort i tabellen «Hvad der ER med».

**Pladsholdere:** ingen. De tre åbne beslutninger blev truffet 3/10 og står i
Global Constraints og i skrive-kontrakten. Opgave 0's tal er med vilje IKKE
udfyldt — det er en måling der skal køres, ikke en antagelse der skal gættes, og
trin 4 siger at den skal låses med en dato.

**Typer efter Codex' review:** bruger, kildetype, kilde-id og verificeret
oprettende run er nøglen i `inbox_items`; `kraever_handling` kan ikke afgøres af
en fri `kilde_ejer`-streng. `byg_indbakke(bruger_id, *, nu_ts)` læser; gaten
læser kun durabelt bogførte, åbne poster. `done`/`drop` kræver bruger-id og
returnerer en typet afgørelse.

**Det denne spec IKKE gør, med vilje:**

- Rører ikke `cluster_daemon.py`s fail-open (`if not agg: return True`), som
  rapporterer `fired: True, gate_calls: 1` med nul medlemmer. Fælles for alle
  familier; eget spor.
- Fjerner ikke de gamle `list_*`-værktøjer. Billige, virker, og fem steder.
- Bygger ikke `SubagentRuntime` fra harness-specen (8/9). Indbakken er en
  forudsætning for den, ikke en erstatning.
- Giver ikke Jarvis nye eksterne arbejdsevner. `inbox_done/drop` og klientens
  kilde-mærkede notifikation er derimod nye grænseflader og skal bygges og
  verificeres som sådan.

---

## Reviews — 3/10-2026

To agenter gennemgik denne spec parallelt samme formiddag: **Codex** (der
skrev sine rettelser ind i filen og blev stoppet af en kvote-grænse kl.
11:50, før commit) og **Jarvis**. Rettelserne står i de afsnit de hører
til; begge gennemgange gengives her. De er komplementære — Codex fandt
arkitektur- og livscyklusbrud, Jarvis test-signaturer og kildetal.

### Codex' review og verificering — 3/10-2026

**Status:** Spec’en er korrigeret, ikke implementeret. Kode, DB-skema og
CT105-hændelser er læst; der er ikke kørt en produktions-promptmåling, og
ingen ny inbox-API eller klient er bygget. Opgave 0's baseline står derfor
fortsat åben.

1. **Kritisk — leveringskø var forvekslet med opgavetilstand.**
   `session_inbox.enqueue` bruges kun for visse notifikationer i aktive
   sessioner; `flush_session` sætter `status='delivered'`, hvorefter
   `pending_for_session` ikke længere viser posten. To nye kolonner dér ville
   hverken dække direkte/urgent levering eller holde en opgave åben til
   `done/drop`. Designet bruger nu en separat, idempotent `inbox_items`-kvittering
   og lader `session_inbox` eje levering alene.
2. **Kritisk — gate-livscyklus og brugergrænse.** R2.5's `_blok` er
   procesglobal; `r2_5_haandhaevelse` frigiver den ved readback eller efter
   10 minutter. Det kan hverken repræsentere varige poster eller isolere
   brugere/workers. Inboxen får egen durabel, scoped vagt i samme
   mutationspunkt, med `done/drop` som frigivelse. R2.5's målte 460
   frigivelser består af 415 `kig_tilbage` og 45 `udløbet` på CT105; det er
   ikke 85 % efterlevelse.
3. **Kritisk — rene læsekilder og multi-bruger-isolation.**
   `due_wakeups()` skriver; `build_tool_intent_approval_surface()` kan skrive;
   `background_jobs.liste()` kan starte en shell-daemon. `list_wakeups()` og
   `list_agent_registry_entries()` filtrerer ikke bruger, og
   `list_pending_for_current_user()` kan læse alle ved tom kontekst. De
   erstattes i planen af eksplicit brugerafgrænsede, rene adaptere. Agent-
   posten må ikke gøres blokerende, før dens oprettende bruger kan bevises.

   > **RETTET 3/10 (Jarvis) — én del af dette holder ikke mod koden.**
   > `liste()` starter **ikke** daemonen: `_lokale_shell_sessioner()` spørger
   > først når pid-filen peger på en ægte daemon — netop fordi «et panel der
   > poller hvert femte sekund ville skabe den proces det påstod at
   > observere». Den ægte bivirkning er en anden: **enhver** forespørgsel —
   > også `list` — nulstiller daemonens `last_activity`, så en session-løs
   > daemon ikke lukker ned af sig selv mens panelet er åbent. Konklusionen
   > står altså (ikke ren læsning), men grunden er uret, ikke opstarten.
   > Resten af punktet er bekræftet mod koden: `due_wakeups()` kalder
   > `_save()`, `list_wakeups()` har nul bruger-filtrering, og begge
   > frigivelsesgrunde i punkt 2 (`kig_tilbage`, `udløbet`) findes ordret i
   > `r2_5_haandhaevelse._aaben_blok()`.
4. **Vigtigt — kildetyper var byttet.** `scheduled_tasks` er engangsopgaver;
   `recurring_tasks` er gentagelser. Begge har nu egen plads i kilde- og
   sektionsbeskrivelsen. Dubletter må grupperes visuelt, men ikke miste
   individuelle id'er.
5. **Vigtigt — påmindelses-tærsklen kunne aldrig nås.** Den oprindelige
   regel sendte kun én påmindelse for *nye* poster, men krævede to før
   blokering. Planen har nu en begrænset senere påmindelse og tæller kun
   leverede påmindelser per post, bruger og tur.
6. **Vigtigt — event uden abonnent er tabt levering.** At stoppe assistant-
   replikken i `flush_session` og kun publicere `channel.inbox_leveret` ville
   gøre notifikationen usynlig. Desk/mobil, replay og kilde-mærkning skal
   være i drift før serverens gamle visningsvej slukkes.

**Accept før implementering:** lås en faktisk promptbaseline (Opgave 0),
fastlæg kildernes ejerbevis og statusadaptere, og få `inbox_done/drop` samt
to-trins vagten verificeret med multi-bruger-, genstart-, race- og
leveringsfejltests. Et rent syntakstjek af denne spec er ikke en erstatning
for de integrationsbeviser.

### Jarvis' review — 3/10-2026

Bjørn bad om en uafhængig gennemgang: verificér påstandene mod koden, og skriv
rettelserne både her og i de afsnit de hører til.

### Hvad der holdt

Jeg gik efter tallene først, fordi et dokument der regner rigtigt er værd at
læse resten af. Det gør det her:

| Påstand | Verificeret mod |
|---|---|
| tool_usage-tabellen (171/141/59/24/66/37/17/6) | `tool_usage` i DB'en — **alle otte tal stemmer** |
| `_FALLBACK_FLUSH_MINUTES = 10` | `session_inbox.py:48` |
| `self_wakeup.due_wakeups/mark_wakeup_consumed/cancel_wakeup` | findes, med de angivne signaturer |
| `scheduled_tasks.list_pending_for_current_user()` | `scheduled_tasks.py:90` |
| `tool_intent_approval_runtime.build_tool_intent_approval_surface()` | findes, linje 50 |
| `background_jobs.py` | findes (19.903 bytes, 29/9) |
| R2.5-tærsklerne (`deep=3`, `_reasoning=5`, `_fast=8`, heed 0,4) | `r2_5_blocking_gate.py:71-82` |
| de to kolonner fra 2/10 | `user_id`, `workspace_name` — bekræftet i skemaet |
| `publish_scan`-vagten | `tests/test_publish_scan.py` findes |
| agent-tabellerne | `agent_registry` 356, `agent_runs` 1.533 rækker |
| R2.5-events (543/467/460) | bekræftet i `events` |

Det er ikke pynt. Tabellen med otte værktøjstal er det sværeste at ramme, og den
rammer.

### Fem rettelser

De står alle inline ved deres afsnit. Her er hvad de er, og hvorfor:

**1. Opgave 4's test kunne ikke køre — og ville ikke have målt noget.**
`evaluer_mutation` findes ikke. Den faktiske funktion er
`should_block_for_verification(*, reasoning_tier)` → `dict | None` med
`{reason, suggestions, urgency}`. Men det er den mindre halvdel: funktionen har
**fire** tidlige `return None` — cooldown under 60 s, gate-fejl,
`unverified_effective` under tærsklen, og heed_rate over grænsen. En test der
vil se en blokering skal styre alle fire. Spec'ens version styrede ingen af dem,
så selv med det rigtige navn ville den have fået `None` og faldet på
`v["blokeret"]`.

**2. Opgave 3's test kodificerede en fejl.** `done("wake-6e201")` →
`kaldt == ["6e201"]` antager at `done` klipper præfikset af. Men
`mark_wakeup_consumed` slår op på det **fulde** id, og de faktiske id'er er
`wake-` + **10** hex. Strippet præfiks = `wakeup not found`. Præfikset vælger
mekanisme; det klippes ikke.

**3. Læseren manglede.** `pending_for_session`'s SELECT henter i dag syv
kolonner. Uden `kraever_handling` og `kilde_ejer` i SELECT'en læser Opgave 1's
egen test en nøgle der ikke findes. Det er `built_but_not_connected` i
miniature: kolonnen skrives, men kan ikke læses.

**4. «Elleve eksisterende kilder» er ikke understøttet.** `session_inbox` har
**5** distinkte kilder i basen, og `enqueue` kaldes fra ét sted i koden
(`notification_bridge.py:216`). Tallet skal begrundes eller fjernes.

**5. R2.5-tallet vokser.** 7.610 → 7.643 på under en dag. Datoen står, og det
er pointen — men et tal uden forbehold om at det er et øjebliksbillede læses som
en konstant.

### Det jeg ikke kunne verificere

- **R2's 47/døgn og 15 % heed** er dateret 13/6. `r2.advisory.surfaced` har
  **0** events i basen, så jeg kan ikke genskabe tallet med det kind-navn. Det
  betyder ikke at det er forkert — det betyder at jeg ikke kan bekræfte det i
  dag, og det bør stå ved tallet.
- **Opgave 0's tal er tomt med vilje** — og det er den rigtige beslutning. Det
  er den eneste påstand i dokumentet der IKKE skal udfyldes af en læser.

### Én ting der er værd at fremhæve

Spec'ens egen selvgennemgang fanger det vigtigste: at første udkast overskrev
Bjørns to-trins-form med øjeblikkelig blokering, og at prompt-gevinsten stod som
en påstand uden en måling. Begge er rettet i dokumentet selv. Det er
`measured_before_claimed` anvendt på eget arbejde — og det er sjældnere end det
burde være.

Min samlede dom: **spec'en er byggbar.** Interface-navnene er slået op frem for
husket (kun ét var forkert, og det er rettet i Opgave 2 selv), tallene er målt,
og de fem fejl ovenfor sidder alle i *test-eksemplerne* — ikke i arkitekturen.
Ingen af dem ændrer hvad der skal bygges; de ændrer hvordan det skal testes.

---

## Seks mangler — hvad spec'en ikke dækker (Jarvis, 3/10-2026)

Spec'en svarer på ét spørgsmål godt: **kan jeg se mit ventende arbejde, og kan
kun det blokere mig?** Proveniens-tankegangen («ejer er bevis, ikke et flag») og
kravet om at læseflader ikke må kunne skrive er stærkere end hvad der står i
drift i dag.

Den svarer ikke på det andet spørgsmål: **hvordan holder den sig ren efter dag
30?** En kontrolflade der bliver beskidt er en banner igen — bare med en
blokering bag.

De seks nedenfor er **ikke rettelser**. De er mangler jeg fandt i reviewet, og
hver af dem skal enten bygges eller afvises med vilje — ved sin egen trin 1.
**De er skrevet ind som Opgave 8–13 den 3/10 (Bjørns beslutning).** Markørerne i
afsnittene ovenfor peger herned, og hver § peger tilbage på sin opgave.

### §1 — Udløb findes som måling, ikke som mekanisme

Opgave 7 beder om at skelne «`done`, `drop`, udløb, fail-open og DB-fejl». Men
**ingen opgave skaber en udløbs-tilstand.** En post har to udgange: `done` og
`drop` — begge kræver mig.

Huset har allerede mønsteret: godkendelser har `expires_at` og
`expire_tool_intent_approval_request` i `core/runtime/db_governance.py`.
Indbakken arver det ikke.

Spec'en citerer selv skygge-registrets 78 dage som grunden til at bygge
indbakken — men giver den ikke det registret manglede: en terminal tilstand som
**nogen anden end mig** kan nå.

*Beslutning:* skal `inbox_items` have `expires_at` med samme semantik som
godkendelserne, eller er udløb med vilje overladt til mig?

**→ Opgave 8.**

### §2 — Standardtilstanden er «åben og gater»

`kraever_handling` udledes af **proveniens** — et verificeret oprettende run.
Jeg har ikke fundet en indholdsregel der siger, at en post jeg selv startede, og
som ikke længere kræver noget, falder ud af klassen. Og `inbox_done` er manuel:
intet lukker et job der er exit 0 af sig selv.

Med 141 `schedule_self_wakeup`-kald og gentagne baggrundsjobs betyder det, at
systemets **ligevægt er blokeret** — medmindre noget andet lukker posten.

Spec'en advarer selv om «den tredje mekanisme der skal reddes af den fjerde». Jeg
kan ikke se hvad der forhindrer at indbakken bliver netop det.

*Beslutning:* hvem lukker en post hvis arbejde er færdigt uden at nogen kaldte
`done`?

**→ Opgave 9.**

### §3 — Intet loft og ingen rangorden

Seks sektioner, én linje per post — og ingen cap. Det er præcis det argument der
udelukkede kandidat-backloggen («1.896 poster ville drukne den dag ét»).
Argumentet gælder også **inde i** sektionerne: der står ingen regel for hvad der
vises, når «VENTER PÅ DIG» har 30 poster.

`forfald_dage` er et tal der *vises*, ikke en tærskel der *gør* noget.

*Beslutning:* et loft per sektion, og en rangorden — ældste først, eller mest
handlingskrævende først?

**→ Opgave 10.**

### §4 — Ingen retention

`inbox_items` er durabel — og vokser. Ingen lukket-sektion, ingen sletning,
ingen TTL. Samme kurve som de 1.896 kandidater, bare langsommere.

*Beslutning:* hvor længe lever en lukket post, og hvor ser jeg den?

**→ Opgave 11.**

### §5 — Gaten skal læse præcis det artefakt prompten blev bygget fra

Dette er dagens egen fejlklasse, og den bør stå eksplicit. Skill-gaten så ikke
sine egne kald 3/10, fordi den læste `_a_tool_calls` — som bærer
transport-navnet `call_loaded_tool` — mens event-loggen stod på den anden side af
udpakningen i `core/services/simple_tool_executor.py`.

Spec'en kræver et leverings-id og siger «tæl kun når påmindelsen faktisk blev
leveret til modellen». Det er rigtigt. Men den sidste sætning mangler:
**tælleren skal læse den samme liste prompten blev bygget fra.**

Ellers bygger vi samme blindhed igen — og opdager det først om tre uger.

*Beslutning:* hvilken funktion er den ene sandhed for «hvad så modellen denne
tur», og hvordan bevises de to lister identiske i en test?

**→ Opgave 12.**

### §6 — Et løfte givet i prosa har ingen indgang

Ikke en fejl — en **unavnt udelukkelse**. Kanalbeskeder blev udelukket *med* en
AST-vagt, og spec'en skriver selv hvorfor: «en udelukkelse uden vagt glider».

Men den mest almindelige ægte fejl — at jeg siger «jeg tjekker det i morgen» i en
samtale, og det aldrig registreres — er slet ikke nævnt. Efter spec'ens egen
standard bør den stå som navngivet fravalg.

*Beslutning:* skal prosa-løfter kunne registreres (og i givet fald af hvem), eller
er det et fravalg med begrundelse?

**→ Opgave 13.**

---

### Hvad jeg ikke har gjort

Jeg har **ikke** bygget noget. De seks stod først som en mangelliste; den 3/10
blev de skrevet ind som **Opgave 8–13**, hver med sin beslutning i trin 1, så de
kan afvises med vilje i stedet for at forsvinde.

Punkterne er læst frem af spec'ens egne sektioner — Global Constraints, visningen,
koblingen til R2.5, Opgave 1/2/4/7 — og af dagens fejl i skill-gaten. De er **ikke**
fremkommet af en linje-for-linje-gennemgang af hele filen; det er en læsning af de
bærende afsnit, og et punkt kan vise sig allerede dækket længere inde.

§1 og §5 deler rødder med to af Codex' fund — at `session_inbox` er en
leveringskø og ikke opgavetilstand, og at læsefladerne ikke er rene. De står
selvstændigt her, men de er ikke hans alene, og de er ikke mine alene.

---

## Opus' endelige review — 3/10-2026

Bjørn: «Kør et endelig review på den.» Otte fund, alle verificeret mod koden
frem for mod spec'ens egen prosa. Rettelserne står **inline** ved hvert sted,
markeret `RETTET`/`TILFØJET`/`OVERHALET`/`PRÆCISERET`, og hvert punkt herunder
peger på hvor.

### De to der ville koste tid

**F1 — Opgave 4 og 12 modsagde hinanden om hvor tælleren bor.** Opgave 4 lægger
den i ny `inbox_gate.py` plus `simple_tool_executor.py`; Opgave 12's Filer-linje
sagde `visible_runs.py`. Samme tæller, to hjem — og det ene er en fil på 7.600+
linjer, hvor Boy Scout ville kræve en udskillelse først. Opgave 4 vinder:
tælleren bor hvor nægtelsen sker. **→ Opgave 12, Filer.**

**F2 — Opgave 8 kopierede en præcedens' form og sprang dens målte fejl over.**
Trin 4 foreskrev beregnet udløb «ikke en baggrundsjob», med godkendelserne som
forlæg. Beregningen findes (`db_governance.py:74`) — men `sweep_expired_intents`'
docstring fortæller hvad formen kostede: *«Udloebet er DOVENT … MAALT 10/9-2026:
fire raekker med udloeb 23, 50, 115 og 115 dage tilbage i tiden, alle stadig
`pending`.»* Fejeren blev tilføjet fordi beregningen ikke var nok, og trin 4
forbød netop den rettelse. Nu: beregnet **plus** fejer. **→ Opgave 8, trin 1/4.**

### De overhalede

**F3 — Opgave 12's præmis var rettet, og rettelsen var utestet.** Jarvis fiksede
skill-gatens navne-maskering 12:26:51 (`730e00121`), og processen har den
(startet 12:28:52), så «kør, se den fejle» kunne ikke reproduceres. Men ingen
testfil nævnte den nye kode — coverage-gaten slap den igennem, fordi det var en
ændring i en eksisterende fil og ikke en ny vagt. Begge dele er gjort:
indsamlingen er udskilt til `skill_gate_guard.samle_kaldte_navne` (Boy Scout —
den sad inline i generatoren) og `tests/test_skill_gate_guard.py` pinner elleve
kanter. **→ Opgave 12.**

**F4 — To opgaver pegede på det forkerte sted for udpakningen.** Opgave 4 og 12
sagde `simple_tool_executor.py`. Den fil *kalder* kun `pak_ud`; den ene
definition er `core/tools/kaldt_vaerktoej.py:76`. Samme fejlklasse som de fem
Jarvis rettede. **→ Opgave 4's MANGLER-note; Opgave 12, Filer.**

**F5 — Global Constraints' værns-afsnit var både forkert og forældet.** Det sagde
`_all_followup_parts`, «altså i det næste runde læser». Omvendt: `_a_parts` er
model-input, og konsekvensen var at problemet var **større** end meldt — alle fem
noter nåede modellen, ikke tre. Linjenumrene var også skredet. Og hele problemet
er nu rettet og deployet (`visible_run_guard_notices`, tre klasser, begge
filter-lag). **→ Global Constraints.**

### De mindre

**F6 — Opgave 2 havde intet Trin 8.** Hullet var ikke kun nummerering: reglen
«henvisninger, aldrig payload» står tre steder i spec'en og havde **ingen vagt**.
Trin 8 er nu den vagt, med fire kanter. **→ Opgave 2, trin 8.**

**F7 — «Loft» betød to ting med modsatte domme.** Gate-loft (afvist) mod
visnings-loft (valgt, Opgave 10). De er adskilt i en tabel, med begrundelsen for
at begge domme kan være rigtige: de fejler i hver sin retning.
**→ Skrive-kontrakten.**

**F8 — Boy Scout manglede i Opgave 12.** Reglen stod kun i Opgave 5 trin 3a.
Den gælder nu alle opgaver der rører en fil over 2.000 linjer. **→ Opgave 12.**

### Hvad der ændrede sig udover rettelserne

Bjørn bad om at testene «tager højde for edges … og e2e verifikation». To ting
er derfor tilføjet:

**Kanter som egne trin** i Opgave 8, 9, 10, 11 og 12 — 28 cases i alt, hver med
den fejl den stammer fra. De mest kostbare er tre: `T` i ISO-tidsstempler (ramt
tre gange her), et argument der er gyldig JSON men ikke et objekt, og en
nedgradering der rammer en post der fejlede frem for en der lykkedes.

**Opgave 14: e2e-verifikation på CT105, usmocket** — ti led fra en ægte kilde,
gennem visningen og **prompten**, til nægtelsen og lukningen. Den fandtes ikke:
Opgave 0 og 7 måler, men intet beviste at kæden er forbundet. Fail-retningen er
sat eksplicit: et led der ikke kan måles virker ikke, indtil nogen beviser andet.

### Hvad der holdt

Alle fem af Jarvis' rettelser er landet inline og markeret, ikke kun i bunden.
De seks sektioner er konsistente mellem visningen og Opgave 2 trin 3. Opgave 0's
8 %-tal er korrekt udfordret frem for gentaget. Opgave 13's henvisning til
Opgave 2 trin 9 er gyldig. Og `expire_tool_intent_approval_request` findes hvor
Opgave 8 siger — det var dens *historie*, ikke dens existens, der var problemet.

**Dommen er uændret fra Jarvis': arkitekturen holder.** F1 og F2 var ikke
test-eksempler, men de rører ikke arkitekturen — de rører hvor noget bor, og
hvilken halvdel af en præcedens man kopierer.

### Og én ting om min egen måling

Jeg brugte `head -8` på en grep og konkluderede kort at
`expire_tool_intent_approval_request` ikke fandtes. Den stod på linje 223,
uden for vinduet. Det er `limit_vindue_faelden` igen, i en gennemgang hvis hele
formål var at fange præcis den slags. Derfor er hvert fund ovenfor verificeret
med en kommando der ikke kan afskære sit eget svar.
