"""Verdict-mapping: `green`/`yellow`/`red` skal kunne SIGES i notation.

BAGGRUND (28/10-2026). Centralens gate-verdicts ligger i `gate_verdict_counts`
— 7,8 mio. rækker — men `render_decision(cluster, verdict=...)` svarede
`None` for ALLE 12 undersøgte rækker. Grunden: `_ALLOW`/`_DENY` indeholdt
kun `allow`/`deny`-familien, mens driften skriver `green`/`yellow`/`red`.

En verdict der ikke kan renderes er ikke en konklusion — den er et tal der
ikke kan siges. Testen her fælder netop det: grøn skal give en sætning,
rød skal give den modsatte, og en ukendt verdict skal stadig give `None`
(sproget må ikke gætte).
"""
from __future__ import annotations

import pytest


@pytest.fixture
def render():
    from core.services import central_render

    return central_render


@pytest.mark.parametrize("verdict", ["green", "yellow"])
def test_green_og_yellow_renderes_som_tilladelse(render, verdict):
    """Driftens mest almindelige verdicts må ikke være usigelige."""
    out = render.render_decision("system", verdict=verdict)
    assert out, f"verdict={verdict!r} kunne ikke siges"


def test_red_renderes_som_afvisning(render):
    out = render.render_decision("system", verdict="red")
    assert out, "verdict='red' kunne ikke siges"


def test_green_og_red_er_forskellige_saetninger(render):
    """Pointen: grøn og rød må ikke kollapse til samme notation.

    Gør de det, er verdict-feltet dekoration — så kan man lige så godt
    lade være at skrive det.
    """
    grøn = render.render_decision("system", verdict="green")
    rød = render.render_decision("system", verdict="red")
    assert grøn and rød
    assert grøn != rød


def test_ukendt_verdict_giver_none(render):
    """Sproget må ikke gætte. En verdict det ikke kender er UBUNDET."""
    assert render.render_decision("system", verdict="måske-senere") is None


def test_eksisterende_allow_familie_virker_stadig(render):
    """Rettelsen må ikke brække de verdicts der allerede virkede."""
    assert render.render_decision("system", verdict="allow")
    assert render.render_decision("system", verdict="deny")
