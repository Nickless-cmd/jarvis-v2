"""Tests for geolocation_tools — mocker HTTP så vi ikke rammer eksterne API'er."""
import core.tools.geolocation_tools as g


def _stub_http(monkeypatch, payload):
    monkeypatch.setattr(g, "_throttle_nominatim", lambda: None)
    monkeypatch.setattr(g, "_http_get_json", lambda *a, **k: payload)


def test_geocode_ok(monkeypatch):
    _stub_http(monkeypatch, [{"lat": "55.86", "lon": "10.39", "display_name": "Svendborg"}])
    r = g.geocode("Svendborg")
    assert r["status"] == "ok" and r["lat"] == 55.86 and r["lon"] == 10.39


def test_geocode_no_match(monkeypatch):
    _stub_http(monkeypatch, [])
    assert g.geocode("xyzzy")["status"] == "error"


def test_geocode_empty_input():
    assert g.geocode("")["status"] == "error"


def test_reverse_geocode_ok(monkeypatch):
    _stub_http(monkeypatch, {"display_name": "Toftegårdsvej, Svendborg",
                             "address": {"road": "Toftegårdsvej", "city": "Svendborg",
                                         "postcode": "5700", "country": "Danmark"}})
    r = g.reverse_geocode(55.86, 10.39)
    assert r["status"] == "ok" and r["city"] == "Svendborg" and r["postcode"] == "5700"


def test_reverse_geocode_bad_coords():
    assert g.reverse_geocode("nope", None)["status"] == "error"


def test_route_directions_ok(monkeypatch):
    # _resolve_point får [lat,lon] direkte → ingen geocode; route-kald mockes.
    _stub_http(monkeypatch, {"routes": [{"distance": 45210, "duration": 2160,
                "legs": [{"steps": [{"name": "Toftegårdsvej", "maneuver": {"type": "depart"}}]}]}]})
    r = g.route_directions([55.06, 10.61], [55.4, 10.39], "driving")
    assert r["status"] == "ok" and r["distance_km"] == 45.21 and r["duration_min"] == 36.0
    assert r["steps"]


def test_route_directions_unresolvable():
    # tom streng → geocode kaldes ikke (tom), _resolve_point None
    assert g.route_directions("", [55.4, 10.39])["status"] == "error"


def test_nearby_search_ok(monkeypatch):
    _stub_http(monkeypatch, {"elements": [
        {"lat": 55.064, "lon": 10.616, "tags": {"name": "365discount", "shop": "supermarket"}},
        {"lat": 55.067, "lon": 10.608, "tags": {"name": "Spar", "shop": "supermarket"}},
    ]})
    r = g.nearby_search(55.06, 10.61, "supermarked", 2000)
    assert r["status"] == "ok" and r["count"] == 2
    # sorteret nærmest-først
    assert r["results"][0]["distance_m"] <= r["results"][1]["distance_m"]


def test_nearby_search_no_query():
    assert g.nearby_search(55.06, 10.61, "", 2000)["status"] == "error"


def test_geolocation_lookup_from_presence(monkeypatch):
    import core.services.device_presence as dp
    dp.reset()
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="away",
                   location={"lat": 55.86, "lon": 10.39, "label": "Toftegårdsvej, Svendborg",
                             "source": "gps", "precision": "precise"})
    r = g.geolocation_lookup("bjorn")
    assert r["status"] == "ok" and r["via"] == "presence" and "Svendborg" in r["label"]


def test_geolocation_lookup_off_no_ip(monkeypatch):
    import core.services.device_presence as dp
    dp.reset()
    monkeypatch.setattr(g, "_ip_location", lambda: None)
    r = g.geolocation_lookup("ghost")
    assert r["status"] == "ok" and r.get("available") is False


def test_exec_wrappers_route_args(monkeypatch):
    monkeypatch.setattr(g, "geocode", lambda a: {"status": "ok", "lat": 1.0, "lon": 2.0})
    assert g.exec_geocode({"address": "x"})["lat"] == 1.0
