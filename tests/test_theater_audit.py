from __future__ import annotations


def test_theater_audit_builds_surface() -> None:
    from core.services.theater_audit import build_theater_audit_surface

    surface = build_theater_audit_surface()

    assert surface["mode"] == "theater-audit-v1"
    assert "summary" in surface
    assert "findings" in surface
    assert "files" in surface
    assert surface["summary"]["findings"] >= 0
    assert surface["summary"]["high_risk"] >= 0
    assert surface["recommendedTheaterTask"] is None or (
        surface["recommendedTheaterTask"]["task_kind"] == "theater_refactor"
    )


def test_theater_audit_findings_are_ranked() -> None:
    from core.services.theater_audit import build_theater_audit_surface

    surface = build_theater_audit_surface()
    files = surface["files"]

    if files:
        assert files[0]["risk_score"] >= files[-1]["risk_score"]
        assert "path" in files[0]
        assert "priority" in files[0]
