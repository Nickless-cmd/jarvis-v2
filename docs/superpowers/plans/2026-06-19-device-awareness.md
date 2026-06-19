# Intelligent Device Awareness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jarvis registrerer hvilken enhed (desktop/mobil) Bjørn er ved og ruter proaktive notifikationer (svar-klar, reminder, initiativ) til den rigtige enhed med eskalering ved manglende ack — i stedet for at blæste til alle.

**Architecture:** Tilgang A (poll-udvidet). In-memory presence-registry i API-processen, hybrid scoring (recency primær + foreground/sleep/netværks-hints). Ny `proactive_router` afløser `push_dispatcher`'s blanket-blast; desktop får en poll-baseret notif-kø (mobil beholder FCM). Presence injiceres også i Jarvis' prompt-awareness. Alt killswitch-gatet, fuld bagudkompatibilitet.

**Tech Stack:** Python 3.11 (core/services, FastAPI), conda env `ai`; desktop Electron/React (vitest); mobil React Native (jest). Backend redigeres + testes på containeren `10.0.0.39` hvor live-koden kører.

**Miljø-noter:**
- Backend: `ssh bs@10.0.0.39`, `cd /media/projects/jarvis-v2`, `source ~/miniconda3/etc/profile.d/conda.sh && conda activate ai`, kør tests med `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest ...`.
- Local checkout (`/media/projects/jarvis-v2` på CheifOne) + container + origin er synket på `54670d95` — commit på containeren og push; pull på local efter.
- Killswitch: ny settings-flag `device_awareness_enabled` (default `True`; rent routing-fallback når `False`).
- Bevar: `push_dispatcher._push_to_user`/`_fcm_send` (kanal-primitiver), `window.jarvisDesk.notifyTaskDone` (bro), eksisterende FCM-adfærd ved tom presence.

---

## File Structure

**Nye filer:**
- `core/services/device_presence.py` — presence-registry + hybrid scoring + summary. Ren logik, injicerbart ur.
- `core/services/desktop_notifications.py` — per-bruger in-memory notif-kø (enqueue/drain/prune).
- `core/services/proactive_router.py` — routing-beslutning + per-pending eskalerings-timer + ack.
- `apps/api/jarvis_api/routes/presence.py` — 3 endpoints (`/presence/ping`, `/notifications/pending`, `/notifications/ack`).
- `tests/test_device_presence.py`, `tests/test_desktop_notifications.py`, `tests/test_proactive_router.py`, `tests/test_presence_routes.py`.

**Modificerede filer:**
- `core/runtime/settings.py` — `device_awareness_enabled`-flag.
- `core/services/push_dispatcher.py` — kald `proactive_router.route(...)` (behold primitiver + fallback).
- `core/services/prompt_contract.py` — device-presence awareness-linje (bagest, killswitch-gatet).
- `apps/api/jarvis_api/app.py` — registrér presence-router.
- `apps/jarvis-desk/electron/main.ts` + `preload.ts` — `powerMonitor` + generaliseret `notify`.
- `apps/jarvis-desk/src/lib/api.ts` + `src/views/ChatView.tsx` (+ ny `src/lib/presence.ts`) — presence-ping + notif-poll.
- `.worktrees/jarvis-mobile-companion-v1/apps/mobile/src/lib/presence.ts` (ny) + `src/App.tsx` + `src/lib/push.ts` — presence-ping på AppState/NetInfo + FCM `notif_id`→ack.

---

## Phase 1 — Presence-kerne (`device_presence.py`)

### Task 1: DeviceState + record_ping + injicerbart ur

**Files:**
- Create: `core/services/device_presence.py`
- Test: `tests/test_device_presence.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_device_presence.py
import core.services.device_presence as dp


def _fake_clock():
    box = {"t": 1000.0}
    return box


def test_record_ping_creates_and_updates_state(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()  # ryd global state mellem tests
    dp.record_ping("bjorn", "dev-A", "desktop", foreground=True, awake=True, network="home", interaction=True)
    st = dp._PRESENCE["bjorn"]["dev-A"]
    assert st.platform == "desktop"
    assert st.last_ping_at == 1000.0
    assert st.last_interaction_at == 1000.0
    assert st.foreground is True

    box["t"] = 1005.0
    dp.record_ping("bjorn", "dev-A", "desktop", foreground=False, awake=True, network="home", interaction=False)
    st = dp._PRESENCE["bjorn"]["dev-A"]
    assert st.last_ping_at == 1005.0
    assert st.last_interaction_at == 1000.0  # interaction=False bevarer gammel
    assert st.foreground is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_device_presence.py -q`
Expected: FAIL (module/attribut findes ikke).

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/device_presence.py
"""In-memory device-presence pr. bruger. Efemær — genopbygges af klient-pings.

Hybrid scoring: aktivitets-recency primær; foreground/desktop-sleep/mobil-netværk
er hints. Reachability: desktop kun online via frisk ping; mobil altid FCM-nåbar.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

_now = time.monotonic  # injicerbart i tests

# Justerbare konstanter
_DESKTOP_ONLINE_TTL_S = 12.0   # desktop pinger ~5s; >12s uden ping = offline
_PRESENCE_TTL_S = 120.0        # ryd state-records ældre end dette
_RECENCY_HORIZON_S = 600.0     # recency-vægt aftager lineært over 10 min
_FOREGROUND_BONUS = 100.0
_AWAY_MOBILE_BONUS = 50.0

_lock = threading.Lock()
_PRESENCE: dict[str, dict[str, "DeviceState"]] = {}


@dataclass
class DeviceState:
    device_key: str
    platform: str           # "desktop" | "mobile"
    last_ping_at: float
    last_interaction_at: float
    foreground: bool = False
    awake: bool = True
    network: str = "unknown"  # "home" | "away" | "unknown"


def reset() -> None:
    """Kun til tests."""
    with _lock:
        _PRESENCE.clear()


def record_ping(
    user_id: str,
    device_key: str,
    platform: str,
    *,
    foreground: bool,
    awake: bool,
    network: str,
    interaction: bool = False,
) -> None:
    uid, key = (user_id or "").strip(), (device_key or "").strip()
    if not uid or not key:
        return
    now = _now()
    with _lock:
        devices = _PRESENCE.setdefault(uid, {})
        st = devices.get(key)
        if st is None:
            st = DeviceState(
                device_key=key, platform=platform,
                last_ping_at=now, last_interaction_at=now,
            )
            devices[key] = st
        st.platform = platform
        st.last_ping_at = now
        st.foreground = bool(foreground)
        st.awake = bool(awake)
        st.network = network or "unknown"
        if interaction:
            st.last_interaction_at = now
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_device_presence.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/device_presence.py tests/test_device_presence.py
git commit -m "feat(presence): DeviceState + record_ping (injicerbart ur)"
```

### Task 2: rank() — reachability + hybrid scoring

**Files:**
- Modify: `core/services/device_presence.py`
- Test: `tests/test_device_presence.py`

- [ ] **Step 1: Write the failing test**

```python
# tilføj til tests/test_device_presence.py
def test_rank_desktop_foreground_beats_background_mobile(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home", interaction=False)
    ranked = dp.rank("bjorn")
    assert [r.device_key for r in ranked][0] == "desk"
    assert ranked[0].reachable_via == "desktop_queue"


def test_rank_excludes_sleeping_desktop(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=False, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="away", interaction=True)
    ranked = dp.rank("bjorn")
    assert [r.device_key for r in ranked] == ["mob"]  # desktop sovende → ekskluderet


def test_rank_offline_desktop_dropped_mobile_stays_fcm(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="unknown", interaction=False)
    box["t"] = 1000.0 + 30.0  # desktop online-TTL=12s → desktop nu offline
    ranked = dp.rank("bjorn")
    keys = [r.device_key for r in ranked]
    assert "desk" not in keys          # desktop offline → ikke nåbar
    assert keys == ["mob"]             # mobil stadig FCM-nåbar
    assert ranked[0].reachable_via == "fcm"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_device_presence.py -q`
Expected: FAIL (`rank` findes ikke).

- [ ] **Step 3: Write minimal implementation**

```python
# tilføj til core/services/device_presence.py
from dataclasses import dataclass as _dc


@_dc
class RankedDevice:
    device_key: str
    platform: str
    score: float
    reachable_via: str   # "desktop_queue" | "fcm"


def _recency_weight(now: float, last_interaction_at: float) -> float:
    age = max(0.0, now - last_interaction_at)
    if age >= _RECENCY_HORIZON_S:
        return 0.0
    return (_RECENCY_HORIZON_S - age) / _RECENCY_HORIZON_S * 100.0


def rank(user_id: str) -> list[RankedDevice]:
    uid = (user_id or "").strip()
    now = _now()
    out: list[RankedDevice] = []
    with _lock:
        for st in (_PRESENCE.get(uid) or {}).values():
            if st.platform == "desktop":
                if not st.awake:
                    continue  # sovende desktop = ikke kandidat
                if (now - st.last_ping_at) > _DESKTOP_ONLINE_TTL_S:
                    continue  # offline desktop = ikke nåbar
                reachable_via = "desktop_queue"
            else:  # mobile — altid FCM-nåbar
                reachable_via = "fcm"
            score = _recency_weight(now, st.last_interaction_at)
            if st.foreground:
                score += _FOREGROUND_BONUS
            if st.platform == "mobile" and st.network == "away":
                score += _AWAY_MOBILE_BONUS
            out.append(RankedDevice(st.device_key, st.platform, score, reachable_via))
    out.sort(key=lambda r: r.score, reverse=True)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_device_presence.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/device_presence.py tests/test_device_presence.py
git commit -m "feat(presence): rank() — reachability + hybrid scoring"
```

### Task 3: prune() + summary()

**Files:**
- Modify: `core/services/device_presence.py`
- Test: `tests/test_device_presence.py`

- [ ] **Step 1: Write the failing test**

```python
# tilføj til tests/test_device_presence.py
def test_prune_drops_stale_records(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "old", "mobile", foreground=False, awake=True, network="home")
    box["t"] = 1000.0 + 200.0  # > _PRESENCE_TTL_S (120)
    dp.record_ping("bjorn", "fresh", "mobile", foreground=True, awake=True, network="home")
    dp.prune()
    keys = set((dp._PRESENCE.get("bjorn") or {}).keys())
    assert keys == {"fresh"}


def test_summary_active_desktop(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    s = dp.summary("bjorn")
    assert "desktop" in s.lower()


def test_summary_no_devices(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    assert "ingen" in dp.summary("bjorn").lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_device_presence.py -q`
Expected: FAIL (`prune`/`summary` findes ikke).

- [ ] **Step 3: Write minimal implementation**

```python
# tilføj til core/services/device_presence.py
def prune(user_id: str | None = None) -> None:
    now = _now()
    with _lock:
        uids = [user_id] if user_id else list(_PRESENCE.keys())
        for uid in uids:
            devices = _PRESENCE.get(uid) or {}
            stale = [k for k, st in devices.items() if (now - st.last_ping_at) > _PRESENCE_TTL_S]
            for k in stale:
                devices.pop(k, None)
            if not devices:
                _PRESENCE.pop(uid, None)


def summary(user_id: str) -> str:
    ranked = rank(user_id)
    if not ranked:
        return "Ingen aktiv enhed lige nu."
    best = ranked[0]
    with _lock:
        st = (_PRESENCE.get((user_id or '').strip()) or {}).get(best.device_key)
    where = "desktop" if best.platform == "desktop" else "mobil"
    fg = "i fokus" if (st and st.foreground) else "i baggrund"
    net = ""
    if st and st.platform == "mobile":
        net = {"home": ", hjemme-wifi", "away": ", på mobildata (ude)"}.get(st.network, "")
    return f"Bjørn er ved {where} ({fg}{net})."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_device_presence.py -q`
Expected: PASS (alle Task 1-3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/services/device_presence.py tests/test_device_presence.py
git commit -m "feat(presence): prune() + summary() til Jarvis-awareness"
```

---

## Phase 2 — Desktop notif-kø (`desktop_notifications.py`)

### Task 4: enqueue / drain / prune

**Files:**
- Create: `core/services/desktop_notifications.py`
- Test: `tests/test_desktop_notifications.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_desktop_notifications.py
import core.services.desktop_notifications as dn


def test_enqueue_then_drain_clears(monkeypatch):
    monkeypatch.setattr(dn, "_now", lambda: 1000.0)
    dn.reset()
    dn.enqueue("bjorn", {"notif_id": "n1", "kind": "answer_ready", "title": "Klar", "body": "svar", "session_id": "s1"})
    items = dn.drain("bjorn")
    assert len(items) == 1 and items[0]["notif_id"] == "n1"
    assert dn.drain("bjorn") == []  # drain rydder


def test_prune_drops_old_undrained(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dn, "_now", lambda: box["t"])
    dn.reset()
    dn.enqueue("bjorn", {"notif_id": "n1", "kind": "reminder", "title": "x", "body": "y", "session_id": ""})
    box["t"] = 1000.0 + 400.0  # > _DESKTOP_NOTIF_TTL_S (300)
    dn.prune()
    assert dn.drain("bjorn") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_desktop_notifications.py -q`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/desktop_notifications.py
"""Per-bruger in-memory kø af proaktive desktop-notifikationer. Desktop poller
GET /notifications/pending → drain. Efemær; TTL-prune for udrainede items."""
from __future__ import annotations

import threading
import time

_now = time.monotonic
_DESKTOP_NOTIF_TTL_S = 300.0

_lock = threading.Lock()
_QUEUE: dict[str, list[dict]] = {}


def reset() -> None:
    with _lock:
        _QUEUE.clear()


def enqueue(user_id: str, item: dict) -> None:
    uid = (user_id or "").strip()
    if not uid:
        return
    rec = dict(item)
    rec["_ts"] = _now()
    with _lock:
        _QUEUE.setdefault(uid, []).append(rec)


def drain(user_id: str) -> list[dict]:
    uid = (user_id or "").strip()
    with _lock:
        items = _QUEUE.pop(uid, [])
    return [{k: v for k, v in it.items() if k != "_ts"} for it in items]


def prune() -> None:
    now = _now()
    with _lock:
        for uid in list(_QUEUE.keys()):
            kept = [it for it in _QUEUE[uid] if (now - it.get("_ts", now)) <= _DESKTOP_NOTIF_TTL_S]
            if kept:
                _QUEUE[uid] = kept
            else:
                _QUEUE.pop(uid, None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_desktop_notifications.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/desktop_notifications.py tests/test_desktop_notifications.py
git commit -m "feat(presence): desktop_notifications-kø (enqueue/drain/prune)"
```

---

## Phase 3 — Proaktiv router (`proactive_router.py`)

### Task 5: route() — bedste enhed + pending-registrering

**Files:**
- Create: `core/services/proactive_router.py`
- Test: `tests/test_proactive_router.py`

**Designnote:** `route` planlægger eskalering via `_arm_timer(notif_id)`. I tests
monkeypatches `_arm_timer` til no-op, og `_escalate(notif_id)` kaldes manuelt for at
simulere timer-fyring. FCM-send + desktop-enqueue injiceres via modul-funktioner der
kan monkeypatches.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_proactive_router.py
import core.services.proactive_router as pr
import core.services.device_presence as dp


def _setup(monkeypatch):
    sent = {"fcm": [], "desk": []}
    monkeypatch.setattr(pr, "_arm_timer", lambda notif_id: None)
    monkeypatch.setattr(pr, "_send_fcm", lambda uid, key, data: sent["fcm"].append((key, data)))
    monkeypatch.setattr(pr, "_send_desktop", lambda uid, item: sent["desk"].append(item))
    monkeypatch.setattr(pr, "_fallback_blast", lambda uid, data: sent.setdefault("blast", []).append(data))
    monkeypatch.setattr(pr, "_new_id", lambda: "nid-1")
    pr.reset()
    return sent


def test_route_sends_to_best_desktop(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home")
    sent = _setup(monkeypatch)
    pr.route("bjorn", {"kind": "answer_ready", "session_id": "s1"}, "answer_ready")
    assert len(sent["desk"]) == 1 and sent["desk"][0]["notif_id"] == "nid-1"
    assert sent["fcm"] == []
    assert "nid-1" in pr._PENDING


def test_route_empty_presence_falls_back_to_blast(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()  # ingen enheder
    sent = _setup(monkeypatch)
    pr.route("bjorn", {"kind": "reminder", "preview": "hej"}, "reminder")
    assert sent.get("blast") == [{"kind": "reminder", "preview": "hej"}]
    assert pr._PENDING == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_proactive_router.py -q`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/proactive_router.py
"""Ruter proaktive notifikationer til bedste enhed + eskalerer ved manglende ack.

Erstatter push_dispatcher's blanket-blast. Tom presence → fallback til blast (mister
aldrig et signal). Eskalering via per-pending threading.Timer; ack annullerer."""
from __future__ import annotations

import logging
import threading
from uuid import uuid4

import core.services.device_presence as device_presence

logger = logging.getLogger(__name__)

_ESCALATE_S = 180.0
_lock = threading.Lock()
_PENDING: dict[str, dict] = {}   # notif_id -> {user_id, payload, kind, remaining, timer}


def reset() -> None:
    with _lock:
        for p in _PENDING.values():
            t = p.get("timer")
            if t:
                t.cancel()
        _PENDING.clear()


def _new_id() -> str:
    return f"notif-{uuid4().hex}"


def _send_fcm(user_id: str, device_key: str, data: dict) -> None:
    from core.services import push_dispatcher as pd
    pd._fcm_send(device_key, data)  # device_key == FCM-token for mobil


def _send_desktop(user_id: str, item: dict) -> None:
    from core.services import desktop_notifications as dn
    dn.enqueue(user_id, item)


def _fallback_blast(user_id: str, data: dict) -> None:
    from core.services import push_dispatcher as pd
    pd._push_to_user(user_id, data)


def _deliver(user_id: str, target, notif_id: str, payload: dict) -> None:
    if target.reachable_via == "desktop_queue":
        _send_desktop(user_id, {
            "notif_id": notif_id,
            "kind": payload.get("kind", ""),
            "title": payload.get("title", "Jarvis"),
            "body": payload.get("preview", "") or payload.get("body", ""),
            "session_id": payload.get("session_id", ""),
        })
    else:
        _send_fcm(user_id, target.device_key, {**payload, "notif_id": notif_id})


def _arm_timer(notif_id: str) -> None:
    t = threading.Timer(_ESCALATE_S, _escalate, args=(notif_id,))
    t.daemon = True
    with _lock:
        if notif_id in _PENDING:
            _PENDING[notif_id]["timer"] = t
    t.start()


def route(user_id: str, payload: dict, kind: str) -> None:
    uid = (user_id or "").strip()
    if not uid:
        return
    ranked = device_presence.rank(uid)
    if not ranked:
        _fallback_blast(uid, payload)
        return
    notif_id = _new_id()
    with _lock:
        _PENDING[notif_id] = {
            "user_id": uid, "payload": payload, "kind": kind,
            "remaining": ranked[1:], "timer": None,
        }
    _deliver(uid, ranked[0], notif_id, payload)
    _arm_timer(notif_id)


def _escalate(notif_id: str) -> None:
    with _lock:
        p = _PENDING.get(notif_id)
        if not p or not p["remaining"]:
            _PENDING.pop(notif_id, None)
            return
        nxt = p["remaining"].pop(0)
        uid, payload = p["user_id"], p["payload"]
    _deliver(uid, nxt, notif_id, payload)
    _arm_timer(notif_id)


def ack(notif_id: str) -> None:
    with _lock:
        p = _PENDING.pop(notif_id, None)
        if p and p.get("timer"):
            p["timer"].cancel()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_proactive_router.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/proactive_router.py tests/test_proactive_router.py
git commit -m "feat(presence): proactive_router.route() — bedste enhed + fallback"
```

### Task 6: _escalate + ack

**Files:**
- Modify: `tests/test_proactive_router.py` (kode findes allerede fra Task 5)
- Test: `tests/test_proactive_router.py`

- [ ] **Step 1: Write the failing test**

```python
# tilføj til tests/test_proactive_router.py
def test_escalate_sends_to_next_then_ack_stops(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home")
    sent = _setup(monkeypatch)
    pr.route("bjorn", {"kind": "answer_ready", "session_id": "s1"}, "answer_ready")
    assert len(sent["desk"]) == 1 and sent["fcm"] == []
    # simulér timer-fyring (ingen ack fra desktop):
    pr._escalate("nid-1")
    assert len(sent["fcm"]) == 1                # eskaleret til mobil
    assert sent["fcm"][0][0] == "mob"
    # ack stopper videre eskalering + rydder pending:
    pr.ack("nid-1")
    assert "nid-1" not in pr._PENDING
    pr._escalate("nid-1")                       # no-op efter ack
    assert len(sent["fcm"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_proactive_router.py::test_escalate_sends_to_next_then_ack_stops -q`
Expected: Bør PASS hvis Task 5-kode er korrekt (denne task bekræfter eskalering+ack-stien). Hvis FAIL, ret `_escalate`/`ack` indtil grøn.

- [ ] **Step 3: (ingen ny kode hvis grøn)** — ellers ret `_escalate`/`ack`.

- [ ] **Step 4: Run full proactive_router tests**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_proactive_router.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_proactive_router.py
git commit -m "test(presence): eskalering→næste enhed + ack annullerer"
```

---

## Phase 4 — Wire push_dispatcher → proactive_router

### Task 7: Killswitch-flag `device_awareness_enabled`

**Files:**
- Modify: `core/runtime/settings.py` (3 steder: dataclass-felt ~linje 220-250, `to_dict` ~401, parse ~789)
- Test: `tests/test_settings_device_awareness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_settings_device_awareness.py
from core.runtime.settings import Settings, _settings_from_dict  # juster import hvis navn afviger


def test_device_awareness_defaults_true():
    s = Settings()
    assert s.device_awareness_enabled is True


def test_device_awareness_parsed_from_dict():
    s = _settings_from_dict({"device_awareness_enabled": False})
    assert s.device_awareness_enabled is False
```

**Note:** Find den faktiske parse-funktion: `grep -n "def .*from_dict\|server_authoritative_runs=bool" core/runtime/settings.py`. Brug det rigtige navn i testen.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_settings_device_awareness.py -q`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

I `Settings`-dataclass (nær `server_authoritative_runs: bool = False`):
```python
    device_awareness_enabled: bool = True
```
I `to_dict` (nær `"server_authoritative_runs": self.server_authoritative_runs,`):
```python
            "device_awareness_enabled": self.device_awareness_enabled,
```
I parse-funktionen (nær `server_authoritative_runs=bool(data.get(...))`):
```python
        device_awareness_enabled=bool(data.get("device_awareness_enabled", defaults.device_awareness_enabled)),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_settings_device_awareness.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py tests/test_settings_device_awareness.py
git commit -m "feat(settings): device_awareness_enabled killswitch (default True)"
```

### Task 8: push_dispatcher kalder proactive_router (killswitch-gatet)

**Files:**
- Modify: `core/services/push_dispatcher.py`
- Test: `tests/test_push_dispatcher_routing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_push_dispatcher_routing.py
import core.services.push_dispatcher as pd


def test_dispatch_run_done_routes_when_enabled(monkeypatch):
    calls = {"route": [], "blast": []}
    monkeypatch.setattr(pd, "_route_or_blast", lambda uid, data, kind: calls["route"].append((uid, kind)))
    # suppression + owner-opslag stubbes:
    monkeypatch.setattr(pd, "_owner_of_run", lambda rid: "bjorn")
    import core.services.run_event_log as rel
    monkeypatch.setattr(rel, "was_consumed_or_active", lambda rid: False)
    monkeypatch.setattr(rel, "session_for_run", lambda rid: "s1")
    pd._dispatch_run_done("run-1")
    assert calls["route"] == [("bjorn", "answer_ready")]


def test_route_or_blast_respects_killswitch(monkeypatch):
    seen = {"router": 0, "blast": 0}
    import core.services.proactive_router as prr
    monkeypatch.setattr(prr, "route", lambda uid, data, kind: seen.__setitem__("router", seen["router"] + 1))
    monkeypatch.setattr(pd, "_push_to_user", lambda uid, data: seen.__setitem__("blast", seen["blast"] + 1))
    from core.runtime import settings as st
    monkeypatch.setattr(st, "load_settings", lambda: type("S", (), {"device_awareness_enabled": False})())
    pd._route_or_blast("bjorn", {"kind": "reminder"}, "reminder")
    assert seen == {"router": 0, "blast": 1}  # flag OFF → gammel blast
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_push_dispatcher_routing.py -q`
Expected: FAIL (`_route_or_blast` findes ikke).

- [ ] **Step 3: Write minimal implementation**

I `core/services/push_dispatcher.py`, tilføj helper + brug den i `_dispatch_run_done`/`on_initiative`/`on_reminder`:
```python
def _route_or_blast(user_id: str, data: dict, kind: str) -> None:
    """Flag ON → intelligent routing; OFF → gammel FCM-blast (bagudkompat)."""
    try:
        from core.runtime.settings import load_settings
        if load_settings().device_awareness_enabled:
            from core.services import proactive_router
            proactive_router.route(user_id, data, kind)
            return
    except Exception as e:
        logger.warning("push: routing-fejl, falder tilbage til blast: %s", e)
    _push_to_user(user_id, data)
```
Erstat de tre kald:
- I `_dispatch_run_done`: `_push_to_user(owner, {...})` → `_route_or_blast(owner, {"kind": "answer_ready", "session_id": sid or "", "run_id": run_id}, "answer_ready")`
- I `on_initiative`: `_push_to_user(user_id, {...})` → `_route_or_blast(user_id, {"kind": "initiative", "preview": (text or "")[:80]}, "initiative")`
- I `on_reminder`: tilsvarende med `"reminder"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_push_dispatcher_routing.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/push_dispatcher.py tests/test_push_dispatcher_routing.py
git commit -m "feat(presence): push_dispatcher ruter via proactive_router (killswitch)"
```

---

## Phase 5 — API-endpoints

### Task 9: routes/presence.py (3 endpoints) + register i app

**Files:**
- Create: `apps/api/jarvis_api/routes/presence.py`
- Modify: `apps/api/jarvis_api/app.py` (nær linje 485-486, hvor push_router registreres)
- Test: `tests/test_presence_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_presence_routes.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

import apps.api.jarvis_api.routes.presence as presence_routes
import core.services.device_presence as dp
import core.services.desktop_notifications as dn
import core.services.proactive_router as pr


def _client(monkeypatch):
    monkeypatch.setattr(presence_routes, "_current_user", lambda: "bjorn")
    app = FastAPI()
    app.include_router(presence_routes.router)
    return TestClient(app)


def test_ping_records_presence(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    c = _client(monkeypatch)
    r = c.post("/presence/ping", json={"device_key": "desk", "platform": "desktop",
                                       "foreground": True, "awake": True, "network": "home", "interaction": True})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert "desk" in dp._PRESENCE["bjorn"]


def test_pending_drains_desktop_queue(monkeypatch):
    monkeypatch.setattr(dn, "_now", lambda: 1000.0)
    dn.reset()
    dn.enqueue("bjorn", {"notif_id": "n1", "kind": "answer_ready", "title": "t", "body": "b", "session_id": "s1"})
    c = _client(monkeypatch)
    r = c.get("/notifications/pending")
    assert r.status_code == 200
    assert [i["notif_id"] for i in r.json()["items"]] == ["n1"]


def test_ack_cancels_pending(monkeypatch):
    pr.reset()
    pr._PENDING["n1"] = {"user_id": "bjorn", "payload": {}, "kind": "x", "remaining": [], "timer": None}
    c = _client(monkeypatch)
    r = c.post("/notifications/ack", json={"notif_id": "n1"})
    assert r.status_code == 200 and "n1" not in pr._PENDING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_presence_routes.py -q`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/jarvis_api/routes/presence.py
"""Device-presence + proaktive desktop-notifikationer. Scoper til auth'et bruger."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

import core.services.desktop_notifications as desktop_notifications
import core.services.device_presence as device_presence
import core.services.proactive_router as proactive_router

router = APIRouter(tags=["presence"])


class PingBody(BaseModel):
    device_key: str
    platform: str
    foreground: bool = False
    awake: bool = True
    network: str = "unknown"
    interaction: bool = False


class AckBody(BaseModel):
    notif_id: str


def _current_user() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


@router.post("/presence/ping")
async def presence_ping(body: PingBody) -> dict:
    uid = _current_user()
    if not uid or not (body.device_key or "").strip():
        return {"ok": False}
    device_presence.record_ping(
        uid, body.device_key, body.platform,
        foreground=body.foreground, awake=body.awake,
        network=body.network, interaction=body.interaction,
    )
    return {"ok": True}


@router.get("/notifications/pending")
async def notifications_pending() -> dict:
    uid = _current_user()
    if not uid:
        return {"items": []}
    return {"items": desktop_notifications.drain(uid)}


@router.post("/notifications/ack")
async def notifications_ack(body: AckBody) -> dict:
    if (body.notif_id or "").strip():
        proactive_router.ack(body.notif_id)
    return {"ok": True}
```
I `apps/api/jarvis_api/app.py` (efter push_router-registreringen ~linje 486):
```python
    from apps.api.jarvis_api.routes.presence import router as presence_router
    app.include_router(presence_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_presence_routes.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/presence.py apps/api/jarvis_api/app.py tests/test_presence_routes.py
git commit -m "feat(presence): /presence/ping + /notifications/{pending,ack} endpoints"
```

---

## Phase 6 — Jarvis-awareness (prompt_contract)

### Task 10: device-presence linje i prompten (bagest, killswitch-gatet)

**Files:**
- Modify: `core/services/prompt_contract.py`
- Test: `tests/test_prompt_contract_presence.py`

**Note (personlighed-følsom fil):** Lav KUN en lille, isoleret helper + ét append.
Rør ikke eksisterende sektioner. Find et eksisterende dynamisk awareness-append nær
slutningen (`grep -n "_runtime_awareness_prompt_surface\|parts.append" core/services/prompt_contract.py | tail`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompt_contract_presence.py
import core.services.prompt_contract as pc


def test_device_presence_line_present_when_enabled(monkeypatch):
    monkeypatch.setattr(pc, "_device_awareness_on", lambda: True)
    import core.services.device_presence as dp
    monkeypatch.setattr(dp, "summary", lambda uid: "Bjørn er ved desktop (i fokus).")
    line = pc._device_presence_line("bjorn")
    assert "desktop" in line


def test_device_presence_line_empty_when_disabled(monkeypatch):
    monkeypatch.setattr(pc, "_device_awareness_on", lambda: False)
    assert pc._device_presence_line("bjorn") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_prompt_contract_presence.py -q`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Tilføj helpers i `core/services/prompt_contract.py`:
```python
def _device_awareness_on() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().device_awareness_enabled)
    except Exception:
        return False


def _device_presence_line(user_id: str) -> str:
    if not _device_awareness_on():
        return ""
    try:
        from core.services import device_presence
        s = device_presence.summary(user_id)
        return f"[enheds-presence]: {s}" if s else ""
    except Exception:
        return ""
```
Find dér hvor den synlige prompts dynamiske hale samles (samme sted som
`_runtime_awareness_prompt_surface` bruges) og tilføj — bagest, best-effort:
```python
        _dpl = _device_presence_line(user_id)
        if _dpl:
            parts.append(_dpl)
```
(Brug det faktiske `user_id`-symbol der er i scope dér; hvis ikke tilgængeligt,
hent via `from core.identity.workspace_context import current_user_id`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_prompt_contract_presence.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_contract.py tests/test_prompt_contract_presence.py
git commit -m "feat(presence): device-presence linje i Jarvis' prompt-awareness"
```

### Task 11: Backend fuld-suite + deploy

- [ ] **Step 1:** Kør hele backend-suiten på containeren:
```bash
PYTHONPATH=/media/projects/jarvis-v2 python -m pytest tests/test_device_presence.py tests/test_desktop_notifications.py tests/test_proactive_router.py tests/test_settings_device_awareness.py tests/test_push_dispatcher_routing.py tests/test_presence_routes.py tests/test_prompt_contract_presence.py -q
```
Expected: alle PASS.

- [ ] **Step 2:** `python -m compileall core apps/api` → ingen fejl.
- [ ] **Step 3:** `sudo systemctl restart jarvis-api`; vent på healthz (HTTP 401 = oppe).
- [ ] **Step 4:** Røgtest endpoints med ægte token (mint som i tidligere session):
```bash
curl -s -m5 https://api.srvlab.dk/presence/ping -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"device_key":"smoke","platform":"desktop","foreground":true,"awake":true,"network":"home","interaction":true}'
# forvent {"ok":true}
curl -s -m5 https://api.srvlab.dk/notifications/pending -H "Authorization: Bearer $TOK"
# forvent {"items":[]}
```
- [ ] **Step 5: Commit** (hvis tweaks): `git commit -am "chore(presence): backend deploy-verifikation"`; push origin; pull local.

---

## Phase 7 — Desktop-klient (`jarvis-desk`)

### Task 12: Electron powerMonitor + generaliseret notify-bro

**Files:**
- Modify: `apps/jarvis-desk/electron/main.ts` (~linje 409 `notify:taskDone`)
- Modify: `apps/jarvis-desk/electron/preload.ts` (~linje 32 `notifyTaskDone`)
- Test: manuel (Electron main testes ikke i vitest) — verificeres i Task 15-build.

- [ ] **Step 1:** I `main.ts`, importér `powerMonitor` fra electron; tilføj sleep-state + IPC:
```typescript
let _systemAwake = true
powerMonitor.on('suspend', () => { _systemAwake = false })
powerMonitor.on('resume', () => { _systemAwake = true })
ipcMain.handle('power:isAwake', () => _systemAwake)
```
- [ ] **Step 2:** Generaliser notify — tilføj ny handler (behold `notify:taskDone`):
```typescript
ipcMain.handle('notify:show', (_event, kind: string, title: string, body: string) => {
  // genbrug samme Notification-logik som notify:taskDone
  showNativeNotification(title, body)
})
```
(Udtræk `notify:taskDone`-kroppen til en `showNativeNotification(title, body)`-funktion
og lad begge handlers kalde den — bagudkompat bevaret.)
- [ ] **Step 3:** I `preload.ts`, eksponér:
```typescript
  isAwake: () => Promise<boolean>
  notifyShow: (kind: string, title: string, body: string) => Promise<void>
```
og i implementeringen:
```typescript
  isAwake: () => ipcRenderer.invoke('power:isAwake'),
  notifyShow: (kind, title, body) => ipcRenderer.invoke('notify:show', kind, title, body),
```
- [ ] **Step 4:** `cd apps/jarvis-desk && npx tsc -b` → ingen fejl.
- [ ] **Step 5: Commit:** `git commit -am "feat(desk): powerMonitor sleep-state + notify:show bro"`

### Task 13: presence.ts + notif-poll i ChatView

**Files:**
- Create: `apps/jarvis-desk/src/lib/presence.ts`
- Modify: `apps/jarvis-desk/src/lib/api.ts` (tilføj `presencePing`, `fetchPendingNotifications`, `ackNotification`)
- Modify: `apps/jarvis-desk/src/views/ChatView.tsx` (presence-interval + notif-poll i eksisterende 1,5s-tick)
- Test: `apps/jarvis-desk/src/lib/presence.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/jarvis-desk/src/lib/presence.test.ts
import { describe, it, expect, vi } from 'vitest'
import { buildPingBody } from './presence'

describe('buildPingBody', () => {
  it('mapper desktop-state til ping-payload', () => {
    const b = buildPingBody({ deviceKey: 'dev-1', foreground: true, awake: false, interaction: true })
    expect(b).toEqual({
      device_key: 'dev-1', platform: 'desktop',
      foreground: true, awake: false, network: 'home', interaction: true,
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/presence.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```typescript
// apps/jarvis-desk/src/lib/presence.ts
// Desktop antages altid på 'home'-netværk (stationær).
export interface DesktopPingState {
  deviceKey: string
  foreground: boolean
  awake: boolean
  interaction: boolean
}

export function buildPingBody(s: DesktopPingState) {
  return {
    device_key: s.deviceKey,
    platform: 'desktop' as const,
    foreground: s.foreground,
    awake: s.awake,
    network: 'home' as const,
    interaction: s.interaction,
  }
}
```
I `src/lib/api.ts` (følg eksisterende `apiFetch`-mønster):
```typescript
export async function presencePing(config: ApiConfig, body: object): Promise<void> {
  await apiFetch(config, '/presence/ping', { method: 'POST', body: JSON.stringify(body) })
}
export async function fetchPendingNotifications(config: ApiConfig): Promise<{ items: Array<{ notif_id: string; kind: string; title: string; body: string; session_id: string }> }> {
  return apiFetch(config, '/notifications/pending')
}
export async function ackNotification(config: ApiConfig, notifId: string): Promise<void> {
  await apiFetch(config, '/notifications/ack', { method: 'POST', body: JSON.stringify({ notif_id: notifId }) })
}
```
I `ChatView.tsx`:
- Generér/læs et persistent `deviceKey` (gem i app-settings via `window.jarvisDesk.config`; generér `crypto.randomUUID()` hvis fraværende).
- Tilføj et 5s presence-interval der kalder `presencePing(cfg, buildPingBody({deviceKey, foreground: document.hasFocus(), awake: await window.jarvisDesk.isAwake(), interaction: _interactedSinceLastPing}))` og nulstiller interaction-flaget. Sæt `_interactedSinceLastPing=true` i `doSend`.
- I den eksisterende 1,5s `tick()` (poll), tilføj `fetchPendingNotifications(cfg)` → for hvert item: `window.jarvisDesk.notifyShow(item.kind, item.title, item.body)` + `ackNotification(cfg, item.notif_id)`; gem `item.session_id` så klik på notifikationen (via eksisterende run:setSession-sti) navigerer dertil.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/presence.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit:** `git commit -am "feat(desk): presence-ping + proaktiv notif-poll"`

---

## Phase 8 — Mobil-klient

### Task 14: presence.ts (AppState/NetInfo → ping) + FCM notif_id→ack

**Files:**
- Create: `.worktrees/jarvis-mobile-companion-v1/apps/mobile/src/lib/presence.ts`
- Modify: `.worktrees/jarvis-mobile-companion-v1/apps/mobile/src/App.tsx` (start presence-rapportering)
- Modify: `.worktrees/jarvis-mobile-companion-v1/apps/mobile/src/lib/push.ts` (ack på notif-visning)
- Test: `.worktrees/jarvis-mobile-companion-v1/apps/mobile/src/lib/presence.test.ts`

**Miljø:** `git -C .worktrees/jarvis-mobile-companion-v1` (gren `codex/jarvis-mobile-companion-v1`). Tests: `cd .worktrees/jarvis-mobile-companion-v1/apps/mobile && npx jest src/lib/presence.test.ts`.

- [ ] **Step 1: Write the failing test**

```typescript
// .../apps/mobile/src/lib/presence.test.ts
import { networkToHint, buildMobilePing } from './presence'

describe('mobil presence', () => {
  it('mapper netværkstype til hint', () => {
    expect(networkToHint('wifi')).toBe('home')
    expect(networkToHint('cellular')).toBe('away')
    expect(networkToHint('none')).toBe('unknown')
  })
  it('bygger ping-payload', () => {
    expect(buildMobilePing({ token: 'tok-1', foreground: true, network: 'away', interaction: false })).toEqual({
      device_key: 'tok-1', platform: 'mobile',
      foreground: true, awake: true, network: 'away', interaction: false,
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .worktrees/jarvis-mobile-companion-v1/apps/mobile && npx jest src/lib/presence.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```typescript
// .../apps/mobile/src/lib/presence.ts
export function networkToHint(type: string): 'home' | 'away' | 'unknown' {
  if (type === 'wifi') return 'home'
  if (type === 'cellular') return 'away'
  return 'unknown'
}

export interface MobilePingInput {
  token: string
  foreground: boolean
  network: 'home' | 'away' | 'unknown'
  interaction: boolean
}

export function buildMobilePing(i: MobilePingInput) {
  return {
    device_key: i.token,
    platform: 'mobile' as const,
    foreground: i.foreground,
    awake: true,
    network: i.network,
    interaction: i.interaction,
  }
}
```
I `App.tsx`: abonnér på `AppState` (active/background) + `@react-native-community/netinfo`
`addEventListener` (eller eksisterende net-modul) + et 30s-interval mens foreground;
ved hver ændring POST `/presence/ping` med `buildMobilePing(...)` (FCM-token som device_key,
`networkToHint(state.type)`). Marker `interaction=true` ved app-åbning/besked-send.
I `push.ts`: når en notifee-notifikation vises med en `notif_id` i FCM-data → POST
`/notifications/ack` med `{notif_id}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .worktrees/jarvis-mobile-companion-v1/apps/mobile && npx jest src/lib/presence.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit:**
```bash
git -C .worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/presence.ts apps/mobile/src/lib/presence.test.ts apps/mobile/src/App.tsx apps/mobile/src/lib/push.ts
git -C .worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): presence-rapportering (AppState/NetInfo) + FCM notif_id→ack"
```

---

## Phase 9 — Fuld verifikation + build

### Task 15: Hele suiten + on-device

- [ ] **Step 1: Backend** (container): kør ALLE 7 nye test-filer + `python -m compileall core apps/api`. Alt grønt.
- [ ] **Step 2: Desktop:** `cd apps/jarvis-desk && npx tsc -b && npx vitest run`. Alt grønt. Bump `package.json`-version (KRITISK før build, ellers no-op'er dpkg). Byg + installér på Bjørns maskine.
- [ ] **Step 3: Mobil:** `cd .worktrees/jarvis-mobile-companion-v1/apps/mobile && npx jest && npx tsc --noEmit`. Bump version (vc). Byg + installér på S24.
- [ ] **Step 4: Deploy/sync:** push container→origin, pull local; push mobil-gren.
- [ ] **Step 5: On-device E2E med Bjørn (afkrydsning):**
  - Desktop åben+fokus, mobil i baggrund → send en besked der trigger et langt svar; luk ikke; bekræft svar-klar lander på DESKTOP (ikke mobil).
  - Desktop lukket/sovende → samme → lander på MOBIL.
  - Reminder/initiativ → rammer den aktive enhed; eskalerer til den anden hvis ingen ack inden ~3 min.
  - Jarvis' prompt: spørg "hvor er jeg lige nu?" → han kender enheden.

---

## Self-Review (udført)

**Spec-dækning:** §1 presence-model→Task 1-3; §2 rapportering→Task 13-14; §3 routing+eskalering→Task 5-6; §3 desktop-kanal→Task 4,12-13; §5 Jarvis-awareness→Task 10; killswitch→Task 7-8; endpoints→Task 9; privacy (kun home/away-hint, per-bruger-scope)→indbygget i Task 1/9; test-plan→hver task + Task 11/15. Ingen åbne spec-krav uden task.

**Placeholder-scan:** Ingen TBD/TODO. Hvert kode-trin har fuld kode. To bevidste
"find det rigtige symbol"-noter (settings parse-funktionsnavn i Task 7; prompt_contract
append-sted i Task 10) — med eksakt grep-kommando, fordi de filer er store/personligheds-
følsomme og det præcise indsætningspunkt skal bekræftes mod live-koden, ikke gættes.

**Type-konsistens:** `RankedDevice.reachable_via` ∈ {"desktop_queue","fcm"} bruges
konsistent i Task 2/5. `record_ping`-signatur identisk i Task 1, routes (Task 9), tests.
`notif_id`-feltnavn konsistent på tværs af desktop-kø, router, endpoints, klienter.
`_route_or_blast(user_id, data, kind)` samme signatur i Task 8 + kald.
