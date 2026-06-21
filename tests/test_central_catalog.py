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
    assert "presentation_invariant" in names and "tool_budget" in names


def test_validate_is_green():
    assert cat.validate() == []          # ingen ugyldige felter


def test_security_clusters_marked_security():
    for spec in cat.CATALOG:
        if spec.cluster in ("auth", "privacy"):
            assert spec.klass is GateClass.SECURITY
