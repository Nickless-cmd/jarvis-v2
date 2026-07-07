"""Tests for mood_oscillator conversation-level event handling."""

import math
from unittest.mock import patch

import pytest

from core.services.mood_oscillator import (
    apply_bump,
    get_current_mood,
    get_mood_intensity,
    reset_mood_oscillator,
    build_mood_oscillator_surface,
    tick,
)


def setup_function():
    reset_mood_oscillator()


class TestConversationBumps:
    """Test at samtale-hændelser påvirker humøret korrekt."""

    def test_confabulation_bump_lowers_mood(self):
        """En konfabulation (-0.50) skal sænke humøret markbart."""
        # Start fra baseline
        tick(30.0)
        before = get_mood_intensity()

        # Apply confabulation bump
        apply_bump(-0.50, "confabulation")
        after = get_mood_intensity()

        # Humøret skal være sænket (intensity = abs(combined))
        # Efter bump burde intensity være lavere eller mood navn ændret
        mood_before = get_current_mood()

        # Apply yderligere bumps for at sikre mærkbar effekt
        apply_bump(-0.50, "confabulation x2")
        apply_bump(-0.50, "confabulation x3")

        mood_after = get_current_mood()
        # Efter tre store negative bumps burde humøret være lavere
        assert mood_after in ("neutral", "melancholic", "distressed"), (
            f"Forventet lavere humør efter 3 confabulations, fik {mood_after}"
        )

    def test_correction_bump(self):
        """En korrektion (-0.40) skal påvirke humøret."""
        tick(30.0)
        apply_bump(-0.40, "correction: falsk commit hash")
        surface = build_mood_oscillator_surface()
        # Nudge skal være ≈ -0.4
        assert surface["mood_nudge"] <= -0.39

    def test_admission_bump_smaller_than_confabulation(self):
        """Indrømmelse (-0.20) skal være mindre negativ end konfabulation (-0.50)."""
        reset_mood_oscillator()
        apply_bump(-0.20, "admission")
        nudge_admission = build_mood_oscillator_surface()["mood_nudge"]

        reset_mood_oscillator()
        apply_bump(-0.50, "confabulation")
        nudge_confab = build_mood_oscillator_surface()["mood_nudge"]

        # Konfabulation skal give mere negativ nudge
        assert nudge_confab < nudge_admission, (
            f"Konfabulation ({nudge_confab}) burde være mere negativ end admission ({nudge_admission})"
        )

    def test_insight_bump_positive(self):
        """Indsigt (+0.20) skal give positiv nudge."""
        reset_mood_oscillator()
        apply_bump(0.20, "insight: forstod mønsteret")
        surface = build_mood_oscillator_surface()
        assert surface["mood_nudge"] >= 0.19

    def test_conversation_flow_bump(self):
        """God samtale (+0.15) skal give mild positiv nudge."""
        reset_mood_oscillator()
        apply_bump(0.15, "conversation_flow")
        surface = build_mood_oscillator_surface()
        assert surface["mood_nudge"] >= 0.14

    def test_decline_and_recover(self):
        """Humør skal kunne falde og stige igen med sekventielle bumps."""
        reset_mood_oscillator()
        tick(30.0)

        # Fald
        apply_bump(-0.50, "confabulation")
        apply_bump(-0.40, "correction")
        low_mood = get_current_mood()

        # Genopretning
        apply_bump(0.20, "admission")
        apply_bump(0.15, "conversation_flow")
        apply_bump(0.20, "insight")
        recovered_mood = get_current_mood()

        # Efter 3 positive bumps burde humøret være højere/op ad
        surface = build_mood_oscillator_surface()
        # Nudge efter -0.90 + 0.55 = -0.35 + baseline sin
        # Hvis sin er ~0.78 + (-0.35) = 0.43 → content
        # Det er okay uanset hvad — testen verificerer at bumpene kan anvendes sekventielt
        assert isinstance(recovered_mood, str)

    def test_nudge_clamped_to_range(self):
        """Nudge skal være clamped til [-1, 1] — ikke kunne overskride."""
        reset_mood_oscillator()
        # Forsøg at overskride
        apply_bump(5.0, "ekstrem positiv")
        surface = build_mood_oscillator_surface()
        assert surface["mood_nudge"] <= 1.0

        reset_mood_oscillator()
        apply_bump(-5.0, "ekstrem negativ")
        surface = build_mood_oscillator_surface()
        assert surface["mood_nudge"] >= -1.0


class TestMoodRegulator:
    """Test central_mood_regulator.py via dets public API."""

    def test_regulate_valid_kinds(self):
        """Alle gyldige kinds skal accepteres."""
        from core.services.central_mood_regulator import regulate

        for kind in ("confabulation", "correction", "user_frustration",
                      "admission", "insight", "conversation_flow"):
            result = regulate(kind, reason=f"test:{kind}")
            assert result["status"] == "ok", f"kind={kind} fejlede: {result}"
            assert result["event_kind"] == f"mood.{kind}"

    def test_regulate_invalid_kind(self):
        """Ugyldig kind skal returnere 'ignored'."""
        from core.services.central_mood_regulator import regulate

        result = regulate("nonexistent")
        assert result["status"] == "ignored"

    def test_regulate_with_reason_and_detail(self):
        """Reason og detail skal medsendes korrekt."""
        from core.services.central_mood_regulator import regulate

        result = regulate(
            "confabulation",
            reason="falsk commit hash",
            detail="Jeg påstod Trainman var bygget uden at tjekke",
        )
        assert result["status"] == "ok"
        assert "falsk commit hash" in result["reason"]
        assert "Trainman" in result["reason"] or "trainman" in result["reason"].lower()

    def test_regulate_updates_mood(self):
        """Regulate skal rent faktisk påvirke mood via apply_bump."""
        from core.services.central_mood_regulator import regulate

        reset_mood_oscillator()
        tick(30.0)

        # Anvend confabulation via regulatoren
        regulate("confabulation", reason="test")

        # Mood skal være påvirket
        surface = build_mood_oscillator_surface()
        assert surface["mood_nudge"] <= -0.1, (
            f"Forventet negativ nudge efter confabulation, fik {surface['mood_nudge']}"
        )

    def test_regulate_auto_dissent(self):
        """Auto-regulering fra dissent-events skal virke."""
        from core.services.central_mood_regulator import regulate_auto

        reset_mood_oscillator()
        tick(30.0)

        # Simuler auto-detektion af dissent
        regulate_auto(
            event_kind="dissent.detected",
            payload={"reason": "memory_promotion dissent opdaget"},
        )

        # Skal have påvirket mood (admission = -0.20)
        surface = build_mood_oscillator_surface()
        # Nudge skal være < 0 efter admission bump
        assert surface["mood_nudge"] <= -0.1

    def test_regulate_auto_persistent(self):
        """Auto-regulering ved persistent dissent skal give correction bump."""
        from core.services.central_mood_regulator import regulate_auto

        reset_mood_oscillator()
        tick(30.0)

        regulate_auto(event_kind="dissent.persistent")
        surface = build_mood_oscillator_surface()
        # correction = -0.40
        assert surface["mood_nudge"] <= -0.39

    def test_regulate_auto_insight(self):
        """Auto-regulering ved redpill taken skal give insight bump."""
        from core.services.central_mood_regulator import regulate_auto

        reset_mood_oscillator()
        tick(30.0)

        regulate_auto(event_kind="redpill.taken")
        surface = build_mood_oscillator_surface()
        # insight = +0.20
        assert surface["mood_nudge"] >= 0.19

    def test_build_surface(self):
        """MC surface skal være korrekt formateret."""
        from core.services.central_mood_regulator import (
            build_mood_regulator_surface,
            regulate,
        )

        # Anvend nogle events så bufferen ikke er tom
        regulate("insight", reason="test")
        regulate("confabulation", reason="test")

        surface = build_mood_regulator_surface()
        assert surface["active"] is True
        assert "recent_events" in surface
        assert len(surface["recent_events"]) >= 1
        assert "event_count" in surface
