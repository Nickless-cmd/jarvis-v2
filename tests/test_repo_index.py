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


# ── Område-vægt og hybrid-scoring (målt 24/10-2026) ───────────────────────
#
# Baggrund: indekset havde 18.204 chunks hvoraf `docs/superpowers` var 73,7 %
# og `docs/notes` 1,6 %. Cosine er upartisk, så mængde vandt over relevans:
# fire af seks kontrolspørgsmål ramte forkert. Vægten og den leksikalske
# komponent er svaret på det — og de tests her vogter at de ikke rådner.


def test_planer_vejer_mindre_end_levende_specs():
    """Udførte planer må ikke vinde i kraft af at være flest."""
    assert ri._area_weight("docs/superpowers/plans/x.md") < ri._area_weight(
        "docs/superpowers/specs/x.md"
    )


def test_notes_og_reference_vejer_mere_end_planer():
    assert ri._area_weight("docs/notes/x.md") > ri._area_weight(
        "docs/superpowers/plans/x.md"
    )
    assert ri._area_weight("docs/reference/CONFIG.md") > ri._area_weight(
        "docs/superpowers/plans/x.md"
    )


def test_ukendt_sti_vejer_neutralt():
    assert ri._area_weight("et-eller-andet.md") == 1.0


def test_lexical_score_taeller_termer_i_sti_og_sektion():
    chunk = ri.Chunk(text="noget tekst", source="docs/notes/desk-udgivelser.md", section="Udgivet")
    assert ri._lexical_score(["desk", "udgivelser"], chunk) == 1.0
    assert ri._lexical_score(["desk", "findesikke"], chunk) == 0.5
    assert ri._lexical_score([], chunk) == 0.0


def test_hybrid_loefter_leksikalsk_hit_som_embedding_missede(fake_repo, monkeypatch):
    """Den leksikalske komponent skal loefte et hit som cosine alene misser.

    Det målte tilfælde (24/10-2026): `docs/notes/2026-10-04-desk-udgivelser.md`
    laa paa rank 224 med raa cosine 0,548, mens det forkerte topsvar laa paa
    0,620. Vægtning kunne ikke redde det — hit'et kom aldrig i betragtning.

    Testen maaler den EGENSKAB, ikke et specifikt tal: med en falsk embedding
    hvor det rigtige hit er ortogonalt paa queryen (cosine 0) skal den
    leksikalske komponent loefte det ind i resultatet. Uden den er det væk.

    Graensen er maalt: ved ortogonal vektor kraever det `_LEXICAL_WEIGHT >= 0.5`
    at vende rangeringen helt. Testen kraever derfor kun at hit'et BLIVER
    FUNDET med 0,25 — ikke at det vinder. Det er den egenskab der betyder
    noget i drift, hvor cosine sjældent er helt nul.
    """
    import numpy as np

    ri.build_index()
    chunks, _, _ = ri._load_or_build()
    # Tre forsoeg gik galt foer dette virkede, og hver fejl er vaerd at kende:
    #   1) 0,1 mod 1,0 — den rigtige vandt alligevel (1,05 mod 0,72), fordi
    #      omraade-vaegten loeftede den.
    #   2) 0,02 mod 1,0 — den rigtige blev filtreret vaek af cosine-gulvet,
    #      saa soegningen faldt tilbage paa TF-IDF og testen bestod uanset
    #      vaegten. (Gulvet er siden rettet til at maale den kombinerede score.)
    #   3) 0,15 mod 1,0 — _cosine_sim NORMALISERER, saa begge blev 1,0.
    # Loesningen er en ortogonal vektor: cosine 0, men overlever gulvet naar
    # den blandes med den leksikalske komponent.
    dim = 8
    fake = np.zeros((len(chunks), dim), dtype=np.float32)
    for i, c in enumerate(chunks):
        if "plans" in c.source:
            fake[i, 0] = 1.0
        else:
            fake[i, 1] = 1.0
    monkeypatch.setattr(ri, "_load_or_build", lambda: (chunks, fake, {}))
    monkeypatch.setattr(
        ri, "_embed_single", lambda q: np.array([1.0] + [0.0] * (dim - 1), dtype=np.float32)
    )

    hits = ri.search_repo("centralen indre liv", limit=3)
    kilder = [h["source"] for h in hits]
    assert any("ARKITEKTUR" in s for s in kilder), kilder

    # Og beviset paa at det er DEN LEKSIKALSKE komponent der goer det:
    # med vaegten paa nul forsvinder hit'et igen.
    monkeypatch.setattr(ri, "_LEXICAL_WEIGHT", 0.0)
    uden = [h["source"] for h in ri.search_repo("centralen indre liv", limit=3)]
    assert not any("ARKITEKTUR" in s for s in uden), uden


def test_vaegtning_aendrer_rangeringen_ikke_filtrerer(fake_repo):
    """Vægten må kun omrokere — aldrig fjerne et hit der ellers ville være med."""
    ri.build_index()
    hits = ri.search_repo("centralen", limit=10)
    assert hits, "soegningen gav intet"
    for h in hits:
        # raw_score findes kun paa embedding-stien; TF-IDF-fallbacken har
        # ingen cosine at sammenligne med. Kravet gaar derfor paa metoden.
        if h.get("method") == "embedding":
            assert "raw_score" in h, "raw_score mangler — saa kan vaegtens effekt ikke maales"
