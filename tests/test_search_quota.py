"""Vagt: kvote-tælleren skal VARSLE før vi rammer loftet — og aldrig blokere.

BAGGRUND (målt 18/10-2026). Søgekæden havde intet forbrugsregnskab: Tavily
198/1000, SerpAPI 43/250, Exa uden kvote-endpoint. SerpAPIs loft er 10×
mindre end Tavilys, og en udtømt kvote blev først opdaget da kæden fejlede.

Det der gør vagten værd at have er ikke at den tæller — det er at den fyrer
FØR væggen, og at den tier når der ikke er noget at sige. Derfor tester vi
begge sider: at varselet kommer ved loftet, og at det IKKE kommer ved 79 %.
"""
from __future__ import annotations

import json

import pytest

from core.services import search_quota as q


@pytest.fixture()
def state(monkeypatch):
    """In-memory state så testene hverken rammer DB eller netværk."""
    lager: dict[str, object] = {}

    def _laes(key, default=None):
        return lager.get(key, default)

    def _skriv(key, vaerdi):
        lager[key] = vaerdi

    monkeypatch.setattr(q, "_laes", _laes)
    monkeypatch.setattr(q, "_skriv", _skriv)
    return lager


@pytest.fixture()
def ingen_net(monkeypatch):
    """Ingen test må ramme et rigtigt API — kvoten skal være mocket."""
    def _boom(*_a, **_k):
        raise AssertionError("testen må ikke kalde netværket")
    monkeypatch.setattr(q, "_http_json", _boom)


# ------------------------------------------------------- parsing af live


def test_tavily_laeses_fra_usage_endpoint(monkeypatch, state):
    monkeypatch.setattr(q, "_api_key", lambda _n: "tk_test")
    monkeypatch.setattr(q, "_http_json", lambda *_a, **_k: {
        "account": {"current_plan": "Researcher", "plan_usage": 198,
                    "plan_limit": 1000}
    })
    data = q._tavily_live()
    assert data == {"brugt": 198, "graense": 1000, "plan": "Researcher"}


def test_serpapi_laeses_fra_account_endpoint(monkeypatch, state):
    monkeypatch.setattr(q, "_api_key", lambda _n: "sk_test")
    monkeypatch.setattr(q, "_http_json", lambda *_a, **_k: {
        "plan_name": "Free Plan", "this_month_usage": 43, "searches_per_month": 250
    })
    data = q._serpapi_live()
    assert data == {"brugt": 43, "graense": 250, "plan": "Free Plan"}


def test_live_kvote_uden_graense_giver_ukendt(monkeypatch, state):
    """`plan_limit: null` = ubegrænset plan → ingen kvote at varsle imod."""
    monkeypatch.setattr(q, "_api_key", lambda _n: "tk_test")
    monkeypatch.setattr(q, "_http_json", lambda *_a, **_k: {
        "account": {"plan_usage": 12, "plan_limit": None}
    })
    assert q._tavily_live() is None


def test_uden_noegle_svares_none_uden_netvaerkskald(monkeypatch, state):
    """Uden nøgle findes ingen kvote at læse — og der må ikke gættes.

    Testen beviser to ting på én gang: at svaret er `None` (ukendt, ikke nul),
    og at der ikke blev sendt et request afsted for at finde ud af det.
    """
    kaldt: list[str] = []

    def _ingen_net(url, **_k):
        kaldt.append(url)
        raise AssertionError("uden nøgle må der ikke kaldes netværk")

    monkeypatch.setattr(q, "_api_key", lambda _n: "")
    monkeypatch.setattr(q, "_http_json", _ingen_net)

    assert q._tavily_live() is None
    assert q._serpapi_live() is None
    assert kaldt == []


# --------------------------------------------------- lokal tælling (Exa)


def test_exa_taelles_lokalt_og_nulstilles_pr_dag(state):
    """Exa er IP-limitet pr. DØGN — ikke på et månedskredit (målt 19/10-2026).

    Månedsnøglen undervurderede forbruget med op til 30× og kunne derfor
    aldrig fyre varselet før væggen var der.
    """
    q.noter_kald("exa", 3)
    s = q.kvote_status("exa", brug_cache=False)
    assert s["brugt"] == 3
    assert s["kilde"] == "lokal"
    assert any(":exa" in k for k in state)
    noegle = next(k for k in state if ":exa" in k)
    assert q._periode_noegle("exa") in noegle


def test_maanedlige_providere_taelles_stadig_pr_maaned(state):
    """SerpAPI og Tavily ER kreditlofter pr. måned — de må ikke skifte periode."""
    q.noter_kald("serpapi", 2)
    noegle = next(k for k in state if ":serpapi" in k)
    assert q._maaned() in noegle
    assert q._periode_noegle("serpapi") == q._maaned()


# ------------------------------------------------- kalibrering via 429


def test_kort_retry_after_er_qps_og_kalibrerer_intet(state):
    """Retry-After: 1 er QPS-vinduet — nulstilles straks, siger intet om kvoten."""
    q.noter_kald("exa", 10)
    assert q.noter_429("exa", 1.0) is False
    assert f"{q._STATE_PREFIX}:maalt_graense:exa" not in state


def test_langt_retry_after_kalibrerer_graensen_til_det_maalte(state):
    """Rammes forbrugsloftet, ER forbruget pr. definition grænsen."""
    q.noter_kald("exa", 47)
    assert q.noter_429("exa", 3600.0) is True
    assert state[f"{q._STATE_PREFIX}:maalt_graense:exa"] == 47
    s = q.kvote_status("exa", brug_cache=False)
    assert s["graense"] == 47
    assert "målt" in s["plan"]


def test_kalibreringen_rykker_kun_ned_ad(state):
    """Et senere 429 ved højere forbrug må ikke hæve grænsen igen."""
    q.noter_kald("exa", 47)
    q.noter_429("exa", 3600.0)
    q.noter_kald("exa", 40)
    q.noter_429("exa", 3600.0)
    assert state[f"{q._STATE_PREFIX}:maalt_graense:exa"] == 47


def test_429_uden_retry_after_kalibrerer_intet(state):
    """Uden Retry-After kan vi ikke skelne QPS fra forbrug — så vi rører intet."""
    q.noter_kald("exa", 10)
    assert q.noter_429("exa", None) is False
    assert f"{q._STATE_PREFIX}:maalt_graense:exa" not in state


def test_ukendt_provider_taelles_ikke(state):
    q.noter_kald("finnes-ikke")
    assert not state


# --------------------------------------------------------- loftvarsling


def test_loft_fyrer_ved_80_procent(state):
    s = q._form({"brugt": 200, "graense": 250}, "serpapi", kilde="live")
    assert s["over_loft"] is True
    assert s["tilbage"] == 50


def test_loft_fyrer_ikke_ved_79_procent(state):
    s = q._form({"brugt": 197, "graense": 250}, "serpapi", kilde="live")
    assert s["over_loft"] is False


def test_varsel_sendes_kun_en_gang(state, monkeypatch):
    """Cooldown: ellers fyrer den ved HVERT søgekald, og så ignoreres den."""
    sendt: list[str] = []
    monkeypatch.setitem(__import__("sys").modules, "core.services.notifikationer",
                        type("M", (), {"opret": staticmethod(
                            lambda **kw: sendt.append(kw.get("titel", "")))}))
    monkeypatch.setitem(__import__("sys").modules, "core.services.ntfy_gateway",
                        type("M", (), {"send_notification": staticmethod(
                            lambda *a, **k: {"status": "ok"})}))

    s = q._form({"brugt": 210, "graense": 250}, "serpapi", kilde="live")
    assert q.varsle_hvis_over_loft(s) is True
    assert q.varsle_hvis_over_loft(s) is False   # cooldown
    assert len(sendt) == 1


def test_varsel_tier_nar_der_ikke_er_noget_at_sige(state, monkeypatch):
    kaldt: list[str] = []
    monkeypatch.setitem(__import__("sys").modules, "core.services.notifikationer",
                        type("M", (), {"opret": staticmethod(
                            lambda **kw: kaldt.append("x"))}))
    s = q._form({"brugt": 10, "graense": 250}, "serpapi", kilde="live")
    assert q.varsle_hvis_over_loft(s) is False
    assert kaldt == []


# --------------------------------------------------------- prioritering


def _mock_status(monkeypatch, per_provider: dict[str, dict]):
    monkeypatch.setattr(q, "alle_status", lambda **_k: per_provider)


def test_foretrukken_vaelges_nar_den_har_plads(monkeypatch, state):
    _mock_status(monkeypatch, {
        "exa": {"over_loft": False}, "serpapi": {"over_loft": False},
        "tavily": {"over_loft": False},
    })
    navn, _ = q.bedste_provider("exa")
    assert navn == "exa"


def test_skifter_til_naestbedste_nar_exa_naermer_sig_loftet(monkeypatch, state):
    """Kvalitetsrækkefølgen holdes: serpapi (50 %) før tavily (20 %)."""
    _mock_status(monkeypatch, {
        "exa": {"over_loft": True}, "serpapi": {"over_loft": False},
        "tavily": {"over_loft": False},
    })
    navn, _ = q.bedste_provider("exa")
    assert navn == "serpapi"


def test_alle_over_loft_giver_none_men_blokerer_ikke(monkeypatch, state):
    """`None` betyder «prøv alligevel» — over loft er ikke det samme som nede."""
    _mock_status(monkeypatch, {
        "exa": {"over_loft": True}, "serpapi": {"over_loft": True},
        "tavily": {"over_loft": True},
    })
    navn, _ = q.bedste_provider("exa")
    assert navn is None


# ------------------------------------------------------------- fail-open


def test_ukendt_kvote_blokerer_ikke(monkeypatch, state):
    """Kan kvoten ikke læses, antages der plads. En vagt der blokerer på
    blindhed er værre end ingen vagt."""
    monkeypatch.setattr(q, "_LIVE", {"exa": lambda: None, "serpapi": lambda: None,
                                     "tavily": lambda: None})
    for p in q.PROVIDERS:
        s = q.kvote_status(p, brug_cache=False)
        assert s["kilde"] == "ukendt"
        assert s["over_loft"] is False
    navn, _ = q.bedste_provider("exa")
    assert navn == "exa"


def test_live_kvote_caches_sa_vi_ikke_spammer_provideren(monkeypatch, state):
    kald: list[int] = []

    def _taeller():
        kald.append(1)
        return {"brugt": 5, "graense": 100, "plan": "test"}

    monkeypatch.setattr(q, "_LIVE", {"exa": lambda: None, "serpapi": _taeller,
                                     "tavily": lambda: None})
    q.kvote_status("serpapi")
    q.kvote_status("serpapi")
    assert len(kald) == 1  # andet kald ramte cachen


def test_rapport_naevner_hver_provider(monkeypatch, state):
    monkeypatch.setattr(q, "_LIVE", {
        "exa": lambda: {"brugt": 10, "graense": 2500, "plan": "gratis"},
        "serpapi": lambda: {"brugt": 43, "graense": 250, "plan": "Free"},
        "tavily": lambda: {"brugt": 198, "graense": 1000, "plan": "Researcher"},
    })
    tekst = q.rapport()
    for navn in q.PROVIDERS:
        assert navn in tekst
