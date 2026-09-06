"""Broen skal flytte rangordningen — ikke omskrive hans sprog."""

from __future__ import annotations

from core.services.query_language_bridge import (
    build_query_language_bridge_surface,
    normalise_for_embedding as n,
)


def test_de_ord_der_faktisk_braekkede_rangordningen():
    """«kalender» og «møde» var præcis dem der gav curiosity_read_dreams."""
    ud = n("kan du lægge et møde ind i min kalender på fredag")
    assert "calendar" in ud and "meeting" in ud
    assert "kalender" not in ud and "møde" not in ud


def test_engelske_fagord_roeres_ikke():
    """Hans fagord er i forvejen engelske — de virker allerede."""
    s = "tool prompt bash code session container image"
    assert n(s) == s


def test_saetningen_bevares_udenom():
    """Broen er ord-substitution, ikke oversættelse. Resten skal stå."""
    ud = n("kan du lægge et møde ind i min kalender på fredag")
    for stump in ("kan du lægge et", "ind i min", "på fredag"):
        assert stump in ud


def test_stort_begyndelsesbogstav_bevares():
    assert n("Kalender") == "Calendar"
    assert n("kalender") == "calendar"


def test_tegn_og_tal_roeres_ikke():
    assert n("møde kl. 14:30 på fredag?") == "meeting kl. 14:30 på fredag?"


def test_boejninger_rammes_ogsaa():
    """«kalenderen» og «filerne» er lige så almindelige som grundformen."""
    assert "calendar" in n("hvad står der i kalenderen")
    assert "files" in n("vis mig filer i mappen")


def test_delord_rammes_ikke():
    """«kalenderår» må ikke blive «calendarår» — ordgrænser holder."""
    assert n("kalenderår") == "kalenderår"


def test_tom_og_none_er_sikre():
    assert n("") == "" and n(None) == ""


def test_uden_danske_ord_er_teksten_uaendret():
    s = "run the tests and check the output"
    assert n(s) == s


def test_observationsflade_siger_om_noget_blev_byttet():
    f = build_query_language_bridge_surface("møde i kalenderen")
    assert f["changed"] is True
    assert "meeting" in str(f["normalised"])
    assert build_query_language_bridge_surface("run tests")["changed"] is False
