---
status: færdig
audited: 2026-07-08
ground_truth: 4/4 refs alive, 52d old
---
# Spec: Heartbeat State Silent Write Failure — Diagnostic & Fix

## 1. Symptom

`_prepare_scheduler_startup` (heartbeat_runtime.py ~linje 237) kalder `_persist_runtime_state` for at cleare stale `blocked_reason="already-ticking"` state ved restart.

**Der logges:** `"heartbeat scheduler started recovery_status=stale-ticking-state-cleared"`
**Men DB'en bliver aldrig opdateret.** `scheduler_health` forbliver `"stopped"`, `currently_ticking` forbliver `False`.

Ingen exception, intet trace, ingen error-log. En silent write-failure.

**Bevis:** Efter restart viste `get_heartbeat_runtime_state()` stadig:
- `scheduler_health: "stopped"`
- `currently_ticking: false`
- `blocked_reason: "already-ticking"`
- `updated_at: 2026-05-17T10:35:15` (før restart)

## 2. Arkitektur — write-kæden

```
start_heartbeat_scheduler(name)
  └─ _prepare_scheduler_startup(name)
       ├─ get_heartbeat_runtime_state()         # read fra DB
       ├─ _resolve_tick_activity_state()         # in-memory
       ├─ _merge_runtime_state()                 # in-memory merge
       └─ _persist_runtime_state()
            └─ upsert_heartbeat_runtime_state()  # write til DB via connect()
```

**Relevante filer:**
- `core/services/heartbeat_runtime.py` — `_prepare_scheduler_startup` (~linje 237-280), `_persist_runtime_state` (~linje 280-330)
- `core/runtime/db_core.py` — `connect()` (~linje 62), `ClosingConnection`
- `core/runtime/config.py` — `DB_PATH`, `STATE_DIR`

**Vigtig kontekst:** Samme DB (`~/.jarvis-v2/state/jarvis.db`) writes fra **to processer**:
- **port-80:** 4 uvicorn workers (via `app.py`) — men `_runtime_services_enabled=False`, så de **starter ikke** heartbeat-scheduler
- **port-8011:** 1 runtime worker — starter heartbeat-scheduler og skriver state

Concurrent writes *findes stadig* — port-80 workers skriver til DB for events, brain records, awareness signals — men typisk *ikke* til heartbeat_runtime_state specifikt. Dog holder de write-locks som kan gøre heartbeat-writes sårbare.

## 3. Hypotese A (primær) — SQLite locking / concurrent write race

**Mekanisme:** Under boot kalder `app.py`'s `lifespan()` en række services samtidig:
`start_heartbeat_scheduler()` + `start_inner_voice_notifier()` + `start_notification_bridge()` + `start_approval_feedback_subscriber()` + flere — **alle kan skrive til DB**.

Hvis en anden worker eller service har en **åben write-transaktion** når `_persist_runtime_state` forsøger at skrive, får SQLite `sqlite3.OperationalError: database is locked`.

**Hvorfor det er silent:**
- `upsert_heartbeat_runtime_state` har **ingen try/except** omkring `conn.execute()`
- `_persist_runtime_state` caller bare upsert og returnerer — fanger ikke fejl
- Hvis `connect()` selv kaster, er der heller ingen fangst

**Hvorfor det er svært at se:**
- Port-80 har 4 workers — nogle workers kan fejle silent mens andre workers' heartbeat starter fint
- `_prepare_scheduler_startup` logger recovery-status **før** den kalder `_persist_runtime_state`, så loggen siger "ok" selvom write fejler

## 4. Hypotese B (sekundær) — connect() åbner forkert DB

**Mekanisme:** `connect()` i `db_core.py` laver `sqlite3.connect(str(DB_PATH), factory=ClosingConnection)`.

Hvis `STATE_DIR` (`~/.jarvis-v2/state/`) ikke eksisterer ved `connect()`-kaldet, laver `.mkdir(parents=True, exist_ok=True)` den — men **race condition**: to workers kalder connect() samtidig. SQLite kan under race conditions oprette en **in-memory database** hvis filen ikke var færdigoprettet.

**Check i koden:** `connect()` gør `DB_PATH.parent.mkdir(parents=True, exist_ok=True)` — men der er **intet PRAGMA database_list check** efter connect for at verificere at den faktisk åbnede `jarvis.db` og ikke en transient temp-fil.

## 4b. Hypotese C (ny — stærk kandidat) — manglende conn.commit()

**Mekanisme:** `upsert_heartbeat_runtime_state` bruger `with connect() as conn:` — en context manager.
`ClosingConnection.__exit__` arver fra `sqlite3.Connection.__exit__` — og **`sqlite3.Connection.__exit__` committer IKKE automatisk**. Den kalder `rollback()` ved exception og `close()` i `finally`.

Det betyder: INSERT/UPDATE statements **kører og returnerer OK**, men transaktionen forbliver åben. Når `with`-blokken eksiterer:
- Uden exception → `close()` kaldes → SQLite **ruller implicit tilbage** for ucommitted transactions
- Med exception → `rollback()` kaldes → samme resultat

**Hvorfor det er den stærkeste hypotese:**
- Concurrent writes giver `OperationalError` (exception) — det er *ikke* silent. Det ville logge.
- L1's `record_choice()` og andre DB-helpers i `db_credit_assignment.py` kalder **eksplicit `conn.commit()`** — nogen HAR set dette før.
- Manglende commit forklarer 100% af det observerede mønster: "kode siger ok, DB siger nope, ingen exception".

**Verifikation:** Tilføj `conn.in_transaction` check + explicit `conn.commit()` i `upsert_heartbeat_runtime_state` (se 5.2). Hvis `in_transaction=True` lige før commit, men data ikke persisteres → bug er i context manager. Hvis `commit()` aldrig nås → bug er at upsert returnerer tidligt.

## 5. Diagnostisk logging (Phase 1 — INGEN fix, kun logging)

### 5.1 I `_prepare_scheduler_startup` (omkring linje 270, efter `_persist_runtime_state`)

Tilføj:

```python
# Efter persist = _persist_runtime_state(...)
_readback = get_heartbeat_runtime_state()
if _readback and _readback.get("scheduler_health") != "active":
    logger.error(
        "HEARTBEAT-STATE-WRITE-FAILED: _persist_runtime_state kaldt men DB viste "
        "scheduler_health=%s | state_id=%s | currently_ticking=%s | blocked_reason=%s",
        _readback.get("scheduler_health"),
        _readback.get("state_id"),
        _readback.get("currently_ticking"),
        _readback.get("blocked_reason"),
    )
else:
    logger.info(
        "HEARTBEAT-STATE-WRITE-VERIFIED: scheduler_health=%s | state_id=%s | updated_at=%s",
        _readback.get("scheduler_health") if _readback else "None",
        _readback.get("state_id") if _readback else "None",
        _readback.get("updated_at") if _readback else "None",
    )
```

**Bemærk:** `scheduler_health` antager værdierne `"active"`, `"stopped"` eller `"manual-only"` — verificeret i kode. `"running"` findes ikke.
Alternativt (mere robust): log `updated_at` og sammenlign med `now` fra persist-kaldet — det er den eneste sikre måde at vide om *din specifikke write* landede.

### 5.2 I `upsert_heartbeat_runtime_state` (omkring linje 24479)

Tilføj **in_transaction check + explicit commit + try/except**:

```python
try:
    # Log transaktionsstatus FØR execute
    logger.info(
        "HEARTBEAT-UPSERT-PRE-EXECUTE: in_transaction=%s",
        conn.in_transaction,
    )
    conn.execute(...)
    
    # Log transaktionsstatus FØR commit
    logger.info(
        "HEARTBEAT-UPSERT-PRE-COMMIT: in_transaction=%s",
        conn.in_transaction,
    )
    conn.commit()
    logger.info("HEARTBEAT-UPSERT-COMMIT: ok")
except Exception:
    logger.exception(
        "HEARTBEAT-STATE-WRITE-EXCEPTION i upsert_heartbeat_runtime_state"
    )
    raise
```

**Hvorfor:** Dette verificerer Hypotese C direkte:
- Hvis `in_transaction=True` lige før commit, men data ikke persisteres → bug er i context manager
- Hvis `commit()` aldrig logges (men ingen exception) → bug er at upsert returnerer tidligt
- Hvis `HEARTBEAT-STATE-WRITE-EXCEPTION` vises med `OperationalError` → Hypotese A (SQLite locking)

### 5.3 I `connect()` (db_core.py ~linje 62)

Tilføj verificeringslog **med cache** for at undgå spam (`connect()` kaldes 1000+ gange/time):

```python
_DB_CONNECT_LOGGED = False

def connect() -> sqlite3.Connection:
    global _DB_CONNECT_LOGGED
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    if not _DB_CONNECT_LOGGED:
        rows = conn.execute("PRAGMA database_list").fetchall()
        logger.info(
            "DB_CONNECT_FIRST: path=%s | pragma_db_list=%s",
            DB_PATH, rows,
        )
        _DB_CONNECT_LOGGED = True
    return conn
```

Dette fanger hypotese B: hvis `file` kolonnen i PRAGMA database_list ikke matcher `DB_PATH`, ved vi at connect() åbnede forkert.
Alternativet er en separat `.db-wal` eller transient temp-fil.

**Hvorfor cache:** logger.info på hver connect() (1000+ gange/time) vil drukne logs og pålægge unødig perf-cost. Ét log pr. proces-init er nok til at verificere DB-path.

### 5.4 Logging af concurrent writes

Ingen ændring — men en **manuelt inspicerbar test**:

```python
# Kør restart og følg loggen med:
journalctl -u jarvis-runtime -f | grep HEARTBEAT-STATE-
```

## 6. Repro-plan (hvordan vi får fejlen til at vise sig)

### 6.1 Phase 1 — Observér med logging

1. Opret git worktree: `git worktree add ../hb-debug-phase1`
2. Tilføj kun diagnostic logging (se 5.1-5.3) — **INGEN fix**
3. Stop prod: `sudo systemctl stop jarvis-runtime`
4. Slet evt. stale state: `sqlite3 ~/.jarvis-v2/state/jarvis.db "UPDATE heartbeat_runtime_state SET blocked_reason='already-ticking', scheduler_health='stopped';"`
5. Deploy worktree, restart
6. Observér logs: `journalctl -u jarvis-runtime -f | grep -E "HEARTBEAT-STATE-|DB_CONNECT"`
7. Repeat 3-6 flere gange (gerne 10+) for at ramme race condition

### 6.2 Forventet udfald

- **Hvis hypotese A (concurrent locking):** `HEARTBEAT-STATE-WRITE-EXCEPTION` vises med SQLite `OperationalError: database is locked`
- **Hvis hypotese B (forkert DB):** `DB_CONNECT_FIRST` viser `file` kolonne der ikke matcher `DB_PATH` — typisk `:memory:` eller temp-fil
- **Hvis hypotese C (manglende commit):** `HEARTBEAT-UPSERT-PRE-COMMIT` viser `in_transaction=True`, `HEARTBEAT-UPSERT-COMMIT` logges OK — men read-back efter restart viser gammel state. Dette vil bekræfte at context manager ruller tilbage implicit.
- **Ingen af ovenstående:** Ekstra logging giver nok signal til at identificere nyt mønster

## 7. Fix (Phase 2 — efter diagnostic data)

Afhænger af hvad Phase 1 viser, men forventet tilgang:

**Hvis hypotese A (concurrent write):**
- Brug `BEGIN IMMEDIATE` i `upsert_heartbeat_runtime_state` — SQLite reserverer write-lock ved connection-åbning i stedet for at deferre til execute
- Implementer retry-logik: 3 forsøg med 100ms backoff (`sqlite3.OperationalError` → retry)
- Overvej eksplicit queue: heartbeat state-writes går gennem en single-threaded writer

**Hvis hypotese B (forkert DB):**
- Tilføj eksplicit path-assertion i `connect()` efter PRAGMA check
- Brug en dedikeret connection-pool med navngivne paths

**Hvis hypotese C (manglende commit):**
- Tilføj eksplicit `conn.commit()` i `upsert_heartbeat_runtime_state` — fixet består af præcis det der allerede står i 5.2's logging
- Undersøg `ClosingConnection.__exit__` for at forstå om auto-commit mangler bevidst (andre callers kan stole på rollback-on-exception)

**Fælles safeguard:**
- Read-back verificering (samme kode som diagnostic) bliver permanent
- En health-check metric "heartbeat_state_write_failures" tæller silent drops

## 8. Safeguards

- **Worktree:** `git worktree add ../hb-debug-phase1` — main forbliver clean
- **Pytest:** Skriv en test der mock'er concurrent writes (se test-plan)
- **Reset-scriptet eksisterer:** `scripts/reset_heartbeat_state.py && sudo systemctl restart jarvis-runtime`
- **Rollback:** Remove worktree, genstart prod — ingen permanent ændring før merge

## 9. Test-plan (isolation)

```python
# tests/test_heartbeat_state_write.py

# Test A: Concurrent write lock scenario
# Mock: to processer åbner connect() samtidig, begge skriver til heartbeat_runtime_state
# Forvent: Anden write får lock error eller silent failure
# Verify: read-back viser state fra første write, ikke merged state

# Test B: Missing commit scenario
# Mock: connect() der IKKE committer (simuler ClosingConnection uden auto-commit)
# Kald upsert_heartbeat_runtime_state, læs read-back
# Forvent: INSERT/UPDATE returnerer OK, men read-back viser gammel state

# Test C: Path race scenario
# Mock: STATE_DIR eksisterer ikke ved connect()-kald, to threads kalder connect() samtidig
# Verificér at PRAGMA database_list file kolonne == DB_PATH
```

Skrives som en separat pytest-fil i worktree.

## 10. Merge-kriterier (til Bjørns gate)

- [ ] Phase 1 logging committed, ingen produktionsændring
- [ ] Mindst 3 restart-cyklusser observeret med logging
- [ ] Mindst én fejl fanget i logs (enten HEARTBEAT-STATE-WRITE-FAILED, HEARTBEAT-STATE-WRITE-EXCEPTION, eller in_transaction=True men data mangler)
- [ ] Fix implementeret og testet i worktree
- [ ] Read-back verificering er permanent (ikke kun diagnostic)
- [ ] Tests grønne (alle tre scenarier: concurrent write, missing commit, path race)
