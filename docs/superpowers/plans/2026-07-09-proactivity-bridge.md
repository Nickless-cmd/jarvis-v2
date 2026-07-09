# Proaktivitets-broen — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route Jarvis' inner questions/initiatives/wonder to Bjørn through a presence-aware contact-gate + shared caps, reusing the existing notification stack (hybrid: urgent single / else digest / else observe suppressed; live-governed, kill-switch, fail-closed for sending).

**Architecture:** One module `core/services/proactivity_bridge.py` — pure decision functions (classify/select/should_reach_owner/build_*) + an I/O orchestrator tick that collects from existing sources, decides, and routes via `route_proactive_notification`, recording into action_router's shared `proactive_log` cap ledger. A cadence producer runs it; a read-only Central route + `jc proactivity` surface its decisions. No new fragment generators.

**Tech Stack:** Python 3.11, pytest, existing `notification_router`/`action_router`/`initiative_queue`/`central_switches`/`internal_cadence`.

**Execution note:** Task 2 (pure functions + tests) → fresh **haiku** subagent (full code below). Tasks 1, 3, 4, 5 (real-presence resolution, I/O orchestrator, wiring, deploy) → **Claude inline** (fragile — real signals + hot-path + governance).

---

## Task 1 (Claude inline): pin the two uncertain APIs

**Goal:** Before writing the I/O layer, verify two names on the live codebase so Task 3's code is correct:

- [ ] **Step 1: Real owner-presence.** Confirm how "is Bjørn *really* visible now" is determined — NOT Jarvis' autonomous runs (the [[reference_outreach_ntfy_blindness]] bug). Verify:
  - `core/services/notification_router.py:362` `_app_device_live(uid)` (device actively pinging).
  - Find the freshest owner-visible chat signal: `grep -rn "def.*last.*visible\|owner.*last.*seen\|def recent_visible_runs\|visible.*owner\|def.*user_active" core/services core/runtime | grep -iv autonomous`. Pick the function that returns the timestamp/bool of the **owner's** last *visible* (non-autonomous) activity. Record its exact name+signature.
  - Decision rule to implement in Task 3's `_owner_presence()`: owner is "present" if `_app_device_live(owner_uid)` **or** owner's last visible activity was < `_PRESENT_WINDOW_S` (900s) ago. "away_seconds" = now − last owner-visible.

- [ ] **Step 2: Cap-ledger record fn.** Confirm the append function used by `action_router._reach_out` to log a send: `grep -n "_append_proactive\|def _append_proactive\|proactive_log" core/services/action_router.py`. Confirm `_proactive_messages_today()`, `_within_cooldown()`, `_max_proactive_per_day()` are importable module-level fns. Record exact names.

- [ ] **Step 3: Owner uid.** Confirm `from core.runtime.settings import load_settings; load_settings().extra.get("owner_user_id")` (per `action_router.py:342`). Record the exact accessor.

- [ ] **Step 4:** Write the three resolved names into Task 3's code below (replace the `# PIN:` markers). No commit (investigation only).

---

## Task 2: pure decision functions + tests

**Files:**
- Create: `core/services/proactivity_bridge.py` (pure functions only in this task)
- Test: `tests/test_proactivity_bridge.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_proactivity_bridge.py
from core.services import proactivity_bridge as pb


def _cand(kind="initiative", text="fix the thing", priority="medium", source_id="a", ts="2026-07-09T00:00:00+00:00"):
    return {"kind": kind, "text": text, "priority": priority, "source": "initiative_queue",
            "source_id": source_id, "ts": ts}


def test_classify_urgent_vs_normal():
    assert pb.classify(_cand(priority="high")) == "urgent"
    assert pb.classify(_cand(kind="critical_impulse", priority="low")) == "urgent"
    assert pb.classify(_cand(priority="medium")) == "normal"


def test_select_dedup_and_split_and_cap():
    cands = [_cand(source_id="a", priority="high"), _cand(source_id="a", priority="high"),  # dup
             *[_cand(source_id=f"n{i}", priority="medium") for i in range(8)]]
    out = pb.select(cands)
    assert len(out["urgent"]) == 1                       # dedup on source_id
    assert 1 <= len(out["normal"]) <= pb._DIGEST_MAX     # normal capped


def test_should_reach_owner_present_blocks():
    ok, reason = pb.should_reach_owner(owner_present=True, is_quiet=False, sent_today=0,
                                       cap=3, within_cooldown=False, urgent=False)
    assert ok is False and reason == "owner_present"


def test_should_reach_owner_quiet_blocks_normal_not_urgent():
    assert pb.should_reach_owner(owner_present=False, is_quiet=True, sent_today=0, cap=3,
                                 within_cooldown=False, urgent=False) == (False, "quiet_hours")
    ok, _ = pb.should_reach_owner(owner_present=False, is_quiet=True, sent_today=0, cap=3,
                                  within_cooldown=False, urgent=True)
    assert ok is True                                    # urgent bypasses quiet


def test_should_reach_owner_cap_and_cooldown_block():
    assert pb.should_reach_owner(owner_present=False, is_quiet=False, sent_today=3, cap=3,
                                 within_cooldown=False, urgent=False) == (False, "daily_cap")
    assert pb.should_reach_owner(owner_present=False, is_quiet=False, sent_today=0, cap=3,
                                 within_cooldown=True, urgent=False) == (False, "cooldown")


def test_should_reach_owner_ok():
    ok, reason = pb.should_reach_owner(owner_present=False, is_quiet=False, sent_today=0,
                                       cap=3, within_cooldown=False, urgent=False)
    assert ok is True and reason == "ok"


def test_build_digest_and_urgent_contain_text():
    d = pb.build_digest([_cand(text="ryd op i cachen"), _cand(text="spørg om X", source_id="b")])
    assert "ryd op i cachen" in d and "spørg om X" in d and d.strip()
    u = pb.build_urgent(_cand(text="noget vigtigt"))
    assert "noget vigtigt" in u and u.strip()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_proactivity_bridge.py -q`
Expected: FAIL — attributes not defined.

- [ ] **Step 3: Write the pure functions**

```python
# core/services/proactivity_bridge.py
"""Proaktivitets-broen — samler Jarvis' indre spørgsmål/initiativer/undren og overflader dem til
Bjørn gennem en presence-bevidst contact-gate + delte caps. Hybrid: urgent-item straks, ellers
'mens du var væk'-digest, ellers observe-suppressed (synlig, ikke sendt). Live-governed via
kill-switch; fail-closed for afsendelse. Self-safe — kaster aldrig i cadence-hot-path."""
from __future__ import annotations

from typing import Any

_DIGEST_MAX = 5           # højst så mange normale items i én digest
_PRESENT_WINDOW_S = 900   # owner regnes "til stede" hvis synlig < 15 min siden
_AWAY_MIN_S = 3600        # digest kræver ≥1t fravær (urgent kræver ikke)
_URGENT_PRIORITIES = {"high", "critical"}
_URGENT_KINDS = {"critical_impulse"}


def classify(candidate: dict[str, Any]) -> str:
    """'urgent' hvis høj/kritisk prioritet eller kritisk kind; ellers 'normal'. Ren."""
    if str(candidate.get("priority") or "").lower() in _URGENT_PRIORITIES:
        return "urgent"
    if str(candidate.get("kind") or "") in _URGENT_KINDS:
        return "urgent"
    return "normal"


def select(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Dedup på source_id, split i urgent/normal, sortér (urgent først/friskest), cap normal-listen."""
    seen: set[str] = set()
    urgent: list[dict[str, Any]] = []
    normal: list[dict[str, Any]] = []
    for c in candidates or []:
        sid = str(c.get("source_id") or "")
        if sid and sid in seen:
            continue
        if sid:
            seen.add(sid)
        (urgent if classify(c) == "urgent" else normal).append(c)
    normal.sort(key=lambda c: str(c.get("ts") or ""), reverse=True)
    return {"urgent": urgent, "normal": normal[:_DIGEST_MAX]}


def should_reach_owner(*, owner_present: bool, is_quiet: bool, sent_today: int, cap: int,
                       within_cooldown: bool, urgent: bool) -> tuple[bool, str]:
    """Ren contact-gate (kalderen injicerer signalerne). Rækkefølge = spam-værn:
    owner til stede → aldrig afbryd; quiet-hours blokerer normal (urgent må bryde); daily-cap;
    cooldown. Returnér (ok, reason) — reason bruges til observe ved suppression."""
    if owner_present:
        return (False, "owner_present")
    if is_quiet and not urgent:
        return (False, "quiet_hours")
    if sent_today >= cap:
        return (False, "daily_cap")
    if within_cooldown:
        return (False, "cooldown")
    return (True, "ok")


def build_urgent(item: dict[str, Any]) -> str:
    """Enkelt-item besked (urgent-gren)."""
    text = str(item.get("text") or "").strip()
    kind = str(item.get("kind") or "note")
    return f"💭 Jarvis ({kind}): {text}"


def build_digest(normal: list[dict[str, Any]]) -> str:
    """'Mens du var væk'-digest af normale items (kort, prioriteret)."""
    lines = ["💭 Mens du var væk tænkte jeg på:"]
    for c in (normal or [])[:_DIGEST_MAX]:
        text = str(c.get("text") or "").strip()
        if text:
            lines.append(f"  • {text}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_proactivity_bridge.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/proactivity_bridge.py tests/test_proactivity_bridge.py
git commit -m "feat(proactivity): pure decision functions for the proactivity bridge

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
The coverage gate needs `tests/test_proactivity_bridge.py` (created) for the new `core/` file.

---

## Task 3 (Claude inline): I/O layer — collect + tick + register + surface

**Files:** Modify `core/services/proactivity_bridge.py` (append the I/O layer using the Task-1-pinned names).

- [ ] **Step 1:** Append the I/O + orchestration code. Replace each `# PIN:` with the exact name resolved in Task 1.

```python
# ── I/O layer (appended) ─────────────────────────────────────────────────
import logging as _logging
from datetime import UTC, datetime, timedelta

logger = _logging.getLogger(__name__)
_KILL_SCOPE, _KILL_NAME = "autonomy", "proactivity_bridge"   # central_switches kill-switch


def _owner_uid() -> str:
    try:
        from core.runtime.settings import load_settings
        return str(load_settings().extra.get("owner_user_id") or "").strip()
    except Exception:
        return ""


def _owner_presence(uid: str) -> tuple[bool, float]:
    """(present, away_seconds) fra ÆGTE owner-synlig aktivitet — ikke autonome runs.
    present = app-enhed live ELLER sidste synlige aktivitet < _PRESENT_WINDOW_S siden."""
    now = datetime.now(UTC)
    last_seen = None
    try:
        from core.services.notification_router import _app_device_live
        if uid and _app_device_live(uid):
            return (True, 0.0)
    except Exception:
        pass
    try:
        # PIN(real-presence): fra Task 1 — funktion der giver owner's sidste SYNLIGE (ikke-autonome)
        # aktivitet som ISO-ts eller datetime. Fald tilbage til "længe væk" ved manglende signal.
        from core.runtime.db_visible import recent_visible_runs  # PIN: bekræft/erstat i Task 1
        rows = recent_visible_runs(limit=1) or []
        ts = rows[0].get("finished_at") if rows else None
        if ts:
            last_seen = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        last_seen = None
    if last_seen is None:
        return (False, float(_AWAY_MIN_S * 2))       # ukendt → antag væk (fail-open for digest)
    away = max(0.0, (now - last_seen).total_seconds())
    return (away < _PRESENT_WINDOW_S, away)


def collect_candidates() -> list[dict[str, Any]]:
    """Læs de EKSISTERENDE kilder (egress-frit, skriver intet). Self-safe → []."""
    out: list[dict[str, Any]] = []
    try:
        from core.services.initiative_queue import get_pending_initiatives
        for it in get_pending_initiatives() or []:
            out.append({"kind": "initiative", "text": str(it.get("focus") or "").strip(),
                        "priority": str(it.get("priority") or "medium"),
                        "source": "initiative_queue", "source_id": str(it.get("initiative_id") or ""),
                        "ts": str(it.get("detected_at") or "")})
    except Exception:
        pass
    try:
        from core.services.existential_wonder_daemon import get_latest_wonder
        w = (get_latest_wonder() or "").strip()
        if w:
            out.append({"kind": "wonder", "text": w, "priority": "medium",
                        "source": "existential_wonder", "source_id": f"wonder:{hash(w) & 0xffff}",
                        "ts": datetime.now(UTC).isoformat()})
    except Exception:
        pass
    return [c for c in out if c.get("text")]


def _route(uid: str, text: str, importance: str) -> dict[str, Any]:
    """Send direkte via den eksisterende notifikations-router (springer nudge-brønden over — broen
    ER beslutnings-laget) og LOG i action_routers delte cap-ledger. Self-safe."""
    from core.services.notification_router import route_proactive_notification
    res = route_proactive_notification(uid, "reach_out", {"preview": text, "body": text}, importance)
    try:
        from core.services.action_router import _append_proactive  # PIN: bekræft navn i Task 1
        _append_proactive({"at": datetime.now(UTC).isoformat(), "outcome": "sent",
                           "reason": "proactivity_bridge", "channel": str(res.get("channel") or ""),
                           "message": text[:240], "importance": importance, "source": "proactivity_bridge"})
    except Exception:
        pass
    return res


def _observe(nerve: str, meta: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "proactivity", "nerve": nerve, **meta})
    except Exception:
        pass


def run_proactivity_bridge_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence run_fn. Hybrid: urgent straks / ellers digest / ellers observe suppressed.
    Fail-CLOSED for afsendelse (kill-switch-fejl → suppress). Self-safe."""
    # Kill-switch (fail-closed: fejl → suppress, ikke send)
    try:
        from core.services import central_switches
        enabled = central_switches.is_enabled(_KILL_SCOPE, _KILL_NAME)
    except Exception:
        _observe("bridge_suppressed", {"reason": "switch_read_error"})
        return {"status": "ok", "action": "suppressed", "reason": "switch_read_error"}
    if not enabled:
        _observe("bridge_suppressed", {"reason": "disabled"})
        return {"status": "ok", "action": "suppressed", "reason": "disabled"}
    try:
        uid = _owner_uid()
        if not uid:
            _observe("bridge_suppressed", {"reason": "no_owner_uid"})
            return {"status": "ok", "action": "suppressed", "reason": "no_owner_uid"}
        sel = select(collect_candidates())
        if not sel["urgent"] and not sel["normal"]:
            _observe("bridge_suppressed", {"reason": "no_candidates"})
            return {"status": "ok", "action": "suppressed", "reason": "no_candidates"}
        present, away = _owner_presence(uid)
        # rate-signaler fra den delte ledger
        from core.services.action_router import (_proactive_messages_today, _within_cooldown,
                                                 _max_proactive_per_day)
        sent_today, cap, cooldown = _proactive_messages_today(), _max_proactive_per_day(), _within_cooldown()
        try:
            from core.services.notification_router import is_quiet_hours, get_preferences
            is_quiet = is_quiet_hours(get_preferences(uid))
        except Exception:
            is_quiet = False
        # urgent-gren
        if sel["urgent"]:
            ok, reason = should_reach_owner(owner_present=present, is_quiet=is_quiet, sent_today=sent_today,
                                            cap=cap, within_cooldown=cooldown, urgent=True)
            if ok:
                item = sel["urgent"][0]
                res = _route(uid, build_urgent(item), "high")
                _observe("bridge_surfaced", {"kind": "urgent", "delivered": bool(res.get("delivered")),
                                             "source_id": item.get("source_id")})
                return {"status": "ok", "action": "surfaced_urgent"}
            _observe("bridge_suppressed", {"reason": reason, "branch": "urgent"})
        # digest-gren (kræver reelt fravær)
        if sel["normal"] and away >= _AWAY_MIN_S:
            ok, reason = should_reach_owner(owner_present=present, is_quiet=is_quiet, sent_today=sent_today,
                                            cap=cap, within_cooldown=cooldown, urgent=False)
            if ok:
                res = _route(uid, build_digest(sel["normal"]), "normal")
                _observe("bridge_surfaced", {"kind": "digest", "n": len(sel["normal"]),
                                             "delivered": bool(res.get("delivered"))})
                return {"status": "ok", "action": "surfaced_digest"}
            _observe("bridge_suppressed", {"reason": reason, "branch": "digest"})
            return {"status": "ok", "action": "suppressed", "reason": reason}
        _observe("bridge_suppressed", {"reason": "not_away_enough" if sel["normal"] else "urgent_gated",
                                       "away_s": int(away)})
        return {"status": "ok", "action": "suppressed"}
    except Exception as exc:  # aldrig vælt cadence
        logger.debug("proactivity_bridge tick failed: %s", exc)
        _observe("bridge_error", {"error": str(exc)[:160]})
        return {"status": "error"}


def register_proactivity_bridge_producer() -> None:
    """Registrér broen som cadence-producer (~10 min, visible_grace 15 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(name="proactivity_bridge", cooldown_minutes=10,
                                   visible_grace_minutes=15, run_fn=run_proactivity_bridge_tick, priority=12))


def build_proactivity_bridge_surface() -> dict[str, Any]:
    """Read-only surface til /central/proactivity + jc. Self-safe."""
    try:
        from core.services import central_switches
        enabled = central_switches.is_enabled(_KILL_SCOPE, _KILL_NAME)
    except Exception:
        enabled = None
    try:
        sel = select(collect_candidates())
        return {"status": "ok", "enabled": enabled,
                "pending_urgent": len(sel["urgent"]), "pending_normal": len(sel["normal"]),
                "candidates": (sel["urgent"] + sel["normal"])[:8]}
    except Exception:
        return {"status": "unavailable", "enabled": enabled}
```

- [ ] **Step 2:** Ensure the kill-switch defaults ON. `central_switches.is_enabled` default: verify it returns True for an unset `autonomy/proactivity_bridge` (per SP flip work, `gate_enforce`/`autonomy` scopes default ON). If it defaults False, add a one-time `set_enabled("autonomy","proactivity_bridge",True)` in the wiring (Task 4). Confirm with:

Run: `conda run -n ai python -c "from core.services import central_switches as s; print(s.is_enabled('autonomy','proactivity_bridge'))"`
Expected: `True` (if `False`, note it for Task 4 Step 3).

- [ ] **Step 3:** Compile + full-module tests.

Run: `conda run -n ai python -m compileall core/services/proactivity_bridge.py -q && conda run -n ai python -m pytest tests/test_proactivity_bridge.py -q`
Expected: compile OK, tests PASS (pure-function tests still green; I/O untested here — exercised live in Task 5).

- [ ] **Step 4: Commit**

```bash
git add core/services/proactivity_bridge.py
git commit -m "feat(proactivity): I/O orchestrator — collect, presence-gated route, cadence producer, surface

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4 (Claude inline): wire producer + route + jc

- [ ] **Step 1:** Register the cadence producer. In `core/services/internal_cadence_central_wiring.py`, inside `register_central_wiring_producers()`, add a self-safe block:

```python
    # Proaktivitets-broen: overflad Jarvis' indre spørgsmål/initiativer til Bjørn (governed).
    try:
        from core.services.proactivity_bridge import register_proactivity_bridge_producer
        register_proactivity_bridge_producer()
    except Exception:
        pass
```
If Task 3 Step 2 found the switch defaults False, add right after the import:
`from core.services import central_switches as _cs; _cs.is_enabled("autonomy","proactivity_bridge") or _cs.set_enabled("autonomy","proactivity_bridge", True)`

- [ ] **Step 2:** Create `apps/api/jarvis_api/routes/central_proactivity.py`:

```python
"""Central 'proactivity' route — proaktivitets-broens beslutninger (owner, read-only, self-safe)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-proactivity"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/proactivity")
async def get_proactivity() -> dict:
    """Proaktivitets-broen: switch-status + ventende urgent/normal kandidater. Owner-only."""
    _require_owner()
    try:
        from core.services.proactivity_bridge import build_proactivity_bridge_surface
        surf = build_proactivity_bridge_surface()
        if not isinstance(surf, dict):
            surf = {"status": "unavailable"}
    except Exception:
        surf = {"status": "unavailable"}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
```

- [ ] **Step 3:** Register the router in `apps/api/jarvis_api/app.py` (next to the other central routes, e.g. after `central_docs_drift`):

```python
    from apps.api.jarvis_api.routes import central_proactivity as _central_proactivity
    app.include_router(_central_proactivity.router)
```

- [ ] **Step 4:** Add `jc proactivity` in `apps/central_cli/central_cli/commands.py` `_GET_ENDPOINTS`:

```python
    "proactivity": "/central/proactivity",
```

- [ ] **Step 5:** Compile + route-registration + producer smoke.

Run:
```bash
conda run -n ai python -m compileall apps/api/jarvis_api/routes/central_proactivity.py core/services/internal_cadence_central_wiring.py -q
conda run -n ai python -c "from apps.api.jarvis_api.app import app; print([r.path for r in app.routes if 'proactivity' in getattr(r,'path','')])"
conda run -n ai python -c "from core.services.proactivity_bridge import register_proactivity_bridge_producer; register_proactivity_bridge_producer(); print('producer registered ok')"
```
Expected: compile OK; prints `['/central/proactivity']`; `producer registered ok`.

- [ ] **Step 6: Commit**

```bash
git add core/services/internal_cadence_central_wiring.py apps/api/jarvis_api/routes/central_proactivity.py apps/api/jarvis_api/app.py apps/central_cli/central_cli/commands.py
git commit -m "feat(proactivity): wire bridge cadence producer + /central/proactivity + jc proactivity

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5 (Claude inline): full suite + deploy + live-verify

- [ ] **Step 1: Full suite** (runtime change).

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS (known order-sensitive isolation flakes re-run alone; see CONTRIBUTING).

- [ ] **Step 2: Push + deploy** to `bs@10.0.0.39` (merge not overwrite; restart BOTH).

```bash
git push
ssh bs@10.0.0.39 'R=/media/projects/jarvis-v2; git -C $R fetch origin -q; (git -C $R pull --ff-only origin main || git -C $R merge --no-edit origin/main); git -C $R rev-parse --short HEAD; sudo systemctl restart jarvis-runtime jarvis-api; sleep 5; echo "runtime=$(systemctl is-active jarvis-runtime) api=$(systemctl is-active jarvis-api)"'
```
Expected: HEAD matches pushed commit; both `active`.

- [ ] **Step 3: Live-verify** the bridge decides + surfaces state (kill-switch ON = live).

```bash
ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python -c "
from core.services.proactivity_bridge import run_proactivity_bridge_tick, build_proactivity_bridge_surface
import json
print(\"surface:\", json.dumps(build_proactivity_bridge_surface(), ensure_ascii=False)[:300])
print(\"tick:\", json.dumps(run_proactivity_bridge_tick(trigger=\"probe\"), ensure_ascii=False))
"'
```
Expected: surface prints `enabled: true` + candidate counts; tick returns an action (`suppressed`/`surfaced_*`) with a reason — a **live decision** (not a crash). If it surfaces while Bjørn is present, that's a bug (presence-gate) — investigate `_owner_presence`.

- [ ] **Step 4:** Confirm owner-gated route + `jc`.

```bash
ssh bs@10.0.0.39 'curl -s -m 6 http://127.0.0.1:8080/central/proactivity | head -c 120'   # expect auth-required (owner-gated), not 404
```

- [ ] **Step 5: Report** the live decision + note the kill-switch: `jc raw /central/proactivity` shows state; flip off anytime with `central_switches.set_enabled("autonomy","proactivity_bridge", False)`. Note SP2 (Agent Smith) is next.

---

## Self-Review

**Spec coverage:** collect→select→contact-gate→route hybrid (Task 2 pure + Task 3 tick) ✓; urgent single / digest / observe-suppressed (Task 3 tick branches) ✓; live-governed kill-switch default ON, fail-CLOSED for sending (Task 3 tick + Task 4 wiring) ✓; presence-gate uses REAL owner-visible signal not autonomous (Task 1 pins + Task 3 `_owner_presence`) ✓; reuse route_proactive_notification/is_quiet_hours/initiative_queue/existential_wonder/action_router caps+ledger (Task 3) ✓; observability `/central/proactivity` + `jc proactivity` (Task 4) ✓; self-safe never-crash (Task 3 try/except) ✓; deploy full-suite + container both services (Task 5) ✓; scope: no new generators, no longing/pressure activation, no Agent Smith ✓.

**Placeholder scan:** the `# PIN:` markers (real-presence fn, `_append_proactive`) are Task-1-resolved before Task 3 code lands — explicit, not vague. No TBD/TODO. Constants (`_DIGEST_MAX`, `_PRESENT_WINDOW_S`, `_AWAY_MIN_S`, caps) all have concrete values.

**Type consistency:** candidate dict `{kind,text,priority,source,source_id,ts}` identical across collect/classify/select/build/tests; `should_reach_owner(*, owner_present, is_quiet, sent_today, cap, within_cooldown, urgent) -> (bool, str)` identical in tests + tick; `select() -> {"urgent":[...], "normal":[...]}` consistent; kill-switch scope/name `("autonomy","proactivity_bridge")` identical in tick/surface/wiring.
