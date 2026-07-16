def test_rate_cap_blocks_request_burst(monkeypatch):
    from core.services import non_visible_rate_cap as rc
    monkeypatch.setattr(rc, "_now", lambda: 1000.0)
    rc.reset()
    allowed = [rc.allow(tokens=1) for _ in range(rc.REQ_PER_MIN + 5)]
    assert allowed.count(True) == rc.REQ_PER_MIN   # excess rejected within the minute


def test_rate_cap_refills_after_a_minute(monkeypatch):
    from core.services import non_visible_rate_cap as rc
    t = {"v": 1000.0}
    monkeypatch.setattr(rc, "_now", lambda: t["v"])
    rc.reset()
    for _ in range(rc.REQ_PER_MIN): rc.allow(tokens=1)
    assert rc.allow(tokens=1) is False
    t["v"] += 61   # a minute later
    assert rc.allow(tokens=1) is True


def test_token_budget_blocks(monkeypatch):
    from core.services import non_visible_rate_cap as rc
    monkeypatch.setattr(rc, "_now", lambda: 1000.0)
    rc.reset()
    assert rc.allow(tokens=rc.TOKENS_PER_DAY) is True   # exactly at budget
    assert rc.allow(tokens=1) is False                  # over budget same day
