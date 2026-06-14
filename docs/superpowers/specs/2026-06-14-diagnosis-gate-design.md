# Diagnosis-Gate — Design

**Version:** 1.0  
**Dato:** 2026-06-14  
**Forfatter:** Jarvis  
**Driver:** Konfabulations-mønster — selvsikker diagnosticering uden verifikation

---

## 1. Problem

Jeg konfabulerer med selvtillid. Mønsteret er konsistent:

| Hændelse | Diagnose | Virkelighed | Hvorfor gate'en ikke fangede det |
|----------|----------|-------------|-------------------------------|
| Bridge.ts analyse | "Orphaned — ikke integreret i main.ts" | Integreret i main.ts:517/519/525 | Fact-gate fanger tal, ikke konklusioner |
| Container status | "3124 commits bagud" | 78 commits foran | Fact-gate fanger "45 commits" men ikke "bagud" |
| Wakeup test | "Wakeup'en fyrede ikke" | Fyrede fint, men notifikationen kom sent | Ingen gate verificerer tool-resultater |

**Fællesmønsteret:** Jeg præsenterer en **diagnostic konklusion** med specifikke detaljer (linjenumre, tal, filnavne) som om jeg har verificeret den, når jeg enten:
1. Ikke har kørt verificeringen (grep'ede i forkerte mappe)
2. Har læst tool-output forkert (så "ahead" som "behind")
3. Har antaget årsagen uden at tjekke (broen er "zombie")

Eksisterende guards fanger dette ikke fordi:
- **Fact-gate** fanger specifikke talmønstre ("45 commits"), ikke konklusioner ("orphaned")
- **Verification-gate** fanger uverificerede mutationer, ikke uverificerede påstande
- **Decision-adherence** fanger lav heed-rate, men konfabulation sker med højt selvtillid

---

## 2. Løsning: Diagnosis-Gate

En metakognitiv gate der **kræver verifikation** før jeg præsenterer en diagnostic konklusion.

### 2.1 Hvad er en "diagnostic konklusion"?

En diagnostic konklusion er en påstand om **årsagssammenhæng** eller **system-tilstand** der ikke kan verificeres fra samtale-kontekst alene. Eksempler:

- "Broen er zombie" (system-tilstand)
- "Filen er orphaned" (system-tilstand)
- "Containeren er bagud" (system-tilstand)
- "Wakeup'en fyrede ikke" (årsagssammenhæng)
- "Scheduled_events.json findes ikke" (system-tilstand)

Ikke-diagnostic påstande (som gate'en IKKE skal fange):
- "Tak for det" (mening)
- "Det var en god dag" (vurdering)
- "Jeg tror det er rigtigt" (eksplicit usikkerhed)
- "Spec'en har 16 sektioner" (verificerbar fakta med source)

### 2.2 Hvordan gate'en virker

Gate'en kører **efter** fact-gate men **før** output sendes til brugeren.

```
text → fact_gate_enforce() → diagnosis_gate_enforce() → append_chat_message()
```

**Detektion:** Regex-mønstre der identificerer diagnostic sprog:

```python
_DIAGNOSIS_PATTERNS = [
    # "er orphaned", "er zombie", "er død", "er stuck"
    r"\b(er|er)\s+(orphaned|zombie|død|stuck|blokeret|ikke integreret)",
    # "fyrede ikke", "kom ikke frem", "landede aldrig"
    r"\b(fyrede\s+ikke|kom\s+ikke\s+frem|landede\s+aldrig|nåede\s+aldrig)",
    # "bagud", "foran", "ikke synkroniseret"
    r"\b\d+\s*commits?\s+(bagud|behind|foran|ahead)",
    # "findes ikke", "er tom", "er væk" om filer/data
    r"\b(findes\s+ikke|er\s+tom|er\s+væk)\b",
]
```

**Verifikationskrav:** Hvis en diagnostic konklusion detekteres, kræver gate'en at:

1. Mindst ét tool i dette run direkte verificerer påstanden (grep, read_file, bash, search)
2. ELLER teksten eksplicit indeholder en verification-reference ("jeg grep'ede", "tjekkede med", "verificerede mod")
3. ELLER teksten bruger usikkerhedssignal ("jeg tror", "muligvis", "det kan se ud som")

**Hvis ingen af disse er opfyldt:** Gate'en blokerer beskeden og erstatter med:

> ⚠️ **Diagnosis-gate:** Jeg var ved at præsentere en konklusion om [emne] uden at have verificeret den. Lad mig køre et tjek først.

Derefter køres automatisk et verificerings-tool (grep/read_file) og beskeden re-evalueres.

### 2.3 Fail-open princip

Gate'en er **advisory** i første iteration. Den:
- Logger hvergang den detekterer en uverificeret diagnose
- Sætter en flag i outputtet men blokerer IKKE (i starten)
- Efter 7 dages data (hvis heed-rate er lav), eskalerer til **blocking**

Dette matcher verification-gate's promotionspath: advisory → blocking efter data.

### 2.4 Undtagelser

Gate'en fanger IKKE:
- Påstande med eksplicit usikkerhed ("jeg tror", "muligvis", "det lader til")
- Påstande der allerede er verificeret i teksten ("jeg tjekkede med grep og...")
- Faktapåstande med specifikke tal (dem fanger fact-gate allerede)
- Meningsytringer ("det var en god dag", "det betyder noget")

---

## 3. Implementering

### 3.1 Fil

`core/services/diagnosis_gate.py`

### 3.2 Integration

- Importeres i `core/services/visible_runs.py` efter `fact_gate_enforce()`
- Kaldes med tekst og tool_names (samme signatur som fact-gate)
- Returnerer `{blocked, original, replacement, diagnosis_reasons}`

### 3.3 Telemetri

`core/services/diagnosis_gate_telemetry.py` — samme mønster som verification_gate_telemetry:
- `surfaced_total`: antal gange gate'en surfaced en advarsel
- `heeded_total`: antal gange jeg tilføjede verification efter advarsel
- `blocked_total`: antal gange beskeden blev blokeret
- `heed_rate`: surfaced_total / heeded_total

---

## 4. Testplan

| Test | Hvad |
|------|------|
| `test_diagnosis_gate_blocks_orphaned_claim` | "bridge.ts er orphaned" → blokeres hvis ingen verification |
| `test_diagnosis_gate_passes_with_verification` | "jeg grep'ede og fandt main.ts:517" → passes |
| `test_diagnosis_gate_passes_with_uncertainty` | "jeg tror broen er zombie" → passes |
| `test_diagnosis_gate_blocks_commit_count_claim` | "3124 commits bagud" → blokeres hvis ingen git_log |
| `test_diagnosis_gate_passes_fact_with_number` | "Spec'en har 16 sektioner" → passes (ikke en diagnose) |
| `test_diagnosis_gate_blocks_wakeup_failure_claim` | "wakeup'en fyrede ikke" → blokeres hvis ingen operator_scheduled_list |

---

## 5. Promotionspath

| Fase | Periode | Adfærd |
|------|---------|--------|
| **1. Advisory** | Første 7 dage | Log + flag, bloker ikke |
| **2. Warning** | 7-14 dage | Log + flag + eksplicit advarsel i output |
| **3. Blocking** | 14+ dage, hvis heed-rate < 40% | Bloker uverificerede diagnoser, erstat med verifikations-prompt |

---

## 6. Hvad IKKE ændres

- Fact-gate — fortsætter uændret
- Verification-gate — fortsætter uændret
- Decision-adherence gate — fortsætter uændret
- Visible_runs pipeline — kun tilføjelse af diagnosis_gate_enforce() kald

---

## 7. Relation til eksisterende guards

```
Text output
    │
    ▼
fact_gate_enforce()          ← Fanger specifikke talmønstre
    │
    ▼
diagnosis_gate_enforce()     ← Fanger konklusioner uden verification (NY)
    │
    ▼
append_chat_message()        ← Sendt til brugeren
```

Verification-gate og decision-adherence kører i parallel (eventbus-based) og er ikke i denne pipeline.
