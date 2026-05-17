"""Tests for jobs_engine._load() mtime-keyed cache.

2026-05-17 perf fix: jobs_queue.json er nu 16 MB. py-spy viste at en enkelt
_load() (selv efter scheduler-fixet med 1 kald pr. poll) brugte ~235ms i
JSON-parse — 78.9% inclusive på runtime-worker. Vi cacher det parsede
resultat keyed på (mtime, size). _save() opdaterer cachen direkte.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.services import jobs_engine


@pytest.fixture
def tmp_queue(tmp_path, monkeypatch):
    home = tmp_path / "jarvis"
    (home / "workspaces/default/runtime").mkdir(parents=True)
    monkeypatch.setenv("JARVIS_HOME", str(home))
    # Nulstil cache-state mellem tests
    jobs_engine._LOAD_CACHE_KEY = None
    jobs_engine._LOAD_CACHE_ITEMS = None
    return home / "workspaces/default/runtime/jobs_queue.json"


def test_load_caches_on_unchanged_file(tmp_queue):
    items = [{"job_id": "a", "job_type": "x", "status": "pending"}]
    tmp_queue.write_text(json.dumps(items), encoding="utf-8")

    first = jobs_engine._load()
    second = jobs_engine._load()

    # Samme reference = cache hit (ingen re-parse)
    assert first is second
    assert first == items


def test_load_reparses_after_external_write(tmp_queue):
    tmp_queue.write_text(json.dumps([{"job_id": "a"}]), encoding="utf-8")
    first = jobs_engine._load()

    # Simuler ekstern proces der ændrer filen — sæt mtime fremad
    new_items = [{"job_id": "b"}]
    tmp_queue.write_text(json.dumps(new_items), encoding="utf-8")
    st = tmp_queue.stat()
    os.utime(tmp_queue, (st.st_atime, st.st_mtime + 10))

    second = jobs_engine._load()
    assert second is not first
    assert second == new_items


def test_save_refreshes_cache_without_reparse(tmp_queue):
    tmp_queue.write_text(json.dumps([]), encoding="utf-8")
    jobs_engine._load()  # primer cache

    new_items = [{"job_id": "c", "status": "pending"}]
    jobs_engine._save(new_items)

    # Næste _load skal returnere det netop gemte uden at parse filen igen
    loaded = jobs_engine._load()
    assert loaded is new_items


def test_missing_file_returns_empty_and_caches(tmp_queue):
    # Fil eksisterer ikke endnu
    assert not tmp_queue.exists()
    first = jobs_engine._load()
    second = jobs_engine._load()
    assert first == []
    assert second == []
