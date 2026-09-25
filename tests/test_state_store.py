from __future__ import annotations

import os

import pytest

from core.runtime import state_store


def test_save_json_strict_propagates_atomic_replace_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)

    def fail_replace(source, destination):
        raise OSError("disk unavailable")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="disk unavailable"):
        state_store.save_json_strict("recovery", {"run": "r1"})


def test_save_json_remains_self_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(
        state_store,
        "save_json_strict",
        lambda name, data: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    state_store.save_json("recovery", {"run": "r1"})


def test_aendret_ns_er_nul_for_fil_der_ikke_findes():
    from core.runtime import state_store

    assert state_store.aendret_ns("findes-slet-ikke") == 0


def test_aendret_ns_rykker_naar_filen_skrives():
    from core.runtime import state_store

    foer = state_store.aendret_ns("mtime-proeve")
    state_store.save_json("mtime-proeve", {"a": 1})
    efter = state_store.aendret_ns("mtime-proeve")

    assert foer == 0
    assert efter > 0
