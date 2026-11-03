"""Unit tests for agent_self_evaluation."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.agent_self_evaluation import (
    evaluate_tick_quality,
    tick_quality_summary,
    detect_stale_goals,
    stale_goals_section,
    decision_adherence_summary,
    self_evaluation_section,
)


def _fake_tick(act_kind="productive_idle", priorities=None, actions=None, elapsed_ms=1000):
    return {
        "elapsed_ms": elapsed_ms,
        "phases": {
            "sense": {
                "mood_name": "x", "active_goals": [], "events_last_hour": 0,
                "context_pressure_level": "comfortable", "errors_last_hour": 0,
            },
            "reflect": {"priorities": priorities or []},
            "act": {
                "kind": act_kind,
                "result": {"actions": actions or []},
            },
        },
    }


# 2026-09-05: scoringen måler nu SPOR, ikke form. De tre tests herunder holdt
# tidligere fast i formen (havde slaget priorities? hvor mange handlinger?), og
# netop den form gav 70 til 199 af 200 slag. Et slag med priorities der ikke
# efterlader noget, skal kunne score lavt — det er hele pointen.


def _uden_spor(monkeypatch=None):
    """Patch spor-opslaget til tomt, så testen ikke afhænger af en levende DB."""
    return patch("core.services.agent_self_evaluation._trace_kinds_since",
                 return_value=[])


def _med_spor(*kinds):
    return patch("core.services.agent_self_evaluation._trace_kinds_since",
                 return_value=list(kinds))


def test_slag_uden_spor_scorer_lavt():
    """Ingen handlinger, ingen spor: kun tiden er sund."""
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), _uden_spor():
        result = evaluate_tick_quality(tick_result=_fake_tick())
    assert "score" in result and "evaluated_at" in result
    assert result["score"] < 60


def test_priorities_alene_giver_ikke_hoej_score():
    """Den gamle scoring gav +45 for priorities + dispatch uanset udbytte."""
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), _uden_spor():
        result = evaluate_tick_quality(tick_result=_fake_tick(
            act_kind="tick_dispatched",
            priorities=["compact_context", "verify_mutations"],
            elapsed_ms=2000,
        ))
    assert result["score"] < 60, "form uden spor må ikke give høj score"


def _score_med_spor(antal: int) -> dict:
    """Kør ét slag med præcis ``antal`` spor-arter og intet forrige slag."""
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), \
         _med_spor(*[f"spor.art{i}" for i in range(antal)]):
        return evaluate_tick_quality(tick_result=_fake_tick(
            act_kind="productive_idle",
            actions=["personality_snapshot", "composite_candidates:2"],
            elapsed_ms=5000,
        ))


def test_spor_loefter_scoren():
    """Spor skal løfte — og leddet må ikke mætte ved seks arter.

    3/11-2026: denne test krævede ≥80 ved seks arter. Niveauet var kalibreret
    til en virkelighed hvor seks var meget; målt samme dag er medianen 82 og
    ALLE 200 slag lå på 14-120, så trappen gav 50 point til hvert eneste slag
    og scoren kunne reelt kun være 75 eller 90. Kravet låste altså netop den
    mætning der skulle fjernes. Nu værner testen FORMEN i stedet for ét
    niveau: flere arter giver mere, hele vejen op.
    """
    seks = _score_med_spor(6)
    fyrre = _score_med_spor(40)
    hel = _score_med_spor(120)

    assert seks["score"] > 60, "seks spor-arter skal stadig løfte slaget"
    assert fyrre["score"] > seks["score"], "40 arter må ikke give det samme som 6"
    assert hel["score"] > fyrre["score"], "120 arter må ikke give det samme som 40"
    assert hel["score"] >= 90


def test_spor_listen_klippes_ikke_ved_fyrre():
    """3/11-2026: ``trace_kinds[:40]`` gjorde nyheds-målingen halvblind — den
    målte bredde er 14-120, så 120 af 200 poster var klippede og næste slag
    blev sammenlignet mod de første 40 alfabetisk i stedet for mod alle.
    """
    result = _score_med_spor(90)
    assert len(result["trace_kinds"]) == 90
    assert result["trace_kind_count"] == 90


def test_historikken_raekker_til_vinduet():
    """3/11-2026: 200 poster dækkede 2,2 døgn, så ``days=7``, ``(14)`` og
    ``(30)`` gav identiske tal — et vindue der ikke kan rumme sin egen etiket.
    """
    from core.services import agent_self_evaluation as ase

    assert ase._MAX_TICK_EVALS_KEPT >= 30 * 90, (
        "loftet skal dække 30 døgn ved ~90 slag i døgnet"
    )


def test_komprimering_bevarer_tal_men_skærer_detaljer():
    """Ældre poster behøver tal, ikke hvilke event-arter der skrev den gang."""
    from core.services import agent_self_evaluation as ase

    evals = [
        {"evaluated_at": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}T00:00:00+00:00",
         "score": 80, "trace_kinds": [f"art{i}"] * 120, "actions": ["b"] * 20}
        for i in range(300)
    ]
    slim = ase._slim_history(evals)

    assert len(slim) == 300, "ingen poster må forsvinde"
    assert all(p["score"] == 80 for p in slim), "scoren skal bevares"
    assert slim[-1]["trace_kinds"] and slim[-1]["actions"], "de nyeste beholder detaljen"
    assert "trace_kinds" not in slim[0], "de ældste skal være skåret"
    assert len(json.dumps(slim)) < len(json.dumps(evals)) / 3


def test_opsummeringen_siger_hvor_langt_historikken_raekker():
    """Et 30-dages vindue over 2 døgn er en etiket, ikke en måling."""
    nu = datetime.now(UTC)
    evals = [{"evaluated_at": (nu - timedelta(hours=h)).isoformat(), "score": 80}
             for h in range(48)]
    with patch("core.services.agent_self_evaluation.load_json", return_value=evals):
        kort = tick_quality_summary(days=30)
        daekket = tick_quality_summary(days=1)

    assert kort["window_covered"] is False
    assert "ikke dækket" in kort["coverage_warning"]
    assert daekket["window_covered"] is True


def test_samme_spor_som_sidst_giver_ingen_nyhed():
    """Et system der kører den samme runde igen, er ikke produktivt."""
    forrige = [{"evaluated_at": (datetime.now(UTC) - timedelta(seconds=30)).isoformat(),
                "score": 40, "trace_kinds": ["memory.written", "dream.recorded"]}]
    with patch("core.services.agent_self_evaluation.load_json", return_value=forrige), \
         patch("core.services.agent_self_evaluation.save_json"), \
         _med_spor("memory.written", "dream.recorded"):
        gentaget = evaluate_tick_quality(tick_result=_fake_tick(actions=["x"]))
    with patch("core.services.agent_self_evaluation.load_json", return_value=forrige), \
         patch("core.services.agent_self_evaluation.save_json"), \
         _med_spor("noget.helt_nyt", "og_et_til.ogsaa_nyt"):
        nyt = evaluate_tick_quality(tick_result=_fake_tick(actions=["x"]))
    assert nyt["score"] > gentaget["score"], "nye spor skal score højere end en gentagelse"


def test_haengende_slag_faar_ingen_tidspoint():
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), _uden_spor():
        result = evaluate_tick_quality(tick_result=_fake_tick(elapsed_ms=200_000))
    assert any("HANG" in n for n in result["notes"])


def test_posten_gemmer_hvad_slaget_udrettede():
    """Uden actions/trace_kinds i posten kan nyheds-målingen ikke virke næste gang."""
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), \
         _med_spor("memory.written"):
        result = evaluate_tick_quality(tick_result=_fake_tick(actions=["a", "b"]))
    assert result["actions"] == ["a", "b"]
    assert result["trace_kinds"] == ["memory.written"]
    assert result["window_seconds"] >= 0


def test_laast_maaling_raabes_op_i_opsummeringen():
    """Den fejl vi lige har rettet, må aldrig kunne gemme sig igen."""
    nu = datetime.now(UTC)
    evals = [{"evaluated_at": (nu - timedelta(minutes=i)).isoformat(), "score": 70}
             for i in range(20)]
    with patch("core.services.agent_self_evaluation.load_json", return_value=evals):
        s = tick_quality_summary()
    assert s["trend"] == "locked"
    assert s["distinct_scores"] == 1
    assert "låst" in s["warning"]


def test_summary_no_evals_returns_empty():
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]):
        s = tick_quality_summary()
    assert s["count"] == 0
    assert s["avg_score"] is None


def test_summary_calculates_trend_improving():
    now = datetime.now(UTC)
    evals = [
        {"evaluated_at": (now - timedelta(days=6)).isoformat(), "score": 30},
        {"evaluated_at": (now - timedelta(days=5)).isoformat(), "score": 35},
        {"evaluated_at": (now - timedelta(days=4)).isoformat(), "score": 40},
        {"evaluated_at": (now - timedelta(days=1)).isoformat(), "score": 80},
        {"evaluated_at": (now - timedelta(hours=12)).isoformat(), "score": 85},
        {"evaluated_at": now.isoformat(), "score": 90},
    ]
    with patch("core.services.agent_self_evaluation.load_json", return_value=evals):
        s = tick_quality_summary(days=7)
    assert s["count"] == 6
    assert s["trend"] == "improving"


def test_detect_stale_goals_returns_old_ones():
    old_iso = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    fresh_iso = datetime.now(UTC).isoformat()
    with patch("core.services.long_horizon_goals.list_active_goals", return_value=[
        {"goal_id": "g1", "title": "stale one", "priority": "high",
         "updated_at": old_iso, "created_at": old_iso},
        {"goal_id": "g2", "title": "fresh one", "priority": "low",
         "updated_at": fresh_iso, "created_at": fresh_iso},
    ]):
        stale = detect_stale_goals(stale_days=3)
    assert len(stale) == 1
    assert stale[0]["title"] == "stale one"


def test_stale_goals_section_returns_none_when_clean():
    with patch("core.services.agent_self_evaluation.detect_stale_goals", return_value=[]):
        assert stale_goals_section() is None


def test_stale_goals_section_lists_when_present():
    with patch("core.services.agent_self_evaluation.detect_stale_goals", return_value=[
        {"goal_id": "g1", "title": "stagnerer", "priority": "high",
         "last_update": "2026-04-20T00:00:00Z", "days_stale": 3},
    ]):
        section = stale_goals_section()
    assert section is not None
    assert "stagnerer" in section


def test_adherence_returns_none_when_no_decisions():
    with patch("core.runtime.db_decisions.list_decisions", return_value=[]):
        result = decision_adherence_summary()
    assert result["score"] is None


def test_adherence_calculates_score():
    with patch("core.services.decision_action_gate.opportunity_summary", return_value={"quote": {"opportunities": 2, "kept": 1, "unconfirmed": 1}}), \
         patch("core.runtime.db_decisions.list_decisions", return_value=[
        {"decision_id": "d1", "directive": "x", "adherence_score": 1.0},
        {"decision_id": "d2", "directive": "y", "adherence_score": 0.5},
    ]):
        result = decision_adherence_summary()
    assert result["score"] == 75.0
    assert result["flag"] is None  # 75 > 60
    assert result["observed_opportunities"]["quote"]["kept"] == 1


def test_adherence_flags_low_score():
    with patch("core.runtime.db_decisions.list_decisions", return_value=[
        {"decision_id": "d1", "directive": "x", "adherence_score": 0.0},
        {"decision_id": "d2", "directive": "y", "adherence_score": 0.5},
    ]):
        result = decision_adherence_summary()
    assert result["flag"]
    assert result["recovery"]["needed"] is True
    assert result["low_decisions"][0]["decision_id"] == "d1"


def test_adherence_recovery_detects_duplicate_active_decisions():
    with patch("core.runtime.db_decisions.list_decisions", return_value=[
        {"decision_id": "d1", "directive": "Do the thing", "priority": 80, "adherence_score": 0.5, "created_at": "1"},
        {"decision_id": "d2", "directive": "  do   the thing  ", "priority": 75, "adherence_score": None, "created_at": "2"},
    ]):
        result = decision_adherence_summary()
    assert result["duplicate_groups"][0]["keeper_id"] == "d1"
    assert result["duplicate_groups"][0]["duplicate_ids"] == ["d2"]
    assert "duplicate" in result["recovery"]["actions"][0].lower()


def test_self_evaluation_section_combines_all():
    with patch("core.services.agent_self_evaluation.tick_quality_summary",
               return_value={"avg_score": 65, "trend": "stable", "count": 10}), \
         patch("core.services.agent_self_evaluation.decision_adherence_summary",
               return_value={"score": 50, "flag": True}), \
         patch("core.services.agent_self_evaluation.detect_stale_goals",
               return_value=[{"goal_id": "g1"}]):
        section = self_evaluation_section()
    assert section is not None
    assert "65" in section
    assert "50%" in section
    # Section text was lowercase "stagnerer"; now capitalized "Stagnerende"
    # (Danish gerund form, more readable as section header). Match either.
    assert "tagnerer" in section or "Stagnerende" in section or "stagnerende" in section


def test_adherence_ser_alle_aktive_ikke_kun_de_foerste():
    """Målt 5/10-2026: `limit=50` skjulte 30 af 80 aktive beslutninger for
    tallet i prompten. Sorteringen er `priority DESC, updated_at DESC`, så
    skæringen FLYTTEDE sig — et opdateret direktiv skubbede et andet ud, uden
    at nogen kunne se hvilke. Præcis samme fejl som `_ALL_ACTIVE=500` rettede i
    `decision_review_prompter` og `_ALLE_AKTIVE=500` i `decision_gate`.

    Den falske liste RESPEKTERER `limit`, så testen kun består når måleren
    spørger uden grænse. Sætter nogen en grænse tilbage, falder den.
    """
    alle = [
        {"decision_id": f"d{i}", "directive": f"x{i}", "priority": 100 - i,
         "adherence_score": 1.0, "created_at": str(i)}
        for i in range(60)
    ]

    def falsk_liste(*, status="active", limit=50):
        raekker = sorted(alle, key=lambda d: -int(d["priority"]))
        return raekker if limit is None else raekker[: int(limit)]

    with patch("core.runtime.db_decisions.list_decisions", side_effect=falsk_liste):
        result = decision_adherence_summary()

    assert result["total"] == 60, (
        f"måleren ser kun {result['total']} af 60 aktive beslutninger — "
        "en grænse skærer listen"
    )
