def test_runs_reads_central_with_limit():
    from central_cli import datasource
    seen = {}
    class FC:
        def get_json(self, p, params=None):
            seen["path"] = p
            seen["params"] = params
            return {"runs": [{"run_id": "r-1", "status": "completed"}], "count": 1}
    out = datasource.runs(FC(), limit=20)
    assert seen["path"] == "/central/runs"
    assert seen["params"] == {"limit": 20}
    assert len(out) == 1 and out[0]["run_id"] == "r-1"


def test_runs_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): raise RuntimeError("nej")
    assert datasource.runs(FC()) == []


def test_runs_non_dict_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): return None
    assert datasource.runs(FC()) == []


def test_run_detail_reads_central():
    from central_cli import datasource
    seen = {}
    class FC:
        def get_json(self, p, params=None):
            seen["path"] = p
            return {"run": {"run_id": "r-9", "status": "failed"}, "found": True}
    out = datasource.run_detail(FC(), "r-9")
    assert seen["path"] == "/central/runs/r-9"
    assert out["run_id"] == "r-9" and out["status"] == "failed"


def test_run_detail_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): raise RuntimeError("nej")
    assert datasource.run_detail(FC(), "r-9") == {}


def test_run_detail_not_found_returns_empty():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): return {"run": None, "found": False}
    assert datasource.run_detail(FC(), "nope") == {}
