"""Test af det udvidede vejr-værktøj (18/10-2026).

Bjørn: «det tool burde kunne mange flere ting». Før hentede ``get_weather``
udelukkende ``/data/2.5/weather`` — altså NÆRVÆRET — selv om skemaet lovede en
«short forecast». Nu dækker det nu, 3-timers prognose, døgn-opsummering og
luftkvalitet.

Testene kører uden netværk: ``_owm_get`` og ``_read_api_key`` er isoleret, så
de måler vores formning af data — ikke OpenWeatherMaps oppetid. Det er præcis
dér fejlene kan gå stille hen: et felt der hedder noget andet, en dagsbøtte der
lægger nat med dag, eller et svar der ser rigtigt ud men mangler prognosen.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.tools import simple_tools_web as web

# Stedets offset i testene: +2 timer (som dansk sommertid).
_OFFSET = 7200


def _epok(dag: int, time: int = 0, minut: int = 0, maaned: int = 10) -> int:
    """Epoch for et UTC-tidspunkt — læsbart i stedet for et magisk tal."""
    return int(datetime(2026, maaned, dag, time, minut, tzinfo=timezone.utc).timestamp())


def _nu_svar(**over):
    svar = {
        "coord": {"lat": 55.06, "lon": 10.61},
        "weather": [{"description": "skydække"}],
        "main": {"temp": 6.5, "feels_like": 2.5, "humidity": 82, "pressure": 1030},
        "wind": {"speed": 6.7, "gust": 12.6, "deg": 45},
        "clouds": {"all": 89},
        "visibility": 10000,
        "dt": _epok(18, 4),
        "timezone": _OFFSET,
        "sys": {"country": "DK", "sunrise": _epok(18, 5, 45), "sunset": _epok(18, 16)},
        "name": "Svendborg",
    }
    svar.update(over)
    return svar


def _punkt(dag: int, time: int, temp: float, beskrivelse: str, pop: float = 0.0, regn: float = 0.0):
    p = {
        "dt": _epok(dag, time),
        "main": {"temp": temp, "temp_min": temp, "temp_max": temp},
        "weather": [{"description": beskrivelse}],
        "wind": {"speed": 5.0, "gust": 9.0},
        "pop": pop,
        "clouds": {"all": 50},
        "visibility": 10000,
    }
    if regn:
        p["rain"] = {"3h": regn}
    return p


def _forecast_svar(punkter=None):
    return {
        "cod": "200",
        "cnt": len(punkter or []),
        "list": punkter if punkter is not None else [
            _punkt(18, 6, 6.0, "spredte skyer"),
            _punkt(18, 11, 9.0, "sol"),          # 13 lokal = dagens ansigt
            _punkt(18, 20, 7.0, "regn", pop=0.8, regn=1.2),
            _punkt(19, 11, 11.0, "let regn", pop=0.6, regn=0.4),
        ],
        "city": {"name": "Svendborg", "country": "DK", "timezone": _OFFSET},
    }


def _luft_svar(aqi: int = 2):
    return {
        "coord": {"lat": 55.06, "lon": 10.61},
        "list": [
            {
                "main": {"aqi": aqi},
                "components": {"co": 147.0, "no2": 2.0, "o3": 74.0, "pm2_5": 0.5, "pm10": 0.5},
                "dt": _epok(18, 4),
            }
        ],
    }


@pytest.fixture
def owm(monkeypatch):
    """Isolér netværket. Returnerer en kontrol der kan ændre svarene pr. sti."""
    svar = {
        "/data/2.5/weather": _nu_svar(),
        "/data/2.5/forecast": _forecast_svar(),
        "/data/2.5/air_pollution": _luft_svar(),
    }
    kald: list[tuple[str, dict]] = []

    def _falsk_get(path, params, api_key, timeout=12.0):
        kald.append((path, dict(params)))
        vaerdi = svar[path]
        return vaerdi() if callable(vaerdi) else vaerdi

    monkeypatch.setattr(web, "_owm_get", _falsk_get)
    monkeypatch.setattr(web, "_read_api_key", lambda key: "test-noegle")
    svar["_kald"] = kald
    return svar


def test_current_henter_kun_nu(owm):
    """mode='current' skal ikke betale for prognose- og luftkald."""
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "current"})

    assert r["status"] == "ok"
    assert "now" in r
    assert "hourly" not in r
    assert "daily" not in r
    assert "air" not in r
    stier = [k[0] for k in owm["_kald"]]
    assert stier == ["/data/2.5/weather"], f"uventede kald: {stier}"


def test_all_giver_nu_prognose_doegn_og_luft(owm):
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "all"})

    assert r["status"] == "ok"
    for noegle in ("now", "hourly", "daily", "air"):
        assert noegle in r, f"mangler {noegle}"
    stier = [k[0] for k in owm["_kald"]]
    assert "/data/2.5/forecast" in stier
    assert "/data/2.5/air_pollution" in stier


def test_nu_baerer_solopgang_sigtbarhed_og_vindstoed(owm):
    """Felterne der gør «nu» brugbart til mere end en temperatur."""
    nu = web._exec_get_weather({"city": "Svendborg, DK", "mode": "current"})["now"]

    assert nu["temp_c"] == 6.5
    assert nu["wind_gust_ms"] == 12.6
    assert nu["visibility_km"] == 10.0
    assert nu["pressure_hpa"] == 1030
    assert nu["clouds_pct"] == 89
    assert nu["sunrise"].startswith("2026-10-18T07:45")
    assert nu["daylight_h"] > 10.0


def test_hourly_respekterer_hours(owm):
    """hours=12 må kun give punkter inden for 12 timer — ikke hele prognosen."""
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "hourly", "hours": 12})

    assert len(r["hourly"]) == 2, r["hourly"]
    # Nu = 06 lokal (04 UTC). Punkterne er 06 og 11 UTC = 08 og 13 lokal.
    assert [p["time"][11:16] for p in r["hourly"]] == ["08:00", "13:00"]


def test_hourly_uden_graense_giver_hele_prognosen(owm):
    """hours=48 skal nå alle fire punkter — loftet må ikke skære for tidligt."""
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "hourly", "hours": 48})

    assert len(r["hourly"]) == 4, r["hourly"]


def test_hourly_baerer_nedboerssandsynlighed_og_maengde(owm):
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "hourly", "hours": 24})

    regn = [p for p in r["hourly"] if p["precip_mm"] > 0]
    assert regn, "ingen nedbørspunkter — pop/rain blev ikke læst"
    assert regn[0]["chance_pct"] == 80
    assert regn[0]["precip_mm"] == 1.2


def test_daily_aggregerer_min_max_og_nedboer(owm):
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "daily", "days": 2})

    assert len(r["daily"]) == 2
    dag1 = r["daily"][0]
    assert dag1["date"] == "2026-10-18"
    assert dag1["min_c"] == 6.0
    assert dag1["max_c"] == 9.0
    assert dag1["precip_mm"] == 1.2
    assert dag1["chance_pct"] == 80


def test_daily_vaelger_beskrivelsen_naer_middag(owm):
    """Dagens ansigt er kl. 13 — ikke nattens første punkt."""
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "daily", "days": 1})

    assert r["daily"][0]["description"] == "sol"


def test_bagudkompatible_topfelter_bestaar(owm):
    """Morgenbriefet og ældre læsere henter stadig description/temp_c herfra."""
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "current"})

    assert r["description"] == "skydække"
    assert r["temp_c"] == 6.5
    assert r["feels_like_c"] == 2.5
    assert r["humidity_pct"] == 82
    assert r["wind_ms"] == 6.7
    assert r["city"] == "Svendborg, DK"


def test_ukendt_by_giver_paen_fejl(owm):
    owm["/data/2.5/weather"] = {"_error": "/data/2.5/weather: HTTP Error 404: Not Found"}

    r = web._exec_get_weather({"city": "Zzzqwxnotacity"})

    assert r["status"] == "error"
    assert "404" in r["error"]


def test_forecast_fejl_braekker_ikke_nuet(owm):
    """Prognosen er en berigelse — dør den, skal nu stadig leveres."""
    owm["/data/2.5/forecast"] = {"_error": "/data/2.5/forecast: timeout"}

    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "all"})

    assert r["status"] == "ok"
    assert r["temp_c"] == 6.5
    assert "forecast_error" in r
    assert "hourly" not in r and "daily" not in r


def test_luftkvalitet_mapper_aqi_til_dansk(owm):
    r = web._exec_get_weather({"city": "Svendborg, DK", "mode": "all"})

    assert r["air"]["aqi"] == 2
    assert r["air"]["aqi_label"] == "rimelig"
    assert r["air"]["pm2_5"] == 0.5


def test_imperial_videresendes_til_api(owm):
    web._exec_get_weather({"city": "London, UK", "mode": "current", "units": "imperial"})

    sti, params = owm["_kald"][0]
    assert params["units"] == "imperial"


def test_ugyldige_args_falder_tilbage_paa_standard(owm):
    """Et vrøvle-mode eller ikke-tal må ikke kaste — værktøjet skal svare."""
    r = web._exec_get_weather({"mode": "tulipan", "hours": "abc", "days": 99})

    assert r["status"] == "ok"
    assert r["mode"] == "all"
    # days=99 klippes til loftet 5 — her findes kun to døgn med data.
    assert len(r["daily"]) == 2
    assert len(r["daily"]) <= 5, "loftet på 5 døgn skal holde"


def test_lang_dansk_er_standard(owm):
    web._exec_get_weather({"city": "Svendborg, DK", "mode": "current"})

    _, params = owm["_kald"][0]
    assert params["lang"] == "da", "beskrivelsen skal komme på dansk som standard"
