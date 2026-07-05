def test_inner_life_path_and_shape():
    from central_cli import datasource
    seen = {}

    class FC:
        def get_json(self, p, params=None):
            seen["path"] = p
            return {"inner_life": {
                "sections": {"thought_stream": {"liveness": True, "count": 5}},
                "live_count": 1,
                "total": 12,
            }}

    out = datasource.inner_life(FC())
    assert seen["path"] == "/central/inner-life"
    assert out["sections"] == {"thought_stream": {"liveness": True, "count": 5}}
    assert out["live_count"] == 1
    assert out["total"] == 12


def test_inner_life_missing_key_defaults():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            return {}

    out = datasource.inner_life(FC())
    assert out == {"sections": {}, "live_count": 0, "total": 0}


def test_inner_life_non_dict_is_self_safe():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            return "nope"

    assert datasource.inner_life(FC()) == {"sections": {}, "live_count": 0, "total": 0}


def test_inner_life_self_safe_on_raise():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            raise RuntimeError("nej")

    assert datasource.inner_life(FC()) == {"sections": {}, "live_count": 0, "total": 0}
