"""Tests for workspace_bootstrap — især §16 .enc-aware seeding."""
from __future__ import annotations

import pytest


@pytest.fixture
def _member_env(isolated_runtime, tmp_path, monkeypatch):
    """Isolér users.json + WORKSPACES_DIR; registrér member 'mikkel'."""
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    ws_root = tmp_path / "workspaces"
    monkeypatch.setattr("core.identity.workspace_bootstrap.WORKSPACES_DIR", str(ws_root))
    from core.identity.users import add_user
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")
    return ws_root


def test_bootstrap_skips_reseed_over_enc(_member_env) -> None:
    """En krypteret MEMORY.md.enc må IKKE få en plaintext-stub oven på (§16)."""
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    ws = _member_env / "mikkel"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "MEMORY.md.enc").write_bytes(b"ciphertext")
    (ws / "USER.md.enc").write_bytes(b"ciphertext")

    bootstrap_user_workspace("mikkel", display_name="Mikkel")

    # Ingen plaintext-stub gen-sået oven på de krypterede filer
    assert not (ws / "MEMORY.md").exists()
    assert not (ws / "USER.md").exists()


def test_bootstrap_creates_stub_when_absent(_member_env, monkeypatch) -> None:
    """Uden eksisterende fil (plaintext eller .enc) skabes stub som normalt.

    2026-10-01: testen antog plaintext, men `JARVISX_ENCRYPT_WORKSPACES=1` er
    sat i driftsmiljøet, så member-filer skrives som `.enc`. Den var derfor grøn
    i CI (uden flaget) og rød i drift (med). Krypterings-tilstanden pinnes nu
    eksplicit; .enc-vejen — den der faktisk kører — har sin egen test nedenfor.
    """
    monkeypatch.delenv("JARVISX_ENCRYPT_WORKSPACES", raising=False)
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    bootstrap_user_workspace("mikkel", display_name="Mikkel")
    ws = _member_env / "mikkel"
    assert (ws / "MEMORY.md").exists()
    assert (ws / "USER.md").exists()


def test_bootstrap_skriver_krypteret_stub_naar_flaget_er_til(_member_env, monkeypatch) -> None:
    """Med ENCRYPT_ON_WRITE til skal stubbene opstå som .enc, ikke plaintext.

    Det er den vej der kører i drift, og som den gamle test fejlede på uden at
    sige hvorfor: den ledte efter `MEMORY.md` mens filen lå som `MEMORY.md.enc`.
    """
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    bootstrap_user_workspace("mikkel", display_name="Mikkel")
    ws = _member_env / "mikkel"
    assert (ws / "MEMORY.md.enc").exists()
    assert (ws / "USER.md.enc").exists()
    assert not (ws / "MEMORY.md").exists()


def test_generisk_bootstrap_gen_saar_ikke_plaintext_over_enc(_member_env) -> None:
    """Den GENERISKE bootstrap må ikke gen-så klartekst oven på en .enc-fil (§16).

    Målt 8/10-2026: `bootstrap_workspace` — den generiske vej, nået gennem
    `ensure_default_workspace()` fra ~20 steder i core/ — tjekkede kun
    `dest.exists()` og skrev med rå `shutil.copy2`. `bootstrap_user_workspace`
    (medlems-vejen) var allerede .enc-bevidst; denne var ikke.

    Konsekvensen stod i michelle/ og mikkel/: 10 døde klartekst-filer oven på
    deres krypterede profiler — bl.a. en USER.md med «Primary user: Bjørn» inde
    i et medlems workspace. Filen læses aldrig (læseren foretrækker .enc), men
    den ligger ukrypteret og peger på den forkerte person.

    Testen dækker hullet: den generiske vej havde ingen test, kun medlems-vejen.
    """
    from core.identity.workspace_bootstrap import bootstrap_workspace

    ws = _member_env / "mikkel"
    ws.mkdir(parents=True, exist_ok=True)
    # Et medlems workspace har sine filer som .enc — intet i klartekst.
    for navn in ("USER", "MEMORY", "SOUL", "IDENTITY", "MILESTONES", "STANDING_ORDERS"):
        (ws / f"{navn}.md.enc").write_bytes(b"ciphertext")

    res = bootstrap_workspace("mikkel")

    for navn in ("USER", "MEMORY", "SOUL", "IDENTITY", "MILESTONES", "STANDING_ORDERS"):
        assert not (ws / f"{navn}.md").exists(), (
            f"{navn}.md blev gen-sået i klartekst oven på {navn}.md.enc"
        )
    # Filen var ikke manglende — den var krypteret. Den skal meldes som EKSISTERENDE.
    assert "USER.md" in res.existing_files
    assert "USER.md" not in res.created_files


def test_generisk_bootstrap_opretter_stadig_manglende_filer(_member_env, monkeypatch) -> None:
    """Fixet må ikke gøre bootstrap til en no-op.

    En helt tom workspace skal stadig fyldes op fra templaten — ellers ville
    fixet være «ingen filer nogen steder» i stedet for «ingen stubbe oven på
    krypterede filer».
    """
    monkeypatch.delenv("JARVISX_ENCRYPT_WORKSPACES", raising=False)
    from core.identity.workspace_bootstrap import bootstrap_workspace

    res = bootstrap_workspace("mikkel")

    ws = _member_env / "mikkel"
    assert res.created_files, "bootstrap oprettede intet i en tom workspace"
    assert (ws / "SOUL.md").exists()
    assert (ws / "USER.md").exists()


# ── system-regeltekster følger templaten (side-e0deddd6da) ────────────────


def test_foraeldet_system_regeltekst_opdateres_fra_template(_member_env, monkeypatch) -> None:
    """En .enc der er bagud skal opdateres — det var hele defekten.

    Målt 9/10-2026: begge medlemmers .enc stod på 14. juni-versionen mens
    templaten var fra 1. oktober. VISIBLE_CHAT_RULES manglede honesty-reglerne.
    """
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    from core.services.workspace_crypto import read_text_for_path, write_text_for_path

    ws = _member_env / "mikkel"
    ws.mkdir(parents=True, exist_ok=True)
    # En forældet regeltekst — som den bootstrap skrev første gang.
    write_text_for_path(ws / "VISIBLE_CHAT_RULES.md", "# gammel version\n")

    bootstrap_user_workspace("mikkel", display_name="Mikkel")

    laest = read_text_for_path(ws / "VISIBLE_CHAT_RULES.md") or ""
    assert "gammel version" not in laest
    assert "Honesty of action" in laest, "templatens honesty-regler mangler stadig"


def test_memory_og_user_roeres_ikke_af_regeltekst_opdatering(_member_env, monkeypatch) -> None:
    """Medlemmets EGNE filer må aldrig overskrives — kun de tre system-filer."""
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    from core.services.workspace_crypto import read_text_for_path, write_text_for_path

    ws = _member_env / "mikkel"
    ws.mkdir(parents=True, exist_ok=True)
    write_text_for_path(ws / "MEMORY.md", "# Mikkels egne erindringer\n")
    write_text_for_path(ws / "USER.md", "# Mikkel\n\nHans egne ord.\n")

    bootstrap_user_workspace("mikkel", display_name="Mikkel")

    assert read_text_for_path(ws / "MEMORY.md") == "# Mikkels egne erindringer\n"
    assert "Hans egne ord." in (read_text_for_path(ws / "USER.md") or "")


def test_identisk_regeltekst_skrives_ikke_unodigt(_member_env, monkeypatch) -> None:
    """Er indholdet allerede templatens, skal filen ikke røres (mtime bevares)."""
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    from core.services.workspace_crypto import read_text_for_path, write_text_for_path

    ws = _member_env / "mikkel"
    ws.mkdir(parents=True, exist_ok=True)
    from core.identity.workspace_bootstrap import TEMPLATE_DIR
    tpl = (TEMPLATE_DIR / "VISIBLE_CHAT_RULES.md").read_text(encoding="utf-8")
    write_text_for_path(ws / "VISIBLE_CHAT_RULES.md", tpl)

    foer = (ws / "VISIBLE_CHAT_RULES.md.enc").stat().st_mtime_ns
    bootstrap_user_workspace("mikkel", display_name="Mikkel")
    efter = (ws / "VISIBLE_CHAT_RULES.md.enc").stat().st_mtime_ns

    assert foer == efter, "filen blev skrevet selvom indholdet var identisk"
    assert read_text_for_path(ws / "VISIBLE_CHAT_RULES.md") == tpl
