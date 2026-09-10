"""Tests for de udskilte fil-tool executors + encryption-aware I/O-helpers."""
from __future__ import annotations

import os

import pytest


def test_ws_helpers_plaintext_roundtrip(tmp_path) -> None:
    from core.tools.file_tools_exec import _ws_read_text, _ws_write_text, _ws_path_exists
    p = tmp_path / "note.md"
    _ws_write_text(p, "hej verden")
    assert _ws_path_exists(p) is True
    assert _ws_read_text(p) == "hej verden"
    assert _ws_read_text(tmp_path / "nope.md") is None


def test_exec_read_file_plaintext(tmp_path) -> None:
    from core.tools.file_tools_exec import _exec_read_file
    p = tmp_path / "f.txt"
    p.write_text("indhold", encoding="utf-8")
    res = _exec_read_file({"path": str(p)})
    assert res["status"] == "ok"
    assert res["text"] == "indhold"


def test_exec_read_file_missing(tmp_path) -> None:
    from core.tools.file_tools_exec import _exec_read_file
    res = _exec_read_file({"path": str(tmp_path / "missing.txt")})
    assert res["status"] == "error"
    assert "not found" in res["error"].lower()


def test_ws_helpers_member_enc_roundtrip(isolated_runtime, tmp_path, monkeypatch) -> None:
    """Member .enc læses/skrives transparent via de udskilte helpers (§16)."""
    from core.identity.users import add_user
    from core.tools import file_tools_exec as fx
    import core.services.keyring_store as ks

    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")

    p = tmp_path / "workspaces" / "mikkel" / "MEMORY.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    fx._ws_write_text(p, "- mikkels note\n")
    assert (tmp_path / "workspaces" / "mikkel" / "MEMORY.md.enc").exists()
    assert not p.exists()
    assert fx._ws_path_exists(p) is True
    assert fx._ws_read_text(p) == "- mikkels note\n"


def test_exec_read_file_decrypts_member_enc(isolated_runtime, tmp_path, monkeypatch) -> None:
    """read_file-toolet dekrypterer en members .enc-fil efter flip (§16)."""
    from core.identity.users import add_user
    from core.tools import file_tools_exec as fx
    import core.services.keyring_store as ks

    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")

    p = tmp_path / "workspaces" / "mikkel" / "USER.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    fx._ws_write_text(p, "hemmelig profil")
    res = fx._exec_read_file({"path": str(p)})
    assert res["status"] == "ok"
    assert res["text"] == "hemmelig profil"


# ── Read-back: mutationen skal være selv-bevisende (10. sep 2026) ──────────
#
# Baggrund: R2 heed-rate var 17–26%, median 27 minutter fra advarsel til første
# kig. Hintet («kør verify_file_contains») fandtes allerede og flyttede intet,
# fordi et hint er en OPFORDRING. `edit_file` returnerede en PÅSTAND fra
# værktøjet (`replacements: 1`), ikke et bevis fra disken. Testene her binder
# at resultatet nu bærer filen som den FAKTISK står — og at det siger højt når
# den ikke gør.


def test_edit_file_readback_comes_from_disk(tmp_path) -> None:
    from core.tools import file_tools_exec as fx
    p = tmp_path / "note.txt"
    p.write_text("linje et\nlinje to\nlinje tre\n", encoding="utf-8")

    res = fx._exec_edit_file({
        "path": str(p), "old_text": "linje to", "new_text": "LINJE TO",
    })

    assert res["status"] == "ok"
    assert res["replacements"] == 1
    assert res["readback"] is True
    # Beviset skal komme fra DISKEN, ikke fra argumentet.
    assert "LINJE TO" in p.read_text(encoding="utf-8")
    assert "LINJE TO" in res["text"]
    assert "»" in res["text"], "ændringen skal markeres i udsnittet"


def test_edit_file_readback_flags_a_change_that_never_landed(tmp_path, monkeypatch) -> None:
    """Kernen i fixet: værktøjet kan tro det gik — read-back'en siger sandheden.

    Uden dette ville en tavs skrivefejl blive bygget videre på, og først blive
    opdaget 27 minutter senere (median) eller slet ikke.
    """
    from core.tools import file_tools_exec as fx
    p = tmp_path / "note.txt"
    p.write_text("original\n", encoding="utf-8")
    monkeypatch.setattr(fx, "_ws_write_text", lambda *_a, **_k: None)

    res = fx._exec_edit_file({"path": str(p), "old_text": "original", "new_text": "ændret"})

    assert res["status"] == "ok"       # værktøjet melder succes ...
    assert res["readback"] is False    # ... disken siger nej
    assert "står IKKE" in res["text"]
    assert "original" in res["text"], "readback'en skal vise hvad der FAKTISK står"


def test_edit_file_readback_shows_a_deletion(tmp_path) -> None:
    """En sletning har ingen new_text at søge efter — vinduet rammes via gammel offset."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "note.txt"
    p.write_text("a\nb\nSLET MIG\nc\nd\n", encoding="utf-8")

    res = fx._exec_edit_file({"path": str(p), "old_text": "SLET MIG\n", "new_text": ""})

    assert res["status"] == "ok"
    assert res["readback"] is True
    assert "SLET MIG" not in p.read_text(encoding="utf-8")
    assert "c" in res["text"], "udsnittet skal vise stedet hvor linjen forsvandt"


def test_write_file_readback_from_disk(tmp_path) -> None:
    from core.tools import file_tools_exec as fx
    p = tmp_path / "out.txt"

    res = fx._exec_write_file({"path": str(p), "content": "alpha\nbeta\ngamma\n"})

    assert res["status"] == "ok"
    assert res["readback"] is True
    assert res["line_count"] == 4          # tre linjer + den afsluttende tomme
    assert "alpha" in res["text"]
    assert p.read_text(encoding="utf-8") == "alpha\nbeta\ngamma\n"


def test_write_file_readback_flags_mismatch(tmp_path, monkeypatch) -> None:
    """Filen KAN læses, men indholdet er ikke det vi skrev → sig det højt."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "out.txt"
    monkeypatch.setattr(
        fx, "_ws_write_text",
        lambda path, content: path.write_text("noget ANDET", encoding="utf-8"),
    )

    res = fx._exec_write_file({"path": str(p), "content": "noget"})

    assert res["status"] == "ok"
    assert res["readback"] is False
    assert "afviger" in res["text"], "skal sige at indholdet ikke matcher"


def test_write_file_readback_flags_unreadable_file(tmp_path, monkeypatch) -> None:
    """En tavs skrivefejl må ikke blive tavs: filen findes ikke bagefter.

    Uden dette gren ville `readback`-flaget mangle helt, og et totalt svigt
    ville se ud som en helt almindelig skrivning.
    """
    from core.tools import file_tools_exec as fx
    p = tmp_path / "out.txt"
    monkeypatch.setattr(fx, "_ws_write_text", lambda *_a, **_k: None)

    res = fx._exec_write_file({"path": str(p), "content": "noget"})

    assert res["status"] == "ok"
    assert res["readback"] is False
    assert "kunne IKKE læses" in res["text"]


def test_readback_is_bounded(tmp_path) -> None:
    """Read-back'en må ikke sprænge konteksten på en stor fil."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "big.txt"
    p.write_text("\n".join(f"linje {i} " + "x" * 200 for i in range(200)), encoding="utf-8")

    res = fx._exec_edit_file({
        "path": str(p), "old_text": "linje 100 ", "new_text": "LINJE 100 ",
    })

    assert res["status"] == "ok"
    assert len(res["text"]) < fx._READBACK_MAX_CHARS + 400


def test_verify_hint_points_at_the_readback(monkeypatch) -> None:
    """Hintet må ikke sende Jarvis ud i et ekstra læs for noget han HAR fået."""
    from core.tools.simple_tools import _verify_hint_for
    hint = _verify_hint_for("edit_file", {
        "status": "ok", "path": "/tmp/x.txt", "replacements": 1, "readback": True,
    })
    assert "Readback" in hint
    assert "verify_file_contains" not in hint
