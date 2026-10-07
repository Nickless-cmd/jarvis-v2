"""En autonom koersel maa ikke bogfoeres som synlig.

`visible_runs` skriver hovedbogen to steder i samme funktion. Den foerste
ligger lige FOER `yield _sse("done", ...)`, fordi SSE-v2 lukker generatoren
dér — det er altsaa den der faktisk koerer paa den normale vej. Den
haardkodede `lane="visible"`, mens soester-kaldet 400 linjer nede brugte
`lane=run.lane`.

Maalt 1/10-2026: 1.087 raekker i hovedbogen med `run_id LIKE 'autonomous-%'`
og `lane='visible'`, mens koerslernes egen lane er `primary` (9.145 raekker).
Ingen penge flyttede sig — den foerste skrivning saetter `cost_usd=0.0` — men
enhver opgoerelse af «den synlige lane» indeholdt autonomt arbejde.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.services import visible_run_cost as vrc


@dataclass
class _Koersel:
    run_id: str = "r1"
    lane: str = "visible"
    provider: str = "deepseek"
    model: str = "deepseek-flash"


@pytest.fixture
def fanget(monkeypatch):
    rows: list[dict] = []
    monkeypatch.setattr("core.costing.ledger.record_cost",
                        lambda **kw: rows.append(kw))
    return rows


def _bogfoer(run, **kw):
    vrc.bogfoer_koerslens_omkostning(
        run, input_tokens=100, output_tokens=10,
        cache_hit_tokens=90, cache_miss_tokens=10, **kw)


def test_en_autonom_koersel_bogfoeres_paa_SIN_EGEN_lane(fanget):
    """Kernen. Koerslens lane er `primary`; den maa ikke blive til `visible`."""
    _bogfoer(_Koersel(run_id="autonomous-abc", lane="primary"))
    assert fanget[0]["lane"] == "primary"
    assert fanget[0]["run_id"] == "autonomous-abc"


def test_en_synlig_koersel_er_stadig_synlig(fanget):
    _bogfoer(_Koersel(run_id="visible-abc", lane="visible"))
    assert fanget[0]["lane"] == "visible"


def test_prisen_er_nul_som_standard(fanget):
    """Beloebet staar paa runde-raekkerne (`lane='agentic_round'`). En pris her
    som standard ville taelle dobbelt."""
    _bogfoer(_Koersel())
    assert fanget[0]["cost_usd"] == 0.0


def test_et_kaldssted_med_den_samlede_pris_kan_sende_den(fanget):
    _bogfoer(_Koersel(), cost_usd=1.25)
    assert fanget[0]["cost_usd"] == 1.25


def test_tokens_naar_uaendret_igennem(fanget):
    _bogfoer(_Koersel())
    r = fanget[0]
    assert (r["input_tokens"], r["output_tokens"]) == (100, 10)
    assert (r["cache_hit_tokens"], r["cache_miss_tokens"]) == (90, 10)
    assert r["provider"] == "deepseek" and r["model"] == "deepseek-flash"


def test_en_koersel_uden_lane_falder_tilbage_paa_synlig(fanget):
    """Tom lane maa ikke blive til en tom streng i hovedbogen — saa ville
    raekken falde ud af enhver lane-opgoerelse i stedet for at vaere forkert ét
    sted, hvor den kan ses."""
    _bogfoer(_Koersel(lane=""))
    assert fanget[0]["lane"] == "visible"


def test_begge_kaldssteder_i_visible_runs_bruger_enheden():
    """Vagten mod at de to skrivninger driver fra hinanden igen."""
    import inspect
    from core.services import visible_runs
    kilde = inspect.getsource(visible_runs)
    assert kilde.count("bogfoer_koerslens_omkostning(") == 2
    assert "record_cost(" not in kilde, "hovedbogen skrives kun gennem enheden"
    assert 'lane="visible"' not in kilde
