def test_council_reads_central():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None):
            assert p == "/central/council"
            return {"sessions": [{"council_id": "a"}], "count": 1}
    out = datasource.council(FC())
    assert isinstance(out, list) and len(out) == 1


def test_council_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): raise RuntimeError("nej")
    assert datasource.council(FC()) == []


def test_scheduled_reads_central():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None):
            assert p == "/central/queues/scheduled"
            return {"tasks": [{"id": 1}, {"id": 2}], "count": 2}
    out = datasource.scheduled(FC())
    assert isinstance(out, list) and len(out) == 2


def test_scheduled_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): raise RuntimeError("nej")
    assert datasource.scheduled(FC()) == []


def test_autonomy_reads_central():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None):
            assert p == "/central/autonomy"
            return {"proposals": [{"id": "p1"}], "pending_count": 1}
    out = datasource.autonomy(FC())
    assert out["pending_count"] == 1 and len(out["proposals"]) == 1


def test_autonomy_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): raise RuntimeError("nej")
    out = datasource.autonomy(FC())
    assert out == {"proposals": [], "pending_count": 0}
