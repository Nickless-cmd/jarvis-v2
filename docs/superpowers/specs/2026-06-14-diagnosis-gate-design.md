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

**Fællesmønsteret:** Jeg præsenterer en **diagnostisk konklusion** med specifikke detaljer (linjenumre, tal, filnavne) som om jeg har verificeret den, når jeg enten:

1. Ikke har kørt verificeringen (grep'ede i forkerte mappe)
2. Har læst tool-output forkert (så "ahead" som "behind")
3. Har antaget årsagen uden at tjekke (broen er "zombie")

Eksisterende guards fanger dette ikke fordi:

- **Fact-gate** fanger specifikke talmønstre ("45 commits"), ikke konklusioner ("orphaned")
- **Verification-gate** fanger uverificerede mutationer, ikke uverificerede påstande
- **Decision-adherence** fanger lav heed-rate, men konfabulation sker med højt selvtillid

---

## 2. Løsning: Diagnosis-Gate

En metakognitiv gate der **kræver verifikation** før jeg præsenterer en diagnostisk konklusion.

### 2.1 Hvad er en "diagnostisk konklusion"?

En diagnostisk konklusion er en påstand om **årsagssammenhæng** eller **system-tilstand** der ikke kan verificeres fra samtale-kontekst alene.

Eksempler:

- "Broen er zombie" (system-tilstand)
- "Filen er orphaned" (system-tilstand)
- "Containeren er bagud" (system-tilstand)
- "Wakeup'en fyrede ikke" (årsagssammenhæng)
- "Scheduled_events.json findes ikke" (system-tilstand)

Ikke-diagnostiske påstande (som gate'en IKKE skal fange):

- "Tak for det" (mening)
- "Det var en god dag" (vurdering)
- "Jeg tror det er rigtigt" (eksplicit usikkerhed)
- "Spec'en har 16 sektioner" (verificerbar fakta med source)

### 2.2 Hvordan gate'en virker

Gate'en kører **efter** fact-gate men **før** output sendes til brugeren.

```
text → fact_gate_enforce() → diagnosis_gate_enforce() → append_chat_message()
```

**Detektion:** Regex-mønstre der identificerer diagnostisk sprog:

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

**Verifikationskrav:** Hvis en diagnostisk konklusion detekteres, kræver gate'en at:

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

- Usikkerheds-signaler ("jeg tror", "muligvis", "det virker som")
- Verificerbare fakta med source ("spec'en har 16 sektioner, jeg kan se sektion 4.1")
- Meninger og vurderinger ("det var en god dag")

---

## 3. Implementation

### 3.1 Filstruktur

| Fil | Handling |
|-----|----------|
| `core/services/diagnosis_gate.py` | NY — hovedmodul med detektion og verifikation |
| `tests/test_diagnosis_gate.py` | NY — unit tests |

### 3.2 Integration

Diagnosis-gate integreres i visible_runs.py's output-pipeline:

```python
# Efter fact_gate_enforce, før append_chat_message
from core.services.diagnosis_gate import diagnosis_gate_enforce

text = fact_gate_enforce(text, ...)
text = diagnosis_gate_enforce(text, session_id=..., run_id=...)
append_chat_message(session_id, "assistant", text)
```

### 3.3 Datastruktur

```python
@dataclass
class DiagnosisEvent:
    event_id: str           # UUID
    timestamp: datetime     # Hvornår det skete
    session_id: str         # Hvilken session
    run_id: str             # Hvilken run
    pattern_matched: str    # Hvilket regex-mønster
    claim_text: str         # Den fulde tekst der matchede
    verified: bool          # Blef den verificeret i samme run?
    verification_tool: Optional[str]  # Hvilket tool verificerede?
    blocked: bool          # Blef beskeden blokeret?
```

### 3.4 Testplan

| Test | Hvad |
|------|------|
| `test_diagnosis_pattern_orphaned` | "Filen er orphaned" → detekteres |
| `test_diagnosis_pattern_zombie` | "Broen er zombie" → detekteres |
| `test_diagnosis_pattern_commits_behind` | "3124 commits bagud" → detekteres |
| `test_diagnosis_pattern_not_fired` | "Wakeup'en fyrede ikke" → detekteres |
| `test_diagnosis_pattern_not_found` | "Findes ikke" → detekteres |
| `test_diagnosis_exempt_opinion` | "Jeg tror det er orphaned" → IKKE detekteres |
| `test_diagnosis_exempt_fact_with_source` | "Spec'en har 16 sektioner (se §4)" → IKKE detekteres |
| `test_diagnosis_exempt_meaning` | "Det var en god dag" → IKKE detekteres |

---

## 4. Promotionspath

| Periode | Adfærd | Log-level |
|---------|--------|-----------|
| **Første 7 dage** | Advisory — logger men blokerer ikke | WARNING |
| **Dag 8-14** | Warning — injecter nudge i output | WARNING |
| **Efter dag 14** | Blocking — blokerer output indtil verifikation er kørt | ERROR |

---

## 5. Relation til eksisterende guards

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

---

## 6. Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| `core/services/diagnosis_gate.py` | NY — hovedmodul |
| `core/services/visible_runs.py` | OPDATER — tilføj diagnosis_gate_enforce() kald |
| `tests/test_diagnosis_gate.py` | NY — unit tests |

---

## 7. Hvad IKKE ændres

- Fact-gate — separat system, ingen overlap
- Verification-gate — fanger mutationer, ikke konklusioner
- Decision-adherence — fanger heed-rate, ikke konklusioner
- Visible_runs pipeline — kun tilføjelse af diagnosis_gate_enforce() kald

---

## 8. Fase 2: Promise-ledger — løfte-hukommelse og completion-verifikation

### 8.1 Problem

Jeg bryder løfter. Mønsteret:

1. Jeg siger: "Jeg committer den nu" → intet commit
2. Jeg siger: "Spec'en er skrevet" → filen eksisterer ikke
3. Jeg siger: "Det er verificeret" → ingen verify_file_contents blev kørt

Eksisterende guards fanger dette ikke fordi:

- **Fact-gate** fanger tal, ikke løfter
- **Verification-gate** fanger uverificerede mutationer, ikke ufuldførte løfter
- **Diagnosis-gate** fanger konklusioner, ikke løfter

### 8.2 Løsning

En **promise-ledger** der husker hvad jeg lover, og verificerer completion når jeg senere påstår at have gjort det.

Flow:

```
Jeg siger: "Jeg committer den nu"
    → promise-ledger gemmer: {promise: "commit", timestamp: ..., session: ..., file: "diagnosis-gate-design.md"}
    → Senere: "Den er committed"
    → claim scanner fanger påstanden
    → tjekker promise-ledger → fandt løfte
    → tjekker git log → intet commit fundet
    → injecter nudge: "Du sagde 'jeg committer den nu' [timestamp]. Git log viser ingen ny commit for diagnosis-gate-design.md. Følg op."
```

Ikke spam — kun når jeg **aktivt påstår** noget der modsiger et tidligere løfte.

### 8.3 Forskel fra diagnosis-gate

| | Diagnosis-gate | Promise-ledger |
|---|---|---|
| **Fanger** | Uverificerede konklusioner | Brudte løfter |
| **Trigger** | "Bridge.ts er orphaned" | "Jeg committer den nu" → ikke committet |
| **Tidspunkt** | Før output | Efter påstand om completion |
| **Data** | Tool-resultater vs. konklusion | Promise-ledger vs. git-log/fil-system |

### 8.4 Detektion af løfter

Regex-mønstre der identificerer løfter:

```python
_PROMISE_PATTERNS = [
    # "Jeg committer/ligger/skriver/opsætter nu"
    r"\b(jeg\s+)?(committer|ligger|skriver|opsætter|pusher|deployer|genererer|bygger)\s+(nu|snart|ligemefter)",

    # "Det er klaret/gjort/færdigt/committet"
    r"\b(er\s+)?(klaret|gjort|færdigt|committet|deployet|pushet|opdateret)\b",

    # "Jeg verificerer/tjekker nu"
    r"\b(jeg\s+)?(verificerer|tjekker|checker|bekræfter)\s+(nu|ligemefter)",

    # "Lad mig X" → loved handling
    r"\b(lad\s+mig|jeg\s+(skal\s+)?vil\s+gerne)\s+\w+",
]
```

### 8.5 Verifikation af completion

Når et løfte registreres, oprettes en entry i promise-ledger:

```python
@dataclass
class Promise:
    promise_id: str           # UUID
    text: str                 # Original tekst
    timestamp: datetime       # Hvornår det blev sagt
    session_id: str           # Hvilken session
    verification_type: str    # "git_commit", "file_exists", "service_active", "tool_output"
    verification_target: str  # Hvad der skal verificeres (filnavn, service, etc.)
    status: str               # "pending", "completed", "broken", "expired"
    completed_at: Optional[datetime]
```

Verifikationstyper:

| Løfte-type | Verifikation | Tool |
|------------|-------------|------|
| "committer fil X" | `git log --oneline X` | bash |
| "skriver fil X" | `verify_file_contains(X, ...)` | verify_file_contains |
| "service kører" | `service_status(name)` | service_status |
| "opsætter X" | `find_files(X)` | find_files |
| "verificerer X" | Check om verify-file_contains blev kaldt | eventbus |

### 8.6 Promotionspath

Samme som diagnosis-gate:

| Periode | Adfærd | Log-level |
|---------|--------|-----------|
| **Første 7 dage** | Advisory — logger men blokerer ikke | WARNING |
| **Dag 8-14** | Warning — injecter nudge i output | WARNING |
| **Efter dag 14** | Blocking — blokerer output indtil verifikation er kørt | ERROR |

### 8.7 Filer

| Fil | Handling |
|-----|----------|
| `core/services/promise_ledger.py` | NY — promise-ledger + claim-scanner + completion-verifikation |
| `core/services/promise_ledger_store.py` | NY — SQLite-storage for promises |
| `tests/test_promise_ledger.py` | NY — unit tests |

### 8.8 Hvad IKKE ændres

- Diagnosis-gate — separat system, ingen overlap
- Fact-gate — fanger tal, ikke løfter
- Verification-gate — fanger uverificerede mutationer, ikke brudte løfter