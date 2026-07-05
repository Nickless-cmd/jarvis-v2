import pytest
from unittest.mock import patch


def test_costs_daily_shapes_and_absorbs():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake_days = [
        {"day":"2026-07-05","lane":"primary","calls":10,"total_tokens":1000,"total_cost":6.0},
        {"day":"2026-07-05","lane":"cheap","calls":5,"total_tokens":500,"total_cost":1.0},
        {"day":"2026-07-04","lane":"primary","calls":8,"total_tokens":800,"total_cost":2.0},
    ]
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.costing.ledger.daily_cost_summary", lambda: fake_days), \
         patch("core.costing.ledger.today_cost", lambda: 7.0), \
         patch("core.costing.ledger.this_week_cost", lambda: 20.0), \
         patch("core.costing.ledger.telemetry_summary", lambda: {"total_cost_usd": 7.0}), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        import asyncio
        out = asyncio.new_event_loop().run_until_complete(m.get_costs_daily())
    assert out["today_cost"] == 7.0
    assert out["week_cost"] == 20.0
    assert out["today_total"] == 7.0   # 6.0 + 1.0
    assert out["prev_total"] == 2.0
    assert out["days"] == fake_days
    assert calls["absorb"], "absorb skal kaldes"
    a, k = calls["absorb"][0]
    assert a[0] == "cost" and a[1] == "daily"


def test_costs_daily_self_safe_on_producer_error():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    def boom(): raise RuntimeError("nej")
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.costing.ledger.daily_cost_summary", boom), \
         patch("core.costing.ledger.today_cost", boom), \
         patch("core.costing.ledger.this_week_cost", boom), \
         patch("core.costing.ledger.telemetry_summary", boom), \
         patch.object(m, "absorb", lambda *a, **k: None):
        import asyncio
        out = asyncio.new_event_loop().run_until_complete(m.get_costs_daily())
    assert out["days"] == [] and out["today_cost"] == 0.0
