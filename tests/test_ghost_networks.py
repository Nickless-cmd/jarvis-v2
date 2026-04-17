"""Tests for ghost_networks.py"""

import pytest
from core.services.ghost_networks import (
    archive_dead_nodes,
    describe_ghost_network,
    format_ghost_for_prompt,
    reset_ghost_networks,
    build_ghost_networks_surface,
)


def setup_function():
    reset_ghost_networks()


def test_archive_dead_nodes():
    archive_dead_nodes(["node1", "node2"])
    surface = build_ghost_networks_surface()
    assert surface["ghost_count"] == 2
    assert surface["active"] is True


def test_describe_ghost_network():
    archive_dead_nodes(["old_node"])
    desc = describe_ghost_network()
    assert "old_node" in desc


def test_format_ghost_for_prompt():
    archive_dead_nodes(["ghost_node"])
    result = format_ghost_for_prompt()
    assert "SPØGELSE:" in result


def test_build_ghost_networks_surface():
    archive_dead_nodes(["node_a", "node_b"])
    surface = build_ghost_networks_surface()
    assert surface["active"] is True
    assert surface["ghost_count"] == 2


def test_reset_ghost_networks():
    archive_dead_nodes(["node1"])
    reset_ghost_networks()
    surface = build_ghost_networks_surface()
    assert surface["ghost_count"] == 0
    assert surface["active"] is False


def test_empty_ghost_networks():
    surface = build_ghost_networks_surface()
    assert surface["active"] is False
    assert surface["ghost_count"] == 0
