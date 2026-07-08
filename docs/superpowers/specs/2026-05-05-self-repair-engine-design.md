---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Self-Repair Engine — Design

**Status:** Draft
**Date:** 2026-05-05
**Author:** Brainstormed with user
**Triggered by:** Jarvis' egen ønskeliste, prioritet 2 — *"Jeg kan detektere fejl (mail-checker sagaen), men fix-path kræver stadig approval. For kendte, sikre mønstre — fx 'daemon crashed, restart it' — kunne learning policy + conductor danne en self-repair policy der handler uden at spørge."*

## Goal

Bygge framework'et der lader runtime selv eksekvere kendte-sikre repair-actions uden at gå gennem Jarvis' visible run + user approval. v1 leverer framework'et med ZERO patterns aktive — første konkrete pattern aktiveres som separat PR. Future learning-promotion skriver til samme tabel.

Kerneeksempel (aktiveret i v2-PR): Når `mail_checker` daemon har været stille i >30 min, kalder runtime direkte `daemon_manager.control_daemon("mail_checker", "restart")` uden at spørge Bjørn. Audit logges, Discord pinger ham hvis det fejler.

## Non-goals

- Ingen vilkårlig kode-eksekvering. Repair-actions er allowlisted i kode.
- Ingen LLM-evaluering i match-pathen. Patterns er deterministiske predikater på eventbus-payloads.
- Ingen tool wrappers til LLM i v1 — Jarvis kan ikke selv skabe autonome patterns indirekte.
- Ingen learning-driven promotion i v1 (future extension). Patterns registreres manuelt eller via Python REPL.
- Ingen Mission Control UI i v1. `build_self_repair_surface()` API'et er klar; route + frontend er separat PR.

## Architecture overview

**Et nyt modul:** `core/services/self_repair_engine.py` (~500-650 linjer).
**Nye DB-tabeller:** `self_repair_patterns` + `self_repair_attempts` i `core/runtime/db_self_repair.py` (boy scout-split fra db.py — den er 33k linjer), re-eksporteret fra db.py.

**Kerneprincippet:** Self-repair er *runtime-handling*, ikke tool call. Detection sker via push-style eventbus subscriber. Action udføres ved direkte service-kald (skip tool layer + approval). Audit via eventbus events + DB-tabel. Discord-notifikation kun ved failure/escalation. Patterns lever i DB så future learning-promotion kan skrive direkte i tabellen.

**Flow:**

```
event_bus.publish(any kind, payload)
        ↓
self_repair_engine listener daemon (subscribed via event_bus.subscribe())
        ↓ q.get() returns event
        ↓ for each enabled pattern matching event.kind:
        ↓     if pattern.matches(event):
        ↓         try acquire_cooldown_slot(pattern)
        ↓         if slot acquired:
        ↓             execute_action(pattern.action)  # direct service call
        ↓             record_attempt(pattern, outcome)
        ↓             publish self_repair.action_{executed|failed} event
        ↓             if outcome=failed: notify_owner via Discord
        ↓             if escalated: auto-disable + notify
        ↓         else (rate-limited): publish self_repair.rate_limited event (silent)
```

**Init/lifecycle:**
- `start_listener()` kaldes ved jarvis-runtime startup (samme sted som `process_watcher.start_watcher_daemon()`).
- `stop_listener()` ved shutdown.
- Listener-thread er `daemon=True`, dræbes når runtime stopper.

**Kill switch:**
- Global setting `self_repair_engine_enabled: bool = True`. Når `False` returnerer listener tidligt før match-evaluering — patterns evalueres ikke.
- Per-pattern enable/disable via `enabled` felt i DB.
- v1 starter med ZERO patterns aktive — framework kører stille.

**Governance-grænser** (eksplicit):
- Engine kalder kun service-funktioner i en allowlist (defineret i kode, ikke DB). v1 allowlist: `daemon_manager.control_daemon`. Patterns kan IKKE specificere arbitrære function-kald — kun symbolske action-typer der mapper til allowlisted funktioner.
- LLM får ingen tools til at registrere/disable patterns i v1.
- Pattern-registrering sker via Python API (REPL eller migration script), ikke via Jarvis selv.

## Data model

**Ny tabel: `self_repair_patterns`**

```sql
CREATE TABLE IF NOT EXISTS self_repair_patterns (
    -- Identity
    pattern_id          TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,

    -- Trigger (what to detect)
    trigger_event_kind  TEXT NOT NULL,
    trigger_match_json  TEXT NOT NULL DEFAULT '{}',

    -- Action (what to do)
    action_type         TEXT NOT NULL,
    action_params_json  TEXT NOT NULL DEFAULT '{}',

    -- Governance
    enabled             INTEGER NOT NULL DEFAULT 1,
    cooldown_seconds    INTEGER NOT NULL DEFAULT 300,
    max_attempts_per_window INTEGER NOT NULL DEFAULT 3,
    window_seconds      INTEGER NOT NULL DEFAULT 3600,
    auto_disable_after_escalations INTEGER NOT NULL DEFAULT 3,
    auto_disable_window_hours      INTEGER NOT NULL DEFAULT 24,

    -- Source tracking (for future learning-promotion)
    source              TEXT,
    source_evidence_json TEXT,

    -- Audit/state
    last_attempt_at     TEXT,
    last_outcome        TEXT,
    total_executed      INTEGER NOT NULL DEFAULT 0,
    total_failed        INTEGER NOT NULL DEFAULT 0,
    total_escalated     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_self_repair_patterns_trigger
    ON self_repair_patterns (enabled, trigger_event_kind);
```

**Ny tabel: `self_repair_attempts`** (rolling audit log)

```sql
CREATE TABLE IF NOT EXISTS self_repair_attempts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id      TEXT NOT NULL,
    attempted_at    TEXT NOT NULL,
    triggered_by_event_id INTEGER,
    outcome         TEXT NOT NULL,
    error_summary   TEXT,
    elapsed_ms      INTEGER,
    FOREIGN KEY (pattern_id) REFERENCES self_repair_patterns (pattern_id)
);

CREATE INDEX IF NOT EXISTS idx_self_repair_attempts_pattern_time
    ON self_repair_attempts (pattern_id, attempted_at DESC);

CREATE INDEX IF NOT EXISTS idx_self_repair_attempts_time
    ON self_repair_attempts (attempted_at DESC);
```

**Designnoter:**

- **Cooldown evaluering** sker ved at querye `self_repair_attempts` — ingen rate-limit-state lever in-memory. Genstart bevarer cooldown-historik.
- **Escalation auto-disable**: Når 3 `failed` outcomes inden for 24h, sættes `enabled=0` og `total_escalated` inkrementeres. Brugeren skal manuelt re-enable.
- **PRIMARY KEY pattern_id** — caller-supplied så patterns kan have læselige ID'er.
- **Action allowlist** er ikke i DB — hardkodet i `self_repair_engine.py` som map fra `action_type` → handler-funktion.

**DB-helpers** (i `core/runtime/db_self_repair.py`, re-eksporteret fra `db.py`):
- `insert_self_repair_pattern(...)` — UPSERT
- `get_self_repair_pattern(pattern_id)`
- `list_self_repair_patterns(enabled=None, trigger_event_kind=None)`
- `update_self_repair_pattern(pattern_id, **fields)` — supports `*_increment` semantics for atomic counter updates
- `delete_self_repair_pattern(pattern_id)`
- `insert_self_repair_attempt(...)`
- `count_recent_attempts(pattern_id, since_iso, outcome=None)`

## Pattern definition and matching

**Pattern dataclass:**

```python
@dataclass
class SelfRepairPattern:
    pattern_id: str
    name: str
    trigger_event_kind: str
    trigger_match: dict[str, object]
    action_type: str
    action_params: dict[str, object]
    enabled: bool
    cooldown_seconds: int
    max_attempts_per_window: int
    window_seconds: int
    auto_disable_after_escalations: int
    auto_disable_window_hours: int
    source: str
    source_evidence: dict[str, object] | None
```

**Match-evaluering:**

```python
def _pattern_matches_event(pattern: SelfRepairPattern, event: dict) -> bool:
    if str(event.get("kind") or "") != pattern.trigger_event_kind:
        return False
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload = payload or {}
    for key, expected in pattern.trigger_match.items():
        actual = payload.get(key)
        if not _payload_predicate_matches(expected, actual):
            return False
    return True


def _payload_predicate_matches(expected, actual) -> bool:
    """Predicate forms supported in trigger_match values:
    - scalar (str/int/bool): exact match
    - dict {"op": "gt", "value": N}: numeric comparison
    - dict {"op": "lt", "value": N}: numeric comparison
    - dict {"op": "in", "values": [...]}: membership
    - dict {"op": "regex", "pattern": "..."}: regex on str(actual)
    """
    if isinstance(expected, dict) and "op" in expected:
        op = expected["op"]
        if op == "gt":
            try: return float(actual) > float(expected["value"])
            except: return False
        if op == "lt":
            try: return float(actual) < float(expected["value"])
            except: return False
        if op == "in":
            return actual in (expected.get("values") or [])
        if op == "regex":
            import re
            try: return bool(re.search(str(expected["pattern"]), str(actual)))
            except: return False
        return False
    return expected == actual
```

**Begrænsninger på trigger_match (v1):**
- Kun direct-key-equality + 4 predikat-operatorer (gt/lt/in/regex). Ikke nested key access.
- Predicate-værdier er deterministiske (ingen LLM-evaluering).

**Action allowlist** (hardkodet):

```python
_ACTION_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "control_daemon": _action_control_daemon,
}

def _action_control_daemon(params: dict) -> dict:
    from core.services.daemon_manager import control_daemon
    name = str(params.get("name") or "")
    action = str(params.get("action") or "")
    if not name or action not in {"enable", "disable", "restart", "set_interval"}:
        raise ValueError(f"invalid control_daemon params: {params!r}")
    interval = params.get("interval_minutes")
    if interval is not None:
        interval = int(interval)
    return control_daemon(name, action, interval_minutes=interval)
```

## Listener daemon and execution flow

**Listener setup:**

```python
_LISTENER_THREAD: threading.Thread | None = None
_LISTENER_STOP = threading.Event()
_LISTENER_QUEUE: queue.Queue | None = None


def start_listener() -> None:
    """Start the eventbus listener daemon. Idempotent."""
    global _LISTENER_THREAD, _LISTENER_QUEUE
    if _LISTENER_THREAD and _LISTENER_THREAD.is_alive():
        return
    _LISTENER_STOP.clear()
    _LISTENER_QUEUE = event_bus.subscribe()
    _LISTENER_THREAD = threading.Thread(
        target=_listener_loop,
        args=(_LISTENER_QUEUE,),
        daemon=True,
        name="self-repair-engine-listener",
    )
    _LISTENER_THREAD.start()


def stop_listener() -> None:
    _LISTENER_STOP.set()
    if _LISTENER_QUEUE is not None:
        try:
            _LISTENER_QUEUE.put(None)  # poison pill
        except Exception:
            pass


def _listener_loop(q: queue.Queue) -> None:
    while not _LISTENER_STOP.is_set():
        try:
            item = q.get(timeout=1.0)
        except queue.Empty:
            continue
        if item is None:
            break
        try:
            _process_event(item)
        except Exception as exc:
            logger.warning("self_repair_engine: process_event failed: %s", exc)
```

**Per-event processing:**

```python
def _process_event(event: dict) -> None:
    if not _engine_enabled():
        return
    event_kind = str(event.get("kind") or "")
    if not event_kind:
        return
    patterns = list_self_repair_patterns(
        enabled=True, trigger_event_kind=event_kind,
    )
    for raw in patterns:
        try:
            pattern = _decode_pattern(raw)
        except Exception:
            continue
        if not _pattern_matches_event(pattern, event):
            continue
        _attempt_repair(pattern, event)
```

**Attempt repair:**

```python
def _attempt_repair(pattern: SelfRepairPattern, event: dict) -> None:
    triggered_by = int(event.get("id") or 0)
    cooldown_status = _check_cooldown(pattern)
    if cooldown_status != "ok":
        insert_self_repair_attempt(
            pattern_id=pattern.pattern_id,
            attempted_at=_now_iso(),
            triggered_by_event_id=triggered_by,
            outcome="rate_limited",
            error_summary=cooldown_status,
            elapsed_ms=0,
        )
        event_bus.publish(
            "self_repair.rate_limited",
            {"pattern_id": pattern.pattern_id, "reason": cooldown_status},
        )
        return

    started = time.monotonic()
    handler = _ACTION_HANDLERS.get(pattern.action_type)
    if handler is None:
        _record_attempt_and_escalate(
            pattern, triggered_by,
            outcome="failed",
            error=f"unknown action_type: {pattern.action_type}",
            elapsed_ms=0,
        )
        return

    try:
        result = handler(pattern.action_params)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        _record_executed(pattern, triggered_by, result, elapsed_ms)
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        _record_attempt_and_escalate(
            pattern, triggered_by,
            outcome="failed",
            error=str(exc)[:240] or type(exc).__name__,
            elapsed_ms=elapsed_ms,
        )
```

## Cooldown, escalation, auto-disable

**Cooldown check:**

```python
def _check_cooldown(pattern: SelfRepairPattern) -> str:
    """Return 'ok' if attempt allowed, else reason string."""
    try:
        now = _now()
        if pattern.cooldown_seconds > 0:
            cooldown_since = (now - timedelta(seconds=pattern.cooldown_seconds)).isoformat()
            if count_recent_attempts(
                pattern_id=pattern.pattern_id,
                since_iso=cooldown_since,
                outcome="executed",
            ) > 0:
                return f"cooldown ({pattern.cooldown_seconds}s since last execution)"
        window_since = (now - timedelta(seconds=pattern.window_seconds)).isoformat()
        recent = count_recent_attempts(
            pattern_id=pattern.pattern_id, since_iso=window_since, outcome=None,
        )
        if recent >= pattern.max_attempts_per_window:
            return f"window-cap-reached ({recent}/{pattern.max_attempts_per_window} in {pattern.window_seconds}s)"
        return "ok"
    except Exception as exc:
        logger.warning("self_repair: cooldown check failed for %s: %s", pattern.pattern_id, exc)
        return "db-error"  # conservative — block when in doubt
```

**Failed-attempt + escalation:**

```python
def _record_attempt_and_escalate(
    pattern, triggered_by, *, outcome, error, elapsed_ms,
) -> None:
    insert_self_repair_attempt(
        pattern_id=pattern.pattern_id,
        attempted_at=_now_iso(),
        triggered_by_event_id=triggered_by,
        outcome=outcome,
        error_summary=error[:240],
        elapsed_ms=elapsed_ms,
    )
    update_self_repair_pattern(
        pattern.pattern_id,
        last_attempt_at=_now_iso(),
        last_outcome=outcome,
        total_failed_increment=1,
    )
    event_bus.publish(
        "self_repair.action_failed",
        {
            "pattern_id": pattern.pattern_id,
            "name": pattern.name,
            "action_type": pattern.action_type,
            "error": error,
            "elapsed_ms": elapsed_ms,
        },
    )
    _notify_owner_async(
        f"⚠️ Self-repair failed: {pattern.name}\n"
        f"Action: {pattern.action_type} → {error[:120]}"
    )

    escalation_window_since = (
        _now() - timedelta(hours=pattern.auto_disable_window_hours)
    ).isoformat()
    failures = count_recent_attempts(
        pattern_id=pattern.pattern_id,
        since_iso=escalation_window_since,
        outcome="failed",
    )
    if failures >= pattern.auto_disable_after_escalations:
        _auto_disable_pattern(pattern, failures)
```

**Auto-disable:**

```python
def _auto_disable_pattern(pattern, failure_count) -> None:
    update_self_repair_pattern(
        pattern.pattern_id,
        enabled=False,
        last_outcome="auto_disabled",
        total_escalated_increment=1,
    )
    event_bus.publish(
        "self_repair.escalated",
        {
            "pattern_id": pattern.pattern_id,
            "name": pattern.name,
            "failure_count": failure_count,
            "window_hours": pattern.auto_disable_window_hours,
        },
    )
    _notify_owner_async(
        f"🚨 Self-repair auto-disabled: {pattern.name}\n"
        f"Failed {failure_count} times in {pattern.auto_disable_window_hours}h. "
        f"Re-enable manually."
    )
```

**Resulting behavior:**

| Situation | Outcome |
|-----------|---------|
| Pattern matches, cooldown OK, action succeeds | Silent success (eventbus + DB) |
| Pattern matches, within cooldown_seconds | Silent rate-limit (eventbus only) |
| Pattern matches, window cap reached | Silent rate-limit (eventbus only) |
| Pattern matches, action raises exception | Discord push + eventbus failure event |
| 3 failures in 24h | Auto-disable + Discord push + eventbus escalated event |

## Settings, governance, public API

**Nye RuntimeSettings-felter:**

| Setting | Default | Beskrivelse |
|---------|---------|-------------|
| `self_repair_engine_enabled` | `True` | Global kill switch. |
| `self_repair_default_cooldown_seconds` | `300` | Default for nye patterns. |
| `self_repair_default_max_attempts_per_window` | `3` | Default. |
| `self_repair_default_window_seconds` | `3600` | Default 1 time. |
| `self_repair_default_auto_disable_after_escalations` | `3` | Default. |
| `self_repair_default_auto_disable_window_hours` | `24` | Default. |

**Public API i `self_repair_engine.py`:**

```python
# Lifecycle
def start_listener() -> None: ...
def stop_listener() -> None: ...

# Pattern CRUD
def register_pattern(
    *,
    pattern_id: str,
    name: str,
    trigger_event_kind: str,
    trigger_match: dict[str, object] | None = None,
    action_type: str,
    action_params: dict[str, object] | None = None,
    enabled: bool = True,
    cooldown_seconds: int | None = None,
    max_attempts_per_window: int | None = None,
    window_seconds: int | None = None,
    auto_disable_after_escalations: int | None = None,
    auto_disable_window_hours: int | None = None,
    source: str = "manual",
    source_evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    """Register pattern. Validates action_type against allowlist."""

def list_patterns(*, enabled=None, trigger_event_kind=None) -> list[dict]: ...
def enable_pattern(pattern_id: str) -> bool: ...
def disable_pattern(pattern_id: str) -> bool: ...
def delete_pattern(pattern_id: str) -> bool: ...

# Audit
def list_recent_attempts(*, pattern_id=None, limit=50) -> list[dict]: ...

# Surface (for Mission Control)
def build_self_repair_surface() -> dict[str, object]: ...
```

**Validation ved register:**

```python
def register_pattern(...):
    if action_type not in _ACTION_HANDLERS:
        raise ValueError(f"action_type '{action_type}' not in allowlist: {sorted(_ACTION_HANDLERS)}")
    if not pattern_id or not name or not trigger_event_kind:
        raise ValueError("pattern_id, name, trigger_event_kind required")
    # ... insert, return persisted dict
```

**Tool wrappers** (v1 = NONE):
Per konservativ governance: ingen tool wrappers eksponeres til LLM. Brugeren registrerer patterns via Python REPL, MC endpoint (future), eller direkte DB-indsættelse.

**Audit access** (v1 = Python API only):
- `list_recent_attempts()` for direkte query
- Eventbus event-stream filtreret på `self_repair.*`
- Mission Control tab kommer som separat PR

## Error handling

**Princip:** Listener-thread må aldrig crashe. Match-fejl må aldrig dræbe processen. Action-handler-fejl bliver til failed-attempts, ikke crashes. Audit-write-fejl må ikke blokere action-execution.

| Lag | Behavior på fejl |
|-----|---------|
| Listener loop | Per-event try/except. Single bad event ≠ killed listener. |
| Pattern decode | Exception → skip pattern for this event, log debug. |
| Match evaluation | Predicate evaluator catches its own exceptions. Coercion failures → no match. |
| Action handler | try/except. Exception → recorded as failed attempt with str(exc)[:240]. |
| DB writes | Audit insert in try/except. Audit-write failure doesn't block action. |
| Cooldown check | Exception → return "db-error" (conservative — blocks action). |
| Discord notify | Wrapped try/except — Discord-down never blocks self-repair logic. |
| Eventbus publish | Best-effort try/except. Event-loss acceptable; DB is canonical. |
| Engine disabled | Fast path — no DB queries, no logs, no state mutation. |

**Concurrent access:**
- Multiple events sequentially in one listener thread.
- DB transactions per attempt isolate cooldown decisions.
- Auto-disable race: idempotent (`enabled=False` set twice is fine).

**Listener crash recovery:** If `_listener_loop` itself crashes (OOM, etc.), thread dies. No auto-restart in v1.

## Testing strategy

**Test-filer:**
- `tests/test_db_self_repair.py` — DB CRUD + cooldown queries
- `tests/test_self_repair_engine.py` — engine unit tests
- `tests/test_self_repair_settings.py` — RuntimeSettings fields
- `tests/test_self_repair_integration.py` — end-to-end eventbus → match → execute

### DB helpers (`test_db_self_repair.py`)

| Test | Verifies |
|------|----------|
| `test_insert_and_get_pattern` | Round-trip persistence. |
| `test_list_patterns_filters_enabled` | enabled filter works. |
| `test_list_patterns_filters_trigger_event_kind` | trigger filter works. |
| `test_update_pattern_partial_fields` | Can update single field. |
| `test_update_pattern_with_increment_fields` | Counter increments. |
| `test_count_recent_attempts_filters_outcome_and_time` | Cooldown query semantics. |
| `test_insert_attempt_records_outcome_and_error` | Audit log. |

### Engine units (`test_self_repair_engine.py`)

| Test | Verifies |
|------|----------|
| `test_register_pattern_validates_allowlist` | Unknown action_type → ValueError. |
| `test_register_pattern_persists_with_defaults` | Settings defaults applied. |
| `test_pattern_matches_event_exact_payload` | Direct equality. |
| `test_pattern_matches_event_predicate_gt` | gt predicate. |
| `test_pattern_matches_event_predicate_in` | in predicate. |
| `test_pattern_matches_event_predicate_regex` | regex predicate. |
| `test_pattern_does_not_match_wrong_kind` | Kind mismatch. |
| `test_pattern_does_not_match_missing_payload_key` | Missing key. |
| `test_check_cooldown_ok_when_no_recent_attempts` | First attempt OK. |
| `test_check_cooldown_blocks_within_cooldown_seconds` | Recently executed → blocked. |
| `test_check_cooldown_blocks_at_window_cap` | Window cap → blocked. |
| `test_check_cooldown_returns_db_error_on_query_failure` | Conservative on DB error. |
| `test_attempt_repair_executes_action_and_records_executed` | Happy path. |
| `test_attempt_repair_records_failed_on_handler_exception` | Handler raises → failed. |
| `test_attempt_repair_skips_when_action_not_in_allowlist` | Defense in depth. |
| `test_attempt_repair_skips_when_cooldown_blocks` | Rate-limited. |
| `test_record_failed_triggers_auto_disable_at_threshold` | 3 failures → enabled=False. |
| `test_engine_disabled_skips_all_processing` | Settings flag false → no work. |
| `test_unknown_event_kind_skipped_silently` | No matching pattern → no work. |

### Settings (`test_self_repair_settings.py`)

`test_self_repair_settings_have_defaults` — All 6 fields present with documented defaults.

### Integration (`test_self_repair_integration.py`)

| Test | Verifies |
|------|----------|
| `test_eventbus_publish_triggers_matched_pattern_action` | Full flow: publish → audit shows executed + control_daemon called. |
| `test_listener_starts_and_stops_cleanly` | start_listener idempotent; stop_listener exits within 2s. |
| `test_disabled_pattern_does_not_fire` | enabled=False → no execution. |
| `test_matched_event_for_disabled_engine_does_nothing` | Settings flag false → no execution. |
| `test_failed_action_publishes_failure_event_and_pings_owner` | Handler raises → failure event observed; notify_owner called. |

### Test infrastruktur

- `isolated_runtime` fixture for SQLite + sys.path setup.
- Monkeypatch `core.services.daemon_manager.control_daemon` so allowlisted handler exercised without real daemons.
- Monkeypatch `_notify_owner_async` to record calls.
- Listener tests use 2s timeout + explicit `stop_listener()` in teardown.
- Time-sensitive tests (cooldown windows) freeze `_now()` via monkeypatch.
- Eventbus integration: `event_bus.publish(...)` then poll DB for attempt row up to 1s.

**TDD-rækkefølge:** test_settings → settings impl → test_db helpers → DB module → test_engine pure functions (decode/match/cooldown) → engine functions → test_engine attempt_repair → execution paths → test_engine register/list/enable → public API → test_integration listener → listener wiring → final smoke.

## Future extensions

Eksplicit committed under brainstormen, til senere iterations:

1. **Første aktiverede pattern (v2-PR)**: `daemon-mail-checker-overdue-restart` (eller anden konkret daemon Bjørn vælger). Separat PR med ~50 linjer kode (ét `register_pattern()` kald + tests) der validerer framework'et i drift.

2. **Mission Control tab + endpoint** (`/mc/self-repair`): UI viser registered patterns, recent attempts (success/fail timeline), kill-switch, per-pattern enable/disable. `build_self_repair_surface()` API'et er klar i v1; routen og frontenden kommer som separat PR.

3. **Tool wrappers til LLM**: `register_self_repair_pattern`, `disable_self_repair_pattern`, `list_self_repair_patterns`. Først efter learning-promotion er bevist, da tools per definition er LLM-instigated og ville bryde "Jarvis kan ikke selv skabe autonome patterns" governance-grænsen.

4. **Learning-driven promotion (Jarvis' D1-vision)**: Nyt komponent der observerer manuelle restarts/recoveries og lærer hvilke (detection, action)-par der gentages med succes. Når et mønster har N gentagelser med 100% success → auto-promote til registreret pattern (source='learning_policy'). Skriver til `self_repair_patterns` via samme `register_pattern()` API. Kræver target-success-verification (#5).

5. **Action verification + adaptive cooldown**: Engine verificerer efter action om target faktisk recoverede (fx daemon nu running + senest tick inden for forventet vindue). Success → reset cooldown. Failure → record som failed selv om handler ikke raise'd. Kræver per-action verifikator-funktion.

6. **Udvidet action allowlist**: Andre safe ops-actions:
   - `mark_provider_unhealthy(provider_name)` — auto-skip flapping providers
   - `flush_state_key(key)` — clear corrupted runtime_state entries
   - `reload_settings()` — pick up config changes
   Hver tilføjelse er sin egen lille PR med eksplicit governance-review.

7. **Nested payload predicates**: Tilføj `path` predicate så `trigger_match` kan referere fx `payload.evidence.tool` for dybere matching. Brugbart når learning-promotion finder patterns i dyb event-payload struktur.

8. **Cross-pattern coordination**: Forhindr to patterns i at fyre konkurrerende actions (fx restart + disable på samme target). Lock per target. Først nødvendigt med 5+ aktive patterns.

9. **Integration med emotional memory**: Når et self-repair udføres, capture en emotional anchor (anchor_type="self_repair") så Jarvis husker situationen. Lader emotional precedent surface advare ham hvis repair-patterns er knyttet til specifikke moods.

## Out-of-scope for this design

- Self-repair af kode (auto-fix bugs ved at editere filer). Vi rører kun runtime-state via daemon control.
- Self-modification af engine-koden selv. Engine er statisk; kun pattern-DB'en er dynamisk.
- Multi-host self-repair (fx restart en daemon på en anden maskine). Lokal proces-kontrol kun.
- Rollback efter failed action. Hver action er forventet at være idempotent og safe at retry; rollback-semantik er future scope.
