from __future__ import annotations


def test_system_cartographer_builds_broad_inventory() -> None:
    from core.services.system_cartographer import build_system_cartographer_surface

    surface = build_system_cartographer_surface()

    assert surface["mode"] == "system-cartographer-v1"
    assert surface["summary"]["services"] > 50
    assert surface["summary"]["daemons"] > 10
    assert surface["summary"]["edges"] > 0
    assert "observed_events" in surface["summary"]
    assert "observed_causal_edges" in surface["summary"]
    assert surface["causalRuntime"]["mode"] in {
        "causal-runtime-v1",
        "causal-runtime-unavailable",
    }
    assert "services" in surface["nodes"]
    assert "event_families" in surface["nodes"]


def test_system_cartographer_finds_dark_edges() -> None:
    from core.services.system_cartographer import build_system_cartographer_surface

    surface = build_system_cartographer_surface()

    assert isinstance(surface["darkEdges"], list)
    assert all("service" in item for item in surface["darkEdges"])
