def test_inner_life_path_and_shape():
    from central_cli import datasource
    seen = {}

    class FC:
        def get_json(self, p, params=None):
            seen["path"] = p
            return {"inner_life": {
                "inner_life": {"thought_stream": {"liveness": True, "count": 5}},
                "experiment": {"adaptive_learning": {"liveness": True, "count": 3}},
                "live_count": 2,
                "total": 37,
            }}

    out = datasource.inner_life(FC())
    assert seen["path"] == "/central/inner-life"
    assert out["inner_life"] == {"thought_stream": {"liveness": True, "count": 5}}
    assert out["experiment"] == {"adaptive_learning": {"liveness": True, "count": 3}}
    assert out["live_count"] == 2
    assert out["total"] == 37


def test_inner_life_missing_key_defaults():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            return {}

    out = datasource.inner_life(FC())
    assert out == {"inner_life": {}, "experiment": {}, "live_count": 0, "total": 0}


def test_inner_life_non_dict_is_self_safe():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            return "nope"

    assert datasource.inner_life(FC()) == {
        "inner_life": {}, "experiment": {}, "live_count": 0, "total": 0}


def test_inner_life_self_safe_on_raise():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            raise RuntimeError("nej")

    assert datasource.inner_life(FC()) == {
        "inner_life": {}, "experiment": {}, "live_count": 0, "total": 0}
