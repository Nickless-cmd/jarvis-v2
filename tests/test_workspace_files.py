"""Tests for prompt_sections.workspace_files.

Dækker især den 2026-06-09-tilføjede stub-fallback til shared/.
"""
from __future__ import annotations

from pathlib import Path


def test_workspace_file_section_reads_rich_workspace(tmp_path) -> None:
    """Hvis workspace-versionen er rig, brug den direkte."""
    from core.services.prompt_sections.workspace_files import _workspace_file_section

    workspace = tmp_path / "ws"
    workspace.mkdir()
    rich_file = workspace / "SOUL.md"
    rich_file.write_text(
        "Line one of soul content that is meaningful.\n"
        "Line two with more substance.\n"
        "Line three.\n" + ("padding text " * 60),  # >500 bytes
        encoding="utf-8",
    )
    section = _workspace_file_section(
        rich_file, label="SOUL.md", max_lines=2, max_chars=200
    )
    assert section is not None
    assert "Line one of soul content" in section


def test_stub_workspace_falls_back_to_shared(tmp_path, monkeypatch) -> None:
    """2026-06-09 fix: stub workspace (<500 bytes) → læs fra shared."""
    from core.services.prompt_sections import workspace_files

    fake_home = tmp_path / "home"
    shared = fake_home / ".jarvis-v2" / "shared"
    shared.mkdir(parents=True)
    workspaces = fake_home / ".jarvis-v2" / "workspaces" / "bjorn"
    workspaces.mkdir(parents=True)

    # Stub i workspace, rig version i shared
    (workspaces / "SOUL.md").write_text("# stub only\n", encoding="utf-8")
    (shared / "SOUL.md").write_text(
        "Rich soul content line one.\n"
        "Rich soul content line two.\n" + ("padding " * 100),
        encoding="utf-8",
    )

    monkeypatch.setenv("HOME", str(fake_home))

    section = workspace_files._workspace_file_section(
        workspaces / "SOUL.md",
        label="SOUL.md",
        max_lines=3,
        max_chars=200,
    )
    assert section is not None
    assert "Rich soul content" in section


def test_no_fallback_when_workspace_is_rich(tmp_path, monkeypatch) -> None:
    """Hvis workspace er rig, fall-back inaktiv selv hvis shared findes."""
    from core.services.prompt_sections import workspace_files

    fake_home = tmp_path / "home"
    shared = fake_home / ".jarvis-v2" / "shared"
    shared.mkdir(parents=True)
    workspaces = fake_home / ".jarvis-v2" / "workspaces" / "bjorn"
    workspaces.mkdir(parents=True)

    workspace_content = "Workspace-specific identity line.\n" + ("text " * 200)
    (workspaces / "IDENTITY.md").write_text(workspace_content, encoding="utf-8")
    (shared / "IDENTITY.md").write_text("Shared version line.\n" + ("text " * 200), encoding="utf-8")

    monkeypatch.setenv("HOME", str(fake_home))

    section = workspace_files._workspace_file_section(
        workspaces / "IDENTITY.md",
        label="IDENTITY.md",
        max_lines=3,
        max_chars=200,
    )
    assert section is not None
    assert "Workspace-specific" in section
    assert "Shared version" not in section


def test_no_fallback_for_non_identity_file(tmp_path, monkeypatch) -> None:
    """Random.md er ikke i fallback-listen — stub-test gælder ikke."""
    from core.services.prompt_sections import workspace_files

    fake_home = tmp_path / "home"
    shared = fake_home / ".jarvis-v2" / "shared"
    shared.mkdir(parents=True)
    workspace = fake_home / ".jarvis-v2" / "workspaces" / "bjorn"
    workspace.mkdir(parents=True)

    # Stub workspace + rich shared, men file ikke i fallback-list
    (workspace / "RANDOM.md").write_text("# stub\n", encoding="utf-8")
    (shared / "RANDOM.md").write_text("Rich shared random content here.\n" * 20, encoding="utf-8")

    monkeypatch.setenv("HOME", str(fake_home))

    section = workspace_files._workspace_file_section(
        workspace / "RANDOM.md",
        label="RANDOM.md",
        max_lines=3,
        max_chars=200,
    )
    # Stub har "# stub" som er comment → no lines → None
    assert section is None


def test_resolve_with_shared_fallback_handles_missing_workspace(tmp_path, monkeypatch) -> None:
    """Workspace mangler men shared har den → fallback aktiveres."""
    from core.services.prompt_sections.workspace_files import _resolve_with_shared_fallback

    fake_home = tmp_path / "home"
    shared = fake_home / ".jarvis-v2" / "shared"
    shared.mkdir(parents=True)
    (shared / "MEMORY.md").write_text("a" * 1000, encoding="utf-8")
    monkeypatch.setenv("HOME", str(fake_home))

    fake_workspace_path = tmp_path / "non-existent" / "MEMORY.md"
    resolved = _resolve_with_shared_fallback(fake_workspace_path)
    assert resolved == shared / "MEMORY.md"


def test_resolve_with_shared_fallback_preserves_when_shared_missing(tmp_path, monkeypatch) -> None:
    """Hvis shared mangler, returnér original sti (ingen exception)."""
    from core.services.prompt_sections.workspace_files import _resolve_with_shared_fallback

    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))

    workspace_path = tmp_path / "ws" / "SOUL.md"
    resolved = _resolve_with_shared_fallback(workspace_path)
    assert resolved == workspace_path


def test_workspace_file_section_decrypts_member_enc(tmp_path, monkeypatch) -> None:
    """Encryption-aware: en member-fil gemt som .enc læses + dekrypteres
    transparent af _workspace_file_section (uafhængigt af ENCRYPT_ON_WRITE)."""
    from core.identity.users import add_user
    from core.services import workspace_crypto
    from core.services.prompt_sections.workspace_files import _workspace_file_section

    # Isolér users.json + headless KEK/DEK
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    import core.services.keyring_store as ks
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")

    mem = tmp_path / "workspaces" / "mikkel" / "MEMORY.md"
    mem.parent.mkdir(parents=True, exist_ok=True)
    # Skriv krypteret (flag on) → producerer .enc, fjerner plaintext
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    written = workspace_crypto.write_text_for_path(
        mem, "Mikkels hemmelige hukommelse som er rig nok til at undgå stub.\n" + ("x " * 300)
    )
    assert written.endswith(".enc") and not mem.exists()

    section = _workspace_file_section(mem, label="MEMORY.md", max_lines=2, max_chars=200)
    assert section is not None
    assert "Mikkels hemmelige hukommelse" in section
