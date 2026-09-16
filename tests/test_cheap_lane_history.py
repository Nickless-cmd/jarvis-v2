"""Historikken bag cheap lane — 90.000 kald ingen kunne se.

Testene koerer mod en ÆGTE sqlite-tabel (isolated_runtime), ikke en attrap:
hele pointen er at SQL'en taeller rigtigt, og en fake connect ville bare svare
det jeg selv lagde i den.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import cheap_lane_history as H


def _skriv(**kw):
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation
    record_cheap_provider_invocation(**kw)


def _gammel(rows_back_hours: float, **kw):
    """Skriv en raekke og skub dens tidsstempel bagud."""
    from core.runtime.db import connect
    _skriv(**kw)
    naar = (datetime.now(UTC) - timedelta(hours=rows_back_hours)).isoformat()
    with connect() as c:
        c.execute("UPDATE cheap_provider_invocations SET created_at = ? "
                  "WHERE id = (SELECT MAX(id) FROM cheap_provider_invocations)", (naar,))
        c.commit()


@pytest.fixture
def data(isolated_runtime):
    _skriv(provider="alfa", model="m1", status="completed", latency_ms=100, cost_usd=0.001)
    _skriv(provider="alfa", model="m1", status="completed", latency_ms=300, cost_usd=0.001)
    _skriv(provider="alfa", model="m1", status="failed", error_code="rate-limited",
           error_message="429 for mange")
    _skriv(provider="beta", model="m2", status="failed", error_code="http-410",
           error_message="modellen er udgaaet")
    _gammel(48, provider="gammel", model="m3", status="completed", latency_ms=50)
    return True


def test_succesraten_regnes_pr_udbyder(data):
    ud = {u["provider"]: u for u in H.udbyder_historik(timer=24)["udbydere"]}
    assert ud["alfa"]["kald"] == 3 and ud["alfa"]["ok"] == 2
    assert ud["alfa"]["succesrate"] == round(2 / 3, 4)
    assert ud["beta"]["succesrate"] == 0.0        # maalt nul, ikke «ingen data»


def test_vinduet_holder_gamle_kald_ude(data):
    navne = {u["provider"] for u in H.udbyder_historik(timer=24)["udbydere"]}
    assert "gammel" not in navne
    assert "gammel" in {u["provider"] for u in H.udbyder_historik(timer=72)["udbydere"]}


def test_latens_maales_KUN_paa_gennemfoerte(data):
    alfa = next(u for u in H.udbyder_historik(timer=24)["udbydere"] if u["provider"] == "alfa")
    # 100 og 300 er de to gennemfoerte; fejlen (0 ms) maa ikke trykke tallet ned.
    assert alfa["latens_p50_ms"] in (100, 300) and alfa["latens_p95_ms"] == 300


def test_fejlkoderne_foelger_med(data):
    beta = next(u for u in H.udbyder_historik(timer=24)["udbydere"] if u["provider"] == "beta")
    assert beta["fejlkoder"] == [{"kode": "http-410", "antal": 1}]


def test_opsummeringen_daekker_hele_vinduet(data):
    o = H.udbyder_historik(timer=24)["opsummering"]
    assert o["kald"] == 4 and o["fejl"] == 2 and o["udbydere"] == 2


def test_ingen_kald_giver_INGEN_procent(isolated_runtime):
    assert H.udbyder_historik(timer=1)["opsummering"]["succesrate"] is None


def test_fejl_listen_skelner_loft_fra_antal(data):
    ud = H.seneste_fejl(timer=24, loft=1)
    assert ud["vist"] == 1 and ud["antal_i_vinduet"] == 2   # loftet er ikke tallet
    assert ud["raekker"][0]["error_code"] in ("rate-limited", "http-410")


def test_tidsserien_taeller_kald_og_fejl(data):
    s = H.tidsserie(timer=24, spand_minutter=60)["spand"]
    assert sum(x["kald"] for x in s) == 4
    assert sum(x["fejl"] for x in s) == 2
