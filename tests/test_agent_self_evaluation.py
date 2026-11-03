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


def _fake_tick(
    act_kind="productive_idle",
    priorities=None,
    actions=None,
    elapsed_ms=1000,
    koert=30,
    fejlet=0,
    action_status=None,
    action_type=None,
    blocked_reason="",
    **signals,
):
    """Et tick-resultat med samme form som ``tick_with_phases`` returnerer.

    3/11-2026 (Codex' indvending): fixturen gav `tick_dispatched` en `actions`-
    liste, men den ægte dispatch-gren returnerer kun `tick_status` — så testen
    beviste en datastruktur produktionen aldrig leverer. Formen herunder er
    målt i `heartbeat_runtime_ticks`: `action_status`, `action_type`,
    `action_summary`, `decision_type`, `blocked_reason`.
    """
    sense = {
        "mood_name": "x", "active_goals": [], "events_last_hour": 0,
        "context_pressure_level": "comfortable", "errors_last_hour": 0,
        "failed_verifies": 0, "unverified_mutations": 0,
    }
    sense.update(signals)
    if act_kind in ("tick_dispatched", "tick_blocked_then_idle"):
        # Dispatch-formen: outcome i `result`, ingen `actions`.
        result = {
            "tick_status": "ok",
            "action_status": action_status if action_status is not None else "executed",
            "action_type": action_type if action_type is not None else "ping",
            "action_summary": "",
            "decision_type": "",
            "blocked_reason": blocked_reason,
        }
    else:
        result = {"actions": actions or []}
    return {
        "elapsed_ms": elapsed_ms,
        "indre_daemoner": {"koert": koert, "fejlet": fejlet, "brugere": 1},
        "phases": {
            "sense": sense,
            "reflect": {"priorities": priorities or []},
            "act": {"kind": act_kind, "result": result},
        },
    }


# 3/11-2026 (aften): spor-leddet blev fjernet. Det læste `events` globalt, men
# tabellen har ingen kolonne der binder et event til det slag der målte det —
# målt: 17.860 af 48.821 events i ét vindue kom fra én forgetting-daemon. Et
# slag kunne altså score 100 ved at sove mens en baggrundsdaemon arbejdede.
# Alle led læses nu af `tick_result`. Testene herunder værner det.

_IDLE_HANDLINGER = [
    "personality_snapshot", "personality_drift_tick", "tick_elapsed",
    "dreams", "wants", "boredom", "idle_daemon:event_trigger_shadow",
]


def _eval(tick, forrige=None):
    """Kør scoringen isoleret fra den levende historik."""
    with patch("core.services.agent_self_evaluation.load_json",
               return_value=forrige or []), \
         patch("core.services.agent_self_evaluation.save_json"):
        return evaluate_tick_quality(tick_result=tick)


def test_tomt_slag_scorer_lavt():
    """Intet sweep, intet at reagere på, ingen handlinger: kun tiden er sund."""
    r = _eval(_fake_tick(koert=0, actions=[]))
    assert "score" in r and "evaluated_at" in r
    assert r["score"] < 30


def test_daemon_sweepet_er_et_led_der_kan_mangle():
    """Sweepet sker ikke af sig selv — og det skal kunne ses i scoren."""
    uden = _eval(_fake_tick(koert=0, actions=[]))
    med = _eval(_fake_tick(koert=30, actions=[]))
    assert med["score"] > uden["score"]
    assert any("daemon-sweepet kørte ikke" in n for n in uden["notes"])


def test_daemon_fejl_traekker_ned():
    """De fejlende daemoner er et ægte kvalitetssignal — ikke pynt."""
    rent = _eval(_fake_tick(koert=30, fejlet=0, actions=[]))
    fejl = _eval(_fake_tick(koert=27, fejlet=3, actions=[]))
    assert fejl["score"] < rent["score"]
    assert any("3 fejlet" in n for n in fejl["notes"])


def test_reaktion_beloenner_kaeden_signal_prioritet_handling():
    """Kæden skal holdes hele vejen — ellers er prioriteringen teater.

    Bruger den ÆGTE dispatch-form: outcome i `result`, ingen `actions`.
    """
    handlede = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="executed", action_type="ping"))
    så_men_uden_handling = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="executed", action_type="productive_idle"))
    uden_prioritet = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=[], action_status="executed", action_type="ping"))
    assert handlede["score"] > så_men_uden_handling["score"]
    assert så_men_uden_handling["score"] > uden_prioritet["score"]
    assert any("dannede ingen prioritet" in n for n in uden_prioritet["notes"])


def test_dispatch_uden_udfoert_handling_faar_ingen_reaktionspoint():
    """Kernen i Codex' indvending: et dispatch der ikke udrettede noget må
    ikke kunne score som et der gjorde. `tick_status=ok` er ikke nok."""
    udrettede = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="executed", action_type="ping"))
    blokeret = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="blocked", action_type="ping",
        blocked_reason="active-chat-gate"))
    kun_idle = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="executed", action_type="productive_idle"))
    assert udrettede["score"] > blokeret["score"]
    assert udrettede["score"] > kun_idle["score"]
    assert any("blokeret" in n for n in blokeret["notes"])
    assert any("ledig drift" in n for n in kun_idle["notes"])


def test_dispatch_med_tom_status_taelles_ikke_som_handling():
    """Målt i produktion: felterne kan være tomme strenge. Tom status er
    ikke bevis for at noget skete."""
    tom = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="", action_type=""))
    assert any("uden udført handling" in n for n in tom["notes"])


def test_afsendt_handling_taelles_som_udfoert():
    """Codex 3/11-2026: kun `executed` blev godkendt, men målt i
    heartbeat_runtime_ticks har 681 rækker `action_status="sent"` — heraf 195
    webchat-heartbeat-ping og 173 discord-heartbeat-ping. En ping der faktisk
    blev afsendt er en effektueret handling, og blev dømt som resultatløs.
    """
    afsendt = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="sent", action_type="webchat-heartbeat-ping"))
    blokeret = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="blocked", action_type="webchat-heartbeat-ping",
        blocked_reason="active-chat-gate"))
    assert afsendt["score"] > blokeret["score"]
    assert any("webchat-heartbeat-ping" in n for n in afsendt["notes"])


def test_recorded_er_ikke_en_effektueret_handling():
    """`recorded` er `recorded-preview` (heartbeat_runtime.py:4474) med TOM
    `action_type` — intet blev sendt. Husets feedback-domæne i
    `runtime_operational_memory.py:209` regner den som succes, men dér måles om
    posten blev REGISTRERET; her måles om handlingen blev EFFEKTUERET.
    """
    r = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="recorded", action_type=""))
    assert any("uden udført handling" in n for n in r["notes"])


def test_dispatch_handlingen_foeres_videre_til_nyhed_og_historik():
    """Codex' anden indvending: `_score_reaktion` dannede den syntetiske
    dispatch-handling LOKALT, så kalderens liste forblev tom — hvert dispatch
    blev gemt med `actions: []` og fik 0 nyhedspoint, selv når handlingstypen
    var ny. Handlingen skal både gemmes og kunne være ny næste gang.
    """
    foerste = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="sent", action_type="discord-heartbeat-ping"))
    assert foerste["actions"], "dispatch-handlingen blev ikke gemt i posten"

    forrige = [{
        "evaluated_at": datetime.now(UTC).isoformat(), "score": 40,
        "actions": ["dispatch udførte discord-heartbeat-ping"],
    }]
    gentaget = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="sent", action_type="discord-heartbeat-ping"),
        forrige=forrige)
    nyt = _eval(_fake_tick(
        act_kind="tick_dispatched", failed_verifies=2,
        priorities=["address_failed_verifications"],
        action_status="sent", action_type="webchat-heartbeat-proposal"),
        forrige=forrige)
    assert nyt["score"] > gentaget["score"], (
        "en ny handlingstype gav ingen nyhed — handlingen føres ikke videre"
    )


def test_et_ledigt_slag_kan_ikke_laengere_score_90():
    """Kernen i indvendingen (3/11-2026): et slag der kører den samme runde
    igen fik 90-100, fordi spor-leddet talte baggrundsstøj. Nu måler nyheds-
    leddet slagets EGNE handlinger — og de syv gentagne giver nul nyhed.
    """
    forrige = [{"evaluated_at": datetime.now(UTC).isoformat(), "score": 90,
                "actions": list(_IDLE_HANDLINGER)}]
    r = _eval(_fake_tick(actions=list(_IDLE_HANDLINGER)), forrige=forrige)
    assert r["score"] <= 70, f"et gentaget ledigt slag scorer {r['score']}"
    assert any("samme handlinger" in n for n in r["notes"])


def test_nye_handlinger_giver_nyhed():
    """Et system der kører den samme runde igen, er ikke produktivt."""
    forrige = [{"evaluated_at": datetime.now(UTC).isoformat(), "score": 40,
                "actions": list(_IDLE_HANDLINGER)}]
    gentaget = _eval(_fake_tick(actions=list(_IDLE_HANDLINGER)), forrige=forrige)
    nyt = _eval(_fake_tick(actions=["memory.written", "dream.recorded"]),
                forrige=forrige)
    assert nyt["score"] > gentaget["score"]


def test_scoringen_laeser_ikke_globale_events():
    """Selve rettelsen, som AST — en vagt mod at koblingen sniger sig ind igen.

    Målt 3/11-2026: `events` har fire kolonner, og ingen af dem henfører et
    event til det slag der målte det. Læser scoringen den tabel igen, er
    scoren tilbage til at måle systemets puls i stedet for slagets arbejde.
    """
    import ast
    import inspect
    import textwrap

    from core.services import agent_self_evaluation as ase

    # Vagtens omfang er SCORINGS-STIEN, ikke hele modulet: adhærence-måleren
    # længere nede læser beslutninger fra DB med rette.
    for navn in ("evaluate_tick_quality", "_score_daemons", "_score_reaktion",
                 "_score_novelty", "_previous_eval"):
        fn = getattr(ase, navn)
        trae = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        moduler = set()
        for n in ast.walk(trae):
            if isinstance(n, ast.ImportFrom) and n.module:
                moduler.add(n.module)
            elif isinstance(n, ast.Import):
                moduler.update(a.name for a in n.names)
        assert not any(m.startswith("core.runtime.db") for m in moduler), (
            f"{navn} importerer databasen igen: {sorted(moduler)}"
        )
        sql = [
            n.value for n in ast.walk(trae)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and "FROM EVENTS" in n.value.upper()
        ]
        assert sql == [], f"{navn} har stadig en SQL der læser events: {sql}"
    assert not hasattr(ase, "_trace_kinds_since"), (
        "det globale spor-opslag er tilbage"
    )


def test_posten_gemmer_hvad_slaget_udrettede():
    """Uden handlinger og prioriteter kan nyheds-målingen ikke virke næste gang."""
    r = _eval(_fake_tick(actions=["a", "b"], priorities=["p1"],
                         koert=29, fejlet=1))
    assert r["actions"] == ["a", "b"]
    assert r["priorities"] == ["p1"]
    assert r["daemon_koert"] == 29
    assert r["daemon_fejlet"] == 1


def test_haengende_slag_faar_ingen_tidspoint():
    r = _eval(_fake_tick(elapsed_ms=200_000))
    assert any("HANG" in n for n in r["notes"])


def test_historikken_raekker_til_vinduet():
    """3/11-2026: 200 poster dækkede 2,2 døgn, så ``days=7``, ``(14)`` og
    ``(30)`` gav identiske tal — et vindue der ikke kan rumme sin egen etiket.
    """
    from core.services import agent_self_evaluation as ase

    assert ase._MAX_TICK_EVALS_KEPT >= 30 * 90, (
        "loftet skal dække 30 døgn ved ~90 slag i døgnet"
    )


def test_komprimering_bevarer_tal_men_skærer_detaljer():
    """Ældre poster behøver tal, ikke hvilke handlinger der skrev den gang."""
    from core.services import agent_self_evaluation as ase

    evals = [
        {"evaluated_at": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}T00:00:00+00:00",
         "score": 80, "actions": ["b"] * 20, "priorities": ["p"] * 10}
        for i in range(300)
    ]
    slim = ase._slim_history(evals)

    assert len(slim) == 300, "ingen poster må forsvinde"
    assert all(p["score"] == 80 for p in slim), "scoren skal bevares"
    assert slim[-1]["actions"] and slim[-1]["priorities"], "de nyeste beholder detaljen"
    assert "actions" not in slim[0], "de ældste skal være skåret"
    # 3/11-2026: posten er blevet mindre (spor-listen på op til 200 arter er
    # væk), så den gamle 1/3-tærskel målte noget andet. Halvdelen er grænsen
    # for at komprimeringen stadig gør sit arbejde.
    assert len(json.dumps(slim)) < len(json.dumps(evals)) / 2


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
