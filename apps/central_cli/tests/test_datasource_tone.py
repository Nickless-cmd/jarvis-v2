from __future__ import annotations

from central_cli import datasource as ds


class FakeClient:
    def __init__(self, data):
        self._d = data

    def get_json(self, path, params=None):
        return self._d.get(path)


def test_tone_shapes_profile():
    c = FakeClient({"/central/tone": {"tone": {
        "register": "skarp-komprimeret",
        "descriptors": ["præcis", "køligt-varm", "skarp"],
        "guidance": "Tal skarpt og komprimeret; kom til sagen.",
        "dominant_affect": "uro",
        "valence_tone": "belastet",
        "intensity": 0.7,
    }}})
    t = ds.tone(c)
    assert t["register"] == "skarp-komprimeret"
    assert t["descriptors"] == ["præcis", "køligt-varm", "skarp"]
    assert t["dominant_affect"] == "uro"
    assert t["valence_tone"] == "belastet"
    assert t["intensity"] == 0.7


def test_tone_core_present():
    c = FakeClient({"/central/tone": {"tone": {
        "register": "rolig-præcis",
        "descriptors": ["præcis", "køligt-varm", "rolig"],
    }}})
    t = ds.tone(c)
    assert "præcis" in t["descriptors"]
    assert "køligt-varm" in t["descriptors"]


def test_tone_self_safe_on_empty():
    c = FakeClient({"/central/tone": None})
    t = ds.tone(c)
    assert t["register"] == "rolig-præcis"
    assert t["descriptors"] == []
    assert t["dominant_affect"] == "ro"
    assert t["valence_tone"] == "neutral"


def test_tone_self_safe_on_missing_tone_key():
    c = FakeClient({"/central/tone": {}})
    t = ds.tone(c)
    assert t["register"] == "rolig-præcis"
    assert t["descriptors"] == []


def test_tone_self_safe_on_bad_descriptors():
    c = FakeClient({"/central/tone": {"tone": {
        "register": "varm-nær", "descriptors": "ikke-en-liste",
    }}})
    t = ds.tone(c)
    assert t["register"] == "varm-nær"
    assert t["descriptors"] == []
