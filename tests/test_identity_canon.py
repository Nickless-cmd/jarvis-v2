"""Kanonisk identitets-store (Spec H) — canon-tråde + acknowledged_corrections.

Dækker: set/get canon-tråd; add/list corrections; seed-idempotens (to seeds → ÉN sonnet-korrektion);
build_identity_canon_surface; self-safe. Fresh-DB via monkeypatch af db_core.DB_PATH.
"""
import importlib

import pytest

from core.runtime import db_core


@pytest.fixture()
def canon(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "canon.db")
    monkeypatch.setattr(db_core, "_DB_WAL_INITIALIZED", False, raising=False)
    import core.services.identity_canon as ic
    importlib.reload(ic)
    return ic


def test_seed_on_first_use_sonnet_correction(canon):
    corrs = canon.list_acknowledged_corrections()
    assert len(corrs) == 1
    assert "sonnet" in corrs[0]["claim_pattern"].lower()
    assert "konfabuleret" in corrs[0]["reason"].lower()
    assert corrs[0]["status"] == "active"


def test_seed_idempotent(canon):
    # Kald der udløser _ensure_and_seed flere gange → stadig ÉN sonnet-korrektion.
    canon.get_canon()
    canon.list_acknowledged_corrections()
    canon.get_canon()
    sonnet = [c for c in canon.list_acknowledged_corrections()
              if "sonnet" in c["claim_pattern"].lower()]
    assert len(sonnet) == 1


def test_voice_canon_seeded(canon):
    c = canon.get_canon()
    assert "voice" in c
    assert "model-uafhængig" in c["voice"]


def test_set_and_get_canon_thread(canon):
    res = canon.set_canon_thread(thread="self_story", canon_text="Jeg er en vedvarende entitet.")
    assert res["ok"] is True
    c = canon.get_canon()
    assert c["self_story"] == "Jeg er en vedvarende entitet."


def test_set_canon_thread_upsert(canon):
    canon.set_canon_thread(thread="values", canon_text="a")
    canon.set_canon_thread(thread="values", canon_text="b")
    assert canon.get_canon()["values"] == "b"


def test_set_canon_thread_rejects_unknown(canon):
    res = canon.set_canon_thread(thread="bogus", canon_text="x")
    assert res["ok"] is False


def test_add_and_list_corrections(canon):
    res = canon.add_acknowledged_correction(claim_pattern="jeg er gpt", reason="ikke sandt")
    assert res["ok"] is True
    patterns = [c["claim_pattern"] for c in canon.list_acknowledged_corrections()]
    assert "jeg er gpt" in patterns


def test_add_correction_rejects_empty(canon):
    assert canon.add_acknowledged_correction(claim_pattern="  ", reason="x")["ok"] is False


def test_build_surface_shape(canon):
    surf = canon.build_identity_canon_surface()
    assert set(surf) >= {"canon_threads", "acknowledged_corrections", "recent_drift_catches", "felt"}
    assert isinstance(surf["canon_threads"], dict)
    assert isinstance(surf["acknowledged_corrections"], list)
    assert isinstance(surf["recent_drift_catches"], list)
