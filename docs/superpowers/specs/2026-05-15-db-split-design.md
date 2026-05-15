# db.py Split — Design Spec

**Dato:** 2026-05-15
**Status:** Approved, ready for implementation planning
**Forfatter:** Brainstorm mellem Bjørn + Claude
**Affected:** `core/runtime/db.py` (34.072 linjer, 1.15 MB)

---

## Problem

`core/runtime/db.py` er på **34.072 linjer / 1.15 MB** og indeholder:
- **708 top-level funktioner**
- **175 distinkte domæner** (de fleste følger CRUD-mønster: get/list/update/upsert/supersede × ~7 per domæne)
- **117 schema-bootstrap-funktioner** (`_ensure_*_table`)
- **5.317 import-sites** spredt over hele kodebasen
- 1 klasse (`Database`)

Cold import koster **135ms**, warm import **16ms**. Med 4 uvicorn workers betales import-cost × 4 ved hver restart. Memory-fodaftryk per worker er signifikant. Kognitiv loadbarhed er nul — ingen kan holde 34k linjer i hovedet.

**12 sibling `db_*.py` filer eksisterer allerede** (db_emotional_memory, db_concept_baseline, db_decisions m.fl.) — splittet er allerede *delvist i gang* via Boy Scout-reglen, men har aldrig nået kritisk masse.

Boy Scout-reglen alene flytter ikke nok på en fil så stor. Derfor: proaktivt split.

## Mål

Reducer `db.py` fra 34.072 → ~500-1.000 linjer som **ren facade**. Bevar 100% bagudkompatibilitet for alle 5.317 import-sites. Etabler tematisk gruppering der gør hver fil kognitivt håndterbar (200-2.000 linjer per fil).

## Ikke-mål

- **Ingen API-redesign** — alle funktions-signaturer bevares 1:1
- **Ingen call-site-migration** — alle 5.317 import-sites forbliver uændrede
- **Ingen test-refaktorering** — tests rører vi kun hvis de brækker pga. splittet
- **Ingen logisk refaktorering** — vi flytter kode, vi forbedrer den ikke

## Granularitet: Mellem-granular (~24 nye filer)

Valgt over fin-granular (150+ filer) og grov-granular (5-8 filer). Begrundelse: eksisterende `db_*.py` søskendefiler ligger på 1k-12k linjer; mellem-granular passer til etableret praksis og giver balance mellem oversigt og isolation.

**Slut-tilstand:** ~24 nye filer + 12 eksisterende + 1 facade (`db.py`) + 1 infrastructure (`db_core.py`) = ~38 filer i `core/runtime/db_*`.

## Tematisk gruppering

### Infrastruktur
- **`db_core.py`** — `connect()`, `init_db()`, pragmas, `_now_iso()`, andre infrastruktur-helpers. Eneste fil andre db_*.py må importere fra.

### Selvbillede
- **`db_runtime_self.py`** — runtime_self_* (~56 funcs)
- **`db_runtime_selfhood.py`** — selfhood, autonomy, attachment, loyalty (~30)

### Indre liv
- **`db_runtime_private.py`** — private_* (~42)
- **`db_runtime_dream.py`** — dreams (~21)
- **`db_runtime_chronicle.py`** — chronicle (~21)
- **`db_runtime_inner.py`** — inner, reflective, witness (~30)
- **`db_runtime_meaning.py`** — meaning, reflection, regulation, temperament (~30)

### Eksterne relationer
- **`db_runtime_user.py`** — user_* (~14)
- **`db_runtime_relation.py`** — relation_* (~14)
- **`db_runtime_open.py`** — open_* (~14)
- **`db_runtime_contract.py`** — contract_* (~14)
- **`db_runtime_proactive.py`** — proactive_* (~14)

### Verden/kognition
- **`db_runtime_world.py`** — world_* (~7)
- **`db_runtime_awareness.py`** — awareness, temporal, remembered (~21)
- **`db_runtime_goals.py`** — goal, executive (~14)
- **`db_runtime_initiative.py`** — initiative, task, flow (~12)
- **`db_cognitive.py`** — cognitive_* + latest_cognitive (~25)

### Hukommelse
- **`db_runtime_memory.py`** — memory, consolidation, release, selective (~28)
- **`db_runtime_metabolism.py`** — metabolism (~7)

### Approval & agents
- **`db_capability_approval.py`** — capability_approval, approval_feedback (~10)
- **`db_agents.py`** — agent_registry, scheduled_task (~11)
- **`db_tools.py`** — tool_intent, cheap_provider (~10)

### Resten
- **`db_runtime_misc.py`** — heartbeat_runtime, development, webchat, web_cache, daemon_output_log, aesthetic_motif_log m.fl. (~50+)

## Bagudkompatibilitet (ikke-forhandlelig)

`db.py` bliver **ren facade** der re-eksporterer alt via eksplicitte navngivne imports:

```python
# db.py (slut-tilstand)
"""Facade for core.runtime.db submodules.

Genererer bagudkompatibel import-overflade for 5.317 eksisterende import-sites.
Alt nyt kode bør importere direkte fra submodulet (fx core.runtime.db_runtime_self).
"""
from core.runtime.db_core import (
    connect,
    init_db,
    _now_iso,
    # ...
)
from core.runtime.db_runtime_self import (
    get_runtime_self_state,
    list_runtime_self_changes,
    # ...
)
# ... osv per submodul

__all__ = [
    "connect", "init_db", "_now_iso",
    "get_runtime_self_state", "list_runtime_self_changes",
    # ... komplet liste
]
```

**Hvorfor eksplicit, ikke `from .X import *`:**
- Statisk analyse (linters, IDE) virker
- Konflikt-detektion ved overlap mellem submoduler
- `__all__` er tydelig og auditerbar

## Faseopdelt eksekvering

### Phase 0 — Infrastructure (~2 timer)
1. Identificer alle infrastructure-symboler i db.py (connect, init_db, pragmas, helpers)
2. Scan for top-level side-effekter i db.py (initialiseringer ved import)
3. Udskil til `db_core.py`
4. `db.py` importerer fra `db_core`
5. Kør fuld test-suite (188+ tests)
6. Verificer 5.317 imports stadig virker (grep + targeted import-tests)
7. Mål cold/warm import-tid før og efter
8. Restart `jarvis-runtime` + `jarvis-api`, smoke check
9. **Commit:** `refactor(db): extract db_core infrastructure (Phase 0)`

### Phase 1 — Warm-up split (~1 time)
Vælg lille velafgrænset klynge (fx `db_capability_approval.py` ~10 funcs) for at validere mønster, test-gate, performance-gate. Bevis at processen virker før vi tager store klynger.

### Phase 2-N — Store klynger (~1 time per fase)
En domæne-klynge per commit. Suggested rækkefølge:
1. `db_runtime_self.py` (56) — størst, mest gevinst
2. `db_runtime_private.py` (42)
3. `db_runtime_chronicle.py` (21)
4. `db_runtime_dream.py` (21)
5. ... osv ned i størrelse

### Phase Final — Cleanup (~3 timer)
Resterende mindre domæner samles i tematiske residual-filer (især `db_runtime_misc.py`). Slutter med db.py som ~500-1.000 linjers facade.

**Total estimat: 25-30 timers arbejde** fordelt over flere sessioner. Ikke single-session.

## Per-fase gates (ikke-forhandlelige)

Hver fase skal passere ALLE fire gates før commit:

1. **Test-gate**: fuld test-suite grøn (`pytest tests/ -x`)
2. **Import-gate**: alle 5.317 import-sites virker (sample-test med `python -c "from core.runtime.db import <symbol>"` på en udvalgt liste)
3. **Performance-gate**: cold import af db.py må ikke blive langsommere end baseline (måles før Phase 0, sammenlignes efter hver fase)
4. **Live-gate**: restart `jarvis-runtime` + `jarvis-api`, smoke check heartbeat + chat virker

Hvis nogen gate fejler → revert + diagnose + retry. Ingen "fix later".

## Kritiske regler

1. **Ingen cirkulære imports**: domæne-filer importerer KUN fra `db_core`. Hvis to domæner deler kode, flyttes det til `db_core`.
2. **`_ensure_*_table` schema-bootstrap følger funktionen** der bruger den (ikke split fra domænet).
3. **Top-level side-effekter bevares**: hvis db.py kører noget ved import (initialisering, registrering), skal det fortsætte med at virke fra facade-versionen.
4. **Funktions-signaturer er frosne**: ingen `*args` → keyword-only, ingen type-hint-tilføjelser, ingen rename. Pure flyt.
5. **Module-level state-deling identificeres før split**: hvis funktioner deler module-level dicts/caches, kan splittet brække dem. Scannes per fase.

## Risici

| Risiko | Mitigation |
|---|---|
| Top-level side-effekter i db.py går tabt | Phase 0 scanner og bevarer dem eksplicit |
| Funktioner deler module-level globals | Per-fase scan for `global` keyword + module-level mutables |
| Pickled objekter med `core.runtime.db.X` path knækker | Grep efter `pickle.dumps`/`dill` med db-objekter; facade re-eksporterer derfor symboler |
| Cirkulære imports mellem nye db_*.py | Hård regel: kun `db_core` må importeres af andre db_*.py |
| Performance-regression | Per-fase måling, revert hvis værre |
| Test-suite brækker subtilt | `pytest -x` per fase, ingen "skip and continue" |
| Live jarvis brækker | Restart + smoke check per fase, revert ved fejl |

## Hvad gør succes ud

- `db.py` ≤ 1.000 linjer, ren facade
- Alle 5.317 import-sites virker uændrede
- Cold import af db.py ≤ 135ms (helst lavere)
- ~38 filer i `core/runtime/db_*` hver 200-2.000 linjer
- Fuld test-suite grøn (≥ 188 tests)
- Live jarvis kører uden regression efter alle faser

## Næste skridt

Efter denne spec er godkendt: kald `writing-plans`-skill for **Phase 0 + Phase 1 (warm-up)** som første implementation-plan. Phase 2+ får hver deres plan når vi når dertil.
