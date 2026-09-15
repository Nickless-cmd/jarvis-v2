# Prompten bad om et værktøj der ikke lå i kaldet

**15/9-2026.** Codex leverede en analyse af hvorfor skill-gaten ikke virker.
Jeg efterprøvede den før jeg byggede.

## Hvad der holdt

Hovedpåstanden, og den er værre end beskrevet:

```
katalog: 471 værktøjer, heraf 24 med «skill» i navnet
«brug pdf skill»               → 48 værktøjer | skill-: INGEN
«lav en analyse af regnearket» → 48 værktøjer | skill-: INGEN
```

Ikke ét skill-værktøj overlevede beskæringen til de 48 i den synlige lane.
Alligevel skriver prompten ordret:

    skill_invoke("<navn>") og læs HELE SKILL.md før du skriver svaret

Jarvis gjorde derfor det rationelle: fandt filen med `explore` og læste
SKILL.md i hånden. Det var ikke ulydighed; det var den eneste vej han kunne se.

Selvmodsigelsen holdt også — hentet ud af den ægte prompt: «du skal ikke kalde
skill_suggest eller skill_gate først», mens decision-gaten kræver det modsatte.

Matcher-påstanden holdt og er skarpere end hans: han fik forkerte match, jeg
fik **ingenting**.

| forespørgsel | match |
|---|---|
| «brug pdf skill» | **intet** — og et PDF-skill findes |
| «lav en pdf rapport» | deep-research (0,65), composio-canvas-design (0,61) |
| «hjælp mig med excel» | excel-automation (0,79) ✓ |

## Hvad der ikke holdt

**«Ingen rigtig `skill_invoke` siden 4. september»** — der er tre, senest
14/9 kl. 18:00:50 (`git-advanced`). Men lasten er kun `{"name": "..."}` uden
run-id, så man kan ikke afgøre om de er ægte eller fra tests. Konklusionen var
for stærk; pointen om sporbarhed er til gengæld præcis rigtig — og er selve
grunden til at det ikke kan afgøres.

**«Døren er fjernet»** — nej. `load_more_tools` **er** blandt de 48, så
værktøjerne er nåelige. Prompten undlader bare at sige at man først skal hente
nøglen. Det gør rettelsen mindre end analysen lægger op til.

## Rettelsen: atomaritet

> Runtimen må aldrig instruere modellen i at kalde et værktøj, som ikke findes
> i den aktuelle request.

`skill_invoke` fæstnes nu i kappen **netop de ture hvor prompten nævner det** —
ikke altid. Uden et match nævner prompten ingen skills, og værktøjet ville være
uden et navn at give det: en spildt plads ud af 48.

Betingelsen er den samme som prompt-sektionens, og de **deler ét opslag**
(memoiseret på beskeden). To opslag kunne give to forskellige svar, og så ville
kontrakten kunne brydes uden at nogen af siderne var forkerte hver for sig.
Sektionen koster 101 ms; beskæreren får svaret gratis.

## Tredje gang mønsteret bider

Kommentaren over `REQUIRED_LAZY_TOOL_NAMES` beskriver præcis det samme for
`explore` den 6/9: «scope tillod det, kataloget nævnte det, prompten anbefalede
det — og pruneren fjernede det fra selve tool-arrayet».

## Og en fejl der skjulte rettelsen

Første forsøg virkede ikke, og målingen viste stadig brud. Årsagen var at
fæstnings-logikken lå i **to kopier i samme funktion** — én i den tidlige
udgang (`remaining <= 0`) og én efter Tier 2. Jeg ramte kun den ene, og det er
netop den tidlige der tages: Tier 1 sprænger kappen alene i cowork-scope.

To kopier af samme beslutning er dobbelt sandhed. Nu er der én, og en test
kræver at der bliver ved med at være det.

## Efter

```
forespørgsel                     prompt nævner   skill_invoke med
hjaelp mig med excel             True            True
lav en pdf rapport               True            True
skriv en rapport om kvartalet    True            True
docker container starter ikke    True            True
brug pdf skill                   False           False
hej                              False           False

kontraktbrud: 0
```

## Mutations-prøve

| Mutation | Udfald |
|---|---|
| betingelsen fjernes | 6 røde |
| fæstnes altid (spilder en plads) | 4 røde |
| den tidlige udgang fæstner ikke | 7 røde |
| kappen håndhæves ikke | 6 røde |
| memoen deles ikke (to opslag) | 1 rød |
| fejl i matcheren fæstner alligevel | 1 rød |

## Matcheren (samme dag) — og Codex' diagnose var forkert her

Han konkluderede at matcheren manglede eksplicit navne-genkendelse. Den
fejlede ikke. Den kendte **63 skills, og PDF-skillet var ikke iblandt dem.**

`_scan_skills` kiggede kun ét niveau ned. `composio-document-skills/` har ingen
egen SKILL.md — det er en mappe med fire skills i:

```
66 SKILL.md paa dybde 2   ← det scanneren saa (63 unikke mapper)
 4 paa dybde 3            ← docx, pdf, xlsx, pptx — usynlige
```

**Loader-rettelsen alene løste det.** 63 → 67 skills, og «brug pdf skill» giver
`pdf (0,76)`. Matcheren kunne ikke matche noget den aldrig havde fået at se.

### To lag mere, som først blev synlige bagefter

**Ankeret.** «brug pdf skill» trak også `composio-skill-creator` (0,71) og
`composio-template-skill` (0,71) — kun fordi ordet «skill» stod på begge sider.
To af tre pladser gik til støj. Ord der handler om *mekanismen* bærer ikke
længere et anker.

**Længde-gulvet.** «brug pdf skill» er 14 tegn mod en tærskel på 15. Ét tegn.
Den mest eksplicitte skill-anmodning der findes, blev kasseret som småsnak.
Prisen for undtagelsen er målt: af 1.527 brugerbeskeder på 30 dage var 294
under 15 tegn, og **nul** af dem nævnte «skill».

De to regler ser modsatrettede ud og er det ikke: ordet «skill» siger at vi
skal **se efter**, men det kan ikke **bevise** et match. At spørge og at bevise
er ikke det samme.

### Efter

```
forespørgsel                 matchet            i prompten  værktøj
brug pdf skill               pdf                True        JA
udfyld en pdf formular       pdf                True        JA
hjaelp mig med excel         excel-automation   True        JA
brug excel skillet           excel-automation   True        JA
hej                          —                  False       nej
hvilke skills har du         —                  False       nej
```

### To fejl i mine egne tests undervejs

Begge samme slags: **skillets navn er MAPPENS navn**, ikke frontmatterens
(`name = path.parent.name`). Første test antog det modsatte og bestod derfor
selv når koden gjorde det forkerte. Skrevet ned i testen, så den næste ikke
skal finde det igen.

Og kollisions-værnet havde et hul jeg selv byggede: mapperne scannes sorteret,
så `bundt/pdf` kom før `pdf`. Når rod-skillet ankom, var bundtnavnet tomt,
kvalificeringen gav samme navn — og den overskrev alligevel, med en advarsel
der sagde «indlæser som 'pdf'» om noget der allerede hed `pdf`.

## Autonome ture undtaget (samme dag, efter måling)

Vagten på kæden gav sit første svar, og det var ikke det jeg ventede. Tre
fæstnelser på tre timer — og **alle tre var autonome ture**:

```
12:15:59  autonomous-e  «Begge bekræftet. Dream note verificeret…»
13:18:43  autonomous-d  «Data samlet. DB er sund (integrity OK)…»
14:00:43  autonomous-3  «hjemme. Her er den korte rapport…»
```

Der var ingen bruger der spurgte om noget. Fladen foreslog `deep-research`,
`code-review` og `git-advanced` til hans egne baggrundsture, og nul blev brugt.

**Det var korrekt adfærd, ikke en fejl.** Jeg havde en time tidligere skrevet at
«han går udenom døren» — forkert. Døren blev åbnet på ture hvor der ikke var
noget bag den. Og den kostede ~55 ms opslag plus en plads ud af 48 på hver
eneste baggrundstur.

Undtagelsen ligger i `_traef`, som **begge** forbrugere går igennem — prompten
og beskæreren kan derfor ikke komme til at sige hver sit. Run-id'et sættes af
`run_closure_gate._on_run_started`, der kun lytter på
`runtime.autonomous_run_started`, så et `autonomous-`-præfiks er et positivt
bevis. Er id'et tomt, kører vi som før: **tvivlen falder ud til at beholde
skills for hans egne ture.**

## Udestår — og hvordan det måles

Atomariteten gør værktøjet **tilgængeligt**. Om det er **nok** kan kun afgøres
på rigtige ture. Kæden logges nu i sit manglende led:

    [skill-atomaritet] faestner skill_invoke — match: <navne>

Sammen med `cognitive_state.skill_invoked` giver det: matched → surfaced →
tilgængelig → invoked. Det led der stadig mangler er et **run-id** på
invokeringen; uden det kan en ægte invokering ikke skelnes fra en test.

## De fire resterende (samme dag)

**1 — Run-id på invokeringen.** Eventet bar kun `{"name": ...}`, så tre
invokeringer i basen kunne ikke skelnes fra tests. Mekanismen fandtes:
`aktivt_run_id()` blev bygget 12/9 efter to hændelser der ikke kunne
efterforskes, og kommentaren dér siger det selv — «feltet fandtes; kalderen
sendte det bare ikke». Nu bærer eventet `run_id`, `session_id` og `surfaced`,
så kæden **matched → surfaced → invoked** kan lægges sammen bagefter.

**2 — Selvmodsigelsen.** To aktive beslutninger krævede det modsatte af hvad
fladen siger:

| | efterlevelse |
|---|---|
| `dec_06d24592d650` «Før enhver opgave … kør `skill_suggest(query)`» | 0,10 |
| `dec_470e3694d982` «Kald altid `skill_gate(...)` som allerførste step» | 0,00 |

Begge navngav værktøjer der ikke lå i de 48 — de kunne slet ikke efterleves.
Pensioneret via `revoke_decision` med begrundelse. Deres hensigt lever videre i
runtimen; det var kun ritualet der var forkert.

**3 — `skill_autosurface_enabled`: ikke rørt, med vilje.** Kontakten styrer
`skill_gate(autosurface=true)` — og `skill_gate` er ikke blandt de 48 — samt
`agent_loop.py`, som er **jarvis-code**'s loop («Klienten (jarvis-code) ejer
loopet»), og den bruger han ikke længere. Tilladelses-listen er desuden tom, så
`filter_to_approved` returnerer `[]` uanset. At tænde ville ændre ingenting og
samtidig åbne en grænse koden selv beskriver som «widens the injection
surface». Afventer hans ord.

**4 — Dansk.** Seks af otte rimelige danske formuleringer fandt ingenting.
De to der virkede havde det danske ord i navnet («pdf», «youtube»); resten
kræver oversættelse — regneark er ikke excel, præsentation er ikke pptx.

Matcheren **understøtter** tosprogede `use_when` og splitter dem per sprog.
Ingen skill havde en `DA:`-linje. Fjerde gang på én dag at noget findes uden en
kalder.

Tillægget ligger i `core/tools/skill_dansk_tillaeg.py` og ikke i SKILL.md,
fordi de fleste skills er leverandør-filer der overskrives ved opdatering. To
værn holder listen ærlig: den må kun navngive skills der findes (en test
kræver det), og den tilføjer kun **udtryk**, aldrig nye betydninger.

```
før:  6 af 8 fejlede
efter: 0 af 8
```

En vagt fangede straks sin egen svaghed: den fejlede på `pfsense-api`, som
findes i produktion men ikke på min maskine. Miljø-afhængig, ikke forkert i
indhold — den måler nu mod alt der kan bevises findes, og navngiver de
vært-lokale eksplicit.
