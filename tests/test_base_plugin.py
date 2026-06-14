from __future__ import annotations

import pytest


def _manifest(pid="discord-local", kind="channel", modes=None):
    from core.plugins.base_plugin import PluginManifest
    return PluginManifest(
        plugin_id=pid, name="Discord (lokal)", kind=kind,
        modes=modes or ["chat"], auth_fields=["bot_token", "server_id"],
        events=["message_received"], actions=["send_message"],
        description="Forbind til din egen Discord-server lokalt",
    )


def test_register_and_list(isolated_runtime) -> None:
    from core.plugins.base_plugin import register_plugin, available_plugins, clear_registry
    clear_registry()
    register_plugin(_manifest("gmail", kind="connector"))
    register_plugin(_manifest("discord-local", kind="channel"))
    ids = {m.plugin_id for m in available_plugins()}
    assert ids == {"gmail", "discord-local"}
    clear_registry()


def test_invalid_kind_rejected(isolated_runtime) -> None:
    from core.plugins.base_plugin import register_plugin
    with pytest.raises(ValueError):
        register_plugin(_manifest(kind="malware"))


def test_invalid_mode_rejected(isolated_runtime) -> None:
    from core.plugins.base_plugin import register_plugin
    with pytest.raises(ValueError):
        register_plugin(_manifest(modes=["chat", "godmode"]))


def test_manifest_has_no_secret_values(isolated_runtime) -> None:
    # Kontrakten beskriver auth_fields (navne), ALDRIG værdier (token er klient-side).
    m = _manifest()
    d = m.as_dict()
    assert d["auth_fields"] == ["bot_token", "server_id"]
    assert "token_value" not in d and "secret" not in d


def test_status_roundtrip(isolated_runtime) -> None:
    from core.plugins.base_plugin import set_status, get_status
    assert get_status("discord-local")["status"] == "offline"  # default
    set_status("discord-local", "connected", detail="#general")
    s = get_status("discord-local")
    assert s["status"] == "connected" and s["detail"] == "#general"


def test_base_plugin_contract(isolated_runtime) -> None:
    from core.plugins.base_plugin import BasePlugin

    class _Fake(BasePlugin):
        manifest = _manifest()
        def is_connected(self) -> bool:
            return True
        def requires_owner(self, action: str) -> bool:
            return action == "delete_server"

    p = _Fake()
    assert p.is_connected() is True
    assert p.requires_owner("delete_server") is True
    assert p.requires_owner("send_message") is False
