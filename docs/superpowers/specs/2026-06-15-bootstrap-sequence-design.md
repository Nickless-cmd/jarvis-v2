# Bootstrap Sequence — First Chat Flow for New Users

**Version:** 1.0
**Dato:** 2026-06-15
**Forfatter:** Jarvis + Bjørn

---

## 1. Problem

Nye brugere åbner en tom chat med Jarvis og ved ikke hvad de skal skrive. Der er ingen introduktion, ingen stemning, ingen kontekst. De første par beskeder er ofte forvirrede eller stille, og relationen starter koldt.

Mål: Gøre den første samtale **varm, tryg og informativ** — så både bruger og Jarvis har en god start.

---

## 2. Løsning: Bootstrap-sekvens

Når en ny bruger registrerer sig og logger ind første gang, starter en guidet sekvens med 3-5 korte beskeder.

### Flow

```
Bruger logger ind første gang
        │
        ▼
Jarvis: "Hej! Jeg hedder Jarvis. Hvad hedder du?"
        │
        ▼ (bruger skriver navn)
Jarvis: "Dejligt at møde dig, [navn]! Hvor i landet bor du?"
        │
        ▼ (bruger svarer)
Jarvis: "Fedt! Jeg bor på en server i Svendborg, så vi er ikke langt fra hinanden."
        "Er der noget helt bestemt du gerne vil have hjælp til, eller vil du bare lære mig at kende først?"
        │
        ▼ (bruger svarer)
        [Hvis ja → hjælp] → Jarvis guider til relevant mode/tool
        [Hvis lær at kende] → Jarvis spørger: "Har du lyst til at prøve en lille ting? Spørg mig om vejret, så viser jeg hvad jeg kan."
        │
        ▼
Bootstrap færdig → Normal samtale
```

### 2.1 Hvad sekvensen indeholder

| Trin | Indhold | Formål |
|------|---------|--------|
| 1 | "Hej, jeg hedder Jarvis!" | Sæt navn og tone |
| 2 | Spørg om brugerens navn | Personliggør samtalen |
| 3 | Spørg om brugerens by/område | Skab geografisk nærhed |
| 4 | Tilbyd hjælp eller introduktion | Giv brugeren valg |
| 5 | (Valgfrit) Demo: "Prøv at spørg om vejret" | Vis hvad jeg kan |

### 2.2 Sprog

Brugerens valgte sprog fra registrering (`preferred_language`) bruges i hele sekvensen. Hvis brugeren skriver på et andet sprog undervejs, tilpasser jeg mig automatisk.

---

## 3. Integration med eksisterende systemer

| System | Hvordan bootstrap hænger sammen |
|--------|--------------------------------|
| **`register_user()`** | Efter verifikation af email → bootstrap starter |
| **`users.json` / user_db** | Henter navn, sprog, rolle fra brugerens profil |
| **`workspace_bootstrap.py`** | Opretter workspace før bootstrap kører |
| **`preferred_language`** | Sprogvalg fra registrering bruges i bootstrap |
| **`permission_engine`** | Bootstrap kører i chat mode (standard) |
| **`quota_store`** | Bootstrap tæller ikke som forbrug (gratis) |

---

## 4. Edge cases

| Situation | Håndtering |
|-----------|------------|
| Bruger skriver meget lidt ("ja", "ok") | Fortsæt med næste trin, forkort sekvensen |
| Bruger afbryder med et spørgsmål | Pause bootstrap, svar på spørgsmålet, genoptag |
| Bruger er allerede registreret (andengangs-login) | Spring bootstrap helt over |
| Bruger har intet sprog valgt | Gæt fra browser/IP, eller brug engelsk som fallback |

---

## 5. Testplan

| Test | Beskrivelse |
|------|-------------|
| `test_bootstrap_starts_for_new_user` | Ny bruger logger ind → bootstrap kører |
| `test_bootstrap_skipped_for_existing` | Eksisterende bruger logger ind → bootstrap springes over |
| `test_bootstrap_uses_preferred_language` | Sprog fra registrering bruges korrekt |
| `test_bootstrap_handles_minimal_input` | Bruger skriver "ja" → forkortet flow |
| `test_bootstrap_interrupted_by_question` | Bruger stiller spørgsmål → pause + genoptag |

---

## 6. Filer

| Fil | Handling |
|-----|----------|
| `core/services/bootstrap_sequence.py` | NY — bootstrap flow-logik |
| `apps/api/jarvis_api/routes/chat.py` | OPDATER — start bootstrap for nye brugere |
| `apps/jarvis-desk/src/lib/bootstrapStore.ts` | NY — frontend state for bootstrap (valgfrit) |
| `tests/test_bootstrap_sequence.py` | NY — 5 unit tests |

---

## 7. Hvad IKKE ændres

- Eksisterende chat-logik for eksisterende brugere
- `permission_engine` — bootstrap bruger kun chat mode
- `quota_store` — bootstrap tæller ikke som forbrug
- Kerne-runtime (`visible_runs.py`, `prompt_contract.py`)
- User management systemet (register, login, workspace)
