"""Google Places (New), Weather og Air Quality som kilder — målt 1/11-2026.

BAGGRUND. Bjørn aktiverede tre Google-API'er, og de svarer alle 200 mod hans
nøgle (målt 1/11-2026 11:42). Men INGEN kode kaldte dem: `nearby_search` gik
kun til Overpass, og der fandtes intet vejr- eller luftkvalitets-værktøj der
rørte Google. Det er samme fejlform som geocoding havde i morges — en mekanisme
der ser ud som om den virker, fordi nøglen ligger klar og API'et svarer pænt,
men hvor ingen kalder den.

KONTRAKTEN her:
  * `nearby_search(source='osm')` er UÆNDRET — standarden må ikke flytte sig.
  * `nearby_search(source='google')` bruger Places API (New).
  * `nearby_search(source='compare')` kører begge og rapporterer hvor mange
    steder de er enige om, så uenigheden bliver et tal og ikke en mavefornemmelse.
  * Google UDEN nøgle fejler HØJT — den falder ikke stille tilbage til OSM.
  * `google_weather` og `google_air_quality` findes og normaliserer til samme
    ud-form som resten af geo-familien.
"""

from __future__ import annotations

import pytest

from core.tools import geolocation_tools as geo


class _FakeHttp:
    """Fanger URL'er og svarer med forudindstillede payloads."""

    def __init__(self, svar: dict[str, object]) -> None:
        self.svar = svar
        self.kald: list[tuple[str, object]] = []

    def get(self, url: str, **_kw: object) -> object:
        self.kald.append(("GET", url))
        for noegle, vaerdi in self.svar.items():
            if noegle in url:
                return vaerdi
        raise AssertionError(f"uventet URL: {url}")

    def post(self, url: str, payload: object = None, headers: object = None, **_kw: object) -> object:
        self.kald.append(("POST", url))
        for noegle, vaerdi in self.svar.items():
            if noegle in url:
                return vaerdi
        raise AssertionError(f"uventet URL: {url}")


@pytest.fixture()
def med_noegle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(geo, "_google_maps_key", lambda: "test-noegle")


@pytest.fixture()
def uden_noegle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(geo, "_google_maps_key", lambda: None)


# ── nearby_search: standarden må ikke flytte sig ──────────────────────────────
def test_nearby_standard_er_stadig_osm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Uden source skal Overpass bruges — intet eksisterende kald ændrer adfærd."""
    kaldt: list[str] = []

    def _fake_osm(lat: float, lon: float, query: str, radius: int = 1500) -> dict[str, object]:
        kaldt.append("osm")
        return {"status": "ok", "count": 0, "results": []}

    monkeypatch.setattr(geo, "_osm_nearby", _fake_osm)
    geo.nearby_search(55.4, 10.3, "apotek")
    assert kaldt == ["osm"]


def test_nearby_google_bruger_places(monkeypatch: pytest.MonkeyPatch, med_noegle: None) -> None:
    """source='google' skal ramme Places (New) — ikke Overpass."""
    fake = _FakeHttp({
        "places.googleapis.com": {
            "places": [
                {"id": "abc", "displayName": {"text": "Svendborg Apotek"},
                 "location": {"latitude": 55.06, "longitude": 10.61}},
            ]
        }
    })
    monkeypatch.setattr(geo, "_http_post_json", fake.post)
    out = geo.nearby_search(55.06, 10.61, "apotek", source="google")
    assert out["status"] == "ok"
    assert out["source"] == "google"
    assert out["results"][0]["name"] == "Svendborg Apotek"
    assert any("places.googleapis.com" in u for _m, u in fake.kald)


def test_nearby_google_uden_noegle_fejler_hoejt(uden_noegle: None) -> None:
    """Uden nøgle må den IKKE falde stille tilbage til OSM."""
    out = geo.nearby_search(55.06, 10.61, "apotek", source="google")
    assert out["status"] == "error"
    assert out.get("needs_key") is True
    assert "osm" not in str(out.get("source") or "")


def test_nearby_compare_taeller_enighed(monkeypatch: pytest.MonkeyPatch, med_noegle: None) -> None:
    """compare skal give et TAL for hvor mange steder de to kilder deler."""
    monkeypatch.setattr(
        geo, "_osm_nearby",
        lambda lat, lon, query, radius=1500: {
            "status": "ok", "count": 2,
            "results": [{"name": "Svendborg Apotek"}, {"name": "Kun OSM"}],
        },
    )
    fake = _FakeHttp({
        "places.googleapis.com": {
            "places": [
                {"id": "a", "displayName": {"text": "Svendborg Apotek"},
                 "location": {"latitude": 55.06, "longitude": 10.61}},
                {"id": "b", "displayName": {"text": "Kun Google"},
                 "location": {"latitude": 55.07, "longitude": 10.62}},
            ]
        }
    })
    monkeypatch.setattr(geo, "_http_post_json", fake.post)
    out = geo.nearby_search(55.06, 10.61, "apotek", source="compare")
    assert out["status"] == "ok"
    assert out["source"] == "compare"
    assert out["fælles"] == 1
    assert out["kun_osm"] == 1
    assert out["kun_google"] == 1


# ── google_weather ────────────────────────────────────────────────────────────
def test_google_weather_normaliserer(monkeypatch: pytest.MonkeyPatch, med_noegle: None) -> None:
    fake = _FakeHttp({
        "weather.googleapis.com": {
            "timeZone": {"id": "Europe/Copenhagen"},
            "weatherCondition": {"description": {"text": "Overskyet"}, "type": "CLOUDY"},
            "temperature": {"degrees": 9.4, "unit": "CELSIUS"},
            "feelsLikeTemperature": {"degrees": 7.1},
            "wind": {"speed": {"value": 11.2}, "gust": {"value": 20.5}},
            "relativeHumidity": 94,
            "precipitation": {"probability": {"percent": 5}},
        }
    })
    monkeypatch.setattr(geo, "_http_get_json", fake.get)
    out = geo.google_weather(55.4, 10.3)
    assert out["status"] == "ok"
    assert out["source"] == "google"
    assert out["temp_c"] == 9.4
    assert out["feels_like_c"] == 7.1
    assert out["wind_ms"] == 11.2
    assert out["description"] == "Overskyet"


def test_google_weather_uden_noegle_fejler_hoejt(uden_noegle: None) -> None:
    out = geo.google_weather(55.4, 10.3)
    assert out["status"] == "error"
    assert out.get("needs_key") is True


# ── google_air_quality ────────────────────────────────────────────────────────
def test_google_air_quality_normaliserer(monkeypatch: pytest.MonkeyPatch, med_noegle: None) -> None:
    fake = _FakeHttp({
        "airquality.googleapis.com": {
            "indexes": [
                {"code": "uaqi", "displayName": "Universal AQI", "aqi": 78,
                 "category": "Moderate air quality", "dominantPollutant": "pm25"},
            ],
            "pollutants": [
                {"code": "pm25", "concentration": {"value": 12.5, "units": "MICROGRAMS_PER_CUBIC_METER"}},
            ],
        }
    })
    monkeypatch.setattr(geo, "_http_post_json", fake.post)
    out = geo.google_air_quality(55.4, 10.3)
    assert out["status"] == "ok"
    assert out["source"] == "google"
    assert out["aqi"] == 78
    assert out["kategori"] == "Moderate air quality"
    assert out["dominerende"] == "pm25"


def test_google_air_quality_uden_noegle_fejler_hoejt(uden_noegle: None) -> None:
    out = geo.google_air_quality(55.4, 10.3)
    assert out["status"] == "error"
    assert out.get("needs_key") is True


# ── exec-wrapperne skal sende source videre ───────────────────────────────────
def test_exec_nearby_sender_source_videre(monkeypatch: pytest.MonkeyPatch) -> None:
    fanget: dict[str, object] = {}

    def _fake(lat: object, lon: object, query: str, radius: int = 1500, source: str = "osm") -> dict[str, object]:
        fanget["source"] = source
        return {"status": "ok"}

    monkeypatch.setattr(geo, "nearby_search", _fake)
    geo.exec_nearby_search({"lat": 1, "lon": 2, "query": "x", "source": "google"})
    assert fanget["source"] == "google"


def test_exec_google_weather_og_air_quality_findes() -> None:
    assert callable(geo.exec_google_weather)
    assert callable(geo.exec_google_air_quality)
