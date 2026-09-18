from __future__ import annotations

from central_cli import datasource as ds


class FakeClient:
    def __init__(self, data):
        self._d = data

    def get_json(self, path, params=None):
        return self._d.get(path)


class BrokenClient:
    def get_json(self, path, params=None):
        raise RuntimeError("endpoint nede")


_SVAR = {
    "/mc/emotional-memory?limit=5": {
        "counts": {
            "total": 150514,
            "scored": 3198,
            "unscored": 147316,
            "scored_share": 0.0212,
            "by_type": {"perceptual_event": 146824, "cognitive_episode": 3155},
            "scored_by_type": {"cognitive_episode": 3140},
            "by_outcome": {"good": 562, "bad": 2634, "neutral": 2},
        },
        "span": {"oldest_at": "2025-12-19T02:19:35+00:00",
                 "newest_at": "2026-09-18T12:10:33+00:00"},
    }
}


def test_ankre_baerer_andelen_med_udfald():
    """Andelen er fladens egentlige ærinde — den må ikke skulle udregnes af
    den der læser panelet."""
    a = ds.emotional_anchors(FakeClient(_SVAR))
    assert a["total"] == 150514
    assert a["scored"] == 3198
    assert a["scored_share"] == 0.0212


def test_ankre_viser_hvilke_typer_der_kan_afgoeres():
    """Den type der fylder 97 % får aldrig et udfald. Uden denne opdeling
    ligner de 150.000 en erfaring."""
    a = ds.emotional_anchors(FakeClient(_SVAR))
    assert a["by_type"]["perceptual_event"] == 146824
    assert "perceptual_event" not in a["scored_by_type"]
    assert a["scored_by_type"]["cognitive_episode"] == 3140


def test_ankre_er_selv_sikker_ved_fejl():
    for klient in (BrokenClient(), FakeClient({}), FakeClient({"/mc/emotional-memory?limit=5": "nej"})):
        a = ds.emotional_anchors(klient)
        assert a["total"] == 0
        assert a["scored_by_type"] == {}
