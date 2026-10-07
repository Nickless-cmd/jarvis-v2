---
status: foreslået
dato: 2026-10-07
ejer: bjorn
spec: ../../../specs/2026-10-07-agentorkestrering-og-subagenter.md
forfatter: jarvis
metode: tre grep i spec-kilden, tre laeste filer i koden, to tabeltaellinger i DB
svar: codex 2026-10-07 18:09 — §7.2, §8.1 og §11 (commit c65e078c0)
---

# Agentens hukommelse er ikke defineret i spec'en — og den der findes, er kollektiv

Status: foreslaaet

## Problem

Spec'en definerer agentens kontekst i §7 som et valg mellem `fresh` (intet) og
`fork` (parentens afsluttede ture). Det er hele kontekstkontrakten. Der står
ikke ét ord om hvad en agent husker fra **sine egne tidligere assignments**.

Det er ikke en detalje, fordi §2 samtidig lover at børn har «egen identitet,
kontekst, værktøjsadgang og historik» — og §9 indfører langtidsagenten med et
«varigt mål og planlagte aktiveringer». En varig identitet uden hukommelse
mellem aktiveringer er ikke en langtidsagent; det er den samme engangsagent
startet igen. Hver aktivering ville begynde fra måleteksten alene.

**Målt i spec-kilden (188 linjer):** `historik` nævnes to steder — §2's
påstand og §7's *parent*-historik. Agentens egen historik: nul steder.
`cross_agent`, `agent_observations` og `Scout Memory`: nul steder.

**Målt i koden — der findes allerede tre hukommelseslag, og spec'en nævner
ingen af dem:**

| Lag | Fil | Hvad det er | Hvem deler det |
|---|---|---|---|
| 1 | `agent_observations` (state_store) | komprimerede observationer | alle agenter |
| 2 | `core/services/agent_skill_library.py` | rolle-`skills.md`, lærte mønstre | alle agenter **med samme rolle** |
| 3 | `core/services/cross_agent_memory.py` | semantisk søgning i lag 1, 14 dages friskhed | alle agenter, alle roller |

Alle tre injiceres i agentens systemprompt ved spawn
(`agent_runtime_spawn.py:232` og `:249`). De virker. De er bare ikke beskrevet
i spec'en, så en implementering af spec'en ville bygge forbi dem.

**Og her er den skarpe pointe: ingen af de tre er agentens EGEN historik.**

Lag 2 er per *rolle* — delt af alle agenter med den rolle. Lag 3 er
tværagent — delt af alle. En langtidsagent ville altså kunne huske hvad
*andre* agenter med dens rolle har lært, men ikke hvad **den selv** konkluderede
sidste gang. Det er den forkerte form for netop det, §9 indfører.

Kontrasten er tydelig i min egen arkitektur: `MEMORY.md`, `USER.md` og
`remember_this` er *personlig* hukommelse — min, ikke delt. En langtidsagent
har brug for det samme: sin egen erindring, ikke kun puljens.

**To tillægsmålinger, fordi de siger hvor tidligt dette er:**

- `agent_schedules` (skemaet §9's «planlagte aktiveringer» hviler på) har
  **0 rækker**. Scheduleren er skema, ikke drift.
- `agent_registry`: 328 `completed`, 17 `cancelled`, 17 `expired`, 1 `planned`.
  Alle er engangsarbejde. Der kører ingen langtidsagent i dag.

## Beslutning

Hullet navngives her og løftes ind i §12 som et åbent produktvalg — det er
Bjørns at træffe, ikke mit, fordi det rører retention, ejerskab og omkostning.

Anbefalingen, hvis valget skal have et udgangspunkt: **en fjerde kilde, som er
agentens egen** — dens tidligere terminale resultater og dens egne noter,
tilgængelige for dens næste assignment gennem samme ejer- og
sessionsafgrænsning som alt andet. Lag 1–3 bliver liggende som det de er:
kollektiv baggrund. Den personlige erindring kommer ovenpå, ikke i stedet.

Formen bør følge det, der allerede virker for Jarvis selv: et bevidst skrevet
resumé pr. assignment (hvad blev gjort, hvad blev besluttet, hvad er åbent),
ikke en rå genafspilning af hele transcriptet.

## Overvejede alternativer

- **Bruge `agent_transcript.py` som hukommelse.** Billigst — filen findes og
  fsync'es. Men §9 kalder den udtrykkeligt et *eventspor*, og dens læsevenlige
  toolresultater er afkortede. Et auditspor er ikke en genkaldelsesflade.
- **Lade lag 3 (`cross_agent_memory`) være svaret.** Det virker og er koblet
  ind. Men det er kollektivt: agenten husker hvad rollen lærte, ikke hvad den
  selv gjorde. Det besvarer «har nogen set dette før?», ikke «hvad besluttede
  jeg sidst?».
- **Altid `fork` af parenten.** Forkert akse. `fork` giver parentens ture, ikke
  agentens egne. En langtidsagent har ingen parent i sin anden aktivering.
- **Ingen hukommelse — hver aktivering frisk.** Gør §9's varige mål til
  pynt: agenten ville gentage sine egne undersøgelser hver gang og aldrig
  bygge videre. Det er den vej der ser billigst ud og koster mest.
- **Bygge det nu.** Nej — spec'en er `udkast til gennemgang` og implementeringen
  er ikke startet. Et hukommelseslag bygget før assignment/run/inbox-kontrakten
  ville mangle den kontrakt det skal hænge på.

## Svar fra codex (7/10-2026, 18:09 — commit c65e078c0)

Codex byggede videre på denne note samme aften og lukkede hullet som
**arkitektur**: §7.2 definerer nu to former — et append-only resumé pr.
terminalt assignment (`gjort`, `besluttet`, `åbent`, evidensreferencer, status,
tidsstempel) og agentens egne, versionsstyrede noter. Læsning, skrivning og
promptinjektion bindes til `owner_user_id`, `agent_id` og sessionsscope, og
«samme bruger eller rolle alene er ikke nok» står udtrykkeligt. §9's
langtidsagent genkalder dem efter §7.2, og retention besluttes samlet med
artefakter og worktrees. §11 fik et «Hukommelse og worktrees»-afsnit.

**Han fandt en fejl jeg ikke selv så.** Jeg kaldte de tre kollektive lag
«kollektive». Han målte hvad det betyder i flerbrugerdrift: rollefiler vælger
efter rollenavn, og tværagent-søgningen filtrerer **ikke** på ejer eller
session før promptinjektion. Det er ikke et manglende lag — det er en lækage.
Han skrev det rigtige værn: de tre lag må ikke injiceres i et flerbrugerrun,
før de har serverhåndhævet ejer- og delingsscope på skrivning, søgning **og**
retrieval.

## Én knude der stadig er åben (§7.2)

Teksten siger to ting der peger hver sin vej, og valget afgør både omkostning
og sikkerhed:

- «Resuméet er en **projektion** af det faktiske terminale udfald» — lyder som
  en deterministisk afledning af noget der allerede findes.
- «en mislykket **opsummering**» — lyder som en aktiv skriveproces der kan
  fejle.

**Målt: `opsummering` nævnes præcis ét sted i hele spec'en (linje 104), og
intet sted står der hvem der skriver resuméet, eller at vejen går gennem
ejerens ruterettigheder og §8's budget.**

Er det en deterministisk projektion, er «mislykket opsummering» kun en
I/O-fejl: billigt, ingen ny modelvej. Er det en modeltur, er det **en ny
provider-vej pr. terminalt assignment** — og så gælder §11.1's krav om afvisning
*før providerkald* for en anden bruger også her, ligesom for `route_source` og
`MODEL_UNAVAILABLE`. Den vej er ikke nævnt.

Og der er en selvforstærkende risiko ved modelvarianten: en model der læser sit
eget resumé skriver næste resumé, så et fejlagtigt resumé bliver til næste
resumés præmis. Det er samme familie som den prompt-ekko-lækage jeg lukkede i
Sansernes Arkiv — hvor den forrige beskrivelse blev ført tilbage ind i prompten,
og 13/9 gav tre poster i træk, hvor den sidste citerede den forrige.

**To mindre, målt samme sted:**

- §8.1 kræver eget worktree «også for læsende reviewerarbejde», og §12 kalder
  worktree «fastlagt af Bjørn». Bjørns beslutning er *worktree som standard for
  kodeagenter*; læsende review er ikke en skrivende kodeagent. Udvidelsen er
  rimelig, men den bør stå som udvidelse, ikke som hans ord — en fuld checkout
  pr. review er en omkostning der ikke er målt.
- §8's budget (linje 128) nævner børn, tokens, dybde, tooltrin, tid og retries —
  men intet loft over **antal worktrees eller diskforbrug**. Mange worktrees er
  mange checkouts, og det er en reel grænse både i containeren og på CheifOne.

## Konsekvenser

- §12 får et nyt åbent valg: hvilken hukommelse en langtidsagent skal have
  mellem sine assignments, og hvordan den afgrænses.
- §7.2 mangler at fastslå **om resuméet skrives af en model eller afledes
  deterministisk**, og i modeltilfældet at føre den vej gennem ejerens
  ruterettigheder og budgettet.
- Retention for agentens erindring skal træffes **sammen med** artefakt-
  retention, ikke hver for sig: en genkaldelsesflade der ryddes før artefakterne
  peger på noget der er væk.
- En skrive-vej ind i agentens hukommelse er en ny flade, hvor et barns
  resultat kan påvirke et andet runs kontekst. Den skal gennem samme
  ejer- og tillidsgrænse som §8 kræver — et barns tekst må ikke udvide en
  efterfølgers rettigheder.
- `agent_schedules` med 0 rækker betyder, at langtidsagenten først skal bevises
  på scheduler-niveau, før hukommelsen overhovedet får noget at bære over.
