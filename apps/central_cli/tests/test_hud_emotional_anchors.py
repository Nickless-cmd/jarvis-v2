from __future__ import annotations

import pytest

from central_cli.hud import CentralHud


_REALTIME = {
    "status": "green", "coverage": {}, "incidents": [],
    "open_breakers": [], "clusters": [], "feed": [],
}

_SELF = {
    "self": {
        "living_executive": {"liveness": True, "mode": "attentive",
                             "summary": {"trace_count": 1}},
        "self_model": {"liveness": True, "summary": {"layer_count": 2}},
        "world_model": {"liveness": False, "summary": {"active_count": 1}},
    },
    "ts": 1,
}

_ANKRE = {
    "counts": {
        "total": 150514,
        "scored": 3198,
        "unscored": 147316,
        "scored_share": 0.0212,
        "by_type": {"perceptual_event": 146824, "cognitive_episode": 3155},
        "scored_by_type": {"cognitive_episode": 3140},
        "by_outcome": {"good": 562, "bad": 2634, "neutral": 2},
    },
    "span": {"newest_at": "2026-09-18T12:10:33+00:00"},
}


class FakeClient:
    def __init__(self, ankre=_ANKRE):
        self._ankre = ankre

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/central/self":
            return _SELF
        if path.startswith("/mc/emotional-memory"):
            return self._ankre
        return {}

    def post_json(self, path, body):
        return {"ok": True}


@pytest.mark.asyncio
async def test_mind_panelet_viser_andelen_med_udfald():
    """Fladens ærinde: 150.514 ankre lyder som en erfaring, men kun 3.198
    har et udfald. Begge tal skal stå på skærmen samtidig."""
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(150, 60)):
        app.show_tab("mind")
        vist = str(app.query_one("#hud-panel").render())
        assert "FØLELSESANKRE" in vist
        assert "150514" in vist
        assert "3198" in vist
        assert "2.1 %" in vist


@pytest.mark.asyncio
async def test_mind_panelet_markerer_typen_der_aldrig_afgoeres():
    """97 % af ankrene er perceptual_event, som aldrig får et udfald.
    Uden den markering ligner tallet en hukommelse der har lært noget."""
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(150, 60)):
        app.show_tab("mind")
        vist = str(app.query_one("#hud-panel").render())
        assert "perceptual_event" in vist
        assert "aldrig afgjort" in vist
        assert "3140 m. udfald" in vist


@pytest.mark.asyncio
async def test_mind_panelet_springer_sektionen_over_uden_ankre():
    """Tom tabel → ingen sektion. En overskrift over nul er støj."""
    app = CentralHud(client=FakeClient(ankre={"counts": {"total": 0}}), live=False)
    async with app.run_test(size=(150, 60)):
        app.show_tab("mind")
        vist = str(app.query_one("#hud-panel").render())
        assert "MIND & SELF" in vist
        assert "FØLELSESANKRE" not in vist
