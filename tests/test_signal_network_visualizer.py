"""Tests for signal_network_visualizer.py"""
import pytest

from core.services.signal_network_visualizer import (
    get_current_network_state,
    describe_inner_network,
    get_signal_strengths,
    format_network_for_prompt,
    build_signal_network_visualizer_surface,
)


def test_get_current_network_state():
    state = get_current_network_state()
    assert "nodes" in state
    assert "edges" in state
    assert "node_count" in state


def test_describe_inner_network():
    desc = describe_inner_network()
    assert isinstance(desc, str)
    assert len(desc) > 0


def test_get_signal_strengths():
    strengths = get_signal_strengths()
    assert "witness" in strengths
    assert "tension" in strengths
    assert "loops" in strengths
    assert "emergent" in strengths
    assert "dreams" in strengths


def test_format_network_for_prompt():
    result = format_network_for_prompt()
    assert isinstance(result, str)


def test_build_signal_network_visualizer_surface():
    surface = build_signal_network_visualizer_surface()
    assert "active" in surface
    assert "node_count" in surface
    assert "nodes" in surface
    assert "edges" in surface
    assert "summary" in surface
