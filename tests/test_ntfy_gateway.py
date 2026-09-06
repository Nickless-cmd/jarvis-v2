"""ntfy-porten — og Notification-hooken der kan stoppe en besked.

En notifikation kan ikke kaldes tilbage når den først er ude af huset. Derfor
fyrer hooken FØR afsendelsen: det er det eneste sted «block» betyder noget.
"""
from __future__ import annotations

import json

import pytest

from core.services import ntfy_gateway as ng


@pytest.fixture(autouse=True)
def _ingen_rigtig_afsendelse(monkeypatch):
    """Ingen test må sende en rigtig push-besked."""
    monkeypatch.setattr(ng, "_load_config", lambda: None, raising=False)


def _hooks(tmp_path, monkeypatch, konfiguration):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "hooks.json").write_text(json.dumps(konfiguration))


class TestNotificationHook:
    def test_block_stopper_beskeden(self, tmp_path, monkeypatch):
        _hooks(tmp_path, monkeypatch, {"hooks": {"Notification": [
            {"type": "command", "command": "echo for sent; exit 2"}]}})
        r = ng.send_notification("noget vigtigt")
        assert r["status"] == "blocked" and "for sent" in r["reason"]

    def test_uden_hooks_gaar_den_sin_normale_vej(self, tmp_path, monkeypatch):
        """Uden config skal porten opføre sig præcis som før."""
        _hooks(tmp_path, monkeypatch, {"hooks": {}})
        r = ng.send_notification("hej")
        assert r["status"] == "error" and r["reason"] == "ntfy-not-configured"

    def test_inject_haefter_kontekst_paa(self, tmp_path, monkeypatch):
        fanget = {}
        _hooks(tmp_path, monkeypatch, {"hooks": {"Notification": [
            {"type": "command", "command": "echo 'PS: batteriet er lavt'"}]}})

        def _fake_cfg():
            fanget["kaldt"] = True
            return None

        monkeypatch.setattr(ng, "_load_config", _fake_cfg, raising=False)
        ng.send_notification("hej")
        # Hooken må ikke have forhindret den normale vej.
        assert fanget.get("kaldt") is True

    def test_en_kastende_hook_stopper_ikke_beskeden(self, tmp_path, monkeypatch):
        """Et værn omkring notifikationer må aldrig gøre systemet stumt."""
        _hooks(tmp_path, monkeypatch, {"hooks": {"Notification": [
            {"type": "command", "command": "sleep 99", "timeout_s": 0.1}]}})
        r = ng.send_notification("hej")
        assert r["status"] == "error"  # nåede den normale vej


class TestPortenSelv:
    def test_uden_konfiguration_fejler_den_pænt(self):
        r = ng.send_notification("hej")
        assert r["status"] == "error" and "ntfy-not-configured" in r["reason"]
