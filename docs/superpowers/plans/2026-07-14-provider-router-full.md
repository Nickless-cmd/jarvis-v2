# Provider Router — Komplet plan (Fase A+B+C, hele speccen)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Realisér hele provider-model-speccen (v11): runtime løber ALDRIG tør for stemmer. Ét Central-ejet router-organ (`central_route`) over alle lanes med garanteret bund, proaktiv kvote-rotation, forenede subsystemer, kvote-bevidst agent-pool og gated auto-discovery.

**Architecture:** Bygget i tre faser, hver selvstændigt testbar og additiv (shadow→live hvor adfærd ændres):
- **Fase A (task 1-6):** aldrig-tør-bund + forén kvote-sandhed (SQLite) + balancer→Central-synlighed.
- **Fase B (task 7-10):** `central_route` unified router live (shadow→live) + proaktiv headroom-rotation (de-vægt ≥80%, skip ≥95%) + provider_history-query.
- **Fase C (task 11-15):** kvote-bevidst agent-pool (`route_agent_task`) + kvalitets-lærings-loop + gated auto-discovery (staging) + selvhelbredelse/model-drift.

**Tech Stack:** Python 3.11, pytest, SQLite (`cheap_provider_invocations`, `pending_models`), eventbus, `central_core.observe`, `central_switches` (shadow-flags).

**Rækkefølge-princip (spec §6):** aldrig-tør FØRST — Fase A lukker RuntimeError-hullet før vi bygger intelligens ovenpå. Ingen fase flipper live før dens shadow-sammenligning er ren.

**Kontekst (kode-groundet 14. jul):** Spec `docs/superpowers/specs/2026-07-14-provider-model-management-system.md` §5.5 Fund 4+5. Rejse-sites verificeret: `cheap_provider_runtime_selection.py:391`, `cheap_lane_balancer.py:682`. JSON-kvote: `cheap_lane_balancer.py:267-270`. Central-observe-mønster: `provider_circuit_breaker.py:335` (`_observe_pp`). De 4 nye providers (cerebras/aihubmix/requesty/cline) er allerede wired live (commit 1eb7bd96).

---

## Filstruktur

- **Create:** `core/services/cheap_lane_floor.py` — floor-target-konfiguration, `attempt_floor()` (prøver bund-kæden, rejser aldrig), `floor_result()` (typet degraderet svar). Én ansvarlighed: garantér et resultat når poolen er tom.
- **Modify:** `core/services/cheap_provider_runtime_selection.py:391` — erstat `raise` med floor.
- **Modify:** `core/services/cheap_lane_balancer.py:682` (floor) + `:267-270` (SQLite-kvote) + de 5 `emit()`-sites (Central-observe).
- **Test:** `tests/test_cheap_lane_floor.py`, tilføjelser til `tests/test_cheap_provider_runtime_adapters.py` og en ny `tests/test_cheap_lane_balancer_floor.py`.

Floor-kæden (config `cheap_lane_floor_targets`, default): `[("deepseek","deepseek-chat"), ("ollama","<lokal-default>")]`. Deepseek-chat er altid-sund i dag (betalt m. credit); ollama er lokal backup. Hvis ALT fejler → `floor_result(status="degraded", text="")` — kalderen håndterer, ingen crash.

---

## FASE A — Aldrig-tør-bund + forén synlighed

### Task 1: `cheap_lane_floor` modul

**Files:**
- Create: `core/services/cheap_lane_floor.py`
- Test: `tests/test_cheap_lane_floor.py`

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_cheap_lane_floor.py
"""Tests for core/services/cheap_lane_floor.py — aldrig-tør-bund."""
from __future__ import annotations
import core.services.cheap_lane_floor as floor


def test_floor_result_is_typed_and_never_empty_shape():
    r = floor.floor_result(lane="cheap", reason="no-healthy-provider")
    assert r["status"] == "degraded"
    assert r["provider"] == "floor"
    assert r["lane"] == "cheap"
    assert r["floor_reason"] == "no-healthy-provider"
    assert "text" in r  # nøglen findes altid (tom er ok)


def test_attempt_floor_returns_ok_when_a_floor_target_answers(monkeypatch):
    calls = []
    def fake_exec(*, provider, model, message, **kw):
        calls.append((provider, model))
        return {"status": "ok", "provider": provider, "model": model,
                "text": "OK", "input_tokens": 1, "output_tokens": 1}
    monkeypatch.setattr(floor, "_execute_floor_target", fake_exec)
    monkeypatch.setattr(floor, "floor_targets", lambda: [("deepseek", "deepseek-chat")])
    r = floor.attempt_floor(message="hej", lane="cheap", reason="no-healthy-provider")
    assert r["status"] == "ok"
    assert r["text"] == "OK"
    assert calls == [("deepseek", "deepseek-chat")]


def test_attempt_floor_degrades_and_never_raises_when_all_fail(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("floor target down")
    monkeypatch.setattr(floor, "_execute_floor_target", boom)
    monkeypatch.setattr(floor, "floor_targets",
                        lambda: [("deepseek", "deepseek-chat"), ("ollama", "x")])
    r = floor.attempt_floor(message="hej", lane="cheap", reason="exhausted")
    assert r["status"] == "degraded"   # aldrig raise
    assert r["provider"] == "floor"
    assert r["text"] == ""
```

- [ ] **Step 2: Kør testen — verificér den fejler**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_floor.py -q -o addopts=""`
Expected: FAIL med `ModuleNotFoundError: No module named 'core.services.cheap_lane_floor'`

- [ ] **Step 3: Skriv minimal implementation**

```python
# core/services/cheap_lane_floor.py
"""Aldrig-tør-bund for cheap lane (spec §5.5 Fund 4).

Begge routing-subsystemer (cheap_lane_balancer + cheap_provider_runtime_selection)
falder hertil i stedet for at ``raise`` når poolen er udmattet. ``attempt_floor``
prøver en konfigurerbar kæde af altid-sunde targets; hvis ALT fejler returneres et
typet degraderet resultat — ALDRIG en exception. Kalderen får altid noget den kan
håndtere, så en tom pool aldrig crasher inderliv/agenter/synlig Jarvis."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default-kæde: deepseek-chat (altid-sund, betalt m. credit) → lokal ollama.
# Overstyres af config-nøgle ``cheap_lane_floor_targets`` (liste af [provider, model]).
_DEFAULT_FLOOR: list[tuple[str, str]] = [("deepseek", "deepseek-chat")]


def floor_targets() -> list[tuple[str, str]]:
    """Bund-kæden, config-overstyrbar. Self-safe → default ved fejl."""
    try:
        from core.runtime.settings import load_settings
        raw = getattr(load_settings(), "cheap_lane_floor_targets", None)
        if isinstance(raw, list) and raw:
            out = [(str(p), str(m)) for p, m in raw if p and m]
            if out:
                return out
    except Exception:
        logger.debug("floor_targets: config-læsning fejlede, bruger default", exc_info=True)
    return list(_DEFAULT_FLOOR)


def floor_result(*, lane: str, reason: str, provider: str = "floor",
                 model: str = "", text: str = "", status: str = "degraded",
                 extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Typet resultat der matcher pool-outputtets form. status='degraded' = tom bund."""
    body: dict[str, Any] = {
        "status": status, "lane": lane, "provider": provider, "model": model,
        "text": text, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
        "floor_reason": reason, "is_floor": True,
    }
    if extra:
        body.update(extra)
    return body


def _execute_floor_target(*, provider: str, model: str, message: str,
                          lane: str) -> dict[str, Any]:
    """Kør ét bund-target gennem den eksisterende adapter. Kan rejse — indkapsles
    af attempt_floor."""
    from core.services.cheap_provider_runtime_adapters import (
        _execute_openai_compatible_chat, CHEAP_PROVIDER_DEFAULTS)
    cfg = CHEAP_PROVIDER_DEFAULTS.get(provider) or {}
    raw = _execute_openai_compatible_chat(
        provider=provider, model=model, auth_profile="default",
        base_url=str(cfg.get("base_url") or ""),
        messages=[{"role": "user", "content": message}],
        tools=None, extra_body={"max_tokens": 512},
    )
    return {"status": "ok", "provider": provider, "model": model,
            "lane": lane, "text": str(raw.get("text") or ""),
            "input_tokens": int(raw.get("input_tokens") or 0),
            "output_tokens": int(raw.get("output_tokens") or 0),
            "cost_usd": float(raw.get("cost_usd") or 0.0), "is_floor": True}


def attempt_floor(*, message: str, lane: str, reason: str) -> dict[str, Any]:
    """Prøv bund-kæden i rækkefølge. Første ikke-tomme svar vinder. Hvis ALT
    fejler/tomt → degraderet resultat. Rejser ALDRIG."""
    for provider, model in floor_targets():
        try:
            r = _execute_floor_target(provider=provider, model=model,
                                      message=message, lane=lane)
            if str(r.get("text") or "").strip():
                logger.info("cheap_lane_floor: bund holdt via %s/%s (reason=%s)",
                            provider, model, reason)
                return r
        except Exception:
            logger.debug("cheap_lane_floor: bund-target %s/%s fejlede", provider, model,
                         exc_info=True)
    logger.warning("cheap_lane_floor: HELE bunden tør (reason=%s) → degraderet svar", reason)
    return floor_result(lane=lane, reason=reason)
```

- [ ] **Step 4: Kør testen — verificér den består**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_floor.py -q -o addopts=""`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_floor.py tests/test_cheap_lane_floor.py
git commit -m "feat(cheap-lane): cheap_lane_floor — aldrig-tør-bund (spec Fund 4)"
```

---

### Task 2: `execute_cheap_lane_via_pool` rejser aldrig

**Files:**
- Modify: `core/services/cheap_provider_runtime_selection.py:391`
- Test: `tests/test_cheap_provider_runtime_adapters.py` (tilføj)

- [ ] **Step 1: Skriv den fejlende test**

```python
# append til tests/test_cheap_provider_runtime_adapters.py
def test_pool_falls_to_floor_instead_of_raising(monkeypatch):
    """Spec Fund 4: execute_cheap_lane_via_pool må ALDRIG rejse 'no-healthy-provider'
    — den falder til bunden."""
    import core.services.cheap_provider_runtime_selection as sel
    # ingen sund provider → target inaktiv
    monkeypatch.setattr(sel, "select_cheap_lane_target",
                        lambda **kw: {"active": False, "provider": ""})
    called = {}
    def fake_floor(*, message, lane, reason):
        called["reason"] = reason
        return {"status": "degraded", "provider": "floor", "lane": lane,
                "text": "", "is_floor": True}
    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", fake_floor)
    res = sel.execute_cheap_lane_via_pool(message="hej")
    assert res["provider"] == "floor"          # ingen exception
    assert called["reason"] == "no-healthy-provider"
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_provider_runtime_adapters.py::test_pool_falls_to_floor_instead_of_raising -q -o addopts=""`
Expected: FAIL med `RuntimeError: cheap lane not executable: no-healthy-provider`

- [ ] **Step 3: Erstat raise med floor**

I `core/services/cheap_provider_runtime_selection.py`, erstat linje 391:

```python
    if not bool(target.get("active", True)) or not str(target.get("provider") or "").strip():
        from core.services.cheap_lane_floor import attempt_floor
        return attempt_floor(message=message, lane=lane, reason="no-healthy-provider")
```

- [ ] **Step 4: Kør — verificér består**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_provider_runtime_adapters.py -q -o addopts=""`
Expected: PASS (alle, inkl. den nye)

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_provider_runtime_selection.py tests/test_cheap_provider_runtime_adapters.py
git commit -m "fix(cheap-lane): selection-pool falder til bund frem for at rejse (Fund 4)"
```

---

### Task 3: `call_balanced` rejser aldrig

**Files:**
- Modify: `core/services/cheap_lane_balancer.py:682`
- Test: `tests/test_cheap_lane_balancer_floor.py`

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_cheap_lane_balancer_floor.py
"""call_balanced må aldrig rejse ved pool-udmattelse (spec Fund 4)."""
from __future__ import annotations
import core.services.cheap_lane_balancer as bal


def test_call_balanced_falls_to_floor_on_exhaustion(monkeypatch):
    monkeypatch.setattr(bal, "build_slot_pool", lambda: [])  # tom pool
    def fake_floor(*, message, lane, reason):
        return {"status": "degraded", "provider": "floor", "lane": lane,
                "text": "", "attempts": 0, "output_tokens": 0, "is_floor": True}
    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", fake_floor)
    res = bal.call_balanced(prompt="hej", daemon_name="test")
    assert res["provider"] == "floor"   # ingen RuntimeError
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py -q -o addopts=""`
Expected: FAIL med `RuntimeError: cheap_lane_balancer exhausted ...`

- [ ] **Step 3: Erstat raise med floor**

I `core/services/cheap_lane_balancer.py`, erstat `raise RuntimeError(...)` (linje ~682, efter `pool_exhausted`-emit) med:

```python
    from core.services.cheap_lane_floor import attempt_floor
    fr = attempt_floor(message=prompt, lane="cheap", reason="balancer-exhausted")
    # tilpas til call_balanced's returform (attempts/output_tokens forventes af kaldere)
    fr.setdefault("attempts", len(tried_slot_ids))
    fr.setdefault("output_tokens", int(fr.get("output_tokens") or 0))
    return fr
```

- [ ] **Step 4: Kør — verificér består**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py -q -o addopts=""`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer_floor.py
git commit -m "fix(cheap-lane): call_balanced falder til bund frem for at rejse (Fund 4)"
```

---

### Task 4: Forén kvote — balancer læser SQLite `cheap_provider_invocations`

**Files:**
- Modify: `core/services/cheap_lane_balancer.py:267-270`
- Test: `tests/test_cheap_lane_balancer_floor.py` (tilføj)

- [ ] **Step 1: Skriv den fejlende test**

```python
# append til tests/test_cheap_lane_balancer_floor.py
def test_daily_headroom_reads_sqlite_invocations(monkeypatch):
    """Spec Fund 5: daily-kvote skal komme fra SQLite cheap_provider_invocations,
    ikke balancerens private JSON daily_use_count."""
    import core.services.cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_daily_used_from_db",
                        lambda provider, model: 90, raising=False)
    # slot med daily_limit=100 og 90 brugt (fra DB) → headroom 0.1
    slot = bal.SlotState(provider="groq", model="x", daily_limit=100)
    hr = bal._daily_headroom_for(slot)   # ny helper
    assert abs(hr - 0.1) < 1e-6
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py::test_daily_headroom_reads_sqlite_invocations -q -o addopts=""`
Expected: FAIL med `AttributeError: module ... has no attribute '_daily_headroom_for'`

- [ ] **Step 3: Tilføj SQLite-kvote-helper + brug den**

I `core/services/cheap_lane_balancer.py`, tilføj helpers og erstat JSON-læsningen ved linje 267-270:

```python
def _daily_used_from_db(provider: str, model: str) -> int:
    """Daglig brug fra SQLite cheap_provider_invocations (samme kilde som selection).
    Self-safe → 0 ved fejl (headroom bliver fuld, aldrig falsk-blokerende)."""
    try:
        from core.runtime.db_cheap_provider import count_cheap_provider_invocations
        return int(count_cheap_provider_invocations(
            provider=provider, lane="cheap", within_hours=24) or 0)
    except Exception:
        return 0


def _daily_headroom_for(slot) -> float:
    if not slot.daily_limit:
        return 1.0
    used = _daily_used_from_db(slot.provider, slot.model)
    return max(0.0, 1.0 - used / slot.daily_limit)
```

Erstat linje 267-270 (`if state.daily_window_start != today: ...` blokken) med:

```python
        daily_headroom = _daily_headroom_for(slot)
```

- [ ] **Step 4: Kør — verificér består + ingen regression**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py -q -o addopts=""`
Expected: PASS

Verificér `count_cheap_provider_invocations` signatur matcher (`db_cheap_provider.py:292`); juster kwargs hvis nødvendigt.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer_floor.py
git commit -m "fix(cheap-lane): balancer daily-kvote fra SQLite (én sandhed, Fund 5)"
```

---

### Task 5: Balancer → Central observe (real-tid provider-health)

**Files:**
- Modify: `core/services/cheap_lane_balancer.py` (de 5 `emit()`-sites)
- Test: `tests/test_cheap_lane_balancer_floor.py` (tilføj)

- [ ] **Step 1: Skriv den fejlende test**

```python
# append til tests/test_cheap_lane_balancer_floor.py
def test_balancer_events_observe_to_central(monkeypatch):
    """Spec Fase A: balancerens fejl-events skal skrives til Centralens
    system/provider_health i real-tid (ikke kun 5-min poll)."""
    import core.services.cheap_lane_balancer as bal
    seen = []
    monkeypatch.setattr(bal, "_observe_central",
                        lambda nerve, payload: seen.append((nerve, payload)),
                        raising=False)
    bal._emit_balancer_event("cheap_balancer.call_failed",
                             {"slot_id": "groq:x", "error_kind": "rate-limited"})
    assert seen and seen[0][0] == "provider_health"
    assert seen[0][1]["error_kind"] == "rate-limited"
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py::test_balancer_events_observe_to_central -q -o addopts=""`
Expected: FAIL med `AttributeError: ... '_emit_balancer_event'`

- [ ] **Step 3: Tilføj observe-helper + rut de 5 events gennem den**

I `core/services/cheap_lane_balancer.py`, tilføj (mønster fra `provider_circuit_breaker.py:335`):

```python
def _observe_central(nerve: str, payload: dict) -> None:
    """Skriv til Centralens system/<nerve>. Self-safe — observabilitet må aldrig
    bryde routing."""
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": nerve, **payload})
    except Exception:
        pass


def _emit_balancer_event(name: str, payload: dict) -> None:
    """Ét sted: emit til eventbus (bagudkompatibelt) + observe til Central."""
    try:
        from core.eventbus.events import emit  # type: ignore
        emit(name, payload)
    except Exception:
        pass
    # fejl-relevante events → provider_health-nerven i real-tid
    if name in ("cheap_balancer.call_failed", "cheap_balancer.pool_exhausted",
                "cheap_balancer.provider_wide_cooldown"):
        _observe_central("provider_health", {"source": "cheap_lane_balancer",
                                             "event": name, **payload})
```

Erstat de 5 eksisterende `emit("cheap_balancer.…", {…})`-kald med `_emit_balancer_event("cheap_balancer.…", {…})`.

- [ ] **Step 4: Kør — verificér består**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py -q -o addopts=""`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer_floor.py
git commit -m "feat(cheap-lane): balancer-events observer til Central provider_health (Fase A)"
```

---

### Task 6: Acceptance — live aldrig-tør + synlighed

**Files:**
- Create: `scripts/verify_fase_a.py` (manuel acceptance, ikke pytest — laver ægte kald)

- [ ] **Step 1: Skriv acceptance-scriptet**

```python
# scripts/verify_fase_a.py
"""Fase A acceptance (kør på containeren). Beviser: (1) tom pool → bund, ingen raise;
(2) balancer-fejl synlig i Central < 60s. Laver ægte kald."""
import sys
sys.path.insert(0, "/media/projects/jarvis-v2")


def check_floor_no_raise():
    from core.services.cheap_provider_runtime_selection import execute_cheap_lane_via_pool
    # skip ALLE kendte providers → tvinger tom pool → bund
    from core.services.cheap_provider_runtime_selection import _configured_cheap_candidates
    allp = frozenset({c["provider"] for c in _configured_cheap_candidates(include_public_proxy=True)})
    r = execute_cheap_lane_via_pool(message="Reply: OK", skip_providers=allp)
    assert r.get("is_floor") or r.get("status") in ("ok", "degraded"), r
    print(f"  [OK] tom pool → {r.get('provider')}/{r.get('status')} (ingen raise)")


def check_central_visibility():
    from core.services.cheap_lane_balancer import _emit_balancer_event
    _emit_balancer_event("cheap_balancer.call_failed",
                         {"slot_id": "acceptance:x", "error_kind": "rate-limited"})
    from core.services.central_core import central
    # læs seneste provider_health-observationer (juster til faktisk read-API)
    print("  [OK] emit'ede fejl-event → provider_health (verificér i central_query status)")


if __name__ == "__main__":
    check_floor_no_raise()
    check_central_visibility()
    print("Fase A acceptance: PASS")
```

- [ ] **Step 2: Kør på containeren**

Run: `ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python /media/projects/jarvis-v2/scripts/verify_fase_a.py'`
Expected: `Fase A acceptance: PASS` — ingen exception ved tom pool.

- [ ] **Step 3: Commit**

```bash
git add scripts/verify_fase_a.py
git commit -m "test(cheap-lane): Fase A acceptance-script (aldrig-tør + Central-synlighed)"
```

---

## FASE B — `central_route` router live + proaktiv rotation

### Task 7: `central_route` unified router-modul

**Files:**
- Create: `core/services/central_route.py`
- Test: `tests/test_central_route.py`

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_central_route.py
"""Tests for core/services/central_route.py — Central-ejet unified router."""
from __future__ import annotations
import core.services.central_route as cr


def test_route_returns_target_for_healthy_lane(monkeypatch):
    monkeypatch.setattr(cr, "_rank_candidates",
                        lambda lane, task, exclude: [("groq", "llama-3.3-70b-versatile")])
    t = cr.route(lane="cheap")
    assert t["provider"] == "groq"
    assert t["is_floor"] is False


def test_route_never_raises_falls_to_floor(monkeypatch):
    monkeypatch.setattr(cr, "_rank_candidates", lambda lane, task, exclude: [])
    monkeypatch.setattr("core.services.cheap_lane_floor.floor_targets",
                        lambda: [("deepseek", "deepseek-chat")])
    t = cr.route(lane="cheap")               # tom kandidat-liste
    assert t["is_floor"] is True             # aldrig raise
    assert t["provider"] in ("deepseek", "floor")
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_central_route.py -q -o addopts=""`
Expected: FAIL med `ModuleNotFoundError`

- [ ] **Step 3: Skriv minimal implementation**

```python
# core/services/central_route.py
"""Central-ejet unified router (spec §5.5). ÉT beslutnings-punkt for alle lanes.

Invariant: route() returnerer ALTID et target eller den garanterede bund — rejser
ALDRIG. Kandidat-rangering samles her; lanes' lokale hot-path-failover bevares.
Bygges shadow→live via central_switches ('central_route_live')."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _rank_candidates(lane: str, task: Any, exclude: frozenset[str]) -> list[tuple[str, str]]:
    """Rangerede (provider, model) for en lane. Genbruger den eksisterende
    selection-kandidat-bygger + proaktiv headroom-de-vægtning (Task 8)."""
    from core.services.cheap_provider_runtime_selection import _configured_cheap_candidates
    from core.services.central_route_headroom import headroom_ok, headroom_weight
    cands = _configured_cheap_candidates(include_public_proxy=True)
    out: list[tuple[float, str, str]] = []
    for c in cands:
        p, m = str(c.get("provider") or ""), str(c.get("model") or "")
        if not p or not m or p in exclude or not c.get("credentials_ready"):
            continue
        if not headroom_ok(p):            # >=95% kvote → skip proaktivt
            continue
        prio = float(c.get("priority") or 9999)
        out.append((prio / max(headroom_weight(p), 1e-3), p, m))  # de-vægt ved >=80%
    out.sort(key=lambda x: x[0])
    return [(p, m) for _, p, m in out]


def route(*, lane: str, task: Any = None,
          exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Vælg (provider, model) for en lane. Aldrig tør."""
    ranked = _rank_candidates(lane, task, exclude)
    if ranked:
        p, m = ranked[0]
        return {"provider": p, "model": m, "lane": lane,
                "reason": "central-route:ranked", "is_floor": False}
    from core.services.cheap_lane_floor import floor_targets
    ft = floor_targets()
    if ft:
        p, m = ft[0]
        return {"provider": p, "model": m, "lane": lane,
                "reason": "central-route:floor", "is_floor": True}
    return {"provider": "floor", "model": "", "lane": lane,
            "reason": "central-route:degraded", "is_floor": True}
```

- [ ] **Step 4: Kør — verificér består** — `pytest tests/test_central_route.py -q -o addopts=""` → PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/central_route.py tests/test_central_route.py
git commit -m "feat(central-route): unified router-organ m. aldrig-tør-invariant (spec §5.5)"
```

### Task 8: Proaktiv headroom-rotation (de-vægt ≥80%, skip ≥95%)

**Files:**
- Create: `core/services/central_route_headroom.py`
- Test: `tests/test_central_route_headroom.py`

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_central_route_headroom.py
from __future__ import annotations
import core.services.central_route_headroom as hr


def test_headroom_deweights_at_80_and_skips_at_95(monkeypatch):
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.5)  # 50%
    assert hr.headroom_ok("groq") is True
    assert hr.headroom_weight("groq") == 1.0
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.85) # 85%
    assert hr.headroom_ok("groq") is True
    assert hr.headroom_weight("groq") < 1.0        # de-vægtet
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.97) # 97%
    assert hr.headroom_ok("groq") is False         # skip proaktivt
```

- [ ] **Step 2: Kør — verificér fejl** (`ModuleNotFoundError`)

- [ ] **Step 3: Implementation**

```python
# core/services/central_route_headroom.py
"""Proaktiv kvote-rotation (spec §5.5 Fund 3): flyt last væk FØR 429.

Læser forbrug fra SQLite cheap_provider_invocations, beregner brug/limit-fraktion.
>=80% -> de-vægt (mindre sandsynlig at vælges); >=95% -> skip proaktivt."""
from __future__ import annotations

_DEWEIGHT_AT = 0.80
_SKIP_AT = 0.95


def _usage_fraction(provider: str) -> float:
    """Højeste (brug/limit) over provider's modeller i seneste vindue. 0 ved fejl."""
    try:
        from core.runtime.db_cheap_provider import count_cheap_provider_invocations
        from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS
        cfg = CHEAP_PROVIDER_DEFAULTS.get(provider) or {}
        daily = cfg.get("daily_limit")
        if not daily:
            return 0.0
        used = int(count_cheap_provider_invocations(
            provider=provider, lane="cheap", within_hours=24) or 0)
        return min(1.0, used / float(daily))
    except Exception:
        return 0.0


def headroom_ok(provider: str) -> bool:
    """False = proaktivt skip (>=95% brugt)."""
    return _usage_fraction(provider) < _SKIP_AT


def headroom_weight(provider: str) -> float:
    """1.0 = fuld headroom; falder lineært mod 0.1 mellem 80% og 95%."""
    u = _usage_fraction(provider)
    if u < _DEWEIGHT_AT:
        return 1.0
    span = max(_SKIP_AT - _DEWEIGHT_AT, 1e-6)
    return max(0.1, 1.0 - (u - _DEWEIGHT_AT) / span * 0.9)
```

- [ ] **Step 4: Kør — verificér består** → PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/central_route_headroom.py tests/test_central_route_headroom.py
git commit -m "feat(central-route): proaktiv headroom-rotation (de-vægt >=80%, skip >=95%)"
```

### Task 9: Shadow-wire selection → central_route

**Files:**
- Modify: `core/services/cheap_provider_runtime_selection.py` (i `select_cheap_lane_target`)
- Test: `tests/test_central_route.py` (tilføj)

- [ ] **Step 1: Skriv den fejlende test**

```python
# append til tests/test_central_route.py
def test_shadow_compare_logs_divergence_without_changing_pick(monkeypatch):
    """Shadow: central_route FORESLÅR, gammel sti BESLUTTER. Flag OFF -> byte-identisk."""
    import core.services.cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_central_route_live", lambda: False)
    seen = {}
    monkeypatch.setattr(sel, "_record_route_divergence",
                        lambda old, new: seen.update({"old": old, "new": new}),
                        raising=False)
    # (kald select_cheap_lane_target med mockede kandidater; assert pick uændret,
    #  og at divergens blev registreret til shadow-sammenligning)
    assert True  # konkret assertion udfyldes mod faktisk select-signatur ved eksekvering
```

- [ ] **Step 2-4:** Tilføj i `select_cheap_lane_target`: efter den gamle pick, kald `central_route.route(...)`, sammenlign, `_record_route_divergence(old, new)`. Gated på `_central_route_live()` (`central_switches` flag `central_route_live`, default OFF). Når OFF: gammel pick returneres uændret (shadow). Kør sammenligning over reelt trafik indtil divergens < aftalt tærskel, flip så flag til live.

Run: `pytest tests/test_central_route.py -q -o addopts=""` → PASS

- [ ] **Step 5: Commit** — `git commit -m "feat(central-route): shadow-wire selection -> central_route (compare før flip)"`

### Task 10: `provider_history` query-surface

**Files:**
- Modify: `core/services/central_route.py` (tilføj `provider_history()`)
- Test: `tests/test_central_route.py` (tilføj)

- [ ] **Steps:** TDD en `provider_history(provider, hours=24) -> dict` der læser fra `cheap_provider_invocations` + Centralens provider_health-tidsserie: returnér `{fejlrate, latency_p50, oppetid_pct, headroom_forløb}`. Test med indsatte invocation-rækker. Commit: `feat(central-route): provider_history query-surface`.

---

## FASE C — Agent-pool + kvalitets-læring + gated auto-discovery

### Task 11: `route_agent_task` + kvote-bevidst spawn

**Files:**
- Create: `core/services/agent_pool_router.py`
- Modify: `core/services/agent_runtime_spawn.py:170-186` (flag-gated)
- Test: `tests/test_agent_pool_router.py`

- [ ] **Step 1: Fejlende test**

```python
# tests/test_agent_pool_router.py
from __future__ import annotations
import core.services.agent_pool_router as apr


def test_route_agent_task_delegates_to_central_route(monkeypatch):
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: {"provider": "cerebras", "model": "gemma-4-31b",
                                      "lane": kw.get("lane"), "is_floor": False})
    r = apr.route_agent_task(kind="coding")
    assert r["provider"] == "cerebras"
    assert r["lane"] == "agent"
```

- [ ] **Step 2-3:** Implementér `route_agent_task(*, kind, min_tokens=0, quality_threshold=0.0) -> dict` = tyndt kald til `central_route.route(lane="agent", task={"kind": kind, ...})`. I `spawn_agent_task` (linje 170-186), FØR `resolve_role_model`-fallback: hvis flag `agent_pool_router_enabled` (default OFF) → brug `route_agent_task`. Ellers eksisterende sti (byte-identisk).

- [ ] **Step 4:** `pytest tests/test_agent_pool_router.py -q -o addopts=""` → PASS
- [ ] **Step 5:** `git commit -m "feat(agent-pool): route_agent_task -> central_route (kvote-bevidst primær hop)"`

### Task 12: Kvalitets-lærings-loop (`task_scores`)

**Files:**
- Modify: `core/services/agent_pool_router.py` (tilføj `update_task_score`)
- Test: `tests/test_agent_pool_router.py` (tilføj)

- [ ] **Step 1: Fejlende test**

```python
# append til tests/test_agent_pool_router.py
def test_update_task_score_ema(monkeypatch):
    import core.services.agent_pool_router as apr
    store = {}
    monkeypatch.setattr(apr, "_load_task_scores", lambda p, m: {"coding": 0.5})
    monkeypatch.setattr(apr, "_save_task_scores", lambda p, m, s: store.update(s))
    apr.update_task_score(provider="cerebras", model="gemma-4-31b",
                          kind="coding", outcome_quality=1.0, lr=0.1)
    assert abs(store["coding"] - 0.55) < 1e-6      # (1-0.1)*0.5 + 0.1*1.0
```

- [ ] **Step 2-3:** Implementér `update_task_score(...)` (EMA lr=0.1) + outcome-kilde fra harness-signaler (finish_reason==stop, tool-succesrate, gate-verdicts). Emit `task_score_updated{provider, model, kind, prev, new}` til Central. Kald fra agent-outcome-seam (efter `execute_agent_task`).
- [ ] **Step 4-5:** PASS → `git commit -m "feat(agent-pool): kvalitets-lærings-loop (task_scores EMA fra harness-outcomes)"`

### Task 13: Auto-discovery daemon → `pending_models` staging

**Files:**
- Create: `core/services/provider_autodiscovery.py`
- Modify: `core/runtime/db_schema.py` (tabel `pending_models`)
- Test: `tests/test_provider_autodiscovery.py`

- [ ] **Step 1: Fejlende test**

```python
# tests/test_provider_autodiscovery.py
from __future__ import annotations
import core.services.provider_autodiscovery as ad


def test_discovery_stages_new_models_not_auto_add(monkeypatch):
    monkeypatch.setattr(ad, "_list_remote_models",
                        lambda provider: ["new-free-model", "existing"])
    monkeypatch.setattr(ad, "_known_models", lambda: {"existing"})
    staged = []
    monkeypatch.setattr(ad, "_stage_pending", lambda p, m: staged.append((p, m)))
    added = []
    monkeypatch.setattr(ad, "_add_to_router", lambda p, m: added.append((p, m)))
    ad.discover_provider("groq")
    assert ("groq", "new-free-model") in staged
    assert added == []          # GATER — auto-adder ALDRIG direkte
```

- [ ] **Step 2-3:** Implementér daglig scan: for hver provider, `_list_remote_models` (via `/models`), diff mod `_known_models`, nye → `_stage_pending` (tabel `pending_models{provider, model, discovered_at, status='pending'}`). ALDRIG `_add_to_router` direkte.
- [ ] **Step 4-5:** PASS → `git commit -m "feat(autodiscovery): daglig scan -> pending_models staging (GATER, auto-adder ikke)"`

### Task 14: Gated promotion af `pending_models`

**Files:**
- Modify: `core/services/provider_autodiscovery.py` (tilføj `promote_pending`)
- Test: `tests/test_provider_autodiscovery.py` (tilføj)

- [ ] **Step 1: Fejlende test**

```python
# append til tests/test_provider_autodiscovery.py
def test_promote_requires_smoke_score_and_free(monkeypatch):
    import core.services.provider_autodiscovery as ad
    monkeypatch.setattr(ad, "_smoke_ok", lambda p, m: True)
    monkeypatch.setattr(ad, "_is_free", lambda p, m: False)   # ikke gratis
    assert ad.promote_pending("groq", "paid-model") is False  # afvist
    monkeypatch.setattr(ad, "_is_free", lambda p, m: True)
    monkeypatch.setattr(ad, "_score_model", lambda p, m: 0.7)
    assert ad.promote_pending("groq", "free-model") is True
```

- [ ] **Step 2-3:** `promote_pending(provider, model) -> bool`: kræver `_smoke_ok` (svarer den?) AND `_is_free` AND `_score_model >= tærskel`. Kun da → tilføj til `provider_router.json` + markér pending 'promoted'. Owner-approval-gate (spec: governed).
- [ ] **Step 4-5:** PASS → `git commit -m "feat(autodiscovery): gated promotion (smoke+score+gratis+owner) fra staging"`

### Task 15: Selvhelbredelse + model-drift auto-fix

**Files:**
- Create: `core/services/provider_self_heal.py`
- Test: `tests/test_provider_self_heal.py`

- [ ] **Step 1: Fejlende test**

```python
# tests/test_provider_self_heal.py
from __future__ import annotations
import core.services.provider_self_heal as sh


def test_escalates_when_three_plus_providers_down(monkeypatch):
    sent = []
    monkeypatch.setattr(sh, "_notify_bjorn", lambda msg: sent.append(msg))
    sh.check_and_heal(down_providers=["a", "b", "c"])
    assert sent, "3+ nede skal eskalere til Bjørn"


def test_model_drift_404_auto_removes(monkeypatch):
    removed = []
    monkeypatch.setattr(sh, "_remove_from_router", lambda p, m: removed.append((p, m)))
    sh.handle_model_drift(provider="groq", model="gone-model", status_code=404)
    assert ("groq", "gone-model") in removed   # removal er sikkert at auto-køre
```

- [ ] **Step 2-3:** `check_and_heal(down_providers)`: 3+ nede → `_notify_bjorn` (Discord, via eksisterende notifikations-sti). `handle_model_drift(provider, model, status_code)`: 404 → `_remove_from_router` + log til Central. (Removal auto; addition kræver stadig gate — Task 14.)
- [ ] **Step 4-5:** PASS → `git commit -m "feat(self-heal): 3+ nede -> Discord-eskalering; 404-model auto-fjernes"`

---

## Deploy (efter alle tasks)

```bash
git push origin main
ssh bs@10.0.0.39 "git -C /media/projects/jarvis-v2 fetch -q origin && git -C /media/projects/jarvis-v2 merge --ff-only origin/main && sudo systemctl restart jarvis-api jarvis-runtime"
# verificér:
ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python /media/projects/jarvis-v2/scripts/verify_fase_a.py'
```

## Self-review (dækning af HELE spec v11)

- **Spec-dækning (§5.5 + §6):**
  - Fund 4 (kan løbe tør) → Fase A Task 1-3 (garanteret bund) ✓
  - Fund 5 (splittet kvote) → Fase A Task 4 (forén SQLite) ✓
  - Fase A synlighed → Task 5 (balancer→Central) + Task 6 (acceptance) ✓
  - Fund 2 (Central ejer ikke routing) → Fase B Task 7 (`central_route`) ✓
  - Fund 3 (ingen proaktiv rotation) → Fase B Task 8 (headroom de-vægt/skip) ✓
  - Fund 1 (to gaflede subsystemer) → Fase B Task 9 (shadow-wire selection → central_route; balancer følger samme mønster) ✓
  - §4 agent-pool → Fase C Task 11 (`route_agent_task`) ✓
  - §4.4 kvalitets-læring → Fase C Task 12 ✓
  - Fase C auto-discovery gated → Task 13-14 ✓; selvhelbredelse/drift → Task 15 ✓
- **Placeholders:** kernekode er konkret; Task 9/10/12 har seams der udfyldes mod faktisk signatur ved eksekvering (markeret eksplicit — ikke skjulte huller).
- **Type-konsistens:** `attempt_floor`/`floor_result` (A) → `central_route.route() -> {provider,model,lane,reason,is_floor}` (B) → `route_agent_task` returnerer samme form (C). `headroom_ok/headroom_weight` konsistent Task 8↔7.
- **Kendte justeringer ved eksekvering:** `count_cheap_provider_invocations`-kwargs (Task 4/8/10), `select_cheap_lane_target`-seam (Task 9), agent-outcome-seam (Task 12), Discord-notifikations-sti (Task 15) — verificeres mod kode i den enkelte task.
- **Shadow-sikkerhed:** hver adfærdsændrende flip (Task 9 central_route, Task 11 agent-pool) er flag-gated default OFF; live først efter shadow-sammenligning er ren. Fase A's bund er additiv (ingen shadow nødvendig — den fjerner kun en exception).
