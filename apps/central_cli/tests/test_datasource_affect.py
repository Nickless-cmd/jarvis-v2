from __future__ import annotations

from central_cli import datasource as ds


class FakeClient:
    def __init__(self, data):
        self._d = data

    def get_json(self, path, params=None):
        return self._d.get(path)


def test_affect_shapes_distribution():
    c = FakeClient({"/central/affect": {
        "tryk": 3, "varme": 1, "uro": 5, "ro": 10,
        "dominant": "uro", "total": 19,
    }})
    a = ds.affect(c)
    assert a["uro"] == 5
    assert a["ro"] == 10
    assert a["dominant"] == "uro"
    assert a["total"] == 19


def test_affect_self_safe_on_empty():
    c = FakeClient({"/central/affect": None})
    a = ds.affect(c)
    assert a["dominant"] == "ro"
    assert a["tryk"] == a["varme"] == a["uro"] == a["ro"] == 0


def test_affect_self_safe_on_missing_keys():
    c = FakeClient({"/central/affect": {"dominant": "varme"}})
    a = ds.affect(c)
    assert a["dominant"] == "varme"
    assert a["uro"] == 0
