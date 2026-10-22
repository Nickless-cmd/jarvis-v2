"""En aldrig-målt beslutning med et brud-mønster må ikke blokere hårdest.

Målt 22/10-2026: 36 aktive beslutninger havde aldrig fået en adherence-dom.
`None` blev graderet som «ikke svag», så de blokerede som en beslutning jeg
holder 100 % — selv når brud-historikken viste at jeg bryder dem. Brud er
mistanker, ikke domme, men et MØNSTER af brud er stadig et adfærdssignal.
"""
from __future__ import annotations

from unittest.mock import patch

from core.services import decision_gate as dg


def _kald(decisions, brud):
    with patch(
        "core.services.behavioral_decisions.list_active_decisions",
        return_value=decisions,
    ), patch.object(dg, "_detect_conflict", return_value="konflikt"), patch(
        "core.services.decision_breach_reader.breach_stats",
        return_value=brud,
    ):
        return dg.evaluate_decision_conflict(
            "operator_bash", {"command": "git push"}
        )


def test_aldrig_maalt_med_tre_brud_graderes_som_svag():
    sev, reason = _kald(
        [{
            "decision_id": "d1", "directive": "ingen git push",
            "priority": 92, "adherence_score": None,
        }],
        {"d1": {"count": 3, "last_at": None, "age_hours": 2.0}},
    )
    assert sev == "soft", (
        "et brud-mønster uden en dom er stadig et signal — ellers blokerer "
        "netop de beslutninger jeg ikke kan holde hårdest"
    )
    assert "aldrig målt" in reason
    assert "3 brud" in reason


def test_aldrig_maalt_uden_brud_blokerer_som_foer():
    sev, _ = _kald(
        [{
            "decision_id": "d1", "directive": "ingen git push",
            "priority": 92, "adherence_score": None,
        }],
        {},
    )
    assert sev == "hard", "fravær af data må ikke gøre gaten tandløs"


def test_hoej_adherence_blokerer_stadig_selv_med_brud():
    sev, _ = _kald(
        [{
            "decision_id": "d1", "directive": "ingen git push",
            "priority": 92, "adherence_score": 0.95,
        }],
        {"d1": {"count": 9, "last_at": None, "age_hours": 1.0}},
    )
    assert sev == "hard", "en målt høj adherence skal veje tungere end mistanker"
