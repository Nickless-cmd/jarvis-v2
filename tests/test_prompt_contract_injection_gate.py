"""rule_conclusions og cognitive_state læser injektion når live, ellers direkte build.

Kontrakten er at PROMPT-SAMLINGEN læser den baggrunds-cachede injektion når
flaget er live, og falder tilbage til den direkte build når det ikke er. Den
rollback-vej er hele pointen: en injektion der holder op med at blive skrevet
må ikke gøre sektionen tavs.

**Omskrevet 8/9-2026.** Testene slog `inspect.getsource` op på
``build_visible_chat_prompt_assembly`` og fejlede — ikke fordi noget var gået i
stykker, men fordi funktionen er blevet en tynd tur-cache omkring
``_build_visible_chat_prompt_assembly_impl``, hvor koden nu bor. To røde tests
i dagevis for en refaktor der ikke ændrede adfærd.

De spørger nu MODULET, ikke én funktion. Kontrakten er «samlingen læser
injektionen», ikke «denne bestemte funktion gør det» — og en test der knækker
når nogen tilføjer en cache, lærer folk at ignorere røde tests.
"""

from __future__ import annotations

import inspect

import pytest

import core.services.prompt_contract as pc

_KILDE = inspect.getsource(pc)


@pytest.mark.parametrize("nøgle", ["rule_conclusions", "cognitive_state"])
def test_sektionen_laeser_injektionen_naar_den_er_live(nøgle):
    assert 'injection_live("%s")' % nøgle in _KILDE
    assert 'read_injection("%s")' % nøgle in _KILDE


@pytest.mark.parametrize("nøgle,builder", [
    ("rule_conclusions", "rule_conclusions_section"),
    ("cognitive_state", "cognitive_state"),
])
def test_der_er_en_direkte_build_at_falde_tilbage_paa(nøgle, builder):
    """Rollback-vejen. En injektion der holder op med at blive skrevet må ikke
    gøre sektionen tavs — det er præcis sådan sektioner er forsvundet før."""
    assert builder in _KILDE


def test_samlingen_er_en_wrapper_om_sin_impl():
    """Grunden til at testene ovenfor spørger modulet og ikke funktionen.

    Fejler denne, er strukturen lavet om igen — og så skal nogen læse denne
    fil frem for at jage et fantom.
    """
    ydre = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    assert "_build_visible_chat_prompt_assembly_impl" in ydre
