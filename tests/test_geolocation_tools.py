"""Tests for geolocation_tools — mocker HTTP så vi ikke rammer eksterne API'er."""
import pytest

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


def test_geolocation_lookup_maerker_ip_gaet(monkeypatch):
    """Et IP-opslag må ikke give sig ud for at være brugerens by (7/10-2026).

    På mobildata ligger operatørens NAT-udgang i København, mens Bjørn kan stå
    i Svendborg. Resultatet bærer nu en note der siger at stedet er et gæt.
    """
    import core.services.device_presence as dp
    dp.reset()
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="away",
                   location={"lat": 55.675941, "lon": 12.5655349,
                             "label": "Copenhagen, Region Hovedstaden",
                             "source": "ip", "precision": "city"})
    r = g.geolocation_lookup("bjorn")
    assert r["source"] == "ip"
    assert "note" in r and "IP" in r["note"]


def test_geolocation_lookup_off_no_ip(monkeypatch):
    import core.services.device_presence as dp
    dp.reset()
    monkeypatch.setattr(g, "_ip_location", lambda: None)
    r = g.geolocation_lookup("ghost")
    assert r["status"] == "ok" and r.get("available") is False


def test_exec_wrappers_route_args(monkeypatch):
    monkeypatch.setattr(g, "geocode", lambda a: {"status": "ok", "lat": 1.0, "lon": 2.0})
    assert g.exec_geocode({"address": "x"})["lat"] == 1.0


# ── Google Routes som valgfri kilde (31/10-2026) ──────────────────────────────
def test_google_route_uden_noegle_siger_det_hoejt(monkeypatch):
    """Uden nøgle skal værktøjet svare ærligt — ikke gætte og ikke røre nettet."""
    monkeypatch.setattr(g, "_google_maps_key", lambda: None)

    def _boom(*a, **k):
        raise AssertionError("Google må ikke kaldes uden nøgle")

    monkeypatch.setattr(g, "_http_post_json", _boom)
    r = g.google_route([55.06, 10.61], [55.4, 10.39], "driving")
    assert r["status"] == "error"
    assert r["needs_key"] is True
    assert "google_maps_api_key" in r["error"]


def test_google_route_bygger_request_rigtigt(monkeypatch):
    """Nøgle, field mask, travelMode og protobuf-varighed ('144s') skal stemme."""
    monkeypatch.setattr(g, "_google_maps_key", lambda: "test-noegle")
    fanget = {}

    def _fake_post(url, payload, headers=None, **k):
        fanget["url"] = url
        fanget["payload"] = payload
        fanget["headers"] = headers or {}
        return {"routes": [{
            "distanceMeters": 1680,
            "duration": "144s",
            "legs": [{"steps": [{"navigationInstruction": {"instructions": "Kør mod nord"}}]}],
        }]}

    monkeypatch.setattr(g, "_http_post_json", _fake_post)
    r = g.google_route([55.0606, 10.6002], [55.0591, 10.5657], "driving")

    assert fanget["url"] == g._GOOGLE_ROUTES
    assert fanget["headers"]["X-Goog-Api-Key"] == "test-noegle"
    assert "routes.distanceMeters" in fanget["headers"]["X-Goog-FieldMask"]
    assert fanget["payload"]["travelMode"] == "DRIVE"
    assert fanget["payload"]["origin"]["location"]["latLng"]["latitude"] == 55.0606

    assert r["status"] == "ok" and r["source"] == "google"
    assert r["distance_km"] == 1.68
    assert r["duration_min"] == 2.4          # '144s' → 144 s → 2,4 min
    assert r["steps"] == ["Kør mod nord"]


def test_google_route_cykel_bruger_bicycle(monkeypatch):
    monkeypatch.setattr(g, "_google_maps_key", lambda: "k")
    fanget = {}
    monkeypatch.setattr(g, "_http_post_json",
                        lambda u, p, h=None, **k: fanget.update(payload=p) or {"routes": []})
    g.google_route([55.0, 10.0], [55.1, 10.1], "cykel")
    assert fanget["payload"]["travelMode"] == "BICYCLE"


def test_compare_rapporterer_delta(monkeypatch):
    """De to kilder må ikke smelte sammen til ét svar — uenigheden skal frem."""
    monkeypatch.setattr(g, "_osm_route", lambda f, t, p: {
        "status": "ok", "source": "osm", "distance_km": 1.68, "duration_min": 3.3, "steps": []})
    monkeypatch.setattr(g, "google_route", lambda f, t, p: {
        "status": "ok", "source": "google", "distance_km": 1.9, "duration_min": 4.5, "steps": []})

    r = g.compare_routes([55.0, 10.0], [55.1, 10.1], "driving")
    assert r["status"] == "ok"
    assert r["distance_delta_km"] == 0.22
    assert r["duration_delta_min"] == 1.2
    assert r["sources_agree"] is False


def test_compare_er_aerlig_naar_en_kilde_fejler(monkeypatch):
    """Manglende nøgle må ikke ligne enighed — agree skal være None, ikke True."""
    monkeypatch.setattr(g, "_osm_route", lambda f, t, p: {
        "status": "ok", "source": "osm", "distance_km": 1.68, "duration_min": 3.3, "steps": []})
    monkeypatch.setattr(g, "_google_maps_key", lambda: None)
    r = g.compare_routes([55.0, 10.0], [55.1, 10.1], "driving")
    assert r["sources_agree"] is None
    assert r["google"]["needs_key"] is True
    assert "note" in r


def test_route_directions_source_osm_er_standard(monkeypatch):
    """Default er OSM (gratis, ingen nøgle) — også når source udelades helt."""
    monkeypatch.setattr(g, "_osm_route", lambda f, t, p: {"status": "ok", "source": "osm"})
    monkeypatch.setattr(g, "_google_maps_key", lambda: None)
    assert g.route_directions([55.0, 10.0], [55.1, 10.1])["source"] == "osm"
    google = g.route_directions([55.0, 10.0], [55.1, 10.1], "driving", "google")
    assert google["source"] == "google" and google["needs_key"] is True


def test_compare_bruger_relativ_taerskel_ikke_absolut(monkeypatch):
    """0.14 km er 9.1 % af en 1.54 km-rute — de to kilder er UENIGE.

    Den tidligere absolutte tærskel (delta < 0.2 km) kaldte dem "enige" og
    skjulte dermed den uenighed funktionen findes for at vise. Maalt 31/10-2026
    mod den levende rute Graaesvej -> McDonald's: osm 1.68 km / google 1.54 km.
    """
    monkeypatch.setattr(
        g, "_osm_route",
        lambda f, t, p: {"status": "ok", "distance_km": 1.68, "duration_min": 3.3},
    )
    monkeypatch.setattr(
        g, "google_route",
        lambda f, t, p: {"status": "ok", "distance_km": 1.54, "duration_min": 4.1},
    )
    r = g.compare_routes([55.0, 10.0], [55.1, 10.1], "driving")
    assert r["sources_agree"] is False, "9 % afvigelse skal ikke kaldes enighed"
    assert r["distance_delta_pct"] == pytest.approx(-9.1, abs=0.1)


def test_compare_korte_ruter_faar_absolut_gulv(monkeypatch):
    """På en 200 m-rute er 0.05 km = 25 % — men 0.05 km er under 100 m-gulvet.

    Uden gulvet ville en mikroskopisk rute blive kaldt uenig af støj.
    """
    monkeypatch.setattr(
        g, "_osm_route",
        lambda f, t, p: {"status": "ok", "distance_km": 0.20, "duration_min": 0.5},
    )
    monkeypatch.setattr(
        g, "google_route",
        lambda f, t, p: {"status": "ok", "distance_km": 0.15, "duration_min": 0.5},
    )
    r = g.compare_routes([55.0, 10.0], [55.1, 10.1], "walking")
    assert r["sources_agree"] is True
