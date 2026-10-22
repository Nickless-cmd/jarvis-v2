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


# ── Ærlighed om levering (målt 20/10-2026, fixet 22/10-2026) ─────────────────
# `send_alert` returnerede True for en tidskritisk medicin-påmindelse mens
# ntfy-cachen havde 0 poster: beskeden var havnet i webchat-FEEDEN, og
# `delivered=True` betød blot «en kanal accepterede den». For en alarm der skal
# vække nogen om natten er det en løgn — feeden kvitterer ikke.
#
# `require_push=True` kræver derfor en kanal der bekræftet når telefonen.
# MUTATION: fjern kanal-tjekket i `send_alert_resultat` → begge tests fejler.


def _router_svar(monkeypatch, svar):
    monkeypatch.setattr(
        "core.identity.owner_resolver.owner_user_id", lambda: "bjorn-1", raising=False)
    monkeypatch.setattr(
        "core.services.notification_router.route_proactive_notification",
        lambda *a, **kw: svar)


def test_require_push_afviser_webchat_feeden(monkeypatch):
    """Feed-levering er IKKE en push — den må ikke tælle som leveret."""
    _router_svar(monkeypatch, {"delivered": True, "channel": "auto"})

    assert alarm_ud.send_alert(titel="Test", tekst="x", require_push=True) is False


def test_require_push_afviser_desktop_koeen(monkeypatch):
    """Desktop-køen skriver til feeden; ingen telefon kvitterer."""
    _router_svar(monkeypatch, {"delivered": True, "channel": "desktop"})

    assert alarm_ud.send_alert(titel="Test", tekst="x", require_push=True) is False


def test_require_push_accepterer_mobile(monkeypatch):
    """mobile/push/ntfy er de kanaler der faktisk når telefonen."""
    _router_svar(monkeypatch, {"delivered": True, "channel": "mobile"})

    assert alarm_ud.send_alert(titel="Test", tekst="x", require_push=True) is True


def test_require_push_accepterer_ntfy(monkeypatch):
    _router_svar(monkeypatch, {"delivered": True, "channel": "ntfy"})

    assert alarm_ud.send_alert(titel="Test", tekst="x", require_push=True) is True


def test_uden_require_push_er_feed_levering_stadig_sand(monkeypatch):
    """Bagudkompatibilitet: 16 kaldere læser bool, og en feed-række ER levering
    for dem. Kontrakten må ikke ændre sig under dem."""
    _router_svar(monkeypatch, {"delivered": True, "channel": "auto"})

    assert alarm_ud.send_alert(titel="Test", tekst="x") is True


def test_resultatet_navngiver_kanalen_og_siger_om_telefonen_blev_naaet(monkeypatch):
    """Den ærlige form: hvad skete der, ikke bare om noget skete."""
    _router_svar(monkeypatch, {"delivered": True, "channel": "auto"})

    r = alarm_ud.send_alert_resultat(titel="Test", tekst="x")

    assert r["kanal"] == "auto"
    assert r["naaede_telefonen"] is False
    assert r["leveret"] is True
    assert "auto" in r["grund"]


def test_resultatet_siger_sandt_naar_telefonen_blev_naaet(monkeypatch):
    _router_svar(monkeypatch, {"delivered": True, "channel": "mobile"})

    r = alarm_ud.send_alert_resultat(titel="Test", tekst="x")

    assert r["naaede_telefonen"] is True
    assert r["kanal"] == "mobile"
