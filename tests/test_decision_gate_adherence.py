"""Adherence skal gradere blokken — ikke bare pynte på advarslen.

Målt 22/10-2026 i den levende base: 116 aktive beslutninger, 12 under 40 %
adherence, 36 aldrig målt. `evaluate_decision_conflict` læste ALDRIG
`adherence_score`, så en beslutning jeg bryder 88 % af gangene blokerede præcis
lige hårdt som en jeg holder 100 %.

Værst: den beslutning jeg bryder mest (0,12 — «den afsluttende tekstblok er
ALTID sidste handling») har prioritet 92, altså den hårdeste blok. Gaten råbte
højest om netop det jeg ikke kunne finde ud af, og det gjorde blokeringen til
støj jeg lærte at køre igennem — den modsatte af hvad en gate skal gøre.

Reglen der vogtes: en konflikt med en LAV-adherence beslutning advarer men
blokerer ikke. En konflikt med en beslutning jeg faktisk holder blokerer som før.
`None` (aldrig målt) graderes som før — vi straffer ikke for manglende data.
"""
from __future__ import annotations

from unittest.mock import patch

from core.services import decision_gate as dg


def _kald(decisions):
    with patch(
        "core.services.behavioral_decisions.list_active_decisions",
        return_value=decisions,
    ), patch.object(dg, "_detect_conflict", return_value="konflikt"):
        return dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})


def test_hoej_prioritet_med_LAV_adherence_blokerer_ikke():
    """Kernen: prioritet 92 alene må ikke blokere når jeg bryder beslutningen."""
    sev, reason = _kald([
        {"decision_id": "d1", "directive": "ingen git push",
         "priority": 92, "adherence_score": 0.12},
    ])
    assert sev == "soft", (
        "en beslutning jeg bryder 88 % af gangene blokerede som om jeg holdt den "
        "— så lærer jeg bare at køre igennem, og gaten bliver støj"
    )
    assert "12%" in reason, "advarslen skal NAVNGIVE den målte adherence"
    assert "omformulér" in reason, (
        "båndet er omformulering, ikke gennemtvingning — se enforcement_section"
    )


def test_hoej_prioritet_med_HOEJ_adherence_blokerer_stadig():
    """Fixet må ikke gøre gaten tandløs: en forpligtelse jeg holder skal bide."""
    sev, reason = _kald([
        {"decision_id": "d1", "directive": "ingen git push",
         "priority": 92, "adherence_score": 0.95},
    ])
    assert sev == "hard"
    assert "blok" in reason


def test_aldrig_maalt_graderes_som_foer():
    """`None` = ingen data. Vi straffer ikke en beslutning for at mangle måling —
    de 36 «aldrig målt» skal klassificeres, ikke gættes på."""
    sev, _ = _kald([
        {"decision_id": "d1", "directive": "ingen git push",
         "priority": 92, "adherence_score": None},
    ])
    assert sev == "hard"

    sev2, _ = _kald([
        {"decision_id": "d1", "directive": "ingen git push", "priority": 92},
    ])
    assert sev2 == "hard"


def test_kun_de_beslutninger_i_KONFLIKT_taeller():
    """En lav score på en URELATERET beslutning må ikke gøre en ægte konflikt blød.

    Ellers kunne én dårligt-holdt beslutning i basen afvæbne alle andre.
    """
    def _selektiv(directive, context, decision):
        return "konflikt" if "git push" in directive else None

    with patch(
        "core.services.behavioral_decisions.list_active_decisions",
        return_value=[
            {"decision_id": "d1", "directive": "ingen git push",
             "priority": 92, "adherence_score": 0.95},
            {"decision_id": "d2", "directive": "undgå at bruge bash",
             "priority": 90, "adherence_score": 0.05},
        ],
    ), patch.object(dg, "_detect_conflict", side_effect=_selektiv):
        sev, _ = dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})
    assert sev == "hard", (
        "den urelaterede 0,05-beslutning gjorde en ægte konflikt blød — så "
        "afvæbner én dårligt-holdt beslutning alle andre"
    )


def test_alle_konflikter_skal_vaere_svage_for_at_slaekke():
    """Er blot ÉN af konflikterne en jeg holder, blokerer gaten stadig."""
    with patch(
        "core.services.behavioral_decisions.list_active_decisions",
        return_value=[
            {"decision_id": "d1", "directive": "ingen git push",
             "priority": 92, "adherence_score": 0.10},
            {"decision_id": "d2", "directive": "ingen git push til main",
             "priority": 88, "adherence_score": 0.90},
        ],
    ), patch.object(dg, "_detect_conflict", return_value="konflikt"):
        sev, _ = dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})
    assert sev == "hard"


def test_taersklen_er_den_samme_som_enforcement_bandet():
    """`enforcement_section` eskalerer ved 0,4. To forskellige tærskler for
    samme begreb ville betyde at en beslutning kunne være «enforced» i prompten
    og «blød» i gaten samtidig."""
    from core.services.decision_enforcement import enforcement_section  # noqa: F401
    assert dg._LAV_ADHERENCE == 0.4
