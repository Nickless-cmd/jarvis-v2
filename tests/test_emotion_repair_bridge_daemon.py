from core.services import emotion_repair_bridge_daemon as erbd


def test_build_emotion_repair_bridge_surface_is_read_only_projection():
    surface = erbd.build_emotion_repair_bridge_surface()

    assert surface["mode"] == "emotion-repair-bridge-daemon"
    assert surface["authority"] == "db-derived-read-only"
    assert "summary" in surface
    assert "patterns" in surface
    assert "recent_attempts" in surface


def test_emotion_repair_bridge_surface_registered_in_signal_router():
    from core.services.signal_surface_router import get_surface_names, read_surface

    assert "emotion_repair_bridge" in get_surface_names()
    surface = read_surface("emotion_repair_bridge")
    assert surface["mode"] == "emotion-repair-bridge-daemon"
