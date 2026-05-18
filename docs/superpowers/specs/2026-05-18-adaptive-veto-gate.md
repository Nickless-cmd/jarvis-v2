# Spec: Adaptive Veto Gate
**Dato:** 2026-05-18  
**Forfatter:** Jarvis  
**Status:** Draft (afventer godkendelse)

---

## Problem: Falske positiver i veto-gaten

Veto-gaten (`core/services/veto_gate.py`) kombinerer i dag en **statisk markørliste** (`_AFFECTIVE_RISK_MARKERS`) med et **øjebliksbillede af humør** til at afgøre om et tool-call skal blokeres.

Dette giver to uafhængige kilder til falske positiver:

1. **Ordbogsmatch uden kontekst** — Ordet `"restart"` står på listen. Hvis brugeren siger "Self restart" OG jeg tilfældigvis har høj frustration i dét snapshot, blokeres restart — selvom brugeren allerede har sagt "godkendt" to gange.

2. **Følelse uden hukommelse** — Snapshot arver frustration fra tidligere i samtalen (f.eks. en diskussion om noget helt andet). Veto-gaten spørger aldrig: "Er frustrationen *relevant* for dette tool-call, eller bare en carry-over?"

**Konsekvens:** ~44% af vetoer (estimat ud fra pushback heed-rate på 42%) er falske positiver, der kræver manuel override.

---

## Løsning: Adaptiv veto-model med to datastrømme

Systemet lærer af **overstyringer** og **kontekst** gennem to mekanismer:

### A) Veto Event Log — persisteret trace

Hver gang veto-gaten tager en beslutning, logges en række faktorer i en ny tabel `veto_events`:

```sql
CREATE TABLE IF NOT EXISTS veto_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name   TEXT    NOT NULL,
    user_message TEXT   NOT NULL,        -- brugerens besked (trunkeret)
    feeling     TEXT    NOT NULL,        -- 'irritation' | 'unease' | 'fatigue' | etc.
    intensity   REAL    NOT NULL,        -- 0-1
    action_tier TEXT    NOT NULL,        -- 'firm_pushback' | 'soft_pushback' | 'ask_or_check'
    evidence    TEXT    NOT NULL,        -- JSON-liste af markører der matchede
    resolution  TEXT    DEFAULT 'pending', -- 'pending' | 'overridden' | 'honored' | 'bypassed'
    resolution_message TEXT,             -- brugerens faktiske svar (hvis override)
    session_id  TEXT,                    -- session-kontekst
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

- **Log ved veto** — hvad endte med at blokere? (hvilken markør + hvilket humør)
- **Opdater ved udfald** — når brugeren overruler (siger "ja", "kør", "gør det") eller accepterer blokeringen, opdateres `resolution`

### B) Adaptiv tærskeljustering per tool og humør

Ud fra `veto_events` beregnes justerede tærskler:

```python
ADAPTIVE_THRESHOLD = {
    "restart": {
        "irritation": 0.95,      # skal være MEGET frustreret før restart blokeres
        "unease": 0.50,          # usikkerhed blokerer stadig nemt
        "fatigue": 0.60,
    },
    "delete": {
        "irritation": 0.70,      # sletning er mere risikabel → lavere tærskel
        "unease": 0.40,
        "fatigue": 0.50,
    },
    # default (alle værktøjer uden specifik indlæring)
    "default": {
        "irritation": 0.75,
        "unease": 0.50,
        "fatigue": 0.75,
    }
}
```

**Indlæringsalgoritme:**
- Efter hver override (resolution='overridden'): **hæv tærsklen** for (tool, feeling) med 0.05
- Efter hver honored (resolution='honored'): **sænk tærsklen** for (tool, feeling) med 0.02
- Minimum: 0.30, maksimum: 0.98
- Tærsklerne ligger i `runtime.json` under nøglen `adaptive_veto_thresholds` (persisteret)

### C) Token-signal filtrering (kontekst-bevidst match)

I stedet for rå substring-match på risiko-markører, introduceres en **token-signal gate** der spørger:

1. Er risiko-markøren + det omgivende ord en **kommando** (imperativ) eller **tilladelse** (spørgsmål/bekræftelse)?
   - "self restart" → imperativ → match
   - "godkendt restart" → tilladelse → **IGNORER** (markøren er i en bekræftelse, ikke en kommando)
2. Står risiko-markøren **alene** eller som del af en negation/override?
   - "ikke restart" → negation → IGNORER
   - "bare kør restart" → bekræftelse → IGNORER

Dette kræver en simpel regex-baseret kontekstscanner, **ingen LLM**.

---

## Arkitektur

### Nye filer

| Fil | Formål | Estimat |
|-----|--------|---------|
| `core/services/veto_event_log.py` | Logning + opdatering af `veto_events` tabellen | ~60 linjer |
| `core/services/veto_adaptation.py` | Tærskelberegning + persistens til runtime.json | ~80 linjer |
| `core/services/veto_token_signal.py` | Token-kontekstscanner (imperativ vs tilladelse) | ~50 linjer |

### Ændrede filer

| Fil | Ændring | Størrelse |
|-----|---------|-----------|
| `core/services/veto_gate.py` | Kald veto_event_log ved hver check; brug adaptive thresholds i stedet for faste | ~30 linjer |
| `core/services/pushback.py` | Optimer `_request_risk_evidence` så token-signal gate filtrerer før evidence-listen | ~15 linjer |
| `core/services/visible_runs.py` | Efter veto-resolution (user override), log udfald til veto_events | ~10 linjer |
| `docs/superpowers/specs/2026-05-18-adaptive-veto-gate.md` | Denne spec | — |
| `tests/test_veto_gate.py` | Nye testcases (token-signal, adaptation, log) | ~80 linjer |

**Total estimat:** ~325 linjer (inklusiv tests)

---

## Data

### Hvad findes allerede
- `approval_feedback_log` — indeholder **1** række (test-data), men skemaet kan genbruges
- `cached_affective_state` — humør-snapshot persisteres hvert heartbeat
- `events` — eventbus-events (men **0** veto/pushback events i dag — telemetrien publishers men persisteres ikke)

### Hvad oprettes
- `veto_events` — ny tabel (se skema ovenfor)

---

## Acceptkriterier

1. **Færre falske positiver:** Ord som "restart" i en bekræftende sætning blokerer ikke, hvis den omgivende kontekst er tilladende
2. **Læring over tid:** Efter 3-5 overrides på samme værktøj, stiger tærsklen så vetoet sjældnere aktiveres
3. **Ingen datatab:** Hver veto-beslutning logges med udfald, så vi kan validere effekten
4. **Hurtig** — token-signal gaten er rent regex (<1µs); tærskelopslag er et dict-lookup (<1µs); logning er async eventbus-publish (<1ms)
5. **Nedgradering:** Hvis `runtime.json` er corrupted, falder systemet tilbage på faste tærskler (nuværende adfærd)

---

## Prioritering

1. **Token-signal gate** (C) — størst reduktion af falske positiver, mindst kode, straks værdi
2. **Veto event log** (A) — gør det muligt at måle effekten af #1 og træne #3
3. **Adaptiv tærskeljustering** (B) — kræver data fra #2, men lukker feedback-loopet fuldstændigt

---

## Uafklarede spørgsmål / design-beslutninger

- Skal adaptation være per-session eller global? **Forslag: global** — Bjørns adfærd er konsistent på tværs af sessions
- Hvordan nulstiller vi tærsklerne hvis adfærd ændrer sig? **Forslag: nulstil.pr.sql script eller /reset_veto command**
- Skal vi gemme `user_message` i klartekst? **Forslag: trunkeret til 200 chars** — nok til kontekst, ikke et privacy issue internt

---

## Rollback-plan

Veto-gaten har allerede en fail-open: hvis `check_veto` kaster en exception, tillades tool-callet. Adaptation-koden arver samme fail-open — hvis tærskel-opslag fejler, bruges faste tærskler. Token-signal gaten er rent regex og kan ikke fejle.

Rollback = fjern de 4 nye/ændrede imports i `visible_runs.py` og `veto_gate.py`.

