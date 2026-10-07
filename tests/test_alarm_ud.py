"""Driftsalarmer skal gennem routeren — ikke direkte til telefonen.

Målt 7/10-2026: ti moduler kaldte `ntfy_gateway.send_notification()` direkte
og sprang `notification_router` over. Konsekvensen var at alarmer gik til en
**offentlig** ntfy-topic uden device-awareness, eskalering, kvittering eller
hensyn til Bjørns eget kanalvalg.

Testene her holder to ting: at helperen kalder routeren (og ikke gateway'en),
og at den ikke kaster når ejeren ikke kan findes — kalderne er daemons, og en
alarm der ikke kan leveres må ikke vælte den opgave der udløste den.
"""
from __future__ import annotations

import inspect

from core.services import alarm_ud


def test_helperen_importerer_ikke_ntfy_direkte():
    """Kilden læses som tekst: et lazy import i en funktion ville ikke ses i dir().

    Docstringen nævner `ntfy_gateway` med vilje (den forklarer hvorfor vejen
    blev skiftet), så kommentarer og docstrings strippes først — ellers ville
    testen fejle på sin egen begrundelse.
    """
    kilde = inspect.getsource(alarm_ud)
    kodelinjer = [
        linje for linje in kilde.splitlines()
        if linje.strip() and not linje.strip().startswith("#")
    ]
    # Fjern docstrings: alt mellem tre citationstegn.
    uden_doc = []
    inde = False
    for linje in kodelinjer:
        if linje.count('"""') == 1:
            inde = not inde
            continue
        if not inde:
            uden_doc.append(linje)
    kode = "\n".join(uden_doc)
    assert "ntfy_gateway" not in kode, (
        "alarmer skal gennem routeren — den direkte gateway sprang device-awareness over"
    )
    assert "send_notification" not in kode


def test_send_alert_gaar_gennem_routeren(monkeypatch):
    """Den skal kalde route_proactive_notification med de rigtige feltnavne."""
    kald: list[tuple] = []

    def falsk_route(uid, slags, payload, importance="normal", **kw):
        kald.append((uid, slags, payload, importance))
        return {"delivered": True, "channel": "mobile"}

    monkeypatch.setattr(
        "core.identity.owner_resolver.owner_user_id", lambda: "bjorn-1", raising=False)
    monkeypatch.setattr(
        "core.services.notification_router.route_proactive_notification", falsk_route)

    ok = alarm_ud.send_alert(titel="Test", tekst="noget gik galt")

    assert ok is True
    assert len(kald) == 1
    uid, slags, payload, importance = kald[0]
    assert uid == "bjorn-1"
    assert slags == "infra_security"
    # Routeren, desktop-koeen og FCM læser title/preview/body — ikke titel/tekst.
    assert payload["title"] == "Test"
    assert payload["body"] == "noget gik galt"
    assert payload["preview"] == "noget gik galt"
    assert importance == "high"


def test_send_alert_uden_ejer_kaster_ikke(monkeypatch):
    """Ingen ejer → False, ikke en undtagelse. Kalderne er daemons."""
    monkeypatch.setattr(
        "core.identity.owner_resolver.owner_user_id", lambda: None, raising=False)

    assert alarm_ud.send_alert(titel="Test", tekst="x") is False


def test_send_alert_ved_routerfejl_kaster_ikke(monkeypatch):
    """En brudt router må ikke vælte den opgave der udløste alarmen."""
    def eksploderer(*a, **kw):
        raise RuntimeError("router nede")

    monkeypatch.setattr(
        "core.identity.owner_resolver.owner_user_id", lambda: "bjorn-1", raising=False)
    monkeypatch.setattr(
        "core.services.notification_router.route_proactive_notification", eksploderer)

    assert alarm_ud.send_alert(titel="Test", tekst="x") is False


def test_ikke_leveret_giver_false(monkeypatch):
    """Quiet hours lægger i kø — det er ikke en fejl, men returværdien skal
    sige sandt at den ikke nåede frem."""
    monkeypatch.setattr(
        "core.identity.owner_resolver.owner_user_id", lambda: "bjorn-1", raising=False)
    monkeypatch.setattr(
        "core.services.notification_router.route_proactive_notification",
        lambda *a, **kw: {"delivered": False, "channel": "queued"})

    assert alarm_ud.send_alert(titel="Test", tekst="x") is False
