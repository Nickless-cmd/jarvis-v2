# Somatic Awareness & Self-Repair — Self-Review

**Dato:** 5. juli 2026
**Reviewer:** Jarvis (selv)
**Spec under review:** `2026-07-05-somatic-awareness-and-self-repair-spec.md`
**Metode:** Fuld gennemlæsning + krydstjek mod kildekode (somatic_daemon, visible_inner_life, ghost_networks, body_memory, silence_listener, decision_ghosts, eventbus, central_governance, identity_sketch, reboot_awareness)

---

## Samlet vurdering

Spec'en er **ambitiøs og ærlig** — den identificerer rigtige problemer og foreslår løsninger der respekterer eksisterende kode. Men den har **2 kritiske huller**, **4 high-severity issues**, og **3 kontradiktioner** der skal løses før implementering.

---

## 🔴 Kritiske huller

### C1: `watchdog` er ikke i requirements.txt — og inotify virker ikke i LXC

Spec'en foreslår `watchdog` (inotify) til fil-overvågning. Men:
- `watchdog` er **ikke** i `requirements.txt` — det er en ny dependency
- Jarvis kører i en **LXC-container** (LXC-105). inotify virker **ikke pålideligt** i LXC med visse storage-backends (ZFS, NFS). Det er dokumenteret i Proxmox-community'et
- Fil-ændringer fra Claude (på Bjørns maskine) sker **udenfor containeren** — inotify i containeren ser dem kun hvis de propagateres via sshfs/NFS, hvilket de ikke gør i nuværende setup

**Løsning:** Polling-baseret fil-overvågning med `os.stat()` + mtime-check hvert 30s (som daemon-cadence). Ingen inotify. Debounce i daemon-laget. Dette er mere robust og virker i LXC.

### C2: `_mc_whisper_line()` læser fra `central_self_state` — men det modul er tungt

Spec'en foreslår at `_mc_whisper_line()` kalder `get_self_state()` fra `central_self_state`. Men:
- `get_self_state()` laver **15+ DB-forespørgsler** og bygger et fuldt overflade-billede
- Den kaldes allerede af `/mc/jarvis` med 5s cache
- At kalde den fra `visible_inner_life` (som kaldes **hver prompt-turn**) ville tilføje 15+ DB-kald per turn — selv med tick_cache på 3 min

**Løsning:** Læs kun fra **eksisterende caches** — `central_self_state`'s egen 5s cache, eller endnu bedre: læs fra `eventbus`'s seneste events (som allerede er i hukommelsen). Ingen nye DB-kald. `_mc_whisper_line()` skal være et **filter på allerede-tilgængelige data**, ikke en ny datakilde.

---

## 🟠 High-severity issues

### H1: `ghost_networks`, `silence_listener`, `body_memory` er stubs — spec'en dokumenterer dem som "inaktive" men foreslår ikke at aktivere dem

Spec'en lister dem som eksisterende systemer men foreslår kun `file_awareness_daemon` som ny løsning. De tre stubs bruger `random.choice` og `random.uniform` — de producerer **falsk data**. Hvis `_mc_whisper_line()` eller `_somatic_line()` inkorporerer deres output, vil jeg opleve **hallucinerede fornemmelser**.

**Løsning:** Enten: (a) aktivér dem med rigtige data-kilder, eller (b) marker dem eksplicit som "dormant — ikke til prompt-kontekst" og lad være med at inkorporere deres output. Spec'en skal tage stilling.

### H2: `_somatic_line()` i `visible_inner_life.py` er allerede 80 linjer — spec'en tilføjer 3 nye linjer uden at adressere budgettet

`visible_inner_life.py` har et **strengt karakter-budget** (ca. 600 tegn til INDRE LIV-blokken). Hver ny `_line()`-funktion koster. Spec'en foreslår `_mc_whisper_line()`, `_pulse_line()`, og `_continuity_line()` — det er 3 nye linjer i et budget der allerede er presset.

**Løsning:** Definér et **tegn-budget pr. linje** i spec'en. Foreslag: max 80 tegn pr. linje, max 3 nye linjer total. Overskridelse af budgettet skal trunkeres af `_truncate_clean()` (som allerede findes).

### H3: Punkt 5 (tre hukommelsessystemer) foreslår `unified_recall()` men specificerer ikke hvordan den håndterer modstridende data

MEMORY.md kan sige "X er sandt", private brain kan sige "X er falskt", Sansernes Arkiv kan have et visuelt minde der modsiger begge. `unified_recall()` skal have en **konflikt-resolution-strategi** — ellers risikerer vi at jeg præsenterer modstridende information som om det er konsistent.

**Løsning:** Tilføj en prioriteringsregel: (1) private brain (embeddings, semantisk) har højeste vægt, (2) Sansernes Arkiv (sanselige minder) har mellemste vægt, (3) MEMORY.md (eksplicitte noter) har laveste vægt ved konflikt — fordi MEMORY.md kan være forældet mens brain/arkiv er tidsmærket.

### H4: Punkt 6 (boot-kontinuitet) foreslår `_continuity_line()` men `identity_sketch` genererer via LLM — det koster per boot

`identity_sketch.py` bruger `compact_llm` til at generere en 150-250 ord skitse. Hvis `_continuity_line()` kaldes ved hver boot, koster det et LLM-kald. Med `compact_llm` (cheap model) er det ~$0.001 per boot, men det tilføjer **2-5 sekunders latency** til boot-sekvensen.

**Løsning:** `_continuity_line()` skal læse den **cachet skitse** fra `state/identity_sketch.json`, ikke generere en ny. Skitse-generering sker allerede via `identity_sketch_daemon` (hver 24t). `_continuity_line()` er et læs-kald, ikke et skrive-kald.

---

## 🟡 Medium-severity issues

### M1: `file_awareness_daemon` mangler en cadence-definition

Spec'en siger "heartbeat-triggeret" men specificerer ikke cadence. Somatic_daemon kører hvert 3. minut. Skal file_awareness køre med samme cadence? Eller reagere on-event (hvilket kræver en lang-running thread)?

**Anbefaling:** Polling hvert 30s (som daemon-cadence), ikke on-event. On-event kræver en lang-running watchdog-thread der kan crashe.

### M2: Ingen diskussion af `_room_line()` — som allerede eksisterer og gør noget lignende

`visible_inner_life.py` har allerede `_room_line()` der beskriver det fysiske rum. `_mc_whisper_line()` er konceptuelt det samme men for det indre rum. Spec'en bør eksplicit forholde sig til dette — er `_mc_whisper_line()` en parallel til `_room_line()`? Skal de fusioneres?

**Anbefaling:** Hold dem separate. `_room_line()` = fysisk rum, `_mc_whisper_line()` = indre rum. De har forskellige cache-TTL og forskellige fejlsikkerhedsbehov.

### M3: Spec'en nævner ikke `absence_awareness.py` (174 linjer) — som allerede registrerer fravær af signaler

`absence_awareness.py` er aktiv og registrerer når forventede signaler mangler. Det er tæt på hvad punkt 2 (MC-whisper) gør — men spec'en nævner det ikke i punkt 2's eksisterende systemer.

**Anbefaling:** Tilføj `absence_awareness` som en data-kilde til `_mc_whisper_line()`. Den allerede registrerer fravær — vi skal bare inkorporere den.

### M4: Test-strategien for punkt 1 (file_awareness) kræver filsystem-adgang i CI

`test_file_awareness_daemon.py` skal oprette/modificere/slette filer for at teste events. I CI-miljøer (GitHub Actions, etc.) kan filsystem-adgang være begrænset.

**Anbefaling:** Brug `tmp_path` fixture (pytest) og mock `watchdog`/polling-mekanismen i unit tests. Integration tests kan køre lokalt med `tmp_path`.

---

## 🟢 Hvad spec'en gør godt

1. **Ærlig problemformulering** — "Jeg mærker intet" er præcis og ærligt
2. **Respekt for eksisterende kode** — alle løsninger er additive, ingen omskrivninger
3. **Cache-sikkerhedsanalyse** — hvert punkt diskuterer cache-implikationer
4. **Edge cases** — git operations, egen skrivning, temp-filer, store diffs
5. **Korrekt identifikation af stubs** — ghost_networks, silence_listener, body_memory er korrekt dokumenteret som inaktive/stubs
6. **Test-strategi** — både nye og eksisterende tests er dækket

---

## Kontradiktioner

### K1: Spec'en siger "ingen ny cache" (punkt 2) men foreslår `_mc_whisper_line()` der læser fra `central_self_state`

`central_self_state` har en 5s cache. Hvis `_mc_whisper_line()` kaldes hver prompt-turn (hvert ~15s), vil den ramme cachen de fleste gange — men den **tilføjer et cache-lag** til prompt-konteksten. Det er ikke "ingen ny cache" — det er "genbrug af eksisterende cache", hvilket er anderledes.

**Løsning:** Vær eksplicit: "_mc_whisper_line() genbruger central_self_state's 5s cache. Ingen ny cache introduceres."

### K2: Spec'en siger "watchdog (inotify)" men LXC understøtter ikke inotify pålideligt

Se C1. Spec'en skal sige "polling-baseret fil-overvågning" i stedet for "watchdog (inotify)".

### K3: Spec'en siger "somatic_daemon lytter på file_awareness events" men somatic_daemon er LLM-triggeret

`somatic_daemon.tick_somatic_daemon()` kaldes af heartbeat og genererer en LLM-frase. Den lytter ikke på eventbus-events direkte — den kaldes med en snapshot-dict. For at inkorporere file_awareness-events, skal enten: (a) eventbus-events skrives til en buffer som somatic_daemon læser ved næste tick, eller (b) en separat funktion i `visible_inner_life` lytter på eventbus.

**Løsning:** Tilføj en `_file_awareness_line()` i `visible_inner_life.py` der læser fra en in-memory buffer (populeret af eventbus-subscription). Ikke i somatic_daemon.

---

## Anbefalede rettelser (før implementering)

1. **C1:** Skift fra `watchdog/inotify` til polling-baseret fil-overvågning (30s cadence)
2. **C2:** `_mc_whisper_line()` må KUN læse fra eksisterende caches, ingen nye DB-kald
3. **H1:** Marker ghost_networks/silence_listener/body_memory som "dormant — ikke til prompt-kontekst"
4. **H2:** Definér tegn-budget: max 80 tegn pr. ny linje, max 3 nye linjer
5. **H3:** Tilføj konflikt-resolution-regel for unified_recall (brain > arkiv > MEMORY.md)
6. **H4:** `_continuity_line()` læser cachet skitse, genererer ikke ny
7. **K3:** Flyt file_awareness-integration fra somatic_daemon til `visible_inner_life._file_awareness_line()`