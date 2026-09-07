"""Push-vækning — bank på telefonen når den sover.

Testene handler om de fire ting der kan gøre en vækning ubrugelig: at den er
synlig, at den vækker unødigt, at den venter i det uendelige, og at den
lyver om hvorvidt telefonen kom.
"""

from __future__ import annotations

import pytest

from core.services import phone_wake as W


def _presence(monkeypatch, klienter: dict) -> None:
    from core.services import bridge_presence
    monkeypatch.setattr(
        bridge_presence, "all_presence",
        lambda: {"u1": {"process": "api", "clients": klienter}},
    )


def test_telefonen_kendes_paa_hvad_den_kan(monkeypatch):
    """Ikke paa klientnavn — samme mekanik som routing og scope-port.

    Tre steder skal blive enige om hvad en telefon er; bruger de tre
    forskellige regler, opstaar der en tilstand hvor porten aabner for et
    vaerktoej routingen ikke kan levere.
    """
    from core.tools.phone_tools import PHONE_TOOL_NAMES

    _presence(monkeypatch, {"desk": {"capabilities": ["operator_bash"]}})
    assert W.telefon_er_forbundet("u1") is False

    _presence(monkeypatch, {"x": {"capabilities": [PHONE_TOOL_NAMES[0]]}})
    assert W.telefon_er_forbundet("u1") is True


def test_vaekningen_er_TAVS(monkeypatch):
    """Ingen title, ingen preview → fcm tilfoejer ingen notifikations-blok.

    Det er hele forskellen paa en vaekning og en besked: Bjoern maa ikke faa
    en notifikation hver gang Jarvis vil vide hvor telefonen er.
    """
    set_data: list[dict] = []
    monkeypatch.setattr("core.services.device_tokens.list_for_user", lambda uid: ["tok"])
    monkeypatch.setattr("core.services.fcm_gateway.send",
                        lambda t, d: set_data.append(d) or (True, "ok"))

    assert W._send_vaekning("u1") is True
    assert set_data == [{"kind": "bro_vaekning"}]
    assert "title" not in set_data[0] and "preview" not in set_data[0]

    # og fcm bygger saa faktisk en besked UDEN notifikations-blok
    from core.services.fcm_gateway import _build_message
    msg = _build_message("tok", set_data[0])["message"]
    assert "notification" not in msg
    assert msg["android"]["priority"] == "high"


def test_en_forbundet_telefon_vaekkes_ikke(monkeypatch):
    monkeypatch.setattr(W, "telefon_er_forbundet", lambda uid: True)
    monkeypatch.setattr(W, "_send_vaekning", lambda uid: pytest.fail("maatte ikke sende"))
    assert W.vaek_og_vent("u1") is True


def test_uden_device_token_fejler_den_stille(monkeypatch):
    """Ingen token = ingen vej derhen. Det er et nej, ikke en fejl."""
    monkeypatch.setattr("core.services.device_tokens.list_for_user", lambda uid: [])
    assert W._send_vaekning("u1") is False


def test_ventetiden_er_bundet(monkeypatch):
    """Android lukker baggrunds-handleren ned; venter vi laengere, venter vi
    paa noget der ikke findes laengere."""
    monkeypatch.setattr(W, "telefon_er_forbundet", lambda uid: False)
    monkeypatch.setattr(W, "_send_vaekning", lambda uid: True)
    monkeypatch.setattr(W, "POLL_S", 0.01)
    W._sidst_vaekket.clear()

    import time
    t0 = time.time()
    assert W.vaek_og_vent("u1", vent_s=1.0) is False
    assert time.time() - t0 < 3.0


def test_telefonen_der_KOM_giver_true(monkeypatch):
    svar = iter([False, False, True])
    monkeypatch.setattr(W, "telefon_er_forbundet", lambda uid: next(svar, True))
    monkeypatch.setattr(W, "_send_vaekning", lambda uid: True)
    monkeypatch.setattr(W, "POLL_S", 0.01)
    W._sidst_vaekket.clear()

    assert W.vaek_og_vent("u1", vent_s=2.0) is True


def test_to_kald_lige_efter_hinanden_vaekker_kun_een_gang(monkeypatch):
    """Hver vaekning er en FCM-levering og en app-opstart.

    Kalder Jarvis to telefon-vaerktoejer i samme tur, skal appen ikke startes
    to gange — den er allerede paa vej.
    """
    antal: list[int] = []
    monkeypatch.setattr(W, "telefon_er_forbundet", lambda uid: False)
    monkeypatch.setattr(W, "_send_vaekning", lambda uid: antal.append(1) or True)
    monkeypatch.setattr(W, "POLL_S", 0.01)
    W._sidst_vaekket.clear()

    W.vaek_og_vent("u1", vent_s=0.2)
    W.vaek_og_vent("u1", vent_s=0.2)
    assert len(antal) == 1


def test_tom_bruger_giver_false():
    assert W.vaek_og_vent("") is False
