"""Tests for fit-pass-kataloget: deklarativ nerve→cluster/klasse/mekanisme/fit."""
from __future__ import annotations

from core.services import central_catalog as cat
from core.services.gate_kernel import GateClass


def test_catalog_nonempty_and_has_loop_cluster():
    assert len(cat.CATALOG) >= 6
    assert "loop" in cat.clusters()


def test_by_cluster_filters():
    loop = cat.by_cluster("loop")
    names = {n.name for n in loop}
    assert "presentation_invariant" in names and "loop_control" in names


def test_validate_is_green():
    assert cat.validate() == []          # ingen ugyldige felter


def test_security_clusters_marked_security():
    for spec in cat.CATALOG:
        if spec.cluster in ("auth", "privacy"):
            assert spec.klass is GateClass.SECURITY


def test_nerve_klass_and_is_security_helpers():
    # Katalog-SECURITY-nerver → is_security_nerve True (autoritativ §11.3-kilde)
    assert cat.is_security_nerve("outbound_scrub") is True
    assert cat.is_security_nerve("abuse_monitor") is True
    assert cat.nerve_klass("cross_user_share") is GateClass.SECURITY
    # Kognitiv nerve → ikke security
    assert cat.is_security_nerve("loop_control") is False
    # Ukendt nerve → None/False (fail til lagets egen fallback-denylist)
    assert cat.nerve_klass("ikke_en_nerve") is None
    assert cat.is_security_nerve("ikke_en_nerve") is False
