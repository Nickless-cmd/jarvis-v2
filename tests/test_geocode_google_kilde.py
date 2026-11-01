"""`geocode`/`reverse_geocode` kunne KUN OpenStreetMap — målt 1/11-2026.

MÅLT: nøglen `google_maps_api_key` findes (39 tegn), og Googles Geocoding API
svarer `OK` på både adresse og koordinat. Men `geocode()` gik direkte til
Nominatim, og `exec_geocode` sendte ikke engang en kilde videre. Kort sagt:
API'et var aktiveret og betalt, og koden rørte det aldrig.

Det er den fejlform hvor en mekanisme ser ud som om den virker — nøglen ligger
der, API'et svarer — men ingen kalder den. Testene her pinner at kilden nu KAN
vælges, og at standarden er uændret (OSM), så intet eksisterende flytter sig.

FÆLDEN DER IKKE MÅ ÅBNES: `source="google"` uden nøgle må IKKE stille falde
tilbage til OSM. Så ville man tro man fik Googles adressekvalitet og få
Nominatims — og opdage det først den dag de to er uenige.
"""
from __future__ import annotations

import pytest

from core.tools import geolocation_tools as geo

# ── Faste svar i de to kilders EGNE formater ──────────────────────────────────
_NOMINATIM_SVAR = [{
    "lat": "55.3445",
    "lon": "10.3270",
    "display_name": "Bellingevej 1, 5250 Odense, Danmark",
    "address": {"road": "Bellingevej", "city": "Odense", "postcode": "5250",
                "country": "Danmark"},
}]

_GOOGLE_SVAR = {
    "status": "OK",
    "results": [{
        "formatted_address": "Bellingevej 1, 5250 Odense, Denmark",
        "geometry": {"location": {"lat": 55.344574, "lng": 10.3270123}},
        "address_components": [
            {"long_name": "Bellingevej", "types": ["route"]},
            {"long_name": "Odense", "types": ["postal_town"]},
            {"long_name": "5250", "types": ["postal_code"]},
            {"long_name": "Denmark", "types": ["country"]},
        ],
    }],
}


class _FakeHttp:
    """Noterer hvilke URL'er der blev kaldt, og svarer i det rigtige format."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str, **kwargs):  # noqa: ANN003
        self.urls.append(url)
        if "googleapis.com" in url:
            return _GOOGLE_SVAR
        if "/reverse" in url:
            return _NOMINATIM_SVAR[0]
        return _NOMINATIM_SVAR


@pytest.fixture()
def fake_http(monkeypatch):
    fake = _FakeHttp()
    monkeypatch.setattr(geo, "_http_get_json", fake)
    monkeypatch.setattr(geo, "_throttle_nominatim", lambda: None)
    return fake


@pytest.fixture()
def med_noegle(monkeypatch):
    monkeypatch.setattr(geo, "_google_maps_key", lambda: "TEST-NOEGLE")


@pytest.fixture()
def uden_noegle(monkeypatch):
    monkeypatch.setattr(geo, "_google_maps_key", lambda: None)


# ── geocode ──────────────────────────────────────────────────────────────────
def test_geocode_standard_er_stadig_osm(fake_http) -> None:
    """Standarden må ikke flytte sig: intet eksisterende kald skal ændre kilde."""
    svar = geo.geocode("Bellingevej 1, Odense")
    assert svar["status"] == "ok"
    assert svar.get("source", "osm") == "osm"
    assert all("googleapis.com" not in u for u in fake_http.urls)


def test_geocode_google_bruger_google(fake_http, med_noegle) -> None:
    svar = geo.geocode("Bellingevej 1, Odense", source="google")
    assert svar["status"] == "ok"
    assert svar["source"] == "google"
    assert any("googleapis.com" in u for u in fake_http.urls)
    assert svar["lat"] == pytest.approx(55.344574)
    assert svar["lon"] == pytest.approx(10.3270123)


def test_geocode_google_uden_noegle_fejler_hoejt(fake_http, uden_noegle) -> None:
    """IKKE stille fallback til OSM — man skal vide hvad man fik."""
    svar = geo.geocode("Bellingevej 1, Odense", source="google")
    assert svar["status"] == "error"
    assert svar.get("needs_key") is True
    assert "google_maps_api_key" in svar["error"]
    assert all("nominatim" not in u for u in fake_http.urls)


def test_geocode_compare_rapporterer_afvigelse(fake_http, med_noegle) -> None:
    svar = geo.geocode("Bellingevej 1, Odense", source="compare")
    assert svar["status"] == "ok"
    assert svar["osm"]["status"] == "ok"
    assert svar["google"]["status"] == "ok"
    # Afvigelsen mellem de to kilder, i meter — ikke et ja/nej.
    assert "afvigelse_m" in svar
    assert svar["afvigelse_m"] >= 0


# ── reverse_geocode ──────────────────────────────────────────────────────────
def test_reverse_standard_er_stadig_osm(fake_http) -> None:
    svar = geo.reverse_geocode(55.3445, 10.3270)
    assert svar["status"] == "ok"
    assert svar.get("source", "osm") == "osm"
    assert svar["road"] == "Bellingevej"


def test_reverse_google_mapper_komponenterne(fake_http, med_noegle) -> None:
    svar = geo.reverse_geocode(55.344574, 10.3270123, source="google")
    assert svar["status"] == "ok"
    assert svar["source"] == "google"
    assert svar["road"] == "Bellingevej"
    assert svar["city"] == "Odense"
    assert svar["postcode"] == "5250"
    assert any("googleapis.com" in u for u in fake_http.urls)


def test_reverse_google_uden_noegle_fejler_hoejt(fake_http, uden_noegle) -> None:
    svar = geo.reverse_geocode(55.3445, 10.3270, source="google")
    assert svar["status"] == "error"
    assert svar.get("needs_key") is True
    assert all("nominatim" not in u for u in fake_http.urls)


# ── exec-wrapperne skal sende kilden videre ───────────────────────────────────
def test_exec_geocode_sender_source_videre(monkeypatch) -> None:
    fanget: dict[str, object] = {}

    def _fake(address: str, source: str = "osm") -> dict[str, object]:
        fanget["address"] = address
        fanget["source"] = source
        return {"status": "ok"}

    monkeypatch.setattr(geo, "geocode", _fake)
    geo.exec_geocode({"address": "Bellingevej 1", "source": "google"})
    assert fanget["source"] == "google"


def test_exec_reverse_sender_source_videre(monkeypatch) -> None:
    fanget: dict[str, object] = {}

    def _fake(lat: object, lon: object, source: str = "osm") -> dict[str, object]:
        fanget["source"] = source
        return {"status": "ok"}

    monkeypatch.setattr(geo, "reverse_geocode", _fake)
    geo.exec_reverse_geocode({"lat": 55.3, "lon": 10.3, "source": "google"})
    assert fanget["source"] == "google"


# ── Google-svaret skal normaliseres, ikke lækkes råt ─────────────────────────
def test_google_svar_normaliseres_til_samme_form(fake_http, med_noegle) -> None:
    """En kalder skal ikke behøve at kende to formater."""
    osm = geo.geocode("Bellingevej 1, Odense", source="osm")
    goog = geo.geocode("Bellingevej 1, Odense", source="google")
    assert set(osm) - {"source"} <= set(goog) | {"address_components"}
    assert {"status", "lat", "lon"} <= set(goog)
