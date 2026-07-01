"""Tests for core/services/eventbus_central_bridge.py — KEYSTONE poll-bro (M0, §23/§24)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries
from core.services import eventbus_central_bridge as br


class _FakeCentral:
    def __init__(self, *, raise_on_observe: bool = False):
        self.observed: list[dict] = []
        self.raise_on_observe = raise_on_observe

    def observe(self, event):
        if self.raise_on_observe:
            raise RuntimeError("boom")
        self.observed.append(dict(event))


class _FakeBus:
    def __init__(self, rows):
        self._rows = rows

    def recent(self, *, limit=1):
        return list(self._rows[-limit:]) if self._rows else []

    def recent_since_id(self, after_id, *, limit=200):
        out = [r for r in self._rows if int(r.get("id") or 0) > int(after_id)]
        return out[:limit]


class _FakeCache:
    def __init__(self):
        self.store: dict = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, *, ttl_seconds):
        self.store[key] = value


def _ev(eid, kind):
    return {"id": eid, "kind": kind, "family": kind.split(".", 1)[0]}


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


@pytest.fixture
def wired(monkeypatch):
    """Bind bro'en til fakes. Returnerer (central, bus, cache) + helper til at sætte enabled."""
    fake_central = _FakeCentral()
    cache = _FakeCache()

    monkeypatch.setattr(br, "central", lambda: fake_central)
    monkeypatch.setattr(br, "shared_cache", cache)
    # kill-switch default ON
    import core.services.central_switches as sw
    monkeypatch.setattr(sw, "is_enabled", lambda scope, name: True)

    def _bind_bus(rows):
        monkeypatch.setattr(br, "event_bus", _FakeBus(rows))

    return fake_central, cache, _bind_bus, fake_central


# ── Design-invarianter (statiske) ──

def test_allowlist_excludes_private_families():
    # §24.4: ingen privat/inner-life family må være i routing-allowlisten i M0.
    assert set(br.FAMILY_ROUTES).isdisjoint(br.PRIVATE_FAMILIES_EXCLUDED_M0)


def test_allowlist_routes_are_wellformed():
    for fam, route in br.FAMILY_ROUTES.items():
        assert isinstance(route, tuple) and len(route) == 2
        assert all(isinstance(x, str) and x for x in route)


def test_central_not_in_allowlist():
    # rekursions-guard: central.* må aldrig routes.
    assert "central" not in br.FAMILY_ROUTES


# ── Adfærd ──

def test_cold_start_seeds_and_observes_nothing(wired):
    central, cache, bind_bus, _ = wired
    bind_bus([_ev(1, "tool.x"), _ev(7, "runtime.y")])
    res = br.run_bridge_tick()
    assert res["observed"] == 0
    assert res["seeded"] == 7  # seedede fra max-id
    assert central.observed == []  # backlog IKKE re-observed
    assert cache.store[br._LAST_SEEN_KEY] == {"id": 7}


def test_routes_only_whitelisted(wired):
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}  # ikke kold start
    bind_bus([
        _ev(1, "tool.called"),          # → observes (tools/event)
        _ev(2, "central.observed"),     # → skip (rekursions-guard)
        _ev(3, "inner_voice.spoke"),    # → skip (privat, hverken allowlist ELLER no-egress)
        _ev(4, "runtime.run_ended"),    # → observes (loop/lifecycle)
        _ev(5, "cognitive_state.shift"),# → PRIVATE_NO_EGRESS: observeres EGRESS-FRIT (ikke i central.observed)
    ])
    res = br.run_bridge_tick()
    assert res["observed"] == 3   # cognitive_state tælles med, men egress-frit
    assert res["skipped"] == 2    # central-guard + inner_voice
    assert res["last_seen_id"] == 5
    # KRITISK egress-invariant: den private cognitive_state-event nåede ALDRIG central().observe
    kinds = {o["event_kind"] for o in central.observed}
    assert kinds == {"tool.called", "runtime.run_ended"}, "privat event må ALDRIG egress'e via central().observe"
    clusters = {(o["cluster"], o["nerve"]) for o in central.observed}
    assert clusters == {("tools", "event"), ("loop", "lifecycle")}


def test_metadata_only_no_payload_forwarded(wired):
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    # event med potentielt følsomt payload-indhold
    ev = {"id": 1, "kind": "channel.message_received", "family": "channel",
          "payload": {"text": "hemmelig brugerbesked"}}
    bind_bus([ev])
    br.run_bridge_tick()
    assert len(central.observed) == 1
    forwarded = central.observed[0]
    # KUN metadata — intet payload/brugerindhold (§24.4)
    assert set(forwarded) <= {"cluster", "nerve", "kind", "event_id", "event_kind", "family"}
    assert "payload" not in forwarded
    assert "hemmelig" not in str(forwarded)


def test_killswitch_skips(wired, monkeypatch):
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    bind_bus([_ev(1, "tool.x")])
    import core.services.central_switches as sw
    monkeypatch.setattr(sw, "is_enabled", lambda scope, name: False)
    res = br.run_bridge_tick()
    assert res["status"] == "skipped"
    assert res["reason"] == "killswitch"
    assert central.observed == []


def test_observe_failure_counted_not_raised(wired, monkeypatch):
    _, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    failing = _FakeCentral(raise_on_observe=True)
    monkeypatch.setattr(br, "central", lambda: failing)
    bind_bus([_ev(1, "tool.x"), _ev(2, "runtime.y")])
    res = br.run_bridge_tick()  # må ikke kaste
    assert res["failures"] == 2
    assert res["observed"] == 0
    # last_seen skal stadig avancere (vi vil ikke hænge fast og re-fejle evigt)
    assert res["last_seen_id"] == 2


def test_idempotent_advances_last_seen(wired):
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    bind_bus([_ev(1, "tool.x"), _ev(2, "tool.y")])
    br.run_bridge_tick()
    assert cache.store[br._LAST_SEEN_KEY] == {"id": 2}
    # andet tick, ingen nye rows → intet observed igen
    res2 = br.run_bridge_tick()
    assert res2["observed"] == 0
    assert len(central.observed) == 2  # ikke dobbelt-observed


def test_timeseries_recorded(wired):
    _, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    bind_bus([_ev(1, "tool.x")])
    br.run_bridge_tick()
    assert len(central_timeseries.recent("tools", "event")) == 1


def test_global_workspace_keystone_routed():
    # LivingNeuron keystone: GWT-broadcast SKAL routes til Central (cognition/global_broadcast)
    # og må ALDRIG være privat-ekskluderet (det er tvær-daemon salience, ikke privat indhold).
    from core.services.eventbus_central_bridge import FAMILY_ROUTES, PRIVATE_FAMILIES_EXCLUDED_M0
    assert FAMILY_ROUTES.get("global_workspace") == ("cognition", "global_broadcast")
    assert "global_workspace" not in PRIVATE_FAMILIES_EXCLUDED_M0


def test_private_no_egress_invariant():
    # §24.4 keystone: PRIVATE_NO_EGRESS-families må ALDRIG stå i FAMILY_ROUTES (som kan egress'e),
    # og de SKAL være dokumenteret som private (i excluded-listen).
    from core.services.eventbus_central_bridge import (
        PRIVATE_NO_EGRESS_ROUTES, FAMILY_ROUTES, PRIVATE_FAMILIES_EXCLUDED_M0)
    for fam in PRIVATE_NO_EGRESS_ROUTES:
        assert fam not in FAMILY_ROUTES, f"{fam} i FAMILY_ROUTES = egress-læk-risiko!"
        assert fam in PRIVATE_FAMILIES_EXCLUDED_M0, f"{fam} bør dokumenteres som privat"


def test_observe_private_writes_egress_free():
    # _observe_private skriver til trace+timeseries men kalder ALDRIG central().observe.
    from core.services import eventbus_central_bridge as b
    ok = b._observe_private("cognition", "cognitive_state",
                            {"kind": "cognitive_state.emergent_goal_created", "id": 1})
    assert ok is True
