"""Maal-signalernes domaenenoegle.

25/9-2026 blev to hardkodede broer fjernet herfra. De fik
`development-focus:communication:danish-concise-calibration` til at kollapse
til `danish-concise-calibration`, saa den matchede en droemme-hypotese med
samme sidste segment. Maalt: af 1125 fokus-noegler aendrede PRAECIS TO sig da
broerne kom vaek — netop de to. Det var den eneste grund til at kaeden
nogensinde foejede noget sammen.
"""
from __future__ import annotations

from core.services.goal_signal_tracking import _domain_key_from_focus


def test_noeglen_beholder_hele_sin_sti():
    assert _domain_key_from_focus(
        "development-focus:communication:danish-concise-calibration"
    ) == "communication-danish-concise-calibration"


def test_et_almindeligt_fokus_stripper_kun_praefikset():
    assert _domain_key_from_focus("development-focus:tooling") == "tooling"
    assert _domain_key_from_focus("development-focus:a:b") == "a-b"


def test_en_noegle_uden_praefiks_giver_tom():
    """Ingen gaet. Et tomt domaene betyder «denne hoerer ikke til noget» — og
    det er bedre end at haefte den paa et omraade paa et skoen."""
    assert _domain_key_from_focus("focus:bearing:Runtime-inspektion") == ""
    assert _domain_key_from_focus("") == ""
    assert _domain_key_from_focus(None) == ""
