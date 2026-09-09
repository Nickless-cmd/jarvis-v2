"""Svarerne formidler et svar — de afgoer ikke politikken. Fase 4.

«Mission Control, UI, and CLI act as answerers without owning policy.»

Maalt 9/9-2026: kriteriet HOLDT. Ingen af overfladerne afgoer hvad der kraever
godkendelse; de sender et ja eller nej og VISER den klassifikation serveren
gav dem. CLI'ens `destructive` er `h.get("destructive")` — laest, ikke
besluttet.

Filen findes fordi det er en egenskab der kan smuldre stille: den dag en
overflade selv beslutter «det her er vist harmloest nok», er politikken
flyttet ud til kanten, og huset har to sandheder om hvad der maa koeres.
"""
from __future__ import annotations

import inspect
import re

import pytest

# De ord der ville betyde at en overflade traf beslutningen SELV.
_POLITIK = re.compile(
    r"""(classification\s*=\s*["']|                 # saetter en klassifikation
         requires?_approval\s*=|                     # afgoer kravet
         is_destructive\s*\(|                        # doemmer selv
         from\s+core\.services\.gate_execution)""",  # eller kalder gaten
    re.X)


def _kilde(modul) -> str:
    return inspect.getsource(modul)


@pytest.mark.parametrize("navn", ["chat", "cowork"])
def test_http_svarerne_afgoer_ingen_politik(navn):
    from apps.api.jarvis_api.routes import chat, cowork
    kilde = _kilde({"chat": chat, "cowork": cowork}[navn])
    fund = _POLITIK.findall(kilde)
    assert not fund, f"{navn} traeffer selv en politik-beslutning: {fund[:3]}"


def test_svarerne_kalder_den_FAELLES_afgoerelse():
    """De skal gaa gennem ét sted, ikke hver sin kopi."""
    from apps.api.jarvis_api.routes import chat, cowork
    for modul in (chat, cowork):
        assert "resolve_pending_approval" in _kilde(modul)


def test_CLI_en_LAESER_klassifikationen_frem_for_at_doemme():
    """`destructive` kommer fra serverens data. Regnede CLI'en den ud selv,
    kunne de to vaere uenige om samme kommando."""
    from apps.central_cli.central_cli import hud_populate
    kilde = _kilde(hud_populate)
    assert 'h.get("destructive")' in kilde
    assert not _POLITIK.findall(kilde)


def test_mission_control_er_LAESE_only_paa_vaerktoejs_godkendelser():
    """MC's approve/reject gaelder INITIATIVER — en anden koe. Dens
    godkendelses-flade for vaerktoejer er en GET."""
    from apps.api.jarvis_api.routes import mission_control_runs_ops as MC
    kilde = _kilde(MC)
    assert '@router.get("/approvals")' in kilde
    assert "resolve_pending_approval" not in kilde


def test_politikken_bor_ET_sted():
    """Klassifikationen traeffes i gaten — og vaerktoejerne SPOERGER den.

    (Foerste udgave af denne test sluttede paa `or True` og kunne derfor ikke
    gaa roed. En test der ikke kan fejle, maaler ingenting.)
    """
    from core.services import gate_execution
    from core.tools import simple_tools_web
    gate = _kilde(gate_execution)
    assert "def check_file" in gate and "def check_command" in gate
    assert "gate_execution" in _kilde(simple_tools_web), (
        "bash spoerger ikke gaten — saa hvor kommer klassifikationen fra?")
