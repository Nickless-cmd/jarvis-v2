from unittest import mock
from core.services import central_relational as rel


def _state(age_s=None, tone="", reboot=False):
    return {"continuity": {"age_s": age_s, "reboot": reboot}, "valence": {"tone": tone}}


def test_days_and_tone_from_self_state():
    with mock.patch("core.services.central_self_state.get_self_state",
                    return_value=_state(age_s=80 * 86400, tone="rolig")):
        st = rel.relational_state()
    assert st["days_together"] == 80.0 and st["tone"] == "rolig"


def test_wake_greeting_grounded_in_duration_and_tone():
    with mock.patch("core.services.central_self_state.get_self_state",
                    return_value=_state(age_s=80 * 86400, tone="varm")):
        g = rel.wake_greeting()
    assert "80 dage" in g and "varm" in g and "betyder noget" in g


def test_wake_greeting_safe_without_age():
    with mock.patch("core.services.central_self_state.get_self_state", return_value=_state()):
        g = rel.wake_greeting()
    assert "Velkommen tilbage" in g


def test_record_observes_metadata_only():
    obs = []
    fc = mock.MagicMock(); fc.observe.side_effect = lambda e: obs.append(e)
    with mock.patch("core.services.central_self_state.get_self_state",
                    return_value=_state(age_s=5 * 86400, tone="fokuseret")), \
            mock.patch("core.services.central_core.central", return_value=fc):
        rel.record_relational()
    # KUN dage + tone-label, aldrig samtaleindhold (§24.4)
    assert obs and obs[0]["nerve"] == "relational"
    assert set(obs[0]) <= {"cluster", "nerve", "kind", "days_together", "tone"}
