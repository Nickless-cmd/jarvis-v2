"""Værktøjet Jarvis selv kalder: `suggest_next_message`.

## Hvad det er

Bjørn 24/9-2026: «i chatview er det dig selv der sætter ord på runderne...
det burde endelig osse være dig der kommer med forslag i composer?»

Komponistens forslag kom fra en lokal 4b-model der læser ÉN besked. Jarvis kan
skrive et bedre et, fordi han ved hvad han lige har lavet. Værktøjet lægger
hans forslag ned; læsse-vejen foretrækker det frem for modellen (se
`tests/test_composer_suggest.py`).

## Strikst bekræftelse

Som `set_flag` LÆSER værktøjet tilbage efter skriv — et «ok» er først bevis
når rækken faktisk står der. Det bruger `kig_forslag` og ikke `tag_forslag`,
for bekræftelsen må ikke forbruge det forslag Bjørn endnu ikke har set.
"""
from __future__ import annotations

from core.runtime import db_composer_jarvis as dj


def test_vaerktoejet_gemmer_og_BEKRAEFTER_ved_at_laese_tilbage(isolated_runtime):
    from core.tools.composer_suggest_tools import _exec_suggest_next_message

    ud = _exec_suggest_next_message({
        "tekst": "Vis mig de to i karantaene", "_runtime_session_id": "s1"})
    assert ud["status"] == "ok" and ud["confirmed"] is True
    # ... og bekræftelsen spiste ikke forslaget.
    assert dj.kig_forslag(session_id="s1")["forslag"] == "Vis mig de to i karantaene"


def test_vaerktoejet_uden_session_fejler_aabent(isolated_runtime):
    from core.tools.composer_suggest_tools import _exec_suggest_next_message

    ud = _exec_suggest_next_message({"tekst": "x"})
    assert ud["status"] == "error" and "session" in ud["error"]


def test_vaerktoejet_uden_tekst_fejler_aabent(isolated_runtime):
    from core.tools.composer_suggest_tools import _exec_suggest_next_message

    ud = _exec_suggest_next_message({"tekst": "  ", "_runtime_session_id": "s1"})
    assert ud["status"] == "error" and "tekst" in ud["error"]


def test_vaerktoejet_er_registreret_og_kaldbart():
    """Navnet skal staa i baade definitions-listen og handler-dict'en —
    ellers er det et værktøj Jarvis kan se men ikke kalde."""
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    navne = [(t.get("function") or {}).get("name") for t in TOOL_DEFINITIONS]
    assert navne.count("suggest_next_message") == 1
    assert "suggest_next_message" in _TOOL_HANDLERS
