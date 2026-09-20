"""Tests for app-release-vagten — push-vejen (20/9-2026).

Vagten er den eneste kilde til «der er en ny release» for desk-klienterne. Det
der skal holdes fast er derfor ikke at den kan hente noget — det er at den
læser GitHub-feedet rigtigt, at den springer fremmede tags over (repoet bærer
både ``jarvis-desktop-v*`` og gamle ``v0.1.x-poc``), og at den lægger eventet
på bussen med det navn klienten lytter efter.
"""
from __future__ import annotations

import apps.api.jarvis_api.routes.app_release as mod

# Samme form som det rigtige feed: nyeste først, og med et fremmed tag iblandt.
FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Release notes from jarvis-v2</title>
  <entry>
    <title>jarvis-desktop-v0.6.59</title>
    <updated>2026-09-20T17:07:00Z</updated>
    <link rel="alternate" href="https://github.com/Nickless-cmd/jarvis-v2/releases/tag/jarvis-desktop-v0.6.59"/>
  </entry>
  <entry>
    <title>v0.1.8-poc</title>
    <updated>2026-01-01T00:00:00Z</updated>
    <link rel="alternate" href="https://example.invalid/gammel"/>
  </entry>
</feed>
"""


def test_parser_finder_desk_tagget_og_springer_fremmede_over():
    data = mod._parse_atom(FEED)
    assert data is not None
    assert data["tag"] == "jarvis-desktop-v0.6.59"
    assert data["version"] == "0.6.59"
    assert data["url"].endswith("jarvis-desktop-v0.6.59")


def test_parser_taaler_uforstaaeligt_og_tomt_feed():
    assert mod._parse_atom("ikke xml overhovedet") is None
    # Gyldigt feed uden et eneste desk-tag → None, ikke en fejl.
    tomt = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    assert mod._parse_atom(tomt) is None


def test_state_filen_skrives_og_laeses_saa_baselinen_overlever_genstart(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # Uden fil: ingen baseline. Det er den tilstand der udsender et falsk
    # «ny release» ved genstart, hvis vagten ikke selv håndterer første gennemløb.
    assert mod._laes_sidste_tag() is None
    mod._skriv_sidste_tag("jarvis-desktop-v0.6.59")
    assert mod._laes_sidste_tag() == "jarvis-desktop-v0.6.59"


def test_udsend_lægger_eventet_på_bussen_med_klientens_navn(monkeypatch):
    from core.eventbus import bus as bus_mod

    kald: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        bus_mod.event_bus,
        "publish",
        lambda kind, payload=None, **kw: kald.append((kind, payload or {})),
    )

    mod._udsend(
        {
            "version": "0.6.59",
            "tag": "jarvis-desktop-v0.6.59",
            "url": "https://example.invalid/r",
            "published_at": "2026-09-20T17:07:00Z",
        }
    )

    assert len(kald) == 1
    kind, payload = kald[0]
    # Navnet skal matche KIND i apps/jarvis-desk/electron/appRelease.ts — ellers
    # lytter klienten forgæves, og fejlen er usynlig (der sker bare ingenting).
    assert kind == "app.release.available"
    assert payload["version"] == "0.6.59"


def test_release_eventet_gaar_gennem_den_rigtige_validering():
    """Regression 20/9-2026: push-vejen meldte aldrig en ny release.

    Testen ovenfor mocker ``event_bus.publish`` — og mockede dermed praecis det
    der var i stykker: ``Event.validate`` afviste familien ``app``, saa hvert
    publish kastede ValueError, og vagtens ``_udsend`` slugte den i en except.
    En mock af publish kan pr. konstruktion ikke se den fejl; den svarer bare
    «ja» til et kald der i virkeligheden ville raise.

    Familien stod heller ikke i ALLOWED_EVENT_FAMILIES, og state-filen blev
    skrevet alligevel — saa vagten SAa releasen, den kunne bare ikke sige det.

    Derfor denne: den roerer den aegte validering, uden mock.
    """
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES, Event

    assert "app" in ALLOWED_EVENT_FAMILIES, (
        "familien `app` mangler i ALLOWED_EVENT_FAMILIES — publish() raiser og "
        "fejlen sluges, saa klienterne faar aldrig besked om en ny release"
    )
    ev = Event.create("app.release.available", {"version": "0.6.61"})
    assert ev.family == "app"


def test_udsend_kaster_ikke_naar_bussen_er_nede(monkeypatch):
    from core.eventbus import bus as bus_mod

    def braender(*_a, **_kw):
        raise RuntimeError("bussen er nede")

    monkeypatch.setattr(bus_mod.event_bus, "publish", braender)
    # En fejl her maa ikke dræbe vagt-loekken — den skal bare logge og koere videre.
    mod._udsend({"version": "0.6.59"})
