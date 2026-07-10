from __future__ import annotations

from core.services.source_confidence_gate import (
    assess_source_confidence,
    build_source_confidence_surface,
)


def test_first_hand_existence_claim_is_high_no_caution():
    # Eksistens-påstand bakket af direkte kode-inspektion → high, ingen advarsel.
    a = assess_source_confidence(
        output_text="Der findes et tool der hedder open_ui_panel.",
        tools_used=[{"name": "grep"}, {"name": "read_file"}],
    )
    assert a["provenance"] == "first-hand"
    assert a["confidence"] == "high"
    assert a["has_existence_claim"] is True
    assert a["caution"] is None


def test_second_hand_existence_claim_is_low_with_caution():
    # Dagens ægte fejl: "der findes et CCDN-tool" KUN fra web-søgning → low + advarsel.
    a = assess_source_confidence(
        output_text="Der findes et tool der hedder CCDN i Claude Code.",
        tools_used=[{"name": "web_search"}],
    )
    assert a["provenance"] == "second-hand"
    assert a["confidence"] == "low"
    assert a["has_existence_claim"] is True
    assert a["caution"] is not None
    assert "second-hand" in a["caution"]


def test_unsourced_existence_claim_gets_caution():
    # Påstand uden nogen kilde i turen → advarsel om at verificere.
    a = assess_source_confidence(
        output_text="Det hedder Chicago Desktop Compute-use Control.",
        tools_used=[],
    )
    assert a["provenance"] == "unsourced"
    assert a["confidence"] == "low"
    assert a["caution"] is not None


def test_mixed_provenance_is_high():
    # Både first-hand og second-hand → mixed, høj (first-hand redder claim).
    a = assess_source_confidence(
        output_text="Der er et modul der hedder foo.",
        tools_used=[{"name": "web_search"}, {"name": "read_file"}],
    )
    assert a["provenance"] == "mixed"
    assert a["confidence"] == "high"
    assert a["caution"] is None


def test_second_hand_no_claim_is_medium_no_caution():
    # Web-kilde men INGEN eksistens-påstand → medium, ingen advarsel (ikke farligt).
    a = assess_source_confidence(
        output_text="Jeg opsummerede artiklen om produktivitet.",
        tools_used=[{"name": "web_search"}],
    )
    assert a["provenance"] == "second-hand"
    assert a["confidence"] == "medium"
    assert a["has_existence_claim"] is False
    assert a["caution"] is None


def test_tools_used_accepts_plain_strings():
    a = assess_source_confidence(
        output_text="der er et system", tools_used=["web_fetch"]
    )
    assert a["provenance"] == "second-hand"


def test_surface_active_only_when_caution():
    live = build_source_confidence_surface(
        output_text="der findes et tool X", tools_used=[{"name": "web_search"}]
    )
    assert live["active"] is True
    assert live["mode"] == "source-confidence"
    calm = build_source_confidence_surface(
        output_text="der findes et tool X", tools_used=[{"name": "grep"}]
    )
    assert calm["active"] is False
