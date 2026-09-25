"""Det faelles emne-ordforraad for droemme-kaeden.

Kaeden foejer paa EMNE: hvert hop slaar op paa sidste segment af
`canonical_key` og leder efter et maal eller et fokus i samme emne. Maalt
25/9-2026: `danish-concise-calibration` fandtes 15.–25. maj som hypotese, som
fokus OG som 123 maal-raekker — og det er praecis derfor den sidste
adoptions-kandidat er fra 15. maj.

Navnene er derfor ikke frit valgte. Aendres et, holder det op med at moede det
der allerede baerer det.
"""
from __future__ import annotations

from core.services.dream_domains import DOMAENER, er_gyldigt_domaene


def test_de_otte_domaener_er_dem_der_staar_i_basen():
    """`capability`, `creativity`, `memory` og `identity` er i basen fra 24/9."""
    for navn in ("identity", "memory", "capability", "creativity",
                 "curiosity", "relational", "boundary", "resilience"):
        assert navn in DOMAENER, navn
    assert len(DOMAENER) == 8


def test_hvert_domaene_har_en_beskrivelse():
    """Beskrivelsen er det `dream_hypothesis_forced` skriver som summary."""
    for navn, tekst in DOMAENER.items():
        assert tekst.strip(), navn


def test_den_tvungne_producent_bruger_DETTE_ordforraad():
    """Foer 25/9 stod listen kun i `dream_hypothesis_forced`, og den var derfor
    den eneste producent der skrev et emne kaeden kunne bruge."""
    from core.services.dream_hypothesis_forced import _DOMAINS
    assert dict(_DOMAINS) == DOMAENER


def test_et_ukendt_navn_er_ikke_gyldigt():
    assert er_gyldigt_domaene("identity")
    assert not er_gyldigt_domaene("vis-mig-de-to-nye-commits-fra-claude")
    assert not er_gyldigt_domaene("")
