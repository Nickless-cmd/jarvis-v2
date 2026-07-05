def test_soul_path_and_shape():
    from central_cli import datasource
    seen = {}

    class FC:
        def get_json(self, p, params=None):
            seen["path"] = p
            return {
                "signals": {
                    "longing": {"liveness": True, "count": 3},
                    "identity_drift": {"liveness": False, "count": 0},
                },
                "live_count": 1,
                "total": 2,
            }

    out = datasource.soul(FC())
    assert seen["path"] == "/central/soul"
    assert out["signals"] == {
        "longing": {"liveness": True, "count": 3},
        "identity_drift": {"liveness": False, "count": 0},
    }
    assert out["live_count"] == 1
    assert out["total"] == 2


def test_soul_missing_key_defaults():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            return {}

    assert datasource.soul(FC()) == {"signals": {}, "live_count": 0, "total": 0}


def test_soul_non_dict_is_self_safe():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            return "nope"

    assert datasource.soul(FC()) == {"signals": {}, "live_count": 0, "total": 0}


def test_soul_self_safe_on_raise():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            raise RuntimeError("nej")

    assert datasource.soul(FC()) == {"signals": {}, "live_count": 0, "total": 0}
