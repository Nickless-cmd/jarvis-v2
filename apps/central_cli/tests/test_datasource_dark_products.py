def test_dark_products_path_and_shape():
    from central_cli import datasource
    seen = {}

    class FC:
        def get_json(self, p, params=None):
            seen["path"] = p
            return {
                "signals": {
                    "apophenia": {"liveness": True, "count": 3},
                    "rule_engine": {"liveness": True, "count": 12},
                    "deep_reflection": {"liveness": False, "count": 0},
                },
                "live_count": 2,
                "total": 3,
            }

    out = datasource.dark_products(FC())
    assert seen["path"] == "/central/dark-products"
    assert out["signals"]["apophenia"] == {"liveness": True, "count": 3}
    assert out["live_count"] == 2
    assert out["total"] == 3


def test_dark_products_missing_key_defaults():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            return {}

    assert datasource.dark_products(FC()) == {"signals": {}, "live_count": 0, "total": 0}


def test_dark_products_non_dict_is_self_safe():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            return "nope"

    assert datasource.dark_products(FC()) == {"signals": {}, "live_count": 0, "total": 0}


def test_dark_products_self_safe_on_raise():
    from central_cli import datasource

    class FC:
        def get_json(self, p, params=None):
            raise RuntimeError("nej")

    assert datasource.dark_products(FC()) == {"signals": {}, "live_count": 0, "total": 0}
