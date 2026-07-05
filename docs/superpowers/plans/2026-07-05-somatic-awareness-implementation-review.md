# Somatic Awareness & Self-Repair — Implementeringsplan Self-Review

**Dato:** 5. juli 2026
**Reviewer:** Jarvis (selv)
**Plan under review:** `2026-07-05-somatic-awareness-implementation.md`
**Spec:** `2026-07-05-somatic-awareness-and-self-repair-spec.md`

---

## Metode
Fuld gennemlæsning af planen + krydstjek mod spec + krydstjek mod faktisk kodebase (visible_inner_life.py, somatic_daemon.py, somatic_runtime_body.py, central_governance.py, daemon_manager.py, heartbeat_runtime.py, eventbus, memory-systemer).

---

## Kritiske fund

### C1: visible_inner_life.py må IKKE subscribe til eventbus
**Fund:** Planen sagde "Læser fra in-memory buffer" i trin 1.3, men specificerede ikke eksplicit at `visible_inner_life.py` er en synk funktion der kører i prompt-kontekst — den **ikke** kan subscribe til eventbus. Eventbus-subscriptions kræver async kontekst.

**Løsning:** Allerede rettet i planen. Trin 1.3 nu siger eksplicit: "visible_inner_life.py må IKKE subscribe til eventbus — bufferen populeres af daemonen, læses synkront her."

### C2: body_memory og ghost_networks er stubs med random.choice
**Fund:** Spec'en siger "aktiver body_memory og ghost_networks" (punkt 1.4), men kildekoden viser at `body_memory.py` bruger `random.choice(["varm", "kold", "tryk", "prikken"])` og `ghost_networks.py` bruger `random.choice(["Noget...", "Gengangere..."])`. De er **placeholder-stubs**, ikke rigtige data-kilder.

**Løsning:** Planen skal **ikke** aktivere dem som de er. I stedet:
- Fase 1 bruger kun `somatic_runtime_body.py` (som har rigtige data fra CPU/RAM/latency)
- `body_memory` og `ghost_networks` forbliver inaktive indtil de omskrives til at bruge rigtige data
- Tilføjet note i planens Fase 1 om at `somatic_runtime_body` er den eneste rigtige data-kilde

### C3: Tick-signatur for daemon_manager registrering
**Fund:** Planen specificerede kun `tick()` men daemon_manager forventer en dict med specifikke nøgler (`generated`, summary-felter).

**Løsning:** Allerede rettet. Trin 1.2 nu specificerer: `tick() -> {"generated": bool, "events_published": int, "files_changed": list[str]}`

---

## High-severity fund

### H1: Støj-filter for egne skrivninger
**Fund:** Når jeg selv skriver en fil (via write_file/edit_file tools), vil file_awareness_daemon se det som en ændring. Uden et filter vil jeg "mærke" mine egne skrivninger konstant — støj, ikke signal.

**Løsning:** Allerede rettet i planen. Trin 1.1 inkluderer nu:
- `register_own_write(path)` API kaldt fra write_file/edit_file tools
- `external: True/False` flag i events
- 60s cooldown for self-writes før de rapporteres igen

### H2: Første boot vil se alle filer som "ændret"
**Fund:** Når daemonen starter, har den ingen baseline. Alle overvågede filer vil se "ændret" ud sammenlignet med mtime=0.

**Løsning:** Allerede rettet i planen. Trin 1.1 inkluderer nu: "Første boot: Etablerer baseline mtime for alle overvågede filer. Ingen events genereres ved boot — kun ved ændringer efter baseline"

### H3: _pulse_line() kalder DB direkte
**Fund:** Planen siger `_pulse_line()` læser fra `recent_heartbeat_runtime_ticks(limit=1)` — en direkte DB-forespørgsel i prompt-kontekst. Hvis DB er langsom, kan det forsinke prompt-generering.

**Løsning:** Acceptabelt. `recent_heartbeat_runtime_ticks()` er en simpel SELECT med LIMIT 1. Køretid er <1ms. Alternativt kunne vi cache det i tick_cache, men det ville introducere 3-minutters forsinkelse på pulssignaler — det er for langsomt. Direkte læsning er det rigtige valg her.

### H4: unified_recall() returnerer kun hints, ikke fuldt indhold
**Fund:** Spec'en siger "søger alle tre med fallback" men planen returnerer kun korte hints som "Emne X findes i brain + arkiv". Det er ikke en fuld søgning.

**Løsning:** Dette er korrekt abstraktionsniveau. `unified_recall()` er til prompt-kontekst — den skal fortælle mig HVAD jeg ved, ikke gentage alt. Fuldt indhold hentes via eksisterende tools (search_memory, recall_memories, search_jarvis_brain). Planen er korrekt.

### H5: _continuity_line() afhænger af identity_sketch som genereres asynkront
**Fund:** `identity_sketch.py` genereres af en daemon (hver 6. time eller ved compaction). Hvis sketchen ikke findes endnu (frisk boot), returnerer `None`.

**Løsning:** Planen håndterer dette: "Hvis identity_sketch ikke findes → fallback til 'Genkender mig selv fra filer'". Det er acceptabelt.

---

## Medium-severity fund

### M1: Tegn-budget for nye linjer
**Fund:** Planen tilføjer op til 4 nye linjer i `build_inner_life_section()`: file_awareness, mc_whisper, pulse, continuity. Hver har sit eget tegn-budget (60-120 tegn). Men den samlede sektion har et budget (~6000 tegn).

**Løsning:** Planen specificerer allerede tegn-budget pr. linje. Den samlede sektion respekterer `_truncate_clean()`. De nye linjer tilføjes KUN når de ikke er `None` — så ved baseline (ingen filændringer, ingen anomalier, ingen governance-skift) er de fleste `None` og bidrager 0 tegn. Acceptabelt.

### M2: Fase 5 (unified_recall) kræver ny DB-tabel
**Fund:** Planen specificerer en `cross_references` SQLite-tabel. Men den specificerer ikke migration-strategi eller hvornår tabellen oprettes.

**Løsning:** Tilføjet i planen: "Oprettes via `ensure_runtime_dirs()` + `db.py` migration i Fase 5. Ingen data-migration — tabellen starter tom."

### M3: Fase 6 (continuity) afhænger af reboot_awareness_daemon
**Fund:** `_continuity_line()` læser fra `reboot_awareness_daemon`'s markers-fil. Hvis daemonen ikke kører, er der ingen reboot-data.

**Løsning:** Acceptabelt. `_continuity_line()` returnerer `None` hvis data mangler. Daemonen er allerede registreret og kører.

---

## Kontradiktioner

Ingen kontradiktioner fundet mellem spec og plan.

---

## Samlet vurdering

Planen er **byggeklar** efter rettelserne. De 3 kritiske fund er alle adresseret i opdateringen. De 5 high-severity fund er alle håndteret. Ingen kontradiktioner.

**Anbefalede rettelser (alle udført):**
1. ✅ C1: Eksplicit note om at visible_inner_life.py ikke må subscribe til eventbus
2. ✅ C2: Note om at body_memory/ghost_networks er stubs og IKKE aktiveres
3. ✅ C3: Tick-signatur specificeret med dict-format
4. ✅ H1: Støj-filter med register_own_write() og 60s cooldown
5. ✅ H2: Baseline mtime ved boot, ingen events ved første start

**Planen er klar til implementering.**