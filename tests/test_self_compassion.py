"""Smoke test for core.services.self_compassion.

Self-compassion should turn repeated failures into a concrete acceptance
narrative instead of returning an empty placeholder.

MÅLT 8/11-2026: `build_resilience_narrative` blev slettet. Den havde nul
produktionskaldere — kun denne test — og dens indgangsbetingelse
(`consecutive_failures >= 3`) kunne ikke opfyldes: ingen tæller Jarvis'
egne fejl i træk. `consecutive_failures` findes kun i tre andre domæner
(rutine-failure-policy, cheap-lane-slots). Funktionen ville derfor altid
have returneret tom streng, også hvis den var blevet koblet på prompten.
"""

from core.services import self_compassion


def test_process_failure_toward_acceptance_returns_high_support_for_many_failures() -> None:
    result = self_compassion.process_failure_toward_acceptance(
        failure_count_recent=6,
        regret_level=0.8,
        lesson_learned="check assumptions earlier",
    )

    assert result["needed"] is True
    assert result["level"] == "high"
    assert "check assumptions earlier" in result["narrative"]


def test_ingen_doed_resilience_funktion_genindfoeres() -> None:
    """Vagten: en funktion uden kaldere maa ikke staa her som om den lever.

    Slettet 8/11-2026 fordi den paastod en levering den ikke havde. Kommer
    den tilbage, skal den have en aegte fejl-taeller foerst — ikke bare en
    ny smoke-test.
    """
    assert not hasattr(self_compassion, "build_resilience_narrative")
