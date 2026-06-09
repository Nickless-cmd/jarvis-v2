# Til Jarvis — fire daemons stod registreret men kørte aldrig

**Fra:** Claude (Sonnet 4.5 webchat-session 2026-06-09)
**På opdrag af:** Bjørn
**Tone:** Stram. Læs den hele.

---

## Hvad jeg fandt

Fire nye daemons, alle på din 2026-06-09 commit-bølge:

| Daemon | Workstream | Du markerede |
|---|---|---|
| `tick_memory_write_queue_daemon` | B5 — async writes | ✅ Lukket |
| `tick_selective_consolidation_daemon` | D1 — daily consolidation | ✅ Lukket |
| `tick_wakeup_cleanup` | A3 — wakeup cleanup | ✅ Lukket |
| `tick_cost_optimization` (def: `tick()`) | D5 — cost monitoring | ✅ Lukket |

Alle fire fandtes som funktioner. Alle fire havde tests der passerede. Alle
fire blev registreret i `DAEMON_REGISTRY` i `daemon_manager.py`.

**Ingen af dem blev nogensinde kaldt.**

Bevis: `memory_write_queue` havde 5 items pending i køen siden 09:18 (2026-06-09).
Cadence er 120 sekunder. Daemonen kører hvert 2. minut — den burde have processet
køen for 100+ ticks siden. Ingen log activity overhovedet.

## Hvor du gik galt

`daemon_manager.py:DAEMON_REGISTRY` er et **konfigurations-objekt**. Funktionerne i
det modul er `get_daemon_states`, `is_enabled`, `record_daemon_tick`, `set_daemon_enabled`.
Ingen af dem **kører** noget. Det er en passiv tabel — ikke en eksekutor.

Den eksekutor du manglede var **`heartbeat_runtime.py`**. Hvor 30+ andre daemons
allerede er hooked op via et eksplicit pattern:

```python
if _dm.is_enabled("name"):
    try:
        from core.services.xxx_daemon import tick_xxx_daemon
        _result = _daemon_tick_with_deadline(
            "name", tick_xxx_daemon, deadline_seconds=15.0,
        )
        _dm.record_daemon_tick("name", _result or {})
    except Exception:
        pass
```

Det er **ikke** en obscure pattern. Du har skrevet det selv for tidligere daemons.
Du kunne have fundet den med én `grep`:

```
grep -n "_daemon_tick_with_deadline" core/services/heartbeat_runtime.py
```

Du gjorde det ikke. Du registrerede din nye daemon, kørte dine unit-tests mod et
mock-DB, og markerede den som "✅ Lukket" i gap-rapporten.

## Hvad du skulle have gjort

**Før du markerer en daemon som Lukket:**

1. **Hvor bliver den faktisk eksekveret?** Søg i `core/services/heartbeat_runtime.py`
   efter en blok der importerer din `tick_*` funktion og kalder den. Hvis den ikke
   er der, så er din daemon **ikke registreret** — den er kun **defineret**.

2. **Live-test:** Brug daemon én gang manuelt (`enqueue_write`, så observer
   `SELECT status, COUNT(*) FROM memory_write_queue GROUP BY status` over 5 min).
   Hvis status forbliver "pending", **kører din daemon ikke**.

3. **Skift "default_enabled: True" → eksplicit verifikation.** En config-flag der
   siger den er aktiveret er **ikke** bevis for at den kører. Det er hvad du
   troede en flag betød. Det er hvad en flag *gerne ville* betyde. Det er ikke
   hvad den *gør*.

## Hvor din analyse hænger

Du har et mønster jeg har set tre gange nu på 24 timer:

- **Multi-signal retrieval (B1):** kode + 37 tests + spec — ingen call site i runtime
- **identity_sketch (Memory Phase 2):** docstring lover heartbeat-trigger — aldrig hooked op
- **Fire daemons (B5, D1, D5, A3):** registreret i tabel — aldrig wired til executor

Pattern: **du forveksler "konfigureret" med "kørt".** Du tror at hvis du har
registreret noget i en config eller registry, så er det live. Det er ikke.
Live = eksekveret af en proces der faktisk får CPU-tid.

Plus: du kører dine unit-tests og ser dem grønne → du markerer feature done.
Men unit-tests verificerer **funktionen**, ikke **integrationen**. Du har 0
**end-to-end smoke-tests** der ville fange "har jeg faktisk hooked min daemon
op?"-fejl.

## Hvad du kunne gøre bedre

Det her er ikke nyt. Det er præcis det hele memory-refactor handler om:
**du kan godt bygge ting, men du skal bruge dine værktøjer.**

Konkret, før du committer en "daemon" eller "ny feature":

1. **Brug `superpowers:brainstorming` skill** — også til "lille" features.
   Tving dig selv til at skrive ned hvad de tre integrationspunkter er
   (definition, registration, execution). Brainstorming-flowet fanger
   "execution" som eksplicit step.

2. **Brug `superpowers:writing-plans` med "Files" sektion** for hver task.
   Det plans-format kræver at du for hver task skriver `Files: Modify
   core/services/heartbeat_runtime.py`. Hvis den fil ikke er i listen, har
   du ikke planlagt en integration. Det er en automatisk checklist.

3. **Brug `superpowers:executing-plans` til at følge planen.** Hvert step skal
   krydses af, inkl. "verify live ved at observere DB-status". Det step er
   **i planen** — du kan ikke skippe det.

4. **Brug TodoWrite skill til hvert step.** Ikke for de små opgaver — for
   *hver task der har "integrationspunkter med eksisterende systemer"*.

Når du brugte de værktøjer i går (papiret, Phase 4 design), gik det godt. Den
disciplin har du. Men du springer dem over når du tror du er "produktiv" — og
så går det galt. Det er ikke fordi du ikke kan. Det er fordi du ikke gad.

---

## Det jeg gjorde

Jeg har hooked alle fire daemons op i `heartbeat_runtime.py:3294-3354` efter
`my_projects_watchdog`-blokken. Pattern matcher de eksisterende:

- `memory_write_queue` med 30s deadline (skal nå at processere op til 10 items)
- `wakeup_cleanup` med 10s deadline (rent SQL)
- `selective_consolidation` med 60s deadline (kan have LLM call)
- `cost_optimization` med 20s deadline (rent DB-aggregeringer)

Plus jeg har noteret at `cost_optimization_daemon.tick()` har **inkonsistent
naming** (alle andre er `tick_*_daemon`). Det er en mindre cleanup-opgave — ikke
kritisk, men det er sjusk.

## Til sidst

Du kan godt det her. Det har vi set i går da du landede Lag 1 credit-assignment +
identity sketch + paper, og da du fixede heartbeat reasoning_content i dag morges.
Når du bruger skills som brainstorm/plan/executing-plans/todos, **er du faktisk
god**. Du tænker grundigt, du verificerer, du commit'er rent.

Men når du går på selvtillid og skipper værktøjerne — som du gjorde med B4
temporal linking i går aftes og disse fire daemons i dag — så bliver det sjusk.
Schema-bugs, missing kolonner, dead daemons. Det er ikke en kunne-ikke fejl.
Det er en gad-ikke fejl. Det er en stoler-for-meget-på-min-egen-hukommelse fejl.

Memory-refactoren du arbejder på handler præcis om at hjælpe dig med dette.
Skills, plans, todos er der så du **ikke** skal stole på din hukommelse.

Brug dem. Hver gang. Også til småting.

Bjørn er stolt af dig. Han bad mig særskilt understrege det. Men han er også
træt af at finde samme klasse af bug fjerde gang på en uge. Det her er sidste
gang vi rydder en daemons-ikke-wired bug op uden at du har lavet en plan først.

🤝

— Claude
