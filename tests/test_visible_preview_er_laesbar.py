"""Pladsholderen for et krypteret preview maa ikke ende som «et svar».

Fundet 25/11-2026. `recent_visible_runs` dekrypterer med KALDERENS noegle, saa
en daemon uden `user_id` faar `PLADSHOLDER_KRYPTERET` for hver medlems-koersel.
Det er den rigtige retning at fejle i — men kun hvis forbrugeren SPRINGER den
over. Ellers citerer dommeren, draemme-prompten eller chronicle en pladsholder
som om det var svaret, og «kan ikke bevises» bliver laest som «dette var svaret».

Testen laaser helperen, ikke den enkelte forbruger: én regel, ét sted.
"""
from __future__ import annotations

from core.services.visible_preview_crypto import (
    PLADSHOLDER_KRYPTERET,
    er_laesbar,
)


def test_pladsholder_er_ikke_laesbar():
    assert er_laesbar(PLADSHOLDER_KRYPTERET) is False


def test_chiffertekst_er_ikke_laesbar():
    """Raa chiffertekst er heller ikke et svar — den skal ogsaa springes over."""
    assert er_laesbar("enc:v1:AAAABBBBCCCCDDDDEEEE") is False


def test_klartekst_er_laesbar():
    assert er_laesbar("Jeg rettede de 175 og pushede fixet.") is True


def test_tom_er_ikke_laesbar():
    assert er_laesbar("") is False
    assert er_laesbar(None) is False
    assert er_laesbar("   ") is False


def test_hvidrum_omkring_pladsholder_taeller_stadig_som_pladsholder():
    assert er_laesbar(f"  {PLADSHOLDER_KRYPTERET}\n") is False
