"""Test af de udvidede nyheds-, valuta- og Wolfram-værktøjer (18/10-2026).

Bjørn: «det var nogen af dine aller første tools og er ikk gjort noget ved siden
din fødsel». De havde alle tre et hul der kunne måles på nøglen:

  ``get_news`` krævede en ``query`` og fejlede derfor på «hvad sker der i
  verden»; ``/v2/top-headlines?country=dk`` svarer 200 med NUL artikler.

  ``get_exchange_rate`` kunne kun «lige nu», og ``/historical`` + ``/convert``
  svarer 429 på denne plan — så konverteringen regnes lokalt.

  ``wolfram_query`` brugte kun Short Answers, som giver ÉT ord. ``/v2/query``
  virker på samme app_id og giver de rigtige sektioner.

Testene kører uden netværk: ``urlopen`` og ``_read_api_key`` er isoleret, så de
måler vores formning af data — ikke API'ernes oppetid. Det er præcis dér fejlene
kan gå stille hen: en parameter der aldrig bliver sendt, et beløb der ikke bliver
ganget, eller et pods-svar der ser rigtigt ud men mister teksten.
"""

from __future__ import annotations

import json

import pytest

from core.tools import simple_tools_web as web


class _FalskSvar:
    """Det minimum ``urlopen``-konteksten skal kunne: ``read()`` og ``with``."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> "_FalskSvar":
        return self

    def __exit__(self, *args) -> bool:
        return False


@pytest.fixture
def net(monkeypatch):
    """Isolér netværket. ``svar`` mapper et URL-fragment til det der returneres."""
    svar: dict[str, object] = {}
    kald: list[str] = []

    def _falsk_urlopen(req, timeout=None):
        url = getattr(req, "full_url", None) or str(req)
        kald.append(url)
        for fragment, vaerdi in svar.items():
            if fragment.startswith("_"):
                continue
            if fragment in url:
                if isinstance(vaerdi, Exception):
                    raise vaerdi
                if isinstance(vaerdi, bytes):
                    return _FalskSvar(vaerdi)
                return _FalskSvar(json.dumps(vaerdi).encode())
        raise AssertionError(f"uventet URL: {url}")

    monkeypatch.setattr(web.urllib_request, "urlopen", _falsk_urlopen)
    monkeypatch.setattr(web, "_read_api_key", lambda key: "test-noegle")
    svar["_kald"] = kald
    return svar


def _nyheder(antal: int = 2, total: int = 42) -> dict:
    return {
        "status": "ok",
        "totalResults": total,
        "articles": [
            {
                "title": f"Sag {i}",
                "source": {"name": "dr.dk"},
                "publishedAt": f"2026-10-1{i}T09:30:00Z",
                "description": "kort beskrivelse",
                "url": f"https://dr.dk/{i}",
            }
            for i in range(antal)
        ],
    }


# ── Nyheder ──────────────────────────────────────────────────────────────────


def test_news_uden_query_soeger_bredt_paa_dansk(net):
    """«Hvad sker der i verden» må ikke fejle — den skal give en bred søgning."""
    net["/v2/everything"] = _nyheder()

    r = web._exec_get_news({})

    assert r["status"] == "ok"
    assert r["query"] == "Danmark", "uden query skal der søges bredt"
    assert r["language"] == "da", "dansk er standard"
    url = net["_kald"][0]
    assert "q=Danmark" in url
    assert "language=da" in url


def test_news_sender_datointerval_og_sortering(net):
    """Datoafgrænsning var umulig før — den skal nå URL'en."""
    net["/v2/everything"] = _nyheder()

    r = web._exec_get_news(
        {"query": "valg", "from_date": "2026-10-15", "to_date": "2026-10-17", "sort_by": "relevancy"}
    )

    assert r["status"] == "ok"
    url = net["_kald"][0]
    assert "from=2026-10-15" in url
    assert "to=2026-10-17" in url
    assert "sortBy=relevancy" in url


def test_news_klipper_max_results_til_loftet_100(net):
    net["/v2/everything"] = _nyheder()

    web._exec_get_news({"query": "test", "max_results": 500})

    assert "pageSize=100" in net["_kald"][0], "NewsAPI tager maks 100"


def test_news_ugyldig_dato_sendes_ikke(net):
    """Et vrøvle-input må ikke sende et ugyldigt filter til API'et."""
    net["/v2/everything"] = _nyheder()

    web._exec_get_news({"query": "test", "from_date": "i går"})

    assert "from=" not in net["_kald"][0]


def test_news_returnerer_artikler_og_tekst(net):
    net["/v2/everything"] = _nyheder(antal=2, total=42)

    r = web._exec_get_news({"query": "test"})

    assert r["article_count"] == 2
    assert r["total_results"] == 42
    assert "Sag 0" in r["text"]
    assert r["articles"][0]["source"] == "dr.dk"


def test_news_api_fejl_bliver_en_fejl_ikke_et_tomt_svar(net):
    net["/v2/everything"] = {"status": "error", "message": "apiKeyInvalid"}

    r = web._exec_get_news({"query": "test"})

    assert r["status"] == "error"
    assert "apiKeyInvalid" in r["error"]


# ── Valuta ───────────────────────────────────────────────────────────────────


def _kurser() -> dict:
    return {
        "success": True,
        "timestamp": 1760000000,
        "source": "DKK",
        "quotes": {"DKKUSD": 0.15, "DKKEUR": 0.134, "DKKGBP": 0.113},
    }


def test_exchange_regner_beloeb_lokalt(net):
    """``/convert`` er 429 på planen — beløbet skal ganges lokalt i stedet."""
    net["/live"] = _kurser()

    r = web._exec_get_exchange_rate({"base": "DKK", "amount": 500})

    assert r["status"] == "ok"
    assert r["amount"] == 500.0
    assert r["converted"]["USD"] == pytest.approx(75.0)
    assert r["converted"]["EUR"] == pytest.approx(67.0)


def test_exchange_giver_omvendt_kurs(net):
    net["/live"] = _kurser()

    r = web._exec_get_exchange_rate({"base": "DKK", "targets": "USD"})

    assert r["inverse"]["USD"] == pytest.approx(1 / 0.15, rel=1e-6)


def test_exchange_fjerner_base_prefiks_og_sender_targets(net):
    net["/live"] = _kurser()

    r = web._exec_get_exchange_rate({"base": "DKK", "targets": "USD,EUR"})

    assert set(r["rates"]) == {"USD", "EUR", "GBP"}
    assert "currencies=USD,EUR" in net["_kald"][0]


def test_exchange_ugyldigt_beloeb_falder_tilbage_paa_1(net):
    net["/live"] = _kurser()

    r = web._exec_get_exchange_rate({"base": "DKK", "amount": "mange"})

    assert r["status"] == "ok"
    assert r["amount"] == 1.0


def test_exchange_api_fejl_bliver_en_fejl(net):
    net["/live"] = {"success": False, "error": {"info": "rate_limit_reached"}}

    r = web._exec_get_exchange_rate({"base": "DKK"})

    assert r["status"] == "error"
    assert "rate_limit_reached" in r["error"]


# ── Wolfram ──────────────────────────────────────────────────────────────────


def test_wolfram_short_giver_et_kort_svar(net):
    net["/v1/result"] = b"35"

    r = web._exec_wolfram_query({"query": "5*7"})

    assert r["status"] == "ok"
    assert r["mode"] == "short"
    assert r["answer"] == "35"


def test_wolfram_pods_udtraekker_plaintext_sektioner(net):
    """Pods skal give titel + linjer — ikke et raat JSON-dump."""
    net["/v2/query"] = {
        "queryresult": {
            "success": True,
            "pods": [
                {"title": "Result", "subpods": [{"plaintext": "5.9 million people"}]},
                {"title": "Demographics", "subpods": [{"plaintext": "world rank: 114th"}]},
                {"title": "Tom", "subpods": [{"plaintext": ""}]},
            ],
        }
    }

    r = web._exec_wolfram_query({"query": "population of Denmark", "mode": "pods"})

    assert r["status"] == "ok"
    assert r["mode"] == "pods"
    assert r["pod_count"] == 2, "tomme subpods skal ikke tælles med"
    assert r["pods"][0]["title"] == "Result"
    assert "5.9 million" in r["text"]
    assert "Demographics" in r["text"]


def test_wolfram_pods_success_false_er_en_fejl(net):
    """Wolfram svarer 200 med success=false — det må ikke ligne et gyldigt svar."""
    net["/v2/query"] = {
        "queryresult": {"success": False, "error": {"msg": "could not interpret"}}
    }

    r = web._exec_wolfram_query({"query": "asdfgh", "mode": "pods"})

    assert r["status"] == "error"
    assert "could not interpret" in r["error"]


def test_wolfram_ukendt_mode_falder_tilbage_paa_short(net):
    net["/v1/result"] = b"42"

    r = web._exec_wolfram_query({"query": "6*7", "mode": "tulipan"})

    assert r["mode"] == "short"
    assert r["answer"] == "42"


def test_wolfram_kraever_en_query(net):
    r = web._exec_wolfram_query({"query": "   "})

    assert r["status"] == "error"
    assert not net["_kald"], "et tomt input maa ikke give et netvaerkskald"
