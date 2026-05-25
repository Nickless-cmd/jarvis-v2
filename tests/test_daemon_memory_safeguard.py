from core.services import daemon_memory_safeguard as dms


def test_build_memory_safeguard_surface_is_read_only_projection():
    surface = dms.build_memory_safeguard_surface()

    assert surface["mode"] == "daemon-memory-safeguard"
    assert surface["authority"] == "event-derived-read-only"
    assert "summary" in surface
    assert "latest_missed_save" in surface
    assert "learning_markers" in surface
    assert "save_tools" in surface


def test_memory_safeguard_surface_registered_in_signal_router():
    from core.services.signal_surface_router import get_surface_names, read_surface

    assert "daemon_memory_safeguard" in get_surface_names()
    surface = read_surface("daemon_memory_safeguard")
    assert surface["mode"] == "daemon-memory-safeguard"
