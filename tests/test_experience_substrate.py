"""Vagt: erfaring-substratets embedder må ikke kræve torch.

MÅLT 24/10-2026: `import torch` fejlede med
`undefined symbol: __nvJitLinkCreate_12_8` — en cu12/cu13-kollision i
site-packages. Fordi `sentence_transformers` importerer torch, kunne
embedderen ikke bygges, og hele lag 2 var dødt:

  - `record_episode` kastede (ingen try/except omkring `_get_embedder`)
  - `retrieve_similar_episodes` returnerede tavst `[]`

Konsekvensen var usynlig: `[EXPERIENCE SUBSTRATE]` har aldrig været i
prompten, og 2670 erfaringer lå i SQLite uden vektorer.

Disse tests fælder at embedderen igen bindes til torch, og at dens
dimension ikke matcher det collection'en forventer.
"""

from __future__ import annotations

import sys

import pytest


def test_embedder_importerer_ikke_torch(monkeypatch):
    """Embedderen skal kunne bygges uden at torch importeres.

    Vi blokerer `torch` i sys.modules og kræver at embedderen stadig
    bygges. Kan den ikke det, er vi låst til en pakke der er brækket.
    """
    import core.services.experience_substrate as es

    monkeypatch.setattr(es, "_EMBEDDER", None)
    # Blokér torch: enhver import af den skal fejle hårdt.
    monkeypatch.setitem(sys.modules, "torch", None)

    embedder = es._get_embedder()
    assert embedder is not None
    assert type(embedder).__name__ == "_FastEmbedEmbedder", (
        "embedderen faldt tilbage til sentence-transformers — den kræver torch"
    )


def test_embedder_giver_json_serialiserbare_vektorer():
    """Vektorerne skal være rene floats — ikke np.float64.

    chromadb og json kan ikke serialisere numpy-skalarer, så en vektor
    med np.float64 fejler først ved skrivning, ikke ved encode.
    """
    import json

    import core.services.experience_substrate as es

    vec = es._get_embedder().encode("intent: test", normalize_embeddings=True).tolist()
    assert len(vec) > 0
    assert all(isinstance(x, float) for x in vec), "vektoren indeholder ikke-float værdier"
    json.dumps(vec)  # kaster hvis ikke serialiserbar


def test_embedder_dimension_matcher_collection():
    """Dimensionen skal matche det collection'en blev oprettet med.

    Målt 24/10-2026: den gamle collection var 768-dimensionel (en anden
    model), mens all-MiniLM-L6-v2 giver 384. Uden denne vagt fejler
    første skrivning med `expecting embedding with dimension of 768`.
    """
    import core.services.experience_substrate as es

    vec = es._get_embedder().encode("dimensionstest", normalize_embeddings=True).tolist()
    assert len(vec) == 384, f"forventede 384 dimensioner for all-MiniLM-L6-v2, fik {len(vec)}"


def test_retrieve_taaler_tom_collection():
    """Kold start skal give [] — ikke en exception."""
    import core.services.experience_substrate as es

    res = es.retrieve_similar_episodes(context_intent="noget der ikke findes", k=3)
    assert isinstance(res, list)


def test_record_og_retrieve_runder_igennem(monkeypatch):
    """record → chromadb → retrieve skal virke som en kæde.

    Bruger en isoleret collection så rigtige erfaringer ikke røres.
    """
    import chromadb

    import core.services.experience_substrate as es

    tmp = pytest.importorskip("tempfile").mkdtemp(prefix="chroma-test-")
    client = chromadb.PersistentClient(path=tmp)
    coll = client.create_collection(name=es.COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    monkeypatch.setattr(es, "_get_chroma_collection", lambda: coll)

    eid = es.record_episode(
        session_id="vagt-test",
        context_text="vagtens egen testraekke",
        context_intent="bevise at kaeden virker",
        session_phase="coding",
        tool_sequence=["bash"],
        outcome_signals={"tick_quality": 90},
    )
    assert eid

    res = es.retrieve_similar_episodes(context_intent="bevise at kaeden virker", k=3)
    assert len(res) >= 1, "record skrev men retrieve fandt intet — kaeden er brudt"
    # Tærsklen er 0.5, ikke 0.9: query-teksten er kortere end den gemte
    # (record havde også session_phase), så cosinus lander omkring 0.77.
    # Det afgørende er at den rigtige episode rangeres øverst.
    assert res[0]["similarity"] > 0.5, f"svagt match: {res[0]['similarity']}"
    assert res[0]["context_intent"] == "bevise at kaeden virker"
