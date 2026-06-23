"""Test: pending-plans-sektion dropper vane-halen (Jarvis-spec 2026-06-23 #9)."""
from __future__ import annotations

from core.services import plan_proposals as pp


def test_no_list_plans_habit_tail():
    # Kerne-check (#9): uanset om der er ægte plans eller ej, MÅ vane-halen
    # "Brug list_plans for detaljer..." ikke længere optræde i sektionen.
    section = pp.all_pending_plans_section()
    if section is not None:
        assert "list_plans" not in section
        assert "for detaljer" not in section
