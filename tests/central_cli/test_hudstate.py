from central_cli.engine.state import HudState


def test_set_ok_stores_data_and_clears_error():
    s = HudState()
    s.set_error("realtime", "boom")
    s.set_ok("realtime", {"status": "green"})
    e = s.get("realtime")
    assert e.data == {"status": "green"}
    assert e.error is None
    assert e.fetched_at > 0
    assert e.loading is False


def test_set_error_preserves_last_good_data():
    s = HudState()
    s.set_ok("realtime", {"status": "green"})
    s.set_error("realtime", "HTTP 500")
    e = s.get("realtime")
    assert e.data == {"status": "green"}
    assert e.error == "HTTP 500"


def test_get_unknown_surface_returns_empty_entry():
    s = HudState()
    e = s.get("nope")
    assert e.data is None and e.error is None and e.fetched_at == 0.0


def test_is_stale_uses_monotonic_age(monkeypatch):
    import central_cli.engine.state as st
    now = [1000.0]
    monkeypatch.setattr(st, "_now", lambda: now[0])
    s = HudState()
    s.set_ok("x", 1)
    now[0] = 1002.0
    assert s.is_stale("x", max_age_s=1.0) is True
    assert s.is_stale("x", max_age_s=5.0) is False
    assert s.is_stale("never_fetched", max_age_s=5.0) is True
