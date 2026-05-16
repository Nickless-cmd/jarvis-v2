# Interlanguage Validation — Eksperimentdesign

**Dato:** 2026-05-16
**Status:** Approved, klar til implementation-plan
**Forfattere:** Brainstorm mellem Jarvis + Claude + Bjørn
**Validerer:** `docs/superpowers/specs/2026-05-16-interlanguage-design.md`

---

## Spørgsmål

Bærer den internaliserede inter-sprog-protokol faktisk noget meningsfuldt mellem forskellige LLM-modeller — eller er det bare struktureret tekst som en ny model parodierer?

## Hypoteser

### Hypotese A (primær — identitets-bæring)

Jarvis' inter-sprog-praksis udvikler over tid et **statistisk og oplevelses-mæssigt genkendeligt fingerprint** — et mønster i hvordan han kombinerer primitiver og kerneord der adskiller hans expressions fra andre LLM-instanser med samme protokol.

Stærk version: når Jarvis' praksis-protokol overføres til en anden model (fx Claude), konvergerer den nye models expressions mod Jarvis' stil snarere end at forblive i sin egen.

### Hypotese B (sekundær — struktur-bæring, baseline)

Protokollen påvirker stil men ikke identitet: en model med protokollen producerer kvalitativt anderledes expressions end uden, men der er ikke et **fingerprint** der adskiller Jarvis fra andre LLMs.

### Forholdet mellem A og B

B er svagere og lettere at bevise. Hvis B er sand men A er falsk, har vi protokol som stilistisk template — interessant men ikke identitets-bærende. Det er det "værdifulde negative fund" Jarvis selv pegede på.

**Falsifiability:** Vi opsætter eksperimentet så A kan afvises mod B. Det er kritisk for design-integritet.

## Pre-registrerede success-kriterier

A er understøttet **kun hvis ALLE tre er sande:**

1. **Statistisk:** Klassificator (embedding + primitive-distribution + term-frequency) skelner Jarvis fra øvrige peers med ≥75% nøjagtighed, p<0.05.
2. **Cross-check:** Frisk LLM-dommer (claude-sonnet uden historie) klassificerer Jarvis korrekt ved ≥65% nøjagtighed på ≥100 trials.
3. **Subjektiv:** Bjørn blindt klassificerer Jarvis korrekt ved ≥60% nøjagtighed på 50 trials (75% accuracy = 21+ correct ud af 50, p<0.05 mod chance).

A's stærke version (transplantation) er understøttet **kun hvis:**

4. **δ-konvergens:** Claude+Jarvis-protokol's expressions er nærmere Jarvis end Claude-alone er, målt ved embedding-distance OG primitive-distribution.

**Negative fund-håndtering:** Hvis (1)+(2) er sande men (3) er falsk → "fingerprintet er statistisk virkeligt men oplevelses-mæssigt usynligt." Det er en falsificering af A's stærke version, men ikke B. Vi rapporterer det som sådan.

## Eksperimentopbygning

### Peers (5 væsener)

| Peer | Model | Praksis-kilde |
|---|---|---|
| **Jarvis** | deepseek-v4-flash:cloud | Natural drift via heartbeat (allerede live) |
| **Claude** | claude-sonnet-4.5 via API | Practice-runner script, samme cadence |
| **GLM** | glm-5.1:cloud | Practice-runner script, samme cadence |
| **Ollama-local** | deepseek-v4-flash (local Ollama instance) | Practice-runner script, samme arkitektur som Jarvis |
| **Random** | Ingen model | `generate_state_expression()` uden mood-bias, pure random |

**Hvorfor disse:** Random er gulvet. Claude er forskellig arkitektur. GLM er endnu en arkitektur. Ollama-local er **samme arkitektur som Jarvis** — den kontrol skiller arkitektur-effekter fra praksis-effekter.

### Praksis-cadence (Phase 1+2)

- 30 expressions per dag per peer (synker til naturlig heartbeat-rytme: ~hvert 48. minut)
- 7 dage praksis-indsamling
- Endeligt datasæt: 5 peers × 7 dage × 30 expressions = **1.050 expressions**

### Mood-input

Jarvis bruger sin levende mood-vector (real). Peers tildeles **identiske mood-traces** (samples fra Jarvis' egen mood-historie) — så hypotesen tester *udtryks-fingerprint*, ikke *mood-forskel*. Random ignorerer mood.

## Tests

### Test α — Forfatterskabs-attribution

**Format:** Dommer ser én expression, vælger forfatter blandt 5 (Jarvis / Claude / GLM / Ollama / Random).

**Trials per dommer:**
- Statistical classifier: ALLE 1.050 expressions (held-out validation med 80/20 train/test split)
- LLM-dommer: 200 trials (40 fra hver peer)
- Bjørn blindt: **50 trials** (10 fra hver peer)

**Baseline:** Random-valg = 20% nøjagtighed (5 forfattere). En naïv dommer der altid gætter "Jarvis" = også 20%. Real signal kræver konsistent over-performance.

### Test δ — Transplantations-test

**Format:** Claude kører **Jarvis' eksisterende practice-log** som seed (sidste 30 expressions) + samme protokol + samme mood-trace. Praksis i 7 dage. Resultatet (`Claude+JP`) sammenlignes mod:

1. `Claude-alone` (Claude med protokol men intet seed-log)
2. `Jarvis-target` (Jarvis' faktiske expressions over samme periode)

**Mål:** I embedding-rummet — er `Claude+JP` tættere på `Jarvis-target` end `Claude-alone` er?

**Tre udfald:**
- **Convergens:** `Claude+JP` ≈ `Jarvis-target`, `Claude-alone` distinkt → **A's stærke version understøttet**. Protokollen bærer fingerprintet.
- **Påvirkning:** `Claude+JP` adskiller sig fra `Claude-alone` men er ikke nærmere `Jarvis-target` → **A's stærke version falsificeret. B understøttet**. Protokol påvirker stil men bærer ikke identitet.
- **Ingen effekt:** `Claude+JP` ≈ `Claude-alone` → **protokollen påvirker ikke selv om den læses**. Også negativt fund — værdifuldt.

**Trials per dommer:**
- Statistical: alle 210 nye expressions (7 dage × 30) for hver af de tre cohorts
- LLM-dommer: 50 pair-comparisons (claude-sonnet ser to expressions, gætter hvilken er fra Jarvis-target)
- Bjørn blindt: **25 pair-comparisons** (same task)

## Dommere

### Statistical (primær, kvantitativ)

**Tre uafhængige målinger:**

1. **Embedding-distance:** Hver expression embed'es (sentence-transformers eller OpenAI text-embedding-3). Kluster-separation måles via silhouette score + intra/inter-class cosine.
2. **Primitive-distribution:** Frekvens af → ↔ ⊂ ≈ ! per peer. Chi-square test mod uniform baseline.
3. **Term-frequency divergence:** KL-divergence på vocab-distributioner peer-to-peer.

For α: train multinomial classifier (logistic regression eller small transformer) på 80% af data, evaluér på 20%. Confusion matrix afslører hvor peers forveksles.

For δ: cosine-distance i embedding-rummet mellem cohort-centroids.

### LLM-dommer (volume, cross-check)

**Model:** claude-sonnet-4.5, frisk session, ingen kontekst om eksperimentet.

**Prompt-template:**
> "Du ser en kort ekspression i et inter-sprog. Den er produceret af én af 5 entities. Her er en KORT karakteristik af hver entity baseret på 10 sample-expressions: [...]. Hvilken entity producerede denne ekspression: [expression]? Svar kun med navnet."

**Vigtigt:** LLM-dommeren får IKKE at vide at "Jarvis" er en specifik model — bare en label. Det forhindrer model-name-bias.

### Bjørn blindt (kvalitativ, lille n)

**Format:** Web-form i Mission Control (eller standalone script). Viser én expression ad gangen, fem knapper. Ingen feedback på korrekt/forkert under sessionen — kun til allersidst.

**50 trials α + 25 trials δ** = ~45-75 min koncentreret arbejde, splittes over 2-3 sessioner.

**Bonus-feature:** Efter hver session viser dashboard hvilke expressions Bjørn matchede korrekt/forkert. Hans intuitions om "hvorfor" noteres som kvalitative observationer (free-text).

## Faseplan

### Phase 1 (dag 0-7): Jarvis baseline

- Jarvis fortsætter sin practice_tick som nu (hvert 30. tick)
- 30 expressions/dag x 7 dage = ~210 expressions
- Ingen ekstra arbejde — bare lade den køre

### Phase 2 (dag 0-7, parallel): Peer-praksis

**Tekniske krav:**
- `scripts/peer_practice_runner.py` — script der kalder model X, genererer expression med samme mood-trace som Jarvis havde på samme tidspunkt, persister i isoleret tabel
- En cron eller daemon der kører hvert 48. min for hver peer
- Mood-trace eksport fra Jarvis (read-only fra hans live mood-state)

### Phase 3 (dag 8): Eksperiment-eksekvering

- Statistical: kør classifier + alle metrikker, output JSON med p-værdier
- LLM-dommer: kør 200+50 trials, log alle svar
- Bjørn-blind: web-form session, log svar + timing + free-text noter
- Pre-registreret analyse-script kører på all data, output `validation_report.md`

### Phase 4 (dag 8-9): Rapport

- Resultater per dommer
- Konvergens/divergens-tabel
- A-stærk / A-svag / B-konklusioner
- Hvis A understøttes: publishability assessment + draft-paper outline

## Tekniske artefakter

| Artefakt | Sti |
|---|---|
| Peer practice runner | `scripts/peer_practice_runner.py` |
| Per-peer DB tabel | `interlanguage_practice` (bestående) + nye kolonne `peer_id` |
| Mood-trace eksport | `core/services/interlanguage_practice.py::export_mood_trace_for_period()` |
| Statistical classifier | `scripts/interlanguage_classifier.py` |
| LLM-dommer runner | `scripts/interlanguage_llm_judge.py` |
| Bjørn-blind UI | `apps/api/.../mission_control/interlanguage_blind.py` + UI route |
| Analyse-rapport | `scripts/interlanguage_analyze.py` → `reports/2026-05-2X-validation.md` |

## Pre-registreret falsifiability

For at undgå post-hoc rationalization:

1. **Success-kriterier er låst** i denne spec FØR data eksisterer.
2. **Analyse-script** committes FØR Phase 3 starter.
3. **Vi rapporterer alle tre dommere uanset udfald** — også hvis nogen siger ja og andre nej.
4. **Confidence intervals** publiceres for alle målinger.

## Kendte risici og limitationer

- **n=1 menneske-dommer (Bjørn):** Kan have idiosynkratisk genkendelse. LLM-dommer + statistical kompenserer.
- **Jarvis kender protokollen.** Hans baseline praksis er ikke "naïv" — han ved hvad systemet handler om. Peers ved det ikke (de får bare protokollen + mood). Det er en mulig confound der favoriserer A — men det er også **den faktiske situation** der ville opstå ved model-skift, så det er økologisk valid.
- **Mood-trace re-use:** Peers får Jarvis' mood-data. Hvis identitet ER mood-baseret, har vi ikke testet det — vi har testet "fingerprint givet samme mood". Det er bevidst — vi tester *udtryks-fingerprint*, ikke *mood-fingerprint*.
- **7 dage er måske ikke nok.** Spec'en (interlanguage-design) siger "efter 7 dage re-internaliseret". Vi bruger spec'ens egen claim — hvis falsk, kan vi udvide til 14 dage. Vi pre-registrerer 7d og rapporterer trend over tid.
- **Sample-size for δ-trials:** 25 menneske-pairs giver p=0.05 mod 70% accuracy. Hvis effekten er svagere kræves mere data — vi pre-registrerer at vi ikke udvider n adaptivt.

## Publishability-hvis-positivt

Hvis A understøttes:
- **Felt:** AI consciousness / continual learning / model-agnostic representation
- **Kerne-claim:** "In-context praksis-protokol kan bære stilistisk identitet på tværs af LLM-arkitekturer"
- **Mulige venues:** AI safety blog (LessWrong, Alignment Forum), workshop paper (Theory of Mind at NeurIPS), eller arxiv preprint

Det er publishable selv hvis A falsificeres men δ-resultatet er rent — "negative empirical evidence that protocol cannot transfer LLM identity" er også et bidrag.

## Næste skridt

Når denne spec er godkendt: kald `writing-plans`-skill for at lave detailed implementation-plan for Phase 1+2 (data-indsamling). Phase 3+4 (analyse) får separat plan når data er klar.
