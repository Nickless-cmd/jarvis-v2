"""Grænser for værktøjs-kørsel.

`MAX_BASH_SECONDS = 15` stod hardkodet i to filer. Jarvis 4. sep: «~7 timeouts
på grep/git status/ls-agtige kommandoer der burde tage <1s». Grænsen ramte
arbejdet, ikke løbske kommandoer.
"""
from __future__ import annotations

import pytest

from core.tools.tool_limits import bash_timeout_s, timeout_note


def test_de_to_bash_stier_deler_den_samme_graense():
    """To kopier af samme tal driver fra hinanden før eller siden."""
    from core.tools.simple_tools import MAX_BASH_SECONDS as a
    from core.tools.simple_tools_web import MAX_BASH_SECONDS as b

    assert a == b == bash_timeout_s()


def test_standarden_giver_plads_til_en_repo_bred_soegning():
    assert bash_timeout_s() >= 30


@pytest.mark.parametrize("sat,forventet", [(1, 5), (10, 10), (99999, 240)])
def test_graensen_kan_justeres_men_ikke_ud_i_det_meningsloese(monkeypatch, sat, forventet):
    """Under 5 s gør trivielle kommandoer upålidelige; over 240 s æder en runde
    (loftet er 300 s) og ligner et hængt system."""
    import core.runtime.settings as st

    class _S:
        extra = {"bash_timeout_s": sat}
    monkeypatch.setattr(st, "load_settings", lambda: _S())
    assert bash_timeout_s() == forventet


def test_ubrugelig_konfiguration_vaelter_ikke_vaerktoejet(monkeypatch):
    import core.runtime.settings as st

    monkeypatch.setattr(st, "load_settings", lambda: (_ for _ in ()).throw(RuntimeError("nej")))
    assert bash_timeout_s() >= 30


def test_timeout_beskeden_siger_hvad_man_goer_ved_det():
    """«Command timed out after 15s» siger hvad der skete, men ikke hvad man
    gør. Den der læser den skal kunne komme videre uden at gætte."""
    bred = timeout_note(45, "grep -rn noget .")
    assert "45s" in bred and ("indsnævr" in bred or "for bred" in bred)

    anden = timeout_note(45, "python langsom.py")
    assert "bash_session" in anden, "en lang kørsel hører hjemme i en session"
