# Intelligent Central — Fundament (§13.1 + §13.2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Byg Centralens fundament — `observe`-ansigt, trace-sink, boundary-capture/fejl-catcher, live-switches, circuit-breaker, flag-on-change-skelet — oven på det eksisterende `gate_kernel`, plus en fit-pass-katalog over alle nerver. INGEN cluster instrumenteres endnu.

**Architecture:** Centralen *komponerer* `gate_kernel` (som beholder registry + isoleret `decide`/run_phase) og tilføjer fire flade single-responsibility-moduler: `central_capture` (grænse-fangst), `central_trace` (ring-buffer-sink), `central_switches` (live on/off + circuit-breaker m. sikkerheds-invariant), `central_core` (facade: `observe`/`decide`/`register`). `central_catalog` holder fit-pass-resultatet som deklarativ data. Alt best-effort og selv-sikkert: fejl-fangst må aldrig vælte et run; sikkerheds-beslutninger fail-closed.

**Tech Stack:** Python 3.11 (conda `ai`), pytest, `core/services/gate_kernel.py` (Decision/Verdict/GateClass/kernel), `core/services/shared_cache.py` (flag-lager m. TTL), `core/eventbus/bus.py` (event_bus.publish).

**Kør tests:** `source /opt/conda/etc/profile.d/conda.sh && conda activate ai && python -m pytest tests/test_central_*.py -v`
**Coverage-gate:** hvert nyt `core/services/central_X.py` KRÆVER eksakt `tests/test_central_X.py` (ellers stille commit-fejl).

---

## Filstruktur (låses her)

| Fil | Ansvar |
|---|---|
| `core/services/central_capture.py` | `ErrorRecord` + `safe_call()` — kør en nerve bag en grænse; returnér (resultat, ErrorRecord\|None); kaster ALDRIG (§10.1/10.2/10.3) |
| `core/services/central_trace.py` | `TraceRecord` + `TraceSink` (ring-buffer, trådsikker) + `sink()` singleton (§3.2/§7) |
| `core/services/central_switches.py` | `set_enabled/is_enabled` (live on/off, sikkerheds-invariant §11.3) + `CircuitBreaker` (§11.2) + `drift_flag()` (flag-on-change-skelet §7) |
| `core/services/central_core.py` | `Central` facade: `observe()` + `decide()` + `register()`; `central()` singleton; komponerer kernel+capture+trace+switches (§3.1) |
| `core/services/central_catalog.py` | `NerveSpec` + `CATALOG` (fit-pass-resultat §13.2) + `by_cluster/clusters/validate` |
| `tests/test_central_capture.py` … `tests/test_central_catalog.py` | én test-fil pr. modul (coverage-gate) |
| `docs/notes/2026-06-21-central-fitpass.md` | menneskelæsbar fit-pass-rapport (Task 11) |

---

## Task 1: central_capture — boundary-capture (§10)

**Files:**
- Create: `core/services/central_capture.py`
- Test: `tests/test_central_capture.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_central_capture.py
"""Tests for boundary-capture (§10): safe_call kaster ALDRIG."""
from __future__ import annotations

from core.services.central_capture import safe_call, ErrorRecord
from core.services.gate_kernel import GateClass


def test_safe_call_success_returns_result_and_no_error():
    result, err = safe_call(lambda c: {"decision": "green"}, {"run_id": "r1"}, nerve="n")
    assert result == {"decision": "green"} and err is None


def test_safe_call_exception_is_captured_not_raised():
    def boom(c):
        raise ValueError("nede")
    result, err = safe_call(boom, {"run_id": "r1", "session_id": "s1"},
                            nerve="n", cluster="loop", klass=GateClass.SECURITY)
    assert result is None
    assert isinstance(err, ErrorRecord)
    assert err.kind == "exception" and "ValueError" in err.message
    assert err.nerve == "n" and err.cluster == "loop" and err.klass is GateClass.SECURITY
    assert err.signal == {"run_id": "r1", "session_id": "s1"}
    assert err.stack  # ikke-tom stacktrace


def test_safe_call_malformed_ctx_is_captured():
    result, err = safe_call(lambda c: None, "ikke-en-dict", nerve="n")
    assert result is None and err.kind == "malformed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source /opt/conda/etc/profile.d/conda.sh && conda activate ai && python -m pytest tests/test_central_capture.py -v`
Expected: FAIL (`ModuleNotFoundError: core.services.central_capture`)

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/central_capture.py
"""Boundary-capture for Centralen (§10). Kør en nerve bag en grænse: enhver
exception, malformet input eller anomali fanges og returneres som ErrorRecord —
funktionen kaster ALDRIG selv (§10.3 selv-sikker)."""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from core.services.gate_kernel import GateClass


@dataclass
class ErrorRecord:
    nerve: str
    cluster: str
    kind: str                      # exception|timeout|malformed|sink_down|learning_down|cascade|catcher
    message: str
    klass: GateClass = GateClass.COGNITIVE
    latency_ms: int = 0
    stack: str = ""
    signal: dict[str, Any] | None = None


def safe_call(fn: Callable[[dict], Any], ctx: Any, *, nerve: str = "",
              cluster: str = "", klass: GateClass = GateClass.COGNITIVE
              ) -> tuple[Any, ErrorRecord | None]:
    """Returnér (resultat, None) ved succes, ellers (None, ErrorRecord). Kaster aldrig."""
    t0 = time.monotonic()
    if not isinstance(ctx, dict):
        return None, ErrorRecord(nerve, cluster, "malformed",
                                 f"ctx ikke dict: {type(ctx).__name__}", klass)
    try:
        return fn(ctx), None
    except Exception as e:  # noqa: BLE001 — grænse-fangst er hele pointen
        return None, ErrorRecord(
            nerve, cluster, "exception", f"{type(e).__name__}: {e}", klass,
            int((time.monotonic() - t0) * 1000), traceback.format_exc(),
            {k: ctx.get(k) for k in ("run_id", "session_id")},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_central_capture.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_capture.py tests/test_central_capture.py
git commit -m "feat(central): boundary-capture (§10) — safe_call fanger alt, kaster aldrig"
```

---

## Task 2: central_trace — ring-buffer-sink (§3.2/§7)

**Files:**
- Create: `core/services/central_trace.py`
- Test: `tests/test_central_trace.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_central_trace.py
"""Tests for trace-sink: volumen-tolerant ring-buffer, nøglet på run_id."""
from __future__ import annotations

from core.services.central_trace import TraceRecord, TraceSink, sink


def _rec(run_id="r1", nerve="n", kind="decide"):
    return TraceRecord(run_id=run_id, session_id="s", cluster="loop", nerve=nerve, kind=kind)


def test_records_for_run_filters_by_run_id():
    sk = TraceSink(maxlen=100)
    sk.record(_rec(run_id="r1", nerve="a"))
    sk.record(_rec(run_id="r2", nerve="b"))
    sk.record(_rec(run_id="r1", nerve="c"))
    got = sk.records_for_run("r1")
    assert [r.nerve for r in got] == ["a", "c"]


def test_ringbuffer_drops_oldest_beyond_maxlen():
    sk = TraceSink(maxlen=3)
    for i in range(5):
        sk.record(_rec(run_id=str(i)))
    recent = sk.recent(limit=10)
    assert len(recent) == 3
    assert [r.run_id for r in recent] == ["2", "3", "4"]


def test_sink_singleton_is_stable():
    assert sink() is sink()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_central_trace.py -v`
Expected: FAIL (`ModuleNotFoundError: core.services.central_trace`)

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/central_trace.py
"""Trace-sink for Centralen (§3.2/§7). En trådsikker, volumen-tolerant ring-buffer
af strukturerede records nøglet på run_id. Slip ALDRIG en exception ud (selv-sikker)."""
from __future__ import annotations

import collections
import threading
from dataclasses import dataclass
from typing import Any

_MAX = 2000


@dataclass
class TraceRecord:
    run_id: str
    session_id: str
    cluster: str
    nerve: str
    kind: str                       # decide|observe|error
    decision: str = ""
    reason: str = ""
    latency_ms: int = 0
    payload: dict[str, Any] | None = None


class TraceSink:
    def __init__(self, maxlen: int = _MAX) -> None:
        self._buf: "collections.deque[TraceRecord]" = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self.dropped = 0

    def record(self, rec: TraceRecord) -> None:
        try:
            with self._lock:
                self._buf.append(rec)
        except Exception:
            self.dropped += 1

    def records_for_run(self, run_id: str) -> list[TraceRecord]:
        with self._lock:
            return [r for r in self._buf if r.run_id == run_id]

    def recent(self, limit: int = 50) -> list[TraceRecord]:
        with self._lock:
            return list(self._buf)[-limit:]


_SINK: TraceSink | None = None


def sink() -> TraceSink:
    global _SINK
    if _SINK is None:
        _SINK = TraceSink()
    return _SINK
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_central_trace.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_trace.py tests/test_central_trace.py
git commit -m "feat(central): trace-sink (§3.2/§7) — trådsikker ring-buffer nøglet på run_id"
```

---

## Task 3: central_switches — live on/off + sikkerheds-invariant (§11.1/§11.3)

**Files:**
- Create: `core/services/central_switches.py`
- Test: `tests/test_central_switches.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_central_switches.py
"""Tests for live-switches + circuit-breaker + drift-flag."""
from __future__ import annotations

import core.services.central_switches as sw
from core.services.gate_kernel import GateClass


def test_set_and_read_enabled(monkeypatch):
    store = {}
    monkeypatch.setattr(sw.shared_cache, "set", lambda k, v, ttl_seconds: store.__setitem__(k, v))
    monkeypatch.setattr(sw.shared_cache, "get", lambda k: store.get(k))
    assert sw.is_enabled("nerve", "fact_gate") is True            # default ON
    sw.set_enabled("nerve", "fact_gate", False)
    assert sw.is_enabled("nerve", "fact_gate") is False


def test_security_nerve_cannot_be_disabled(monkeypatch):
    store = {}
    monkeypatch.setattr(sw.shared_cache, "set", lambda k, v, ttl_seconds: store.__setitem__(k, v))
    monkeypatch.setattr(sw.shared_cache, "get", lambda k: store.get(k))
    res = sw.set_enabled("nerve", "auth", False, klass=GateClass.SECURITY)
    assert res["ok"] is False
    assert sw.is_enabled("nerve", "auth") is True                 # uændret — kan ikke slukkes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_central_switches.py -v`
Expected: FAIL (`ModuleNotFoundError: core.services.central_switches`)

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/central_switches.py
"""Live-kontrol for Centralen (§11). On/off pr. nerve/cluster via shared_cache-flag.
SIKKERHEDS-INVARIANT (§11.3): en sikkerheds-nerve kan ALDRIG slås fra — kun isoleres
mod deny. Plus CircuitBreaker (§11.2) og et minimalt drift-flag-skelet (§7)."""
from __future__ import annotations

import threading

from core.services import shared_cache
from core.services.gate_kernel import GateClass

_FLAG_TTL = 365 * 24 * 3600.0   # effektivt permanent indtil ændret


def _key(scope: str, name: str) -> str:
    return f"flag:central.switch.{scope}.{name}"


def set_enabled(scope: str, name: str, enabled: bool, *,
                klass: GateClass = GateClass.COGNITIVE) -> dict:
    """Slå en nerve/cluster on/off live. Sikkerheds-nerve + enabled=False afvises."""
    if klass is GateClass.SECURITY and not enabled:
        return {"ok": False, "scope": scope, "name": name,
                "reason": "sikkerheds-nerve kan ikke slås fra (kun isoleres mod deny)"}
    shared_cache.set(_key(scope, name), {"enabled": bool(enabled)}, ttl_seconds=_FLAG_TTL)
    return {"ok": True, "scope": scope, "name": name, "enabled": bool(enabled)}


def is_enabled(scope: str, name: str) -> bool:
    val = shared_cache.get(_key(scope, name))
    if isinstance(val, dict) and "enabled" in val:
        return bool(val["enabled"])
    return True   # default ON


class CircuitBreaker:
    """Tæl fejl pr. nerve; isolér efter `threshold` på stribe. Nulstil ved succes."""

    def __init__(self, threshold: int = 5) -> None:
        self.threshold = threshold
        self._fails: dict[str, int] = {}
        self._lock = threading.Lock()

    def record(self, nerve: str, ok: bool) -> bool:
        """Returnér True hvis kredsen NETOP blev (eller fortsat er) åben/isoleret."""
        with self._lock:
            if ok:
                self._fails[nerve] = 0
                return False
            self._fails[nerve] = self._fails.get(nerve, 0) + 1
            return self._fails[nerve] >= self.threshold

    def is_open(self, nerve: str) -> bool:
        with self._lock:
            return self._fails.get(nerve, 0) >= self.threshold

    def reset(self, nerve: str) -> None:
        with self._lock:
            self._fails[nerve] = 0


def drift_flag(name: str, value: float, *, baseline: float, tol: float) -> dict | None:
    """Flag-on-change-skelet (§7): returnér en flag-dict hvis |value-baseline| > tol,
    ellers None. Holdes bevidst simpelt; kalibrering kommer i cluster-planerne."""
    if abs(value - baseline) > tol:
        return {"metric": name, "value": value, "baseline": baseline,
                "delta": round(value - baseline, 4)}
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_central_switches.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_switches.py tests/test_central_switches.py
git commit -m "feat(central): live-switches m. sikkerheds-invariant (§11.3) + CircuitBreaker + drift-flag"
```

---

## Task 4: central_switches — CircuitBreaker + drift_flag tests

**Files:**
- Modify: `tests/test_central_switches.py` (tilføj tests; implementeringen findes fra Task 3)

- [ ] **Step 1: Write the failing test (tilføj nederst i filen)**

```python
def test_circuit_breaker_opens_after_threshold_consecutive_failures():
    cb = sw.CircuitBreaker(threshold=3)
    assert cb.record("n", ok=False) is False     # 1
    assert cb.record("n", ok=False) is False     # 2
    assert cb.record("n", ok=False) is True       # 3 → åben
    assert cb.is_open("n") is True


def test_circuit_breaker_resets_on_success():
    cb = sw.CircuitBreaker(threshold=2)
    cb.record("n", ok=False)
    cb.record("n", ok=True)                        # nulstil
    assert cb.is_open("n") is False
    assert cb.record("n", ok=False) is False       # tæller startede forfra


def test_drift_flag_fires_only_beyond_tolerance():
    assert sw.drift_flag("heed", 0.15, baseline=0.149, tol=0.05) is None
    flag = sw.drift_flag("heed", 0.30, baseline=0.149, tol=0.05)
    assert flag is not None and flag["metric"] == "heed"
```

- [ ] **Step 2: Run test to verify it passes (impl findes allerede)**

Run: `python -m pytest tests/test_central_switches.py -v`
Expected: PASS (5 passed total)

- [ ] **Step 3: Commit**

```bash
git add tests/test_central_switches.py
git commit -m "test(central): dæk CircuitBreaker-tærskel/reset + drift_flag-tolerance"
```

---

## Task 5: central_core.observe — telemetri-ansigt (§3.1)

**Files:**
- Create: `core/services/central_core.py`
- Test: `tests/test_central_core.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_central_core.py
"""Tests for Central-facaden: observe + decide."""
from __future__ import annotations

from core.services.central_core import Central
from core.services.central_trace import TraceSink
from core.services.gate_kernel import Decision, GateClass


def _central(emitted=None):
    sink = TraceSink(maxlen=100)
    emit = (lambda kind, payload: emitted.append((kind, payload))) if emitted is not None else (lambda k, p: None)
    return Central(sink=sink, emit=emit), sink


def test_observe_records_trace_and_emits():
    emitted = []
    c, sink = _central(emitted)
    c.observe({"run_id": "r1", "session_id": "s1", "cluster": "loop", "nerve": "budget", "rounds": 5})
    recs = sink.records_for_run("r1")
    assert len(recs) == 1 and recs[0].kind == "observe" and recs[0].nerve == "budget"
    assert recs[0].payload == {"rounds": 5}
    assert emitted and emitted[0][0] == "central.observed"


def test_observe_never_raises_on_bad_event():
    c, _ = _central()
    c.observe(None)        # må ikke kaste
    c.observe("nonsense")  # må ikke kaste
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_central_core.py -v`
Expected: FAIL (`ModuleNotFoundError: core.services.central_core`)

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/central_core.py
"""Den Intelligente Central — facade (§3.1). Komponerer gate_kernel (decide-motor)
med trace-sink, boundary-capture og live-switches. To ansigter: observe (asynkront
telemetri) + decide (synkron beslutning pr. nerve). Alt selv-sikkert."""
from __future__ import annotations

from typing import Any, Callable

from core.services import central_capture, central_switches, central_trace
from core.services.gate_kernel import (Decision, GateClass, GateKernel, Verdict,
                                       _normalize, _Gate, kernel)


def _default_emit(kind: str, payload: dict) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(kind, payload)
    except Exception:
        pass


def _coerce_verdict(nerve: str, raw: Any, klass: GateClass) -> Verdict:
    """Normalisér en nerve-returværdi til Verdict (genbruger kernens parser)."""
    v = _normalize(_Gate(nerve, "", lambda c: raw, klass, 1000, ""), raw)
    v.klass = klass
    return v


class Central:
    def __init__(self, *, k: GateKernel | None = None,
                 sink: central_trace.TraceSink | None = None,
                 breaker: central_switches.CircuitBreaker | None = None,
                 emit: Callable[[str, dict], None] | None = None) -> None:
        self._k = k or kernel()
        self._sink = sink or central_trace.sink()
        self._breaker = breaker or central_switches.CircuitBreaker()
        self._emit = emit or _default_emit

    # ── observe (asynkront-agtigt telemetri-ansigt) ─────────────────────
    def observe(self, event: Any) -> None:
        """Best-effort telemetri. Kaster ALDRIG (§10.3)."""
        try:
            if not isinstance(event, dict):
                return
            reserved = ("run_id", "session_id", "cluster", "nerve")
            rec = central_trace.TraceRecord(
                run_id=str(event.get("run_id") or ""),
                session_id=str(event.get("session_id") or ""),
                cluster=str(event.get("cluster") or ""),
                nerve=str(event.get("nerve") or ""),
                kind="observe",
                payload={k: v for k, v in event.items() if k not in reserved},
            )
            self._sink.record(rec)
            self._emit("central.observed", {
                "run_id": rec.run_id, "session_id": rec.session_id,
                "cluster": rec.cluster, "nerve": rec.nerve, "payload": rec.payload,
            })
        except Exception:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_central_core.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_core.py tests/test_central_core.py
git commit -m "feat(central): Central.observe — telemetri-ansigt, trace + emit, selv-sikker"
```

---

## Task 6: central_core.decide — happy path + fail-mode pr. klasse (§3.1/§9)

**Files:**
- Modify: `core/services/central_core.py` (tilføj `decide` + hjælpere)
- Modify: `tests/test_central_core.py` (tilføj tests)

- [ ] **Step 1: Write the failing test (tilføj i tests/test_central_core.py)**

```python
def test_decide_happy_path_records_verdict():
    c, sink = _central()
    v = c.decide("fact_gate", {"run_id": "r1", "session_id": "s1"},
                 lambda ctx: {"decision": "green"}, cluster="truth")
    assert v.decision is Decision.GREEN
    recs = sink.records_for_run("r1")
    assert recs and recs[-1].kind == "decide" and recs[-1].decision == "green"


def test_decide_cognitive_error_fails_open_skip():
    c, _ = _central()
    v = c.decide("budget", {"run_id": "r1"}, lambda ctx: (_ for _ in ()).throw(RuntimeError()),
                 cluster="loop", klass=GateClass.COGNITIVE)
    assert v.decision is Decision.SKIP            # fail-open


def test_decide_security_error_fails_closed_red():
    c, _ = _central()
    v = c.decide("auth", {"run_id": "r1"}, lambda ctx: (_ for _ in ()).throw(RuntimeError()),
                 cluster="auth", klass=GateClass.SECURITY)
    assert v.decision is Decision.RED and v.action == "block"   # fail-closed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_central_core.py -v`
Expected: FAIL (`AttributeError: 'Central' object has no attribute 'decide'`)

- [ ] **Step 3: Write minimal implementation (tilføj metoder i `Central`)**

```python
    # ── interne verdict-hjælpere ────────────────────────────────────────
    def _fail_verdict(self, nerve: str, klass: GateClass, reason: str) -> Verdict:
        if klass is GateClass.SECURITY:
            return Verdict(nerve, Decision.RED, reason, action="block", klass=klass)
        return Verdict(nerve, Decision.SKIP, reason, action="none", klass=klass)

    def _isolated_verdict(self, nerve: str, klass: GateClass) -> Verdict:
        if klass is GateClass.SECURITY:
            return Verdict(nerve, Decision.RED, "isoleret-deny", action="block", klass=klass)
        return Verdict(nerve, Decision.SKIP, "isoleret", action="none", klass=klass)

    def _record_error(self, err: "central_capture.ErrorRecord") -> None:
        try:
            self._sink.record(central_trace.TraceRecord(
                run_id=str((err.signal or {}).get("run_id") or ""),
                session_id=str((err.signal or {}).get("session_id") or ""),
                cluster=err.cluster, nerve=err.nerve, kind="error",
                reason=err.message, latency_ms=err.latency_ms,
                payload={"kind": err.kind, "klass": err.klass.value, "stack": err.stack},
            ))
            self._emit("central.error", {
                "nerve": err.nerve, "cluster": err.cluster, "kind": err.kind,
                "message": err.message, "klass": err.klass.value,
            })
        except Exception:
            pass

    # ── decide (synkront beslutnings-ansigt) ────────────────────────────
    def decide(self, nerve: str, ctx: Any, fn: Callable[[dict], Any], *,
               cluster: str = "", klass: GateClass = GateClass.COGNITIVE) -> Verdict:
        """Kør én nerve med boundary-capture + circuit-breaker + trace.
        Kognitiv fejl → SKIP (fail-open); sikkerhed → RED (fail-closed §9)."""
        result, err = central_capture.safe_call(fn, ctx, nerve=nerve, cluster=cluster, klass=klass)
        if err is not None:
            opened = self._breaker.record(nerve, ok=False)
            self._record_error(err)
            return self._isolated_verdict(nerve, klass) if opened \
                else self._fail_verdict(nerve, klass, err.message)
        self._breaker.record(nerve, ok=True)
        v = _coerce_verdict(nerve, result, klass)
        try:
            cdict = ctx if isinstance(ctx, dict) else {}
            self._sink.record(central_trace.TraceRecord(
                run_id=str(cdict.get("run_id") or ""), session_id=str(cdict.get("session_id") or ""),
                cluster=cluster, nerve=nerve, kind="decide",
                decision=v.decision.value, reason=v.reason, latency_ms=v.latency_ms))
        except Exception:
            pass
        return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_central_core.py -v`
Expected: PASS (5 passed total)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_core.py tests/test_central_core.py
git commit -m "feat(central): Central.decide — boundary-capture + fail-mode pr. klasse (§9)"
```

---

## Task 7: central_core.decide — live-switch + circuit-breaker-isolation (§11)

**Files:**
- Modify: `core/services/central_core.py` (læg switch/breaker-tjek FØRST i `decide`)
- Modify: `tests/test_central_core.py` (tilføj tests)

- [ ] **Step 1: Write the failing test (tilføj i tests/test_central_core.py)**

```python
import core.services.central_switches as _sw


def test_decide_disabled_cognitive_nerve_skips(monkeypatch):
    monkeypatch.setattr(_sw, "is_enabled", lambda scope, name: False)
    c, _ = _central()
    v = c.decide("budget", {"run_id": "r1"}, lambda ctx: {"decision": "red"}, klass=GateClass.COGNITIVE)
    assert v.decision is Decision.SKIP and v.reason == "disabled"


def test_decide_disabled_security_nerve_denies(monkeypatch):
    monkeypatch.setattr(_sw, "is_enabled", lambda scope, name: False)
    c, _ = _central()
    v = c.decide("auth", {"run_id": "r1"}, lambda ctx: {"decision": "green"}, klass=GateClass.SECURITY)
    assert v.decision is Decision.RED              # isoleret mod deny, ikke off


def test_decide_short_circuits_when_breaker_open():
    from core.services.central_switches import CircuitBreaker
    cb = CircuitBreaker(threshold=1)
    cb.record("budget", ok=False)                  # åbn kredsen
    c, _ = _central()
    c._breaker = cb
    calls = []
    c.decide("budget", {"run_id": "r1"}, lambda ctx: calls.append(1), klass=GateClass.COGNITIVE)
    assert calls == []                             # nerven blev IKKE kaldt (isoleret)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_central_core.py -v`
Expected: FAIL (disabled-nerve kaldes stadig; breaker-åben kortslutter ikke endnu)

- [ ] **Step 3: Write minimal implementation (indsæt FØRST i `decide`, før safe_call)**

```python
        # live-switch (§11.1) — sikkerheds-nerve kan ikke slukkes, kun deny'es
        if not central_switches.is_enabled("nerve", nerve):
            if klass is GateClass.SECURITY:
                return self._isolated_verdict(nerve, klass)
            return Verdict(nerve, Decision.SKIP, "disabled", klass=klass)
        # circuit-breaker allerede åben (§11.2) → isolér uden at kalde nerven
        if self._breaker.is_open(nerve):
            return self._isolated_verdict(nerve, klass)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_central_core.py -v`
Expected: PASS (8 passed total)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_core.py tests/test_central_core.py
git commit -m "feat(central): decide respekterer live-switch + isolerer ved åben circuit-breaker (§11)"
```

---

## Task 8: central_core — register + central() singleton

**Files:**
- Modify: `core/services/central_core.py` (tilføj `register` passthrough + `central()` singleton)
- Modify: `tests/test_central_core.py` (tilføj tests)

- [ ] **Step 1: Write the failing test (tilføj i tests/test_central_core.py)**

```python
def test_register_passes_through_to_kernel():
    from core.services.gate_kernel import GateKernel
    k = GateKernel(flag_reader=lambda key: None, emit=lambda kind, p: None)
    c = Central(k=k, sink=TraceSink())
    c.register("budget", "loop_phase", lambda ctx: None, klass=GateClass.COGNITIVE)
    assert {g.name for g in k.gates_for("loop_phase")} == {"budget"}


def test_central_singleton_is_stable():
    from core.services.central_core import central
    assert central() is central()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_central_core.py -v`
Expected: FAIL (`AttributeError: 'Central' object has no attribute 'register'`; `cannot import name 'central'`)

- [ ] **Step 3: Write minimal implementation**

```python
    # ── registry-passthrough til kernen ─────────────────────────────────
    def register(self, name: str, phase: str, fn: Callable[[dict], Any], *,
                 klass: GateClass = GateClass.COGNITIVE, timeout_ms: int = 1500,
                 flag_key: str = "") -> None:
        self._k.register(name, phase, fn, klass=klass, timeout_ms=timeout_ms, flag_key=flag_key)
```

Og nederst i filen:

```python
# Singleton — én Central pr. proces.
_CENTRAL: Central | None = None


def central() -> Central:
    global _CENTRAL
    if _CENTRAL is None:
        _CENTRAL = Central()
    return _CENTRAL
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_central_core.py -v`
Expected: PASS (10 passed total)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_core.py tests/test_central_core.py
git commit -m "feat(central): register-passthrough til kernen + central() singleton"
```

---

## Task 9: central_catalog — fit-pass-datamodel (§13.2)

**Files:**
- Create: `core/services/central_catalog.py`
- Test: `tests/test_central_catalog.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_central_catalog.py
"""Tests for fit-pass-kataloget: deklarativ nerve→cluster/klasse/mekanisme/fit."""
from __future__ import annotations

from core.services import central_catalog as cat
from core.services.gate_kernel import GateClass


def test_catalog_nonempty_and_has_loop_cluster():
    assert len(cat.CATALOG) >= 6
    assert "loop" in cat.clusters()


def test_by_cluster_filters():
    loop = cat.by_cluster("loop")
    names = {n.name for n in loop}
    assert "presentation_invariant" in names and "tool_budget" in names


def test_validate_is_green():
    assert cat.validate() == []          # ingen ugyldige felter


def test_security_clusters_marked_security():
    for spec in cat.CATALOG:
        if spec.cluster in ("auth", "privacy"):
            assert spec.klass is GateClass.SECURITY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_central_catalog.py -v`
Expected: FAIL (`ModuleNotFoundError: core.services.central_catalog`)

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/central_catalog.py
"""Fit-pass-katalog (§13.2): det maskinlæsbare resultat af kortlægningen af hver nerve.
Bruges senere som kilde til registrering. Fit = 'merge' (homogen, kan smelte sammen),
'instrument' (kald Centralen på stedet), 'leave' (er ikke en request-path-gate)."""
from __future__ import annotations

from dataclasses import dataclass

from core.services.gate_kernel import GateClass

_MECHANISMS = {"verdict", "inline", "daemon", "filter", "tool", "persistence", "validation"}
_FITS = {"merge", "instrument", "leave"}


@dataclass(frozen=True)
class NerveSpec:
    name: str
    cluster: str
    klass: GateClass
    mechanism: str     # se _MECHANISMS
    fit: str           # se _FITS
    location: str      # fil:linje eller modul


# Foreløbig: kun Loop- + Truth-clustrene er kortlagt (fra eksisterende Explore-mapping).
# Øvrige clusters fyldes når deres egne fit-passes køres (cluster-planerne).
CATALOG: tuple[NerveSpec, ...] = (
    # ── Loop-cluster ──
    NerveSpec("run_closure", "loop", GateClass.COGNITIVE, "daemon", "leave",
              "core/services/run_closure_gate.py"),
    NerveSpec("tool_budget", "loop", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/visible_runs.py:1754-2351"),
    NerveSpec("capability_cap", "loop", GateClass.COGNITIVE, "filter", "leave",
              "core/tools/tool_scoping.py"),
    NerveSpec("good_enough", "loop", GateClass.COGNITIVE, "tool", "leave",
              "core/services/good_enough_gate.py"),
    NerveSpec("checkpoints", "loop", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/agentic_checkpoints.py"),
    NerveSpec("presentation_invariant", "loop", GateClass.COGNITIVE, "validation", "instrument",
              "core/services/visible_runs.py:5758-5806"),
    # ── Truth-cluster (allerede adaptere) ──
    NerveSpec("claim_scanner", "truth", GateClass.COGNITIVE, "verdict", "merge",
              "core/services/claim_scanner.py"),
    NerveSpec("fact_gate", "truth", GateClass.COGNITIVE, "verdict", "merge",
              "core/services/fact_gate.py"),
    NerveSpec("diagnosis", "truth", GateClass.COGNITIVE, "verdict", "merge",
              "core/services/diagnosis_gate.py"),
)


def clusters() -> list[str]:
    return sorted({n.cluster for n in CATALOG})


def by_cluster(cluster: str) -> list[NerveSpec]:
    return [n for n in CATALOG if n.cluster == cluster]


def validate() -> list[str]:
    """Returnér liste af problemer (tom = grøn)."""
    problems: list[str] = []
    seen: set[str] = set()
    for n in CATALOG:
        if n.name in seen:
            problems.append(f"duplikat-nerve: {n.name}")
        seen.add(n.name)
        if n.mechanism not in _MECHANISMS:
            problems.append(f"{n.name}: ukendt mekanisme {n.mechanism!r}")
        if n.fit not in _FITS:
            problems.append(f"{n.name}: ukendt fit {n.fit!r}")
    return problems
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_central_catalog.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_catalog.py tests/test_central_catalog.py
git commit -m "feat(central): fit-pass-katalog (§13.2) — deklarativ nerve→cluster/klasse/mekanisme/fit"
```

---

## Task 10: Integrations-smoke + fuld suite

**Files:**
- Create: `tests/test_central_integration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_central_integration.py
"""Ende-til-ende-smoke: en nerve kører gennem Centralen, trace + verdict hænger sammen."""
from __future__ import annotations

from core.services.central_core import Central
from core.services.central_trace import TraceSink
from core.services.gate_kernel import Decision, GateClass


def test_full_cycle_decide_then_observe_traced_together():
    sink = TraceSink(maxlen=100)
    c = Central(sink=sink, emit=lambda k, p: None)
    v = c.decide("tool_budget", {"run_id": "rX", "session_id": "sX"},
                 lambda ctx: {"decision": "yellow", "reason": "tool-only=5"},
                 cluster="loop", klass=GateClass.COGNITIVE)
    c.observe({"run_id": "rX", "session_id": "sX", "cluster": "loop",
               "nerve": "tool_budget", "rounds": 5})
    recs = sink.records_for_run("rX")
    kinds = [r.kind for r in recs]
    assert v.decision is Decision.YELLOW
    assert "decide" in kinds and "observe" in kinds      # hele kæden på ét run_id
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_central_integration.py -v`
Expected: PASS (1 passed)

- [ ] **Step 3: Run HELE central-suiten + nabo-suiter (ingen regression)**

Run: `python -m pytest tests/test_central_capture.py tests/test_central_trace.py tests/test_central_switches.py tests/test_central_core.py tests/test_central_catalog.py tests/test_central_integration.py tests/test_gate_kernel.py tests/test_gate_adapters.py tests/test_gate_eval.py -v`
Expected: PASS (alle grønne — Centralen rører ikke de eksisterende gate-tests)

- [ ] **Step 4: Commit**

```bash
git add tests/test_central_integration.py
git commit -m "test(central): ende-til-ende-smoke — decide+observe traces på samme run_id"
```

---

## Task 11: Fit-pass-rapport (§13.2 menneskelæsbar)

**Files:**
- Create: `docs/notes/2026-06-21-central-fitpass.md`

- [ ] **Step 1: Skriv rapporten** (afledt direkte af `central_catalog.CATALOG`; én række pr. nerve med fil:linje, mekanisme, fit-beslutning og begrundelse). Tabel-kolonner: Nerve · Cluster · Klasse · Mekanisme · Fit · Lokation · Begrundelse. Inkludér en opsummering: hvor mange `merge` vs `instrument` vs `leave` pr. cluster, og hvilke clusters der mangler at blive fit-passet (alle undtagen loop+truth).

- [ ] **Step 2: Verificér at rapporten matcher kataloget**

Run: `python -c "from core.services import central_catalog as c; print(len(c.CATALOG), c.clusters(), c.validate())"`
Expected: `9 ['loop', 'truth'] []`

- [ ] **Step 3: Commit**

```bash
git add docs/notes/2026-06-21-central-fitpass.md
git commit -m "docs(central): fit-pass-rapport for loop+truth — resten afventer cluster-planer"
```

---

## Afslutning

Når alle 11 tasks er grønne:
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch (her: arbejdet er på `main`, så det er commit-verifikation + fuld suite, ikke merge).
- Kør fuld relevant suite: `python -m pytest tests/test_central_*.py tests/test_gate_*.py -v` → alt grønt.
- Deploy sker IKKE her: Centralen er endnu ikke kaldt fra nogen request-path (det er cluster-planerne B-H). Fundamentet er rent additivt — nul live-adfærdsændring.

---

## Self-Review (kørt mod specen)

**Spec-dækning §13.1:**
- observe-ansigt → Task 5 ✓
- decide-ansigt → Task 6 ✓ (genbruger kernens isolation)
- event-sink/trace-model → Task 2 ✓
- boundary-capture/fejl-catcher §10 → Task 1 (safe_call) + Task 6 (_record_error) ✓
- fejl-taksonomi §10.2 → `ErrorRecord.kind` (exception/malformed nu; timeout/sink_down/learning_down/cascade/catcher er enum-værdier klar til cluster-brug) ✓
- selv-sikker §10.3 → Task 5 (observe try/except) + Task 1 (safe_call kaster aldrig) ✓
- flag-on-change-skelet §7 → Task 3 `drift_flag` + Task 4 test ✓
- live-switches §11.1 → Task 3 `set_enabled/is_enabled` + Task 7 (decide respekterer) ✓
- circuit-breaker §11.2 → Task 3 `CircuitBreaker` + Task 7 (isolation) ✓
- sikkerheds-invariant §11.3 → Task 3 (kan ikke disable security) + Task 7 (security→deny ved disable/breaker) ✓
- hård invariant §9 (sikkerhed fail-closed) → Task 6 (`_fail_verdict` security→RED) ✓

**Spec-dækning §13.2:**
- fit-pass-datamodel → Task 9 ✓
- fit-pass-rapport → Task 11 ✓

**Placeholder-scan:** ingen TBD/TODO; alle kode-steps har komplet kode.

**Type-konsistens:** `Central(k=, sink=, breaker=, emit=)` ens i Task 5/6/7/8/10. `decide(nerve, ctx, fn, *, cluster, klass)` ens i Task 6/7/10. `NerveSpec(name, cluster, klass, mechanism, fit, location)` ens i Task 9. `set_enabled(scope, name, enabled, *, klass)` / `is_enabled(scope, name)` ens i Task 3/7. Decision/Verdict/GateClass importeret fra `gate_kernel` overalt.

**Bevidst udeladt (YAGNI til cluster-planerne):** faktisk wiring ind i visible_runs/request-path; timeout-baseret capture (kernen har allerede timeout i `decide`-motoren; Centralens `decide` her er den tynde per-nerve-grænse); DB-persistering af trace (ring-buffer + event_bus rækker til fundamentet).
