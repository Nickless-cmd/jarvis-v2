"""Tests for prompt_relevance_backend — §16 encryption-aware VISIBLE_*-læsning."""
from __future__ import annotations

import pytest


def test_load_visible_relevance_plaintext(tmp_path) -> None:
    from core.services.prompt_relevance_backend import load_visible_relevance_prompt
    (tmp_path / "VISIBLE_RELEVANCE.md").write_text("relevans-regler", encoding="utf-8")
    assert load_visible_relevance_prompt(workspace_dir=tmp_path) == "relevans-regler"


def test_load_visible_memory_selection_missing(tmp_path, monkeypatch) -> None:
    # Ingen workspace- eller template-fil → None
    from core.services import prompt_relevance_backend as prb
    monkeypatch.setattr(prb, "TEMPLATE_DIR", tmp_path / "no_templates")
    assert prb.load_visible_memory_selection_prompt(workspace_dir=tmp_path) is None


def test_load_visible_relevance_member_enc(isolated_runtime, tmp_path, monkeypatch) -> None:
    """Member-krypteret VISIBLE_RELEVANCE.md læses transparent (§16)."""
    from core.identity.users import add_user
    from core.services import workspace_crypto
    from core.services.prompt_relevance_backend import load_visible_relevance_prompt
    import core.services.keyring_store as ks

    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")

    ws = tmp_path / "workspaces" / "mikkel"
    ws.mkdir(parents=True, exist_ok=True)
    workspace_crypto.write_text_for_path(ws / "VISIBLE_RELEVANCE.md", "mikkels regler")
    assert (ws / "VISIBLE_RELEVANCE.md.enc").exists()
    assert load_visible_relevance_prompt(workspace_dir=ws) == "mikkels regler"
