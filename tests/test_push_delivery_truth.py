"""«Leveret» skal betyde leveret — ikke «vi kaldte noget».

Fundet under en E2E-proeve 6/9-2026: approval-outboxen meldte
«delivered: 1» uden at nogen havde afsendt noget. To lag returnerede True
uden at se paa udfaldet:

    _route_or_blast:      notification_router.route_device_aware(...); return True
    _deliver_to_channel:  pd._push_to_user(...); return True

Konsekvensen er ikke kosmetisk: outboxen markerer en godkendelses-
notifikation som leveret og proever aldrig igen. En godkendelse der venter
paa Bjoern kan saaledes forsvinde i stilhed.
"""
from core.services import push_dispatcher as pd


def test_uden_enheder_er_leveret_FALSK(monkeypatch):
    monkeypatch.setattr("core.services.device_tokens.list_for_user", lambda uid: [])
    monkeypatch.setattr("core.services.notification_router.route_device_aware",
                        lambda *a, **k: None)

    class _S:
        device_awareness_enabled = True
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())

    assert pd._route_or_blast("u", {"kind": "x"}, "x") is False


def test_med_en_enhed_er_leveret_SANDT(monkeypatch):
    monkeypatch.setattr("core.services.device_tokens.list_for_user", lambda uid: ["tok"])
    monkeypatch.setattr("core.services.notification_router.route_device_aware",
                        lambda *a, **k: None)

    class _S:
        device_awareness_enabled = True
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())

    assert pd._route_or_blast("u", {"kind": "x"}, "x") is True


def test_kanal_der_fejler_melder_fejl(monkeypatch):
    """Ellers eskalerer routeren aldrig til naeste enhed."""
    from core.services import notification_router as nr
    monkeypatch.setattr(pd, "_push_to_user", lambda uid, d: False)
    assert nr._deliver_to_channel("u", "mobile", {"kind": "x"}, "x") is False


def test_kanal_der_lykkes_melder_succes(monkeypatch):
    from core.services import notification_router as nr
    monkeypatch.setattr(pd, "_push_to_user", lambda uid, d: True)
    assert nr._deliver_to_channel("u", "mobile", {"kind": "x"}, "x") is True


def test_push_to_user_uden_tokens_er_falsk(monkeypatch):
    monkeypatch.setattr("core.services.device_tokens.list_for_user", lambda uid: [])
    assert pd._push_to_user("u", {"kind": "x"}) is False
