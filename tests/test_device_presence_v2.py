from core.services import device_presence


def test_presence_updates_registered_token_separately_from_device_identity(monkeypatch):
    device_presence.reset()

    device_presence.record_ping(
        "u1",
        "mobile-install-1",
        "mobile",
        foreground=True,
        awake=True,
        network="away",
        interaction=True,
        push_token="fcm-token-1",
        device_name="Bjørns Pixel",
        active_session_id="s1",
        battery_saver=True,
    )

    snap = device_presence.debug_snapshot("u1")

    assert snap["devices"][0]["device_key"] == "mobile-insta"
    assert snap["devices"][0]["device_name"] == "Bjørns Pixel"
    assert snap["devices"][0]["active_session_id"] == "s1"
    assert snap["devices"][0]["battery_saver"] is True
