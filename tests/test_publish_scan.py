"""Tilslutnings-test: publicerer vi til en familie der ikke findes?

Jarvis' meta-observation 6/9-2026, efter tre fund på to dage:

  · `tool_discovery.nudge` afvist af ALLOWED_EVENT_FAMILIES — skygge-målingen
    ville have vist nul i ugevis.
  · `pause_and_ask`-resultater aldrig parset i desk.
  · `threshold_proposed` beregnet gennem 656 beslutninger, aldrig anvendt.

«Noget i byggeprocessen lader nye stykker lande *næsten* tilsluttet.»

Kun den første klasse er statisk afgørbar — og til gengæld eksakt: `publish()`
kalder `Event.create()` som kalder `validate()`, så en ikke-registreret familie
raiser HVER gang, og kaldstederne har typisk et `except` der sluger det.

Testen fejler på NYE utilsluttede familier. De 65 kendte står i en frossen
baseline, så gælden kan skrumpe men ikke vokse.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.eventbus.publish_scan import scan_published_families, unregistered_families

_BASELINE = Path(__file__).resolve().parents[1] / "core/eventbus/unregistered_families.baseline.json"


def _kendt() -> set[str]:
    return set(json.loads(_BASELINE.read_text(encoding="utf-8"))["familier"])


def test_ingen_NYE_utilsluttede_familier():
    """En ny familie skal registreres i ALLOWED_EVENT_FAMILIES — ellers er
    eventet tavst, og det opdages først når nogen undrer sig over en tom graf."""
    nye = {f: s for f, s in unregistered_families().items() if f not in _kendt()}
    assert not nye, (
        "Ny event-familie publiceres men er ikke i ALLOWED_EVENT_FAMILIES — "
        "publish() raiser og fejlen sluges:\n"
        + "\n".join(f"  {f}: {steder[0]}" for f, steder in sorted(nye.items()))
        + "\n\nRet det i core/eventbus/events.py. Er familien PRIVAT (telemetri "
          "om hans eget indre), skal den også i PRIVATE_NO_EGRESS_ROUTES og "
          "PRIVATE_FAMILIES_EXCLUDED_M0 — invarianterne kræver alle tre."
    )


def test_baselinen_kan_kun_skrumpe():
    """Er en familie blevet registreret, skal den ud af baselinen.

    Ellers vokser listen til at dække fejl der for længst er rettet, og så
    beskytter den ikke længere — den skjuler bare."""
    stadig_ude = set(unregistered_families())
    overfloedige = _kendt() - stadig_ude
    assert not overfloedige, (
        "Disse familier er nu registreret og skal fjernes fra "
        f"unregistered_families.baseline.json: {sorted(overfloedige)}"
    )


def test_scanneren_finder_faktisk_noget():
    """En scanner der returnerer tomt ville få testene til at bestå på ingenting
    — samme fælde som den tomme logfil der næsten gav «ingen nye fejl»."""
    alle = scan_published_families()
    assert len(alle) > 100, f"kun {len(alle)} familier fundet — scanner den rigtige rod?"
    assert "runtime" in alle, "runtime.* publiceres overalt og SKAL findes"


def test_tool_discovery_er_tilsluttet_hele_vejen():
    """Regression på det konkrete fund der startede det hele."""
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES
    from core.services.eventbus_central_bridge import (
        FAMILY_ROUTES, PRIVATE_FAMILIES_EXCLUDED_M0, PRIVATE_NO_EGRESS_ROUTES,
    )
    assert "tool_discovery" in ALLOWED_EVENT_FAMILIES
    assert "tool_discovery" in PRIVATE_NO_EGRESS_ROUTES
    assert "tool_discovery" in PRIVATE_FAMILIES_EXCLUDED_M0
    assert "tool_discovery" not in FAMILY_ROUTES


def test_publish_raiser_faktisk_paa_ukendt_familie():
    """Hele testens præmis. Holder den ikke, beskytter den intet."""
    import pytest

    from core.eventbus.events import Event

    with pytest.raises(ValueError, match="Unsupported event family"):
        Event.create(kind="denne_familie_findes_ikke.noget")
    Event.create(kind="runtime.noget")  # kontrol: en tilladt familie går igennem


def test_scanneren_er_ikke_blind_for_ikke_ascii(tmp_path):
    """Første udgave brugte [a-zA-Z0-9_.{}] til navne-delen og var dermed blind
    for «hændelse». Min egen verifikations-prøve slap igennem, og testen
    bestod på ingenting. En scanner med et hul er værre end ingen scanner."""
    (tmp_path / "core").mkdir()
    (tmp_path / "apps").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "core" / "x.py").write_text(
        'event_bus.publish("æfamilie.hændelse", {})\n', encoding="utf-8"
    )
    fundet = scan_published_families(tmp_path)
    assert "æfamilie" not in fundet, "familie-delen er bevidst ASCII"
    (tmp_path / "core" / "y.py").write_text(
        'event_bus.publish("ny_familie.hændelse", {})\n', encoding="utf-8"
    )
    assert "ny_familie" in scan_published_families(tmp_path)
