"""Web-push-gateway: VAPID-læsning og de fire udfald (ok/invalid/no-vapid/unavailable)."""
from __future__ import annotations

import sys
import types


class _Svar:
    status_code = 410


def _fake_pywebpush(webpush_fn):
    fake = types.ModuleType("pywebpush")
    fake.webpush = webpush_fn
    sys.modules["pywebpush"] = fake
    return fake


def test_manglende_abonnement_er_invalid():
    from core.services import web_push_gateway as g
    assert g.send({}, {}) == (False, "invalid")
    assert g.send({"endpoint": "https://x", "p256dh": "", "auth": "a"}, {}) == (False, "invalid")


def test_uden_vapid_noegle_sendes_intet(monkeypatch):
    from core.services import web_push_gateway as g
    monkeypatch.setattr(g, "_key", lambda name: "")
    ok, code = g.send({"endpoint": "https://x", "p256dh": "P", "auth": "A"}, {"k": 1})
    assert (ok, code) == (False, "no-vapid")


def test_doedt_abonnement_giver_invalid(monkeypatch):
    """404/410 = abonnementet findes ikke længere → skal slettes, som FCM-stien."""
    from core.services import web_push_gateway as g
    monkeypatch.setattr(g, "_key", lambda name: "test-vapid-private-key-not-a-secret")

    def _kast(**_kw):
        fejl = Exception("gone")
        fejl.response = _Svar()
        raise fejl

    _fake_pywebpush(_kast)
    ok, code = g.send({"endpoint": "https://x", "p256dh": "P", "auth": "A"}, {})
    assert (ok, code) == (False, "invalid")


def test_send_lykkes_og_baerer_noeglerne(monkeypatch):
    from core.services import web_push_gateway as g
    monkeypatch.setattr(g, "_key", lambda name: "test-vapid-private-key-not-a-secret" if name == "vapid_private_key" else "")
    kaldt: dict = {}
    _fake_pywebpush(lambda **kw: kaldt.update(kw))

    ok, code = g.send({"endpoint": "https://x", "p256dh": "P", "auth": "A"}, {"k": 1})

    assert (ok, code) == (True, "ok")
    assert kaldt["subscription_info"]["endpoint"] == "https://x"
    assert kaldt["subscription_info"]["keys"] == {"p256dh": "P", "auth": "A"}
    assert kaldt["vapid_private_key"] == "test-vapid-private-key-not-a-secret"  # pragma: allowlist secret
    assert kaldt["vapid_claims"]["sub"].startswith("mailto:")
