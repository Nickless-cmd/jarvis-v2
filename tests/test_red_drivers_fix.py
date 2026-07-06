"""Tre røde Central-drivere fikset 6. jul (efter Jarvis' rød-diagnose).

1. note_unauthorized: forventet rolle-deny (tool_not_permitted) = error (gult), ikke severe (rødt);
   ægte anomali forbliver severe. Signalet bærer role+run_id.
2. workspace health-guard: aldrig-udfyldt template/tom-bruger-stub flagges IKKE som overwrite.
"""
from __future__ import annotations

from unittest import mock


def test_tool_not_permitted_is_error_not_severe():
    """En member der korrekt blokeres fra et owner-tool er gaten der VIRKER → error, ikke severe."""
    import core.services.connections as conn
    captured = {}
    with mock.patch("core.runtime.db_central_incidents.record_central_incident",
                    side_effect=lambda **k: captured.update(k)), \
            mock.patch.object(conn, "_observe"):
        conn.note_unauthorized("uid-123", "sess-1", "tool:operator_bash", "tool_not_permitted",
                               role="member", run_id="run-9")
    assert captured["severity"] == "error"          # IKKE severe → farver ikke rød
    assert "uid-123" in captured["message"]          # ægte bruger, ikke bare rollen
    assert "member" in captured["message"]           # rollen som kontekst
    assert captured["run_id"] == "run-9"


def test_genuine_anomaly_stays_severe():
    """Identity-spoof / ukendt reason = ægte sikkerheds-anomali → forbliver severe (rødt)."""
    import core.services.connections as conn
    captured = {}
    with mock.patch("core.runtime.db_central_incidents.record_central_incident",
                    side_effect=lambda **k: captured.update(k)), \
            mock.patch.object(conn, "_observe"):
        conn.note_unauthorized("uid-x", "s", "identity:owner", "identity_spoof", role="guest")
    assert captured["severity"] == "severe"


def test_never_populated_stub_is_not_flagged(tmp_path):
    """En aldrig-udfyldt template/tom-bruger-fil (baseline < min) er IKKE en overwrite."""
    from core.identity import workspace_bootstrap as wb
    (tmp_path / "MEMORY.md").write_text("# stub\n", encoding="utf-8")  # ~7B
    # baseline siger den ALTID har været lille (136B) → aldrig substantiel
    warns = wb._check_workspace_file_health(tmp_path, "MEMORY.md", {"MEMORY.md": 136})
    assert not any(level == "critical" for level, _ in warns), warns


def test_real_collapse_from_substantial_is_critical(tmp_path):
    """En fil der VAR substantiel (60KB) og nu er kollapset til stub → CRITICAL (ægte overwrite)."""
    from core.identity import workspace_bootstrap as wb
    (tmp_path / "MEMORY.md").write_text("x", encoding="utf-8")  # 1B — kollapset
    warns = wb._check_workspace_file_health(tmp_path, "MEMORY.md", {"MEMORY.md": 60728})
    assert any(level == "critical" for level, _ in warns), warns
