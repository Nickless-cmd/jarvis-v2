def test_events_no_family_path_and_shape():
    from central_cli import datasource
    seen = {}
    class FC:
        def get_json(self, p, params=None):
            seen["path"] = p
            seen["params"] = params
            return {"items": [{"id": 1}, {"id": 2}], "count": 2}
    out = datasource.events(FC())
    assert seen["path"] == "/central/events"
    assert seen["params"] == {"limit": 50}  # family udeladt når None
    assert out == [{"id": 1}, {"id": 2}]


def test_events_with_family_and_limit_params():
    from central_cli import datasource
    seen = {}
    class FC:
        def get_json(self, p, params=None):
            seen["params"] = params
            return {"items": [{"id": 9}]}
    out = datasource.events(FC(), family="tool", limit=10)
    assert seen["params"] == {"limit": 10, "family": "tool"}
    assert out == [{"id": 9}]


def test_events_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): raise RuntimeError("nej")
    assert datasource.events(FC()) == []


def test_memory_health_path_and_shape():
    from central_cli import datasource
    seen = {}
    class FC:
        def get_json(self, p, params=None):
            seen["path"] = p
            return {
                "added_today": 42,
                "journal_today": True,
                "memory": {"jarvis_brain": {"added_today": 42}},
            }
    out = datasource.memory_health(FC())
    assert seen["path"] == "/central/memory-health"
    assert out["added_today"] == 42
    assert out["journal_today"] is True
    assert out["memory"] == {"jarvis_brain": {"added_today": 42}}


def test_memory_health_self_safe():
    from central_cli import datasource
    class FC:
        def get_json(self, p, params=None): raise RuntimeError("nej")
    out = datasource.memory_health(FC())
    assert out == {"added_today": 0, "journal_today": False, "memory": {}}
