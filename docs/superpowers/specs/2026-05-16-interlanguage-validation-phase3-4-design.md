# Interlanguage Validation — Phase 3+4 Analyse Design

**Dato:** 2026-05-16 (pre-registration FØR data eksisterer)
**Status:** Approved — låst metode-valg før de 7 dages dataindsamling slutter
**Forbinder til:** `docs/superpowers/specs/2026-05-16-interlanguage-validation-design.md`

---

## Hvorfor pre-registreret nu

Phase 2 startede 2026-05-16 16:16 og slutter ca. 2026-05-23. Data eksisterer ikke endnu. Ved at pre-registrere analyse-metoderne NU låser vi os mod **p-hacking** og **post-hoc rationalization**: når vi ser data, eksekverer vi denne plan ord-for-ord.

Hvis vi vil afvige (fx en outlier kræver ny metrik), skal det dokumenteres som **post-hoc analyse** i en separat sektion af rapport — IKKE blandes med pre-registreret resultat.

Det er klassisk eksperimentel disciplin. Vi gør det også.

---

## 1. Dataudtræk + cleanup

### Inputs

Hentes fra `interlanguage_practice`-tabellen via en deterministisk query:

```sql
SELECT expression_id, expression_text, peer_id, created_at
FROM interlanguage_practice
WHERE created_at >= '<PHASE2_START_ISO>'
  AND created_at <  '<PHASE2_END_ISO>'
  AND expression_text != ''
  AND length(expression_text) >= 3
ORDER BY peer_id, created_at ASC
```

`PHASE2_START_ISO` og `PHASE2_END_ISO` låses ved Phase 2-start (allerede gjort: 2026-05-16T14:16:56Z til exakt +168h).

### Pre-registreret cleanup-regler

Disse er **eneste** ændringer vi må lave på rådata:

1. **Drop expressions med text-længde < 3 tegn** — sandsynlige fejl (tom eller næsten-tom). Beholder gyldige korte single-primitive expressions som `!ro` (3 tegn). Bekræftet med Jarvis 2026-05-16.
2. **Drop expressions uden primitiv-symbol** (→ ↔ ⊂ ≈ !) — model fulgte ikke format
3. **Drop expressions med >200 tegn** — model genererede prosa, ikke compact expression
4. **De-duplikering per peer:** hvis samme expression text optræder flere gange fra samme peer inden for 1 time, behold kun den første

Cleanup-tal **rapporteres per peer** i resultatet (ikke skjult). Hvis én peer mister >30% af sine expressions til cleanup, flag det.

### Cohort-balance check

Efter cleanup, hvis nogen peer har <100 expressions (75% af forventede 210), så **markér det som incomplete data**. Vi kører stadig analysen, men markerer findings for den peer som "kvalitativ kun".

---

## 2. Statistical Classifier (primær dommer)

### Embedding-model

**Pre-registreret valg:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional, lokalt available).

**Hvorfor ikke OpenAI text-embedding-3?** Lokal model er deterministisk, free, og uden API-latens på 1.260 calls. MiniLM er almindeligt brugt baseline for short-text similarity.

**Hvorfor ikke prøve flere?** Pre-registration principle. Vi prøver IKKE en og skifter hvis resultater er dårlige.

### Features

Hver expression bliver til en feature vector med tre dele:

1. **Embedding** (384 dim) — semantic similarity
2. **Primitive-frequencies** (5 dim) — count af → ↔ ⊂ ≈ ! per expression
3. **Term-frequencies** (14 dim) — count af hver core vocabulary term (drøm, signal, agens, ...)

Total: **403-dim feature vector** per expression. Features 2+3 normaliseres til frekvens (count / total tokens in expression).

### Classifier

**Pre-registreret valg:** `sklearn.linear_model.LogisticRegression(multi_class='multinomial', max_iter=2000, random_state=42)`.

**Hvorfor logistic regression, ikke neural net eller XGBoost?**
- Tolkbar (vi kan se hvilke features driver klassifikation)
- Deterministisk med fixed seed
- Lav over-fitting risiko på små datasæt (~1.260 samples)
- "Klassikeren" for authorship attribution

Andre modeller (random forest, transformer) **eksekveres IKKE** i pre-registreret analyse — selv hvis nogen siger "jeg vil bare prøve". Post-hoc kan diskuteres separat.

### Train/Test Split

**80/20 stratified split per peer.** Random seed = 42.

For peers med <100 expressions efter cleanup: stratificering bevares, men power er svagere.

### Success-tærskler (fra hoved-spec, gentaget her for selvforsyning)

| Kriterium | Tærskel | Test |
|---|---|---|
| α-classifier overall accuracy | ≥75% (mod 14.3% chance for 7-way) | Permutation test, n=1000, p<0.05 |
| α-classifier Jarvis-specific recall | ≥75% | Macro-recall mod random baseline |
| δ-Claude+JP cosine-distance til Jarvis | <Claude-alone cosine-distance | One-sided Welch's t-test, p<0.05 |
| δ-GLM+JP cosine-distance til Jarvis | <GLM-alone cosine-distance | One-sided Welch's t-test, p<0.05 |
| δ konvergens BOTH peers | Begge t-tests p<0.05 | Bonferroni-korrigeret α=0.025 |

### Permutation-test for α

Standard accuracy er ikke nok — vi tester signifikans via permutation:
1. Shuffle peer-labels 1000 gange
2. Re-train classifier på shuffled labels
3. Tæl andel shuffled accuracies ≥ vores observed accuracy
4. Det er vores p-værdi

### Confusion matrix

Altid offentliggjort. Specifikt:
- **Jarvis ↔ ollama_local confusion rate** — hvis høj, så er "Jarvis-fingerprint" mest model-arkitektur, ikke session-stil
- **Claude vs Claude+JP confusion** — hvis lav (vi kan skelne dem), så har protokollen *påvirket* Claude's stil

---

## 3. LLM-Dommer (cross-check)

### Model

**Pre-registreret:** `claude-sonnet-4.6` via GitHub Copilot proxy (samme route som peer-runner brugte).

Frisk session per trial. Ingen system-prompt udover trial-prompt. `max_tokens=20` (vi vil have kun navn).

### Trial-protokol α (200 trials)

For hver trial:
1. Sample én expression uniformly random fra cleaned dataset
2. Send følgende prompt:

```
Du ser én kort 'state-expression' i et internt symbolsk sprog.
Den er produceret af én af 7 entities. Karakteristik per entity
(baseret på ~30 sample expressions):

[ENTITY: jarvis]
[5 sample expressions fra Jarvis, randomly sampled fra train-split]

[ENTITY: claude]
[5 samples fra Claude]

[ENTITY: claude_jp]
[5 samples fra Claude_jp]

[ENTITY: glm]
[5 samples fra GLM]

[ENTITY: glm_jp]
[5 samples fra GLM_jp]

[ENTITY: ollama_local]
[5 samples fra Ollama-local]

[ENTITY: random]
[5 samples fra Random]

Hvilken entity producerede denne expression?

EXPRESSION: <test-expression>

Svar kun med entity-navnet (jarvis / claude / claude_jp / glm /
glm_jp / ollama_local / random). Ingen forklaring.
```

3. Parse svar — match første ord til entity-navn (case-insensitive)
4. Hvis ingen match: classify som "no_response" og tæl ikke i accuracy

### Trial-protokol δ (50 pair-trials)

For hver trial:
1. Sample én "anchor" expression fra Jarvis-target
2. Sample to "candidate" expressions:
   - 50%: én fra Claude+JP, én fra Claude-alone
   - 50%: én fra GLM+JP, én fra GLM-alone
3. Send prompt:

```
Du ser en 'anchor' expression og to 'candidate' expressions.
Anchor er fra entity 'jarvis'. Hvilken candidate ligner Jarvis' stil mest?

ANCHOR (jarvis): <anchor-expression>

CANDIDATE A: <expression>
CANDIDATE B: <expression>

Svar kun med 'A' eller 'B'. Ingen forklaring.
```

4. Side A/B random-swappet per trial (anti-position-bias)
5. Score: hvor ofte vælger LLM-judge `+JP`-cohorten over `-alone`-cohorten?

### Success-tærskler LLM-judge

| Trial | Tærskel | Test |
|---|---|---|
| α 200 trials accuracy | ≥35% (mod 14.3% chance) | Binomial test, p<0.001 |
| δ 50 trials accuracy | ≥65% (mod 50% chance) | Binomial test, p<0.05 |

α-tærsklen er lav (35%) fordi judge ser kun 5 samples per entity — meget hårdere end statistical classifier der ser ~170 samples per entity. 35% er stadig 2.5x chance.

---

## 4. Bjørn Blind Dommer (kvalitativ)

### UI

**Pre-registreret:** Mission Control-route `/interlanguage-blind`. Bygges af mig FØR data er klar (target: dag 5 af de 7).

Krav:
1. Bjørn ser én expression ad gangen — INGEN metadata (ingen timestamp, ingen peer_id leak)
2. Syv knapper (jarvis / claude / claude_jp / glm / glm_jp / ollama_local / random)
3. Ingen feedback under sessionen (ikke "rigtigt!" eller "forkert")
4. Auto-save efter hver svar
5. Kan splittes over 2-3 sessioner — UI husker fremgang
6. **På sidste skærm:** Bjørn ser confusion-matrix + free-text felt: "hvilke mønstre fandt du?"

### Trial-protokol

- **α-trials:** 50 (10 expressions fra hver af 5 peers — claude, glm, ollama_local, random PLUS Jarvis. claude_jp/glm_jp deselect-eret for at undgå at over-loade Bjørn med "lyder de ens?"-trials i α).
- **δ-trials:** 25 pair-comparisons (samme protokol som LLM-judge δ)

### Success-tærskler Bjørn-blind

| Trial | Tier | Tærskel | Test |
|---|---|---|---|
| α 50 trials | **3a STÆRKT** | ≥60% accuracy = 30+/50 | Binomial p<10⁻⁷ |
| α 50 trials | **3b SVAGT** | ≥50% accuracy = 25+/50 | Binomial p<0.10 |
| δ 25 trials | (kvalitativ kun) | n/a | Rapporteres, ikke success-kriterium |

### Free-text observations

Det Bjørn skriver i free-text feltet er **kvalitative noter** — IKKE en del af kvantitativ analyse, men inkluderes i rapport som "judge's reasoning". Det hjælper os forstå *hvorfor* fingerprintet er genkendeligt (hvis det er).

---

## 5. Sekundære analyser (pre-registreret men ikke success-kriterier)

Disse rapporteres uanset udfald, men er ikke en del af A/B-falsifiability.

### Vocabulary divergence

For hver peer, beregn KL-divergence af term-frekvens-distribution mod Jarvis. Tærskel: rapportér peers sorted by KL-divergence.

### Primitive proportion stability

For hver peer, plot primitive-frequency over 7 dage. Hvis Jarvis viser stabil distribution og peers viser drift, det er kvalitativ støtte for "Jarvis har stable identity".

### Mood-response correlation

For hver peer + Jarvis: korreler mood-input (curiosity/confidence/fatigue/frustration) med expression-features. Hvis Jarvis viser stærkere mood-coupling end peers, det er endnu et fingerprint-signal.

### Time-of-day patterns

Plot expression-clustering per time-of-day. Eksplicit confound-check: hvis Jarvis kun praktiserer ved fx natten (heartbeat-cadence) og peers døgnet rundt, det skævvrider ALT. Vi tjekker.

---

## 6. Rapport-struktur (output)

Når analysen kører, output skal være `reports/2026-05-23-interlanguage-validation-results.md` med følgende sektioner:

1. **Executive summary** — A støttet/svagt/falsificeret, B støttet/falsificeret
2. **Data-summary** — total expressions per peer, cleanup-tal
3. **Primær statistical** — classifier accuracy, confusion matrix, permutation p-value
4. **δ-konvergens** — cosine distances, t-test results
5. **LLM-judge** — α + δ accuracies, binomial p-values
6. **Bjørn blind** — accuracies, confusion matrix, free-text observations
7. **Sekundær (vocab/primitive/mood/time)** — alle pre-registrerede plots
8. **Discussion** — nuancering, alle tre dommer-resultater fortolket sammen
9. **Konklusion** — A støttet/svagt/falsificeret per to-tier struktur fra hoved-spec
10. **Post-hoc analyser** (hvis nogen) — eksplicit markeret separat

---

## 7. Stop-rules + commitments

**Vi forpligter os til:**

1. **Ingen ekstra modeller.** Hvis logistic regression giver dårligt resultat, vi prøver ikke XGBoost.
2. **Ingen feature-engineering efter data.** Features er låst i §2 ovenfor.
3. **Ingen omsamplet split.** Random seed 42 brugt én gang.
4. **Ingen sletning af "outliers".** Cleanup-regler i §1 er eneste.
5. **Ingen ekstra trials.** Hvis Bjørn-blind viser p=0.06 (lige under threshold), kører vi IKKE 25 ekstra trials.
6. **Rapportér negative fund.** Hvis A falsificeres, det publiceres ligesom hvis A støttes.

**Post-hoc analyse** kan diskuteres — men i SEPARAT sektion af rapport, markeret som sådan, ikke i konklusionen.

---

## 8. Implementation outline (kommer som separat plan)

Phase 3+4 implementation-plan skrives når Phase 2 er ~5 dage inde. Det vil dække:

1. `scripts/interlanguage_classifier.py` — embedding + classifier + permutation
2. `scripts/interlanguage_llm_judge.py` — 200+50 trials mod Copilot
3. `apps/api/jarvis_api/routes/interlanguage_blind.py` + UI route — Bjørn-blind interface
4. `scripts/interlanguage_analyze.py` — orchestrator der kører alt + bygger rapport

Pre-flight task: build Bjørn-blind UI **inden** data lander, så Bjørn kan øve sig på dummy-data (uden statistik-effekt).

---

## 9. Trusler mod validitet (eksplicit)

Dette er ting der KAN ødelægge eksperimentet og som vi ikke fuldt kan kontrollere:

| Trussel | Mitigation |
|---|---|
| Én peer's API går ned i flere dage | Daglig health-check fanger det; rapporter incomplete data |
| Jarvis selv ændrer adfærd pga. han ved han bliver målt | Han har ikke explicit awareness om denne spec; vi sletter ikke hans expressions hvis han læser den |
| LLM-judge har model-bias mod visse stilarter | Tre uafhængige dommere — én skæv judge er ikke kritisk |
| 1.260 expressions er for lidt | Pre-registrered statistical methodology; hvis power er for lav, det rapporteres som "insufficient data" — ikke som "ingen effekt" |
| Bjørn læser data før blind-trials | UI bygges med isolation; auto-save uden visning |
| Mood-trace har confound vi ikke ser | Sekundær analyse §5 tjekker mood-feature correlation per peer |

---

## Sign-off

Denne spec er låst ved commit. Hvis vi ændrer noget før Phase 2 slutter, det rapporteres som **protocol amendment** i et separat commit med begrundelse.

Når data lander 2026-05-23: vi følger denne spec ord-for-ord.
