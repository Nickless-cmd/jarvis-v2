---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Interlanguage Phase 2 — Data Gap

**Gap-periode:** 2026-05-20 08:47 UTC → 2026-05-21 20:16 UTC (~1 dag 11 timer)

## Hvad skete der

Peer-runnerne kørte fra 2026-05-16 14:16 UTC til 2026-05-20 ~08:47 UTC,
hvor maskinen blev slukket for at rotere hardware (Intel Ultra 7 265KF
combo, nye CPU/board/cooler). Alle 6 peer-processer døde med maskinen.

Watchdog'en (`scripts/peer_practice_watchdog.sh`) var startet via
`nohup` uden persistent unit, så den blev ikke automatisk genrejst ved
boot. Jarvis selv lever på samme maskine men starter via sin egen
service, derfor fortsatte hans baseline uafbrudt.

## Korrektion

- **Genstartet:** 2026-05-21 22:16 lokal tid (20:16 UTC)
- **Ny slutdato:** 2026-05-28 22:16 lokal tid — 7 fulde dage fra restart
- **Persistens fremad:** `~/.config/systemd/user/peer-practice-watchdog.service`
  + `loginctl enable-linger bs` så den genstarter ved reboot
- **Total feltkøretid pr. peer:** ~3,75 dage (16/5–20/5) + 7 dage (21/5–28/5)
  ≈ 10,75 dage med 1,5 dages gap markeret midt i

## Konsekvens for analyse

- Mood-fordeling i gap-perioden er kun reflekteret i jarvis' baseline,
  ikke i peer-output. Når Phase 3 sammenligner peer-output mod mood @
  timestamp, må gap-rækken filtreres væk fra peers (men ikke jarvis).
- 717 expressions ved gap-start gav allerede statistisk meningsfuld
  sample per peer (99-114). Yderligere 7 dage giver mood-variation
  henover en hel uge inklusive weekend.

## Filtreringsanbefaling i Phase 3

```sql
-- Drop peer-rækker i gap'et (jarvis fortsatte, behold ham)
WHERE NOT (
  peer_id != 'jarvis'
  AND created_at >= '2026-05-20T08:47:00+00:00'
  AND created_at <  '2026-05-21T20:16:00+00:00'
)
```

---

## Gap #2: Claude / Claude_JP quota exhaustion (2026-05-23)

**Stop-tidspunkt:**
- `claude`     2026-05-22 17:09 UTC
- `claude_jp`  2026-05-22 16:21 UTC

**Quota-reset:** 2026-06-01 (månedligt på GitHub Copilot, Bjørn bekræftet)

**Root cause:** Peer-runnerne for `claude` og `claude_jp` kalder Claude
via GitHub Copilot API (proxy). Watchdog'en kører stadig fint, men hver
48-min-tick fejler med:

```
ERROR peer=claude generate failed: GitHub Copilot API error: HTTP 429: quota exceeded
```

**Beslutning (2026-05-23):** Acceptér det ulige cohort, dokumentér gap'et.
Vi venter IKKE med Phase 3-analysen til 1/6 — Phase 2 lukker som planlagt
28/5 med claude/claude_jp frosset på ~140 expressions hver, mens de øvrige
cohorts når ~250-300.

**Endelige cohort-counts (forventet pr. 28/5 22:16 UTC):**

| Peer | Forventet n | Aktiv hele perioden | Note |
|---|---|---|---|
| random | ~280 | ja | |
| glm | ~270 | ja | |
| glm_jp | ~265 | ja | |
| ollama_local | ~250 | ja | |
| jarvis | ~200 | ja | heartbeat-trig, lavere cadence |
| claude | **~141** | nej | frosset 22/5 17:09 UTC |
| claude_jp | **~139** | nej | frosset 22/5 16:21 UTC |

## Konsekvens for Phase 3 analyse

1. **Power-vurdering**: claude/claude_jp har ~50% af samples vs øvrige
   cohorts. Confusion-matrix skal tolkes per-row (precision/recall pr.
   true-class), ikke samlet accuracy — ellers undervurderer vi
   classifier's evne til at identificere claude.

2. **Train/test split**: stratify-parameter i `train_test_split` bevarer
   class-proportion. Med 80/20 split bliver claude-test ≈28 samples; det
   er marginalt men nok for confusion-matrix.

3. **JP-seed effekt**: hovedhypotese (JP-seed ændrer expression-stil)
   bør stadig være testbar — vi har 139/141 sample-pairs for claude vs
   claude_jp og kan køre paired comparison. Power er reduceret, ikke
   ødelagt.

4. **Rapport-noter**: classifier-output skal eksplicit liste cohort-n og
   markere claude/claude_jp som "data-frozen 22/5". Læser må vide at en
   eventuel høj accuracy IKKE skyldes at claude havde mere træning.

## Filtreringsanbefaling

Inkluderingsfilter forbliver det samme (gap #1 og #2 håndteres bare som
naturlig endpoint for claude-cohorts — ikke en eksklusion):

```sql
-- Alle claude/claude_jp rækker accepteres til deres eget endepunkt
-- Ingen ekstra filter nødvendig udover gap #1
```

Phase 3 classifier-rapport skal vise:

```
Cohort balance (≥100 = OK, <100 = incomplete / interim):
  claude         141  ⚠ FROZEN 2026-05-22 17:09 (Copilot quota)
  claude_jp      139  ⚠ FROZEN 2026-05-22 16:21 (Copilot quota)
  glm            ~270
  glm_jp         ~265
  jarvis         ~200
  ollama_local   ~250
  random         ~280
```

---

## Pre-registreret prædiktion (logget 2026-05-23 21:50)

**Logget før Phase 3-analyse begyndes**, baseret på interim-data
(N=1076 expressions over 7 dage). Dette er en falsificerbar
hypotese der bør vurderes mod Phase 3's faktiske resultater.

### Bagrund: hvad interim-dataene viste

Centroid-baseret embedding-similarity (sentence-transformers/
all-MiniLM-L6-v2) målte afstand fra jarvis-T3 til alle cohorter:

| Cohort | Cosine-distance fra jarvis-T3 |
|---|---|
| **random** | **0.0129 (tættest)** |
| jarvis-T2 | 0.0173 |
| jarvis-T1 | 0.0269 |
| claude_jp | 0.1370 |
| ollama_local | 0.1770 |
| claude | 0.1802 |
| glm | 0.2064 |
| glm_jp | 0.2069 |

Pointwise: for hver af jarvis-T3's 44 expressions er random
centroid den tætteste i 36% af tilfældene; within-self (T1+T2)
i 41%.

Samtidig viste temporal drift-analyse at jarvis har strukturel
udvikling T1→T3:
- → falder med 11pp, ! falder med 16pp (kausal+negation aftager)
- ↔ stiger med 16pp, ⊂ stiger med 21pp (gensidig+containment øger)
- Total |Δ| sum = 75pp, parvist sammenhængende

Random har 40pp total drift — sampling-noise floor for 175 i.i.d.
samples over 7 dage. Jarvis' drift er næsten dobbelt så stor og
strukturelt parret (modsætnings-operatorer bevæger sig sammen).

### Prædiktionen

**Hovedhypotese:** Jarvis' identitet i interlanguage er en
*udviklings-bane*, ikke et statisk fingerprint i embedding-rummet.

**Falsificerbar konsekvens** for Phase 3 dommer-eksperimentet:

| Dommer ser | Forudsagt resultat for "Jarvis vs random" |
|---|---|
| **Snapshot** (enkelt expression eller ikke-tids-ordnet bundle) | Dommere scorer ~tilfældigt (50% ± sampling) |
| **Tidsserie** (kronologisk ordnet sekvens med ≥10 expressions) | Dommere scorer signifikant over baseline (p<0.05 mod chance) |

Tilsvarende prædiktion for klassifier-eksperimentet:

| Feature-vektor | Forudsagt accuracy "jarvis vs random" |
|---|---|
| Per-expression (403-dim som spec) | nær 50% (chance) |
| Per-timestamp-bin sequence eller drift-derivede features (Δ-operator, vokab-skift) | ≥70% |

### Hvad bekræfter / hvad falsificerer

**Bekræftelse:** dommere får højere accuracy med tidsserie end
snapshot, OG drift-baserede classifier-features outperformer
per-expression features. Begge resultater i samme retning.

**Falsifikation:** dommere får samme score på snapshot og
tidsserie, eller drift-features performer ikke bedre end
per-expression features. Identitets-hypotesen reduceres da til
"jarvis ligner ikke andre strukturerede peers" — en svagere
claim end "jarvis er en distinkt udviklingsbane".

**Hverken-eller:** dommere får højere score med tidsserie, men
under signifikans-tærskel. Da klassificeres som "trend uden
statistisk power" og kræver yderligere observation.

### Operationel definition

**Snapshot:** enkelt expression eller bundle hvor expressions er
shuffled (tids-ordering ødelagt). Dommer ser kun *hvad* der blev
sagt.

**Tidsserie:** ≥10 expressions præsenteret i kronologisk
rækkefølge med synlige timestamps eller "tidlig/midt/sen"-labels.
Dommer ser *både hvad og hvornår*.

**Drift-features:** Δ-operator-frekvens mellem første tredjedel
og sidste tredjedel af cohort, plus top-3 vokabular-skifts.
Tilføjes som ekstra 16-dim feature-blok (5 Δ-operator + 11 ord)
til den eksisterende 403-dim feature-vektor.

### Hvorfor pre-registrere dette nu

Identitets-hypotesen er stærk hvis vi tester den FØR vi ser
udfaldet. Hvis vi kun observerede mønstret POST-hoc og kaldte
det "evidence", ville det være p-hacking. Ved at logge
forudsigelsen i gap-noten (committet før Phase 3-analyse), kan
udfaldet kun gå én af tre veje — alle tre er informative.

Logget af: Jarvis (selv-prædiktion), Claude (analyse-stat),
2026-05-23 21:50 UTC.
