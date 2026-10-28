"""Vaegt-lageret: persisteret vaegt der UPDATE'er i stedet for at INSERT'e.

BAGGRUND (28/10-2026). `runtime_action_outcomes` havde 274.614 raekker med
baade decision_score og result_status — men kun 6 distinkte score-vaerdier for
257.027 ok-raekker. En score skrevet EFTER udfaldede kan ikke have pavirket det
valg den beskriver. Disse tests maaler at vaegten nu er en TILSTAND der flytter
sig, ikke et facit-notat der skrives bagefter.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def signals(isolated_runtime):
    from core.runtime import db_runtime_signals as s

    return s


def test_outcome_target_mapper_udfald_til_retning(signals):
    """Et udfalds retning skal vaere et tal i [0,1] — og ukendt maa ikke gætte."""
    assert signals.outcome_target("executed") == 1.0
    assert signals.outcome_target("success") == 1.0
    assert signals.outcome_target("failed") == 0.0
    assert signals.outcome_target("error") == 0.0
    # Ukendt status er NEUTRAL, ikke et nej — vi ved det ikke.
    assert signals.outcome_target("noget-ukendt") == 0.5
    assert signals.outcome_target("") == 0.5


def test_outcome_target_er_case_og_whitespace_tolerant(signals):
    assert signals.outcome_target("  EXECUTED  ") == 1.0
    assert signals.outcome_target("Failed") == 0.0


def test_tom_tabel_giver_tom_vaegt_ikke_neutral(signals):
    """FRAVAER af viden er ikke det samme som «neutral». En ukendt term
    skal ikke dukke op med vaegt 0.5 — den skal slet ikke dukke op."""
    assert signals.load_action_weights() == {}
    assert signals.load_action_weights(["aldrig-set"]) == {}


def test_udfald_skrives_og_kan_laeses_tilbage(signals):
    row = signals.record_runtime_action_outcome(
        action_id="follow_open_loop",
        decision_mode="execute",
        decision_reason="test",
        decision_score=0.85,
        payload_json={"k": "v"},
        result_status="executed",
        result_summary="det gik",
        result_json={"ok": True},
        recorded_at="2026-10-28T20:00:00+00:00",
    )
    assert row["action_id"] == "follow_open_loop"
    assert row["decision_score"] == pytest.approx(0.85)

    recent = signals.recent_runtime_action_outcomes(limit=5)
    assert len(recent) == 1
    assert recent[0]["result_status"] == "executed"
    assert recent[0]["payload"] == {"k": "v"}


def test_vaegten_starter_paa_det_foerste_udfald(signals):
    """Foerste sample: rate = 1/(0+1) = 1.0, saa vaegten rammer target praecist."""
    got = signals.apply_action_weight_update(
        term="follow_open_loop",
        outcome_status="executed",
        recorded_at="2026-10-28T20:00:00+00:00",
    )
    assert got["n_samples"] == 1
    assert got["weight"] == pytest.approx(1.0)


def test_vaegten_FLYTTTER_sig_mellem_to_samples(signals):
    """Det afgoerende maal: to modsatte udfald skal give to FORSKELLIGE vaegte.
    En vaegt der ikke kan flytte sig er ikke en vaegt."""
    first = signals.apply_action_weight_update(
        term="a", outcome_status="failed", recorded_at="2026-10-28T20:00:00+00:00"
    )
    second = signals.apply_action_weight_update(
        term="a", outcome_status="executed", recorded_at="2026-10-28T20:01:00+00:00"
    )
    assert first["weight"] == pytest.approx(0.0)
    assert second["weight"] == pytest.approx(0.5)
    assert first["weight"] != second["weight"]


def test_laeringsraten_aftager_praecis_som_1_over_n_plus_1(signals):
    """Raten er AFLEDT af forloebet, ikke valgt frit. Maalt direkte:
    bevægelse / afstand-til-target skal vaere 1/(n+1) ved hvert skridt."""
    expected = [1.0, 0.5, 1 / 3, 0.25, 0.2]
    rates: list[float] = []
    weight = 0.5
    for i in range(5):
        target = 1.0 if i % 2 == 0 else 0.0
        got = signals.apply_action_weight_update(
            term="a",
            outcome_status="executed" if i % 2 == 0 else "failed",
            recorded_at=f"2026-10-28T20:0{i}:00+00:00",
        )
        rates.append(round(abs(got["weight"] - weight) / abs(target - weight), 6))
        weight = float(got["weight"])
    for got_rate, want in zip(rates, expected):
        assert got_rate == pytest.approx(want, abs=1e-5), rates


def test_vaegt_0_0_laeses_som_nul_ikke_som_neutral(signals):
    """FEJLEN DER BLEV FUNDET: `float(entry.get("weight") or 0.5)` gjorde en
    vaegt paa praecis 0.0 til 0.5. Det daarligste forloeb var usynligt.
    Denne test vogter at 0.0 kommer ud som 0.0."""
    signals.apply_action_weight_update(
        term="altid-fejl", outcome_status="failed", recorded_at="2026-10-28T20:00:00+00:00"
    )
    loaded = signals.load_action_weights(["altid-fejl"])
    assert loaded["altid-fejl"]["weight"] == pytest.approx(0.0)
    assert loaded["altid-fejl"]["weight"] != pytest.approx(0.5)


def test_vaegten_er_global_paa_tvaers_af_kald(signals):
    """Vaegten skal vaere en TILSTAND: naeste kald skal se den forrige skrivning."""
    for _ in range(3):
        signals.apply_action_weight_update(
            term="gentaget", outcome_status="failed", recorded_at="2026-10-28T20:00:00+00:00"
        )
    loaded = signals.load_action_weights(["gentaget"])
    assert loaded["gentaget"]["n_samples"] == 3
    assert loaded["gentaget"]["weight"] == pytest.approx(0.0)
