"""Tests for repo_index — det separate dokumentationsindeks.

Dækker det der kan rådne tavst:
  * fil-udvælgelsen (glob, ikke hårdkodet liste)
  * ekskluderingerne (arkiv, genereret API-doc, identitetskopier)
  * at indekset er ADSKILT fra memory-indekset
  * søgning, path-filter og inkrementel genbrug
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.services import repo_index as ri


@pytest.fixture()
def fake_repo(tmp_path, monkeypatch):
    """Et lille repo med docs, rod-md og de kataloger der skal udelades."""
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "superpowers" / "specs").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (root / "docs" / "_archive").mkdir(parents=True)
    (root / "docs" / "reference" / "api").mkdir(parents=True)

    (root / "docs" / "ARKITEKTUR.md").write_text(
        "# Arkitektur\n\n## Centralen\n\nCentralen er Jarvis' indre liv.\n", encoding="utf-8"
    )
    (root / "docs" / "superpowers" / "specs" / "spec.md").write_text(
        "# Spec\n\n## Recall\n\nRecall slår op i hukommelsen.\n", encoding="utf-8"
    )
    (root / "docs" / "superpowers" / "plans" / "plan.md").write_text(
        "# Plan\n\n## Bygget\n\nSådan blev det bygget.\n", encoding="utf-8"
    )
    (root / "docs" / "_archive" / "gammel.md").write_text(
        "# Gammel\n\nForældet indhold.\n", encoding="utf-8"
    )
    (root / "docs" / "reference" / "api" / "genereret.md").write_text(
        "# Genereret\n\nFra koden.\n", encoding="utf-8"
    )
    (root / "README.md").write_text("# README\n\nProjektets indgang.\n", encoding="utf-8")
    (root / "USER.md").write_text("# User\n\nFORÆLDET KOPI.\n", encoding="utf-8")

    monkeypatch.setenv("JARVIS_REPO_ROOT", str(root))
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "home"))
    # Ingen ollama i test: TF-IDF-stien bruges, og baggrundsbygning slås fra
    # så testen ikke racer med en tråd.
    monkeypatch.setattr(ri, "_embed_ollama", lambda texts: None)
    monkeypatch.setattr(ri, "_schedule_background_build", lambda: None)
    return root


def test_filer_inkluderer_docs_og_rod_md(fake_repo):
    names = {f.relative_to(fake_repo).as_posix() for f in ri.repo_files()}
    assert "docs/ARKITEKTUR.md" in names
    assert "docs/superpowers/specs/spec.md" in names
    assert "docs/superpowers/plans/plan.md" in names
    assert "README.md" in names


def test_filer_udelader_arkiv_og_genereret_api(fake_repo):
    names = {f.relative_to(fake_repo).as_posix() for f in ri.repo_files()}
    assert "docs/_archive/gammel.md" not in names
    assert "docs/reference/api/genereret.md" not in names


def test_filer_udelader_identitetskopier_paa_roden(fake_repo):
    names = {f.relative_to(fake_repo).as_posix() for f in ri.repo_files()}
    assert "USER.md" not in names
    # ...men en USER.md der ligger i docs/ er almindeligt indhold.
    (fake_repo / "docs" / "USER.md").write_text("# User\n\nDokumentation.\n", encoding="utf-8")
    assert "docs/USER.md" in {f.relative_to(fake_repo).as_posix() for f in ri.repo_files()}


def test_ny_fil_bliver_taget_med_automatisk(fake_repo):
    """Vagten mod hårdkodede fillister (PLAYBOOKS-fejlen, 23/10-2026)."""
    ny = fake_repo / "docs" / "helt-ny.md"
    ny.write_text("# Ny\n\nNyt indhold der skal kunne søges.\n", encoding="utf-8")
    assert ny in ri.repo_files()


def test_indeks_sti_er_adskilt_fra_memory_indeks(fake_repo):
    """Arkitektur-værn: de to korpora må aldrig dele cache-fil."""
    from core.services import memory_search

    assert ri._index_path() != memory_search._cache_path()
    assert ri._index_path().name == "repo_index.pkl"


def test_soegning_finder_indhold(fake_repo):
    hits = ri.search_repo("Centralen indre liv", limit=3)
    assert hits, "søgningen gav intet"
    assert any("ARKITEKTUR" in h["source"] for h in hits)


def test_path_filter_afgraenser(fake_repo):
    hits = ri.search_repo("bygget", limit=5, path_prefix="docs/superpowers/specs")
    assert all(h["source"].startswith("docs/superpowers/specs") for h in hits)


def test_byg_skriver_cache_og_genbrug_er_unchanged(fake_repo):
    first = ri.build_index()
    assert first["status"] == "built"
    assert first["chunks"] > 0
    assert ri._index_path().exists()

    second = ri.build_index()
    assert second["status"] == "unchanged"
    assert second["chunks"] == first["chunks"]


def test_force_bygger_igen(fake_repo):
    ri.build_index()
    again = ri.build_index(force=True)
    assert again["status"] == "built"


def test_stats_rapporterer_omraader(fake_repo):
    ri.build_index()
    stats = ri.get_stats()
    assert stats["status"] == "ready"
    assert stats["chunk_count"] > 0
    assert stats["file_count"] >= 4
    assert "by_area" in stats


def test_tom_query_giver_tom_liste(fake_repo):
    assert ri.search_repo("") == []
    assert ri.search_repo("   ") == []


def test_invalidate_sletter_cache(fake_repo):
    ri.build_index()
    assert ri._index_path().exists()
    ri.invalidate()
    assert not ri._index_path().exists()
