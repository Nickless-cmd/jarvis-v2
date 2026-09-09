"""Genforsøg som en begrænset beslutning.

Fase 2: «retries preserve accepted request history and obey total attempt/time/
token/cost caps». Og fra streaming-invarianterne: «Limits apply across
providers ... Provider failover does not reset them.»
"""
from __future__ import annotations

import pytest

from core.services import retry_runtime as R
from core.services.retry_runtime import Budget, Spent, decide


def _d(**kw):
    kw.setdefault("failure", R.TIMEOUT)
    kw.setdefault("budget", Budget())
    kw.setdefault("spent", Spent())
    return decide(**kw)


# ── hvad der prøves igen, og hvad der ikke gør ──────────────────────────

@pytest.mark.parametrize("f", R.FORBIGAAENDE)
def test_forbigaaende_fejl_proeves_igen(f):
    assert _d(failure=f).action == R.RETRY


@pytest.mark.parametrize("f", R.UAENDRET_AF_AT_SPOERGE_IGEN)
def test_en_tilstand_der_ikke_aendrer_sig_proeves_IKKE_igen(f):
    """At prøve igen dér er at lave den samme fejl hurtigere."""
    d = _d(failure=f)
    assert d.action == R.STOP and d.rule == "uændret af at spørge igen"


@pytest.mark.parametrize("f", R.FARLIGT_AT_GENTAGE)
def test_ukendt_udfald_proeves_ALDRIG_igen(f):
    """Vi ved ikke om det virkede. Et genforsøg kunne udføre handlingen to
    gange, og det er værre end at fejle."""
    d = _d(failure=f)
    assert d.action == R.STOP and d.rule == "farligt at gentage"


def test_en_UKENDT_fejlklasse_proeves_ikke_igen():
    """En fejl vi ikke har taget stilling til, skal ikke arve «prøv igen» ved
    et tilfælde."""
    d = _d(failure="NOGET_HELT_NYT")
    assert d.action == R.STOP and "ukendt" in d.rule


# ── annullering slår alt ────────────────────────────────────────────────

@pytest.mark.parametrize("f", R.FORBIGAAENDE)
def test_annullering_stopper_ogsaa_en_forbigaaende_fejl(f):
    d = _d(failure=f, cancelled=True)
    assert d.action == R.STOP and d.rule == "brugeren annullerede"


def test_annullering_slaar_igennem_selv_med_fuldt_budget():
    d = _d(cancelled=True, budget=Budget(max_attempts=99), spent=Spent())
    assert d.action == R.STOP


# ── budgettet gælder HELE turen ─────────────────────────────────────────

def test_forsoegsloftet_stopper():
    d = _d(budget=Budget(max_attempts=3), spent=Spent(attempts=3))
    assert d.action == R.STOP and "3 forsøg" in d.reason


def test_UDBYDER_SKIFT_nulstiller_IKKE_forsoegene():
    """Spec en er skarp: «Provider failover does not reset them.» Et loft der
    nulstilles ved skift, findes ikke — det udsætter bare regningen."""
    s = Spent(attempts=3, failovers=1)
    d = _d(budget=Budget(max_attempts=3), spent=s, route_override="anden-udbyder")
    assert d.action == R.STOP


def test_loftet_for_udbyder_skift():
    d = _d(budget=Budget(max_failovers=2), spent=Spent(failovers=2))
    assert d.action == R.STOP and "udbyder-skift" in d.reason


def test_tidsloftet_stopper():
    d = _d(budget=Budget(max_wall_s=300), spent=Spent(wall_s=301))
    assert d.action == R.STOP and "tidsloftet" in d.reason


def test_tokenloftet_stopper():
    d = _d(budget=Budget(max_generated_tokens=1000), spent=Spent(generated_tokens=1000))
    assert d.action == R.STOP and "token-loftet" in d.reason


def test_prisloftet_stopper():
    d = _d(budget=Budget(max_cost_usd=1.0), spent=Spent(cost_usd=1.0))
    assert d.action == R.STOP and "pris-loftet" in d.reason


def test_et_loft_kan_ikke_AABNE_for_noget_der_ikke_skulle_proeves():
    """Rækkefølgen: det farlige afgøres FØR budgettet. Ellers ville et fuldt
    budget kunne få en AUTH-fejl til at se ud som «prøv igen»."""
    d = _d(failure=R.AUTH, budget=Budget(max_attempts=99), spent=Spent())
    assert d.action == R.STOP and d.rule != "budget udtømt"


def test_inden_for_budget_proeves_der_igen():
    d = _d(budget=Budget(max_attempts=5), spent=Spent(attempts=2, wall_s=10))
    assert d.action == R.RETRY and d.delay_s > 0


# ── ventetiden ──────────────────────────────────────────────────────────

def test_ventetiden_vokser():
    assert R.backoff(1) < R.backoff(3) < R.backoff(6)


def test_udbyderens_hint_VINDER():
    """Den ved bedre end os hvornår en rate limit går væk."""
    assert R.backoff(1, provider_hint_s=7.5) == 7.5


def test_men_hintet_klippes_saa_en_udbyder_ikke_kan_bede_os_vente_en_time():
    assert R.backoff(1, provider_hint_s=9999) == 30.0


def test_ventetiden_har_baade_gulv_og_loft():
    assert R.backoff(1) >= 0.5
    assert R.backoff(50) <= 30.0
    assert R.backoff(1, provider_hint_s=0.001) == 0.5


def test_hintet_naar_helt_ud_i_beslutningen():
    assert _d(failure=R.RATE_LIMIT, provider_hint_s=12).delay_s == 12


# ── beslutningen ÆNDRER ingenting ───────────────────────────────────────

def test_beslutningen_er_ren_og_deterministisk():
    b, s = Budget(), Spent(attempts=1)
    assert decide(failure=R.TIMEOUT, budget=b, spent=s) == \
           decide(failure=R.TIMEOUT, budget=b, spent=s)


def test_forbruget_roeres_ikke():
    """En beslutningsfunktion der også handler, kan ikke prøves uden at der
    sker noget — og så bliver den ikke prøvet grundigt."""
    import dataclasses
    s = Spent(attempts=2, wall_s=30, generated_tokens=500, cost_usd=0.2)
    foer = dataclasses.asdict(s)
    decide(failure=R.TIMEOUT, budget=Budget(), spent=s)
    assert dataclasses.asdict(s) == foer


def test_hver_beslutning_siger_HVILKEN_regel_der_afgjorde_den():
    for f in list(R.FORBIGAAENDE) + list(R.UAENDRET_AF_AT_SPOERGE_IGEN) + \
             list(R.FARLIGT_AT_GENTAGE) + ["NOGET_NYT"]:
        assert _d(failure=f).rule


# ── forbruget lægges sammen på tværs af udbydere ────────────────────────

def test_forbruget_akkumulerer():
    s = Spent()
    s = s.plus_attempt(wall_s=10, tokens=100, cost_usd=0.05)
    s = s.plus_attempt(wall_s=12, tokens=140, cost_usd=0.06, failover=True)
    assert s.attempts == 2 and s.failovers == 1
    assert s.wall_s == 22 and s.generated_tokens == 240
    assert round(s.cost_usd, 2) == 0.11


def test_plus_attempt_laver_et_NYT_forbrug():
    s = Spent(attempts=1)
    assert s.plus_attempt() is not s and s.attempts == 1


def test_en_tur_paa_tre_udbydere_deler_ET_budget():
    """Fem forsøg er fem forsøg, uanset hvor mange udbydere de fordeler sig på."""
    b = Budget(max_attempts=5, max_failovers=9)
    s = Spent()
    for i in range(5):
        assert decide(failure=R.TIMEOUT, budget=b, spent=s).action == R.RETRY
        s = s.plus_attempt(failover=(i % 2 == 0))
    assert decide(failure=R.TIMEOUT, budget=b, spent=s).action == R.STOP
