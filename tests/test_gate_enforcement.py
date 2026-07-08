"""Tests for governed per-gate enforce-kill-switch (gate_enforcement)."""
from __future__ import annotations

from core.services import central_switches, gate_enforcement
from core.services.gate_kernel import GateClass


def _reset(nerve: str) -> None:
    # Fjern evt. flag fra andre tests → tilbage til default ON.
    central_switches.set_enabled("gate_enforce", nerve, True)


def test_cognitive_gate_default_on() -> None:
    """Uden flag håndhæver en COGNITIVE-gate (default ON)."""
    _reset("veto")
    assert gate_enforcement.is_enforced("veto", GateClass.COGNITIVE) is True


def test_cognitive_gate_can_be_disabled() -> None:
    """En COGNITIVE-gate kan governed-slås fra → is_enforced False."""
    central_switches.set_enabled("gate_enforce", "decision_gate", False)
    try:
        assert gate_enforcement.is_enforced("decision_gate", GateClass.COGNITIVE) is False
    finally:
        _reset("decision_gate")


def test_cognitive_gate_re_enabled() -> None:
    """Slås en gate til igen, håndhæver den påny."""
    central_switches.set_enabled("gate_enforce", "loop_control", False)
    central_switches.set_enabled("gate_enforce", "loop_control", True)
    assert gate_enforcement.is_enforced("loop_control", GateClass.COGNITIVE) is True


def test_security_gate_always_enforced_even_with_flag_off() -> None:
    """§11.3: en SECURITY-gate kan ALDRIG slås fra — is_enforced altid True,
    selv om nogen forsøger at sætte flag'et."""
    # Forsøg at slå fra (set_enabled afviser selv SECURITY, men vi tester is_enforced-invarianten
    # uafhængigt: den ser på klassen, ikke kun flag'et).
    central_switches.set_enabled("gate_enforce", "exec_workspace_trust", False)
    try:
        assert gate_enforcement.is_enforced("exec_workspace_trust", GateClass.SECURITY) is True
    finally:
        _reset("exec_workspace_trust")


def test_security_gate_ignores_disabled_flag() -> None:
    """Selv hvis et disabled-flag på en eller anden måde sidder i cachen, ignorerer
    is_enforced det for SECURITY-klassen."""
    # Skriv flag'et direkte i cachen (omgår set_enabled's SECURITY-afvisning) for at bevise
    # at is_enforced's klasse-tjek er den reelle invariant-vogter.
    from core.services import shared_cache
    shared_cache.set("flag:central.switch.gate_enforce.exec_workspace_trust",
                     {"enabled": False}, ttl_seconds=3600)
    try:
        assert gate_enforcement.is_enforced("exec_workspace_trust", GateClass.SECURITY) is True
    finally:
        _reset("exec_workspace_trust")


def test_note_suppressed_block_is_self_safe() -> None:
    """note_suppressed_block må aldrig kaste, uanset central-tilstand."""
    # Skal returnere None uden exception (central self-safe).
    assert gate_enforcement.note_suppressed_block("veto", "commit", "test-reason") is None


def test_note_suppressed_block_tolerates_none_reason() -> None:
    """Robust mod None-reason (hot-path-input kan være tomt)."""
    assert gate_enforcement.note_suppressed_block("decision_gate", "commit", None) is None  # type: ignore[arg-type]
