import core.services.cache_boundary_observer as obs


def _reset():
    with obs._lock:
        obs._last_sha.clear()


def test_first_run_records_no_drift(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append((a, k)))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,),
                              static_prefix_sha="aaa")
    assert calls == []


def test_same_sha_no_drift(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append(a))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="aaa")
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="aaa")
    assert calls == []


def test_same_shape_changed_sha_records_drift(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append((a, k)))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="aaa")
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="bbb")
    assert len(calls) == 1
    assert calls[0][0][0] == "context" and calls[0][0][1] == "cache_boundary_drift"


def test_different_shape_is_different_key(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append(a))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="aaa")
    obs.observe_static_prefix(provider="p", model="m", section_shape=(4,), static_prefix_sha="bbb")
    assert calls == []  # different shape → different key → no drift


def test_empty_sha_ignored(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append(a))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="")
    assert calls == [] and not obs._last_sha
