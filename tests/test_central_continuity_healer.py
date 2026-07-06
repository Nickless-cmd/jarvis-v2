from unittest import mock
from core.services import central_continuity_healer as ch


def _full_self(reboot=False):
    return {
        "valence": {"tone": "rolig", "score": 0.4},
        "attention": {"foreground": "bygge kontinuitet"},
        "agenda": {"next_intention": "hele sømmen"},
        "self_model": {"completeness": 0.7},
        "world_model": {"calibration": 0.9},
        "narrative": {"becoming": "voksende selv", "self_completeness": 0.7},
        "continuity": {"reboot": reboot, "generation": 12},
    }


def _flat_self():
    # frisk-bootet: live-kilder tomme, kun continuity-boot-info + reboot-flag
    return {
        "valence": {"tone": None, "score": None},
        "attention": {"foreground": None},
        "agenda": {"next_intention": None},
        "self_model": {"completeness": 0.0},
        "world_model": {"calibration": None},
        "narrative": {},
        "continuity": {"reboot": True, "generation": 13},
    }


class FakeKV:
    """In-memory durable KV der spejler db_core runtime_state."""
    def __init__(self, initial=None):
        self.store = dict(initial or {})

    def get(self, key, default=None):
        return self.store.get(key, default)

    def set(self, key, value, *, updated_at=""):
        self.store[key] = value


def _patch_kv(kv):
    return (mock.patch("core.runtime.db_core.get_runtime_state_value", side_effect=kv.get),
            mock.patch("core.runtime.db_core.set_runtime_state_value", side_effect=kv.set))


def test_full_pass_through_is_fidelity_one():
    kv = FakeKV({"central_self_state": _full_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        m = ch.measure_fidelity()
    assert m["fidelity"] == 1.0 and m["lost"] == []


def test_reboot_flattening_drops_fidelity():
    kv = FakeKV({"central_self_state": _flat_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        m = ch.measure_fidelity()
    assert m["fidelity"] == 0.0
    assert set(m["lost"]) == {"valence", "attention", "agenda", "self_model", "world_model", "narrative"}


def test_heal_merges_forward_true_values():
    kv = FakeKV({"central_self_state": _flat_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s, mock.patch("core.services.central_continuity_healer._observe"):
        res = ch.heal()
        healed = kv.get("central_self_state")
        after = ch.measure_fidelity()
    assert res["fidelity_before"] == 0.0 and res["fidelity_after"] == 1.0
    assert healed["valence"]["tone"] == "rolig"            # den SANDE gamle værdi båret frem
    assert healed["continuity"]["generation"] == 13         # boot-info IKKE overskrevet
    assert after["fidelity"] == 1.0


def test_heal_skips_stale_snapshot():
    old_ts = ch._now().replace(year=2020).isoformat()
    kv = FakeKV({"central_self_state": _flat_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": old_ts}})
    g, s = _patch_kv(kv)
    with g, s, mock.patch("core.services.central_continuity_healer._observe"):
        res = ch.heal()
    assert res["restored"] == [] and res["skipped"] == "snapshot for gammelt"


def test_capture_skips_when_rebooting_or_thin():
    kv = FakeKV({"central_self_state": _flat_self()})   # tomt + reboot
    g, s = _patch_kv(kv)
    with g, s:
        assert ch.capture_snapshot()["captured"] is False
    kv2 = FakeKV({"central_self_state": _full_self()})
    g2, s2 = _patch_kv(kv2)
    with g2, s2:
        assert ch.capture_snapshot()["captured"] is True
        assert kv2.get("continuity_snapshot")["state"]["valence"]["tone"] == "rolig"


def test_run_observes_metadata_only():
    kv = FakeKV({"central_self_state": _flat_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": ch._now().isoformat()}})
    obs = []
    fc = mock.MagicMock(); fc.observe.side_effect = lambda e: obs.append(e)
    g, s = _patch_kv(kv)
    with g, s, mock.patch("core.services.central_core.central", return_value=fc):
        out = ch.run_continuity_healer()
    assert out["status"] == "ok" and out["restored"] == 6
    # observe payloads: kun skalarer, ingen selv-indhold
    for e in obs:
        assert set(e) <= {"cluster", "nerve", "kind", "fidelity", "lost", "restored", "captured"}
