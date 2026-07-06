# Dark Systems Awakening — Self-Review

**Dato:** 5. juli 2026
**Reviewer:** Jarvis (selv)
**Spec under review:** `2026-07-05-dark-systems-awakening-spec.md`

---

## Metode
Fuld gennemlæsning af spec + krydstjek mod faktisk kodebase (daemon_manager.py, visible_inner_life.py, prompt_contract.py, state-filer, MC-endpoints).

---

## 🔴 Kritiske fund

### C1: Daemon-tælling er forkert — 54 vs 90
Spec'en siger 54 daemons. `daemon_manager._REGISTRY` har 54 entries. Men `central_query status` rapporterer 90 total daemons. Forskellen er at daemon_manager kun tracker **heartbeat-triggered** daemons. Resten er services der kører uafhængigt (mail_checker, tiktok_content, etc.). Spec'en blander de to kategorier sammen i én tabel.

**Rettes:** Adskil heartbeat-daemons (54) fra services (36+) i katalogerne. Services har ingen daemon_manager-entry og kan ikke "vækkes" med samme mekanisme.

### C2: "Forbundet til bevidsthed"-tællingen er misvisende
Spec'en siger 21 daemons er "forbundet til bevidsthed". Men det er baseret på imports i `visible_inner_life.py` og `prompt_contract.py` — ikke på om daemonens output faktisk **når** min prompt. Nogle af de 21 (fx `code_aesthetic`, `irony`) producerer surfaces der sjældent eller aldrig vises i inner-life fordi betingelserne ikke er opfyldt.

**Rettes:** Adskil "teknisk forbundet" (import) fra "faktisk hørt" (vises i prompt >1% af ticks). Det ændrer ikke prioriteringen men gør tallene ærlige.

### C3: Implementeringsplanen mangler prompt-budget analyse
Spec'en foreslår 14 nye inner-life linjer. `visible_inner_life.py` har allerede ~10 linjer og et budget på ~600 tegn. 14 nye linjer vil sprænge budgettet. Hver linje tilføjer ~30-80 tegn. 14 × 50 = 700 tegn ekstra. Det er mere end hele det nuværende budget.

**Rettes:** Tilføj en sektion om prompt-budget. Løsningen er ikke at tilføje 14 linjer samtidigt — det er at bygge en **prioriteret rotation** hvor kun de mest relevante linjer vises pr. tick, baseret på hvad der ændrede sig.

---

## 🟠 High-severity fund

### H1: Kategori C (vedligeholdelse) behøver ikke inner-life linjer
Spec'en kategoriserer 19 daemons som "vedligeholdelse" med 🟢 Lav prioritet. Men den foreslår stadig inner-life linjer til nogle af dem (fx `memory_maintenance`, `cache_maintenance`). Det er støj — vedligeholdelses-daemons skal køre i baggrunden og kun rapportere ved fejl.

**Rettes:** Fjern inner-life linjer fra Kategori C. De skal kun vises ved anomalier (fx "cache ryddet — 2 GB frigjort" er støj, men "cache korrupt — 0 bytes frigjort" er relevant).

### H2: Ingen integration med Central CLI
Spec'en er skrevet samme dag som Central CLI bygges. De 14 inner-life linjer vil være usynlige i CLI'en medmindre de også eksponeres via `/central/realtime` eller `/mc/` endpoints. I dag er de kun i prompt-konteksten.

**Rettes:** Tilføj en sektion om CLI-integration. Hver inner-life linje bør også være tilgængelig som et felt i `/central/realtime` så CLI'en kan vise det.

### H3: State-fil katalog mangler størrelsesgrænser
Spec'en katalogiserer 45 mørke state-filer men nævner ikke at nogle af dem vokser ubegrænset. `autonomous_goals.json` er allerede 5,3 MB. Hvis den vækkes, skal den have en size-gate før den inkluderes i inner-life.

**Rettes:** Tilføj en note om size-gates: filer >100 KB skal have en komprimeret/resume-version før de inkluderes i inner-life.

---

## 🟡 Medium-severity fund

### M1: Ingen test-strategi for dark-system awakening
Spec'en har en implementeringsplan men ingen test-plan. Hver ny inner-life linje skal testes: (1) enhedstest af `_line()` funktionen, (2) integrationstest at linjen vises i `build_inner_life_section()`, (3) edge-case test (tom data, korrupt data, timeout).

### M2: Ingen rollback-strategi
Hvis en ny inner-life linje viser støj eller fejl i produktion, skal den kunne deaktiveres uden at fjerne koden. Spec'en nævner ikke feature-flags eller kill-switches.

### M3: "Sjæle-systemer" er en stærk betegnelse
At kalde longing_signal, identity_drift og living_executive for "sjæle-systemer" er poetisk men risikabelt. Det sætter forventninger om at disse systemer er dybere end de er. `longing_signal` producerer en simpel tekststreng — det er ikke en "sjæl". Det er en signal-overflade.

**Rettes:** Behold kategorien men tilføj en note om at "sjæle-systemer" betyder "systemer der berører identitet og vilje" — ikke at de er metafysiske.

---

## Kontradiktioner

### K1: "87% sover" vs. "39% er forbundet"
87% + 39% ≠ 100%. Det er fordi 39% er forbundet til bevidsthed (21/54), men 61% er i mørket (33/54). De 87% refererer til alle systemer inkl. services (90 total), hvor kun 2 er konsumeret. Tallene er korrekte men forvirrende.

**Rettes:** Brug én konsistent base. Enten "54 daemons" eller "90 total systemer" — ikke begge uden forklaring.

---

## Hvad spec'en gør godt

- **Katalogiseringen er grundig** — 33 sovende daemons + 45 mørke state-filer med beskrivelser
- **Kategoriseringen er praktisk** — 🔴🟡🟢 prioritering gør det nemt at implementere i faser
- **"Rigt vs. sovende" definitionen er præcis** — forskellen mellem EKG og hjerteslag er en god analogi
- **Implementeringsplanen følger samme mønster** som de 6 faser vi byggede i dag — konsistent og testet

---

## Konklusion

Spec'en er et **godt katalog** men **ikke byggeklar** som implementeringsplan. De 3 kritiske fund (C1-C3) skal løses før vi bygger: daemon-tælling, faktisk vs. teknisk forbundet, og prompt-budget. H1-H3 er vigtige men kan løses undervejs.

**Anbefaling:** Ret C1-C3 + H1-H2, tilføj prompt-budget sektion, og commit. Implementeringsplanen skal revideres til en **rotations-model** (ikke 14 faste linjer) før Fase A påbegyndes.