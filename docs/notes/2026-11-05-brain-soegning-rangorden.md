# Brain-søgningens rangorden beskrev vigtighed, ikke relevans (5/11-2026)

## Defekten

`search_brain_scored` rangerede på `0.7 * cos + 0.3 * eff`. Målt mod
`jarvis_brain_index.sqlite` (aktive poster med vektor) er cosinus-fordelingen
meget smal, fordi nomic har høj baseline-cosinus:

| spørgsmål | p5 | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| hvilken port kører ntfy på | 0,522 | 0,578 | 0,609 | 0,644 | 0,720 |
| pfsense API nøgle header | 0,462 | 0,531 | 0,567 | 0,600 | 0,701 |
| hvad er el-cyklens watt | 0,474 | 0,523 | 0,551 | 0,582 | 0,674 |
| hvilken port lytter jarvis-api på | 0,476 | 0,545 | 0,592 | 0,645 | 0,744 |
| hvor ligger den levende database | 0,512 | 0,564 | 0,609 | 0,652 | 0,740 |

(Mine tal afviger lidt fra Jarvis' — fx ntfy p5 0,522 mod 0,534 — men samme billede; indekset er vokset siden.)

Max minus median er 0,10–0,20; p99 minus median kun 0,06–0,07. Ganget med 0,7
bliver relevans-spændvidden 0,07–0,14, mens salience kunne give op til 0,30 og
i praksis flyttede 0,10–0,20 mellem importance 0,3 og 0,95. Temporal boost
(op til +0,147, helt uafhængig af relevans) var en tredje term i samme størrelse.
Reproduceret symptom: med boost slået til (produktionens default) var
«Liva udsat for vold af sin kæreste» nr. 1 på ntfy-spørgsmålet.

`recall.py:128` kalder med `min_cosine=0.5`. Andel af indekset der passerer:

| spørgsmål | ≥0,50 | ≥0,55 | ≥0,60 | ≥0,65 |
|---|---|---|---|---|
| ntfy | 96,7 % | 83,1 % | 18,2 % | 0,7 % |
| pfsense | 80,0 % | 26,7 % | 1,0 % | 0,1 % |
| el-cykel | 82,6 % | 10,8 % | 0,3 % | 0,0 % |
| jarvis-api port | 86,4 % | 45,1 % | 7,1 % | 0,8 % |
| levende database | 96,2 % | 67,2 % | 14,9 % | 1,1 % |

0,5 filtrerer altså 3–20 % væk — i praksis intet.

## Hvad jeg ændrede (`core/services/jarvis_brain.py`)

1. `score = _COSINE_WEIGHT * cos + _SALIENCE_WEIGHT * eff` med **0,95 / 0,05**.
   Salience-leddets samlede spænd (importance 0,3→0,95) er nu ≈0,03, under
   p99-minus-median (0,06). Vægtene summerer stadig til 1,0, så scoren ligger på
   omtrent samme skala og `min_score` betyder det samme (ingen kaldere i
   kodebasen sætter den for brain-søgning; default 0,0 er uændret).
2. `_MAX_TEMPORAL_BOOST` og `_compute_search_temporal_boost(boost_factor=)`
   sænket 0,15 → 0,03. Efter punkt 1 alene løftede boosten stadig irrelevante
   poster ind på plads 2–3 for el-cyklen. De to konstanter skal følges ad
   (afskæringen af boost-opslaget er en eksakt ulighed, ikke en tilnærmelse);
   boost_factor refererer nu direkte til loftet. `temporal_boost_recall` er
   en anden funktion og er urørt.
3. Ingen ændring i `recall.py` og `jarvis_brain_tools.py`: signaturer og
   `min_cosine`/`min_score`-semantik er bevaret.

Valgt metode: salience som tiebreaker inden for et relevans-bånd (ikke ren
cosinus), så vi ikke mister salience helt — to poster med samme cosinus
rangeres stadig efter importance (testet).

## Før / efter — top-3 med temporal boost (produktions-default)

Relevans-vurdering af top-1 er min egen.

| spørgsmål | FØR top-1 | relevant? | EFTER top-1 | relevant? |
|---|---|---|---|---|
| ntfy-port | Liva udsat for vold af sin kæreste | nej | Telefon ikke på LAN: ADB-bridge | **nej** |
| pfsense API header | PWA build & servering | nej | pfSense API skill installeret og testet | **ja** |
| el-cyklens watt | Fælles arbejdsaftale: stop-og-spørg | nej | Bjørns cykelrute (nr. 2: Gogobest GF750+ cykel) | **emnenær** (cykel; watt-posten er nr. 2) |
| jarvis-api port | To separate uvicorn processes: API 8080 / runtime 8011 | ja | Inventar: 28 eksterne API-værktøjer | **nej** — se nedenfor |
| levende database | Deepseek-spøgelset fundet og fikset | nej | Bjørn slet ikke DB-rådata direkte | emnenær (DB, men ikke placering) |

Resultat: 1 klar forbedring (pfsense), 2 fra irrelevant til emnenær (el-cykel,
database), 1 uændret dårlig (ntfy), 1 **forværret** (jarvis-api).

Forværringen: «To separate uvicorn processes» (cos 0,698, imp 0,92) lå nr. 1 på
salience og ligger nu nr. 8. Dens cosinus er lavere end otte andre poster, og
rangordenen følger nu cosinus. Det er korrekt ifølge den målte model, men det
viser at cosinus alene ikke kan skelne «handler om API» fra «svarer på portspørgsmålet».

## Regressionstests (`tests/test_jarvis_brain_ranking.py`)

- `test_high_importance_low_cosine_does_not_beat_high_cosine` (3 cosinus-par fra
  den målte fordeling), `test_salience_term_is_smaller_than_realistic_cosine_spread`:
  **fejlede på den gamle kode** (4 fejl) og består nu. Verificeret igen med
  gamle vægte tilbage som mutation: samme 4 fejler.
- `test_salience_still_breaks_ties_between_equally_relevant`: salience er ikke fjernet.
- `test_search_effective_salience_is_capped_by_importance` havde de gamle vægte
  hardkodet (loft 0,79); grænsen afledes nu af konstanterne. Formålet (loft = importance) er uændret.
- 143 brain-relaterede tests grønne.

## Stadig åbent

- **ntfy-spørgsmålet er ikke løst.** Heller ikke ren cosinus har en ntfy-post
  i top-5 (højeste cos 0,72 er «Hvorfor `internal_api` fejler»), selvom posterne
  findes («Selvhostet ntfy klar i CT 107» m.fl.). Det er embedding-kvaliteten, ikke vægtene.
- **Bedre langsigtet løsning: nomic task-prefikser** (`search_query:` /
  `search_document:`). Den bygger jeg bevidst ikke: den kræver re-embedding af
  ~20.000 poster à ~19,7 s på GTX 1050 Ti ≈ 110 timer. Det ville adskille
  spørgsmål fra dokumenter og sandsynligvis udvide cosinus-spændvidden.
- **Leksikalsk signal** (BM25/FTS på titel + ord som «ntfy», «port», «8080»)
  ville fange præcis den slags opslag som embedding misser; ikke undersøgt her.
- **`min_cosine=0.5` i `recall.py` er uændret** og filtrerer næsten intet. Jeg
  rørte den ikke, fordi en højere tærskel (0,6) ville skære p90 af og tabe
  svage-men-rigtige hits; med rangordenen rettet er den mindre kritisk. Bør
  tunes mod et lille facit-sæt, ikke på fem spørgsmål.
- **Facit-sæt**: fem spørgsmål og min egen relevansvurdering er en tynd grundlinje.
- `jarvis_brain.py` er 2.150 linjer (>2000). Boy Scout-reglen kræver at en
  sammenhængende enhed udskilles først; scope for denne opgave tillod ikke en
  ny fil, så det er ikke gjort. Naturlig kandidat: temporal-edge-koden (~linje 1050+).
