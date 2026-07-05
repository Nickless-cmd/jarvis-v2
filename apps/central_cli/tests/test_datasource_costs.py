def test_cost_today_reads_central():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None):
            assert p == "/central/costs-daily"
            return {"today_cost": 3.5, "week_cost": 9.0, "days": []}
    assert datasource.cost_today(FC()) == 3.5


def test_cost_today_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): raise RuntimeError("nej")
    assert datasource.cost_today(FC()) is None


def test_costs_daily_shape():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None):
            return {"today_cost": 3.5, "week_cost": 9.0, "days":[{"day":"2026-07-05","lane":"primary","total_cost":3.5,"calls":2,"total_tokens":100}]}
    out = datasource.costs_daily(FC())
    assert out["week_cost"] == 9.0 and len(out["days"]) == 1
