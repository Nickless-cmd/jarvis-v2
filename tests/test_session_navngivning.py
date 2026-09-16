"""Sessionen doebes efter sin foerste brugerbesked — ogsaa kode-sessioner.

Fejlen, fundet 16/9-2026: pladsholder-saettet indeholdt «kode session» med
MELLEMRUM, mens desk opretter sessionen som «Kode-session» med BINDESTREG. Ét
tegn, og omdoebningen fyrede aldrig. Tolv kode-sessioner stod som
«Kode-session» med foerste beskeder som «Godmorgen» og «Er du der?» der aldrig
blev brugt.

Testen maaler stavemaaderne, fordi det var praecis dér fejlen laa.
"""
import pytest

from core.services.chat_sessions import _er_pladsholder


@pytest.mark.parametrize("titel", [
    "Kode-session",      # desk (bindestreg) — DEN der fejlede
    "kode-session",
    "Kode session",      # mellemrum
    "kode_session",      # understreg
    "Kode  Session",     # dobbelt mellemrum
    "  Ny samtale  ",
    "New Chat",
    "Ny chat",
    "untitled",
    "uden titel",
    "",
    "   ",
])
def test_pladsholdere_kan_omdoebes(titel):
    assert _er_pladsholder(titel) is True, f"{titel!r} burde kunne omdoebes"


@pytest.mark.parametrize("titel", [
    "Godmorgen ven",
    "Kode-session om broen",          # brugerens EGET navn der ligner en pladsholder
    "Autonom · Hjerteslag · 04:00",   # maskin-titel MED betydning
    "💭 Proaktive spoergsmaal",
    "Ny samtale om pumpen",
])
def test_rigtige_navne_roeres_ALDRIG(titel):
    # Har brugeren selv navngivet sessionen — eller baerer den en maskin-titel
    # med betydning — skal den staa. En omdoebning her ville slette et valg.
    assert _er_pladsholder(titel) is False, f"{titel!r} er ikke en pladsholder"
