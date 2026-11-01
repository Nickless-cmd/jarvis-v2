"""`profile="transit"` gav en BILRUTE — målt 1/11-2026.

`_PROFILE_MAP` kender kun driving/cycling/walking, og `_GOOGLE_TRAVEL_MODE`
kender kun DRIVE/BICYCLE/WALK. Så `transit` faldt tilbage til `driving` /
`DRIVE` — og svarede med bilafstand og billet-tid uden at sige det.

Målt mod den levende API: `transit` gav 46,45 km / 33,6 min, præcis samme tal
som `driving`. En togrejse Svendborg-Odense tager ~54 min og er ikke 46 km bil.

Det er den farlige form: et svar der SER rigtigt ud, men svarer på et andet
spørgsmål end det stillede. En bruger der spørger «hvornår er hun fremme med
toget» må ikke få billetiden uden at vide det.
"""

from __future__ import annotations

import core.tools.geolocation_tools as geo


def test_transit_er_ikke_driving_i_profilkortet() -> None:
    """transit skal mappes til sig selv — ikke arve driving."""
    assert geo._PROFILE_MAP.get("transit") == "transit", (
        "transit mangler i _PROFILE_MAP og falder derfor tilbage til driving"
    )


def test_transit_er_ikke_drive_i_google_travelmode() -> None:
    """Google skal have TRANSIT, ikke DRIVE, når der spørges til tog/bus."""
    assert geo._GOOGLE_TRAVEL_MODE.get("transit") == "TRANSIT", (
        "transit mangler i _GOOGLE_TRAVEL_MODE og falder derfor tilbage til DRIVE"
    )


def test_danske_navne_virker_ogsaa_for_tog() -> None:
    """«tog» og «offentlig» skal ramme transit, ligesom «bil» rammer driving."""
    for navn in ("tog", "offentlig", "bus"):
        assert geo._PROFILE_MAP.get(navn) == "transit", f"{navn!r} rammer ikke transit"


def test_ukendt_profil_falder_stadig_tilbage_til_driving() -> None:
    """Kontrakten: en ukendt profil må ikke fejle — den falder tilbage."""
    assert geo._PROFILE_MAP.get("svaevefly", "driving") == "driving"
    assert geo._GOOGLE_TRAVEL_MODE.get("svaevefly", "DRIVE") == "DRIVE"


def test_transit_uden_google_noegle_siger_det_hoejt(monkeypatch) -> None:
    """Uden nøgle skal transit-grenen svare ærligt, ikke stiltiende bil.

    OSM/OSRM har ingen transit-profil. Så når Google-kilden ikke kan bruges,
    må svaret ikke være en bilrute der ligner en togrejse.

    Koordinater i stedet for adresser: ellers geocoder _resolve_point mod
    Nominatim, og så måler testen netværket i stedet for grenen.
    """
    monkeypatch.setattr(geo, "_google_maps_key", lambda: "")
    r = geo.route_directions(from_=[55.0598, 10.6097], to=[55.3617, 10.3233], profile="transit")
    assert r.get("status") != "ok" or r.get("source") == "google", (
        f"transit uden Google-nøgle gav et 'ok'-svar fra {r.get('source')!r} — "
        "det er en bilrute der udgiver sig for at være en togrejse"
    )


def test_osm_afviser_transit_eksplicit() -> None:
    """_osm_route må ikke svare med en bilrute når den bliver bedt om tog.

    Uden denne gren ville OSRM få profilen 'transit', ikke kende den, og
    falde tilbage til noget der ligner en rute — uden at sige hvad den er.
    """
    r = geo._osm_route([55.0598, 10.6097], [55.3617, 10.3233], "transit")
    assert r.get("status") == "error", f"OSM svarede 'ok' på transit: {r}"
    assert r.get("source") == "osm"
    assert "google" in str(r.get("error", "")).lower(), (
        "fejlen skal pege på den kilde der KAN svare"
    )


def test_transit_omdirigeres_til_google_naar_kilden_er_osm(monkeypatch) -> None:
    """Standardkilden er 'osm' — men transit kan kun besvares af Google.

    Uden omdirigeringen ville et transit-kald uden ``source`` lande hos OSRM
    og få et 'error' (efter fixet) eller en bilrute (før). Kalderen skal ikke
    behøve at kende den begrænsning.
    """
    kaldt: dict[str, object] = {}

    def _falsk_google(from_: object, to: object, profile: str = "driving") -> dict[str, object]:
        kaldt["profile"] = profile
        return {"status": "ok", "source": "google", "profile": profile}

    monkeypatch.setattr(geo, "google_route", _falsk_google)
    r = geo.route_directions([55.0598, 10.6097], [55.3617, 10.3233], profile="transit")
    assert r.get("source") == "google", f"transit gik ikke til Google: {r}"
    assert kaldt.get("profile") == "transit", "profilen blev ikke sendt videre"


def test_driving_gaar_stadig_til_osm_som_standard(monkeypatch) -> None:
    """Kontrakten: kun transit omdirigeres. Bil må ikke ændre standardkilde."""
    kaldt: dict[str, object] = {}

    def _falsk_osm(from_: object, to: object, profile: str = "driving") -> dict[str, object]:
        kaldt["profile"] = profile
        return {"status": "ok", "source": "osm", "profile": profile}

    monkeypatch.setattr(geo, "_osm_route", _falsk_osm)
    r = geo.route_directions([55.0598, 10.6097], [55.3617, 10.3233], profile="driving")
    assert r.get("source") == "osm", f"driving blev omdirigeret væk fra OSM: {r}"
