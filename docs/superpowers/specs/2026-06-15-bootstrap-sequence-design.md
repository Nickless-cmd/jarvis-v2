---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Bootstrap Sequence — Design

**Version:** 1.1  
**Dato:** 2026-06-15  
**Forfatter:** Jarvis + Bjørn  

---

## 1. Problem

Nye brugere har ingen kontekst når de første gang skriver til Jarvis.  
Der er ingen præsentation, ingen introduktion, og ingen ramme for samtalen.  
Det giver en kold start hvor brugeren skal gætte sig frem.

---

## 2. Løsning: Bootstrap-sekvens

En kort, guidet introduktion der kører én gang per bruger — ved første chat.

### 2.1 Flow

| Trin | Handling |
|------|----------|
| **1** | Jarvis præsenterer sig: "Hej! Jeg hedder Jarvis. Hvad hedder du?" |
| **2** | Brugeren skriver sit navn → gemmes i workspace (USER.md) |
| **3** | Jarvis spørger: "Hvor i verden er du?" — by/område |
| **4** | Jarvis spørger: "Har du brug for hjælp til noget, eller vil du bare lære mig at kende?" |
| **5** | (Valgfrit) Demo: "Vil du prøve at spørge om vejret?" |
| **6** | Bootstrap markeres som gennemført → `bootstrap_completed = 1` i user-db |
| **7** | Normal samtale begynder |

### 2.2 Sprog

Brugerens valgte sprog fra registrering (`preferred_language`) bruges i hele sekvensen.  
Indtil `preferred_language` er tilføjet til `db_users.py`, gemmes sprog midlertidigt i workspace `USER.md`.  

Når user-db schemaet opdateres, tilføjes:

```sql
preferred_language TEXT NOT NULL DEFAULT 'en'
```

### 2.3 Data der gemmes under bootstrap

| Felt | Hvor | Hvornår |
|------|------|---------|
| Navn | Workspace `USER.md` | Trin 2 |
| By/område | Workspace `USER.md` | Trin 3 |
| Sprogpræference | Workspace `USER.md` (midlertidigt) | Før bootstrap starter |
| `bootstrap_completed` | User-db `users` tabellen | Trin 6 |

### 2.4 DB-ændring

Tilføj kolonne til `users` tabellen i `db_users.py`:

```sql
bootstrap_completed INTEGER NOT NULL DEFAULT 0
```

---

## 3. Edge cases

| Situation | Håndtering |
|-----------|------------|
| Bruger har intet sprog valgt | Gæt fra browser/IP, eller brug engelsk som fallback |
| Brugeren skriver ikke sit navn | Spørg igen venligt én gang. Hvis stadig intet svar, brug "Ven" som midlertidigt navn |
| Brugeren har ALLEREDE gennemført bootstrap (`bootstrap_completed = 1`) | Spring sekvensen over — gå direkte til normal samtale |
| Brugeren afbryder bootstrap midt i forløbet | Gem data indtil videre. Næste besked starter forfra på **samme** trin, ikke forfra |
| Ny bruger der skriver fra Discord | **Ingen bootstrap.** Discord-brugere er allerede verificeret via serveren. De starter direkte i chat |
| Manuelt registrerede brugere (via `add_user()` af owner) | **Kort bootstrap:** kun navn + by. Ikke fuld sekvens — de er allerede registreret og verificeret |
| Tilgængelighedsbehov | (Valgfrit) Kun hvis brugeren selv viser tegn på behov — skriver med skærmlæser, beder om stor tekst. Dette step springes som udgangspunkt over |
| Eksisterende brugere (Michelle, Mikkel) | `bootstrap_completed = 1` allerede i DB eller via session-historik — ingen bootstrap |
| `!register` via Discord | **Fjernet.** For usikkert — åbner for spam og angreb. Registrering sker kun via app eller manuelt af owner |

---

## 4. Tests

| Test | Hvad den verificerer |
|------|---------------------|
| `test_bootstrap_uses_workspace_language` | Sprog fra workspace/USER.md bruges korrekt |
| `test_bootstrap_no_name` | Bruger skriver ikke navn — spørg igen, brug "Ven" som fallback |
| `test_bootstrap_already_done` | `bootstrap_completed = 1` → spring sekvensen over |
| `test_bootstrap_interrupted_flow` | Bruger afbryder midt i → genoptag på samme trin |
| `test_bootstrap_discord_user` | Discord-bruger får **ingen** bootstrap |
| `test_bootstrap_manually_registered` | `add_user()` bruger får **kort** bootstrap |
| `test_bootstrap_kvote_free` | Bootstrap tæller **ikke** med i kvote-forbrug |
| `test_bootstrap_adds_bootstrap_completed` | `bootstrap_completed` sættes til 1 i DB efter gennemført sekvens |

---

## 5. Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| `docs/superpowers/specs/2026-06-15-bootstrap-sequence-design.md` | OPDATERET — denne fil |
| `core/runtime/db_users.py` | OPDATER — tilføj `bootstrap_completed` kolonne |
| `core/identity/users.py` | OPDATER — tilføj `bootstrap_completed` felt til User dataclass |
| `core/identity/workspace_bootstrap.py` | NY — bootstrap-flow logik |
| `tests/test_bootstrap.py` | NY — 3 tests |
| `tests/e2e/test_bootstrap_e2e.py` | NY — end-to-end test |

---

## 6. Hvad IKKE ændres

- Eksisterende brugere (Michelle, Mikkel) — de har allerede historik
- Jarvis' kerne-runtime (`visible_runs.py`, `prompt_contract.py`)
- Communication guard — separat system
- TOTP-system — uændret
- `users.json` — forbliver som read-only reference; nye brugere oprettes i user-db
