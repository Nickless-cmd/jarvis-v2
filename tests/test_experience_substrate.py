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
    assert type(embedder).__name__ in {"_FastEmbedEmbedder", "_HashingEmbedder"}, (
        "embedderen faldt tilbage til en torch-afhængig implementering"
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


# ── Vagt: ONNX-trådantal skal sættes eksplicit (24/10-2026) ─────────
#
# MÅLT 24/10-2026 på kold initialisering i denne LXC:
#   uden threads=  → 4× "pthread_setaffinity_np failed", init 0,132 s
#   threads=4      → 0 fejl,                              init 0,135 s
#   threads=1      → 0 fejl,                              init 0,128 s
# Containeren blokerer CPU-affinity, så onnxruntime fejler for hver tråd den
# selv sætter op. Uden et eksplicit tal spammer den journalen — og det var
# den ene observerede "nye=13"-byge, der ikke var narrativizeren.
# Fixet koster ingenting i tid, så der er ingen grund til at lade være.


def _fake_fastembed(monkeypatch):
    """Indsæt et fake `fastembed`-modul der fanger TextEmbedding-kwargs.

    Importen sker inde i `_FastEmbedEmbedder.__init__`, så et fake modul i
    `sys.modules` rammer kaldet — ikke modul-load.
    """
    import sys
    import types

    fanget: dict = {}

    class _FakeTextEmbedding:
        def __init__(self, model_name, **kwargs):
            fanget["model_name"] = model_name
            fanget["kwargs"] = kwargs

        def embed(self, tekster):
            yield [0.1] * 384

    modul = types.ModuleType("fastembed")
    modul.TextEmbedding = _FakeTextEmbedding
    monkeypatch.setitem(sys.modules, "fastembed", modul)
    return fanget


def test_embedder_sender_threads_eksplicit(monkeypatch):
    """`TextEmbedding` skal kaldes MED `threads=` — ellers fejler affinity."""
    import core.services.experience_substrate as es

    fanget = _fake_fastembed(monkeypatch)
    es._FastEmbedEmbedder()

    assert "threads" in fanget["kwargs"], (
        "embedderen kalder TextEmbedding uden threads= — onnxruntime sætter da "
        "sin egen pulje op og pthread_setaffinity_np fejler i denne container"
    )
    assert fanget["kwargs"]["threads"] == es.DEFAULT_FASTEMBED_THREADS


def test_embedder_respekterer_runtime_noeglen(monkeypatch):
    """Runtime-nøglen `embed_fastembed_threads` skal styre begge embeddere."""
    import core.services.experience_substrate as es

    monkeypatch.setattr(es, "_fastembed_threads", lambda: 2)
    fanget = _fake_fastembed(monkeypatch)
    es._FastEmbedEmbedder()

    assert fanget["kwargs"]["threads"] == 2, (
        "runtime-nøglen blev ikke respekteret — de to embeddere ville køre "
        "med hvert sit trådantal"
    )


def test_fastembed_threads_default_er_fire(monkeypatch):
    """Uden nøgle i runtime-config skal default være 4, som i semantic_memory."""
    import core.services.experience_substrate as es

    def _tom_nogle(_navn):
        return None

    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", _tom_nogle)
    assert es._fastembed_threads() == 4


def test_fastembed_threads_ignorerer_ugyldig_vaerdi(monkeypatch):
    """En ikke-numerisk nøgle må ikke give threads=0 eller kaste."""
    import core.services.experience_substrate as es

    for ugyldig in ("", "  ", "otte", "0", "-2"):
        monkeypatch.setattr(
            "core.runtime.secrets.read_runtime_key", lambda _n, v=ugyldig: v
        )
        assert es._fastembed_threads() == 4, f"ugyldig nøgle {ugyldig!r} gav ikke default"


def test_fastembed_threads_laeser_gyldig_noegle(monkeypatch):
    """En gyldig nøgle skal ændre resultatet — ikke kun defaulten.

    24/10-2026: den første udgave af disse vagter var TOM. Mutationen der
    fjernede `return int(raa)` blev ikke fældet, fordi ingen test beviste at
    en gyldig værdi faktisk slår igennem — de øvrige tests monkeypatch'ede
    enten funktionen selv eller brugte kun ugyldige værdier (der giver
    default alligevel). Denne test er den der fælder mutationen.
    """
    import core.services.experience_substrate as es

    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", lambda _n: "2")
    assert es._fastembed_threads() == 2, (
        "en gyldig runtime-nøgle blev ignoreret — funktionen returnerer altid default"
    )

    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", lambda _n: " 8 ")
    assert es._fastembed_threads() == 8, "whitespace omkring tallet blev ikke trimmet"


# ── Vagt: varmning ved opstart (24/10-2026) ─────────────────────────
#
# Kold init måler 153 % CPU i 0,39 s (130 % med threads=4) og efterlader
# 10-12 tråde. Uden varmning rammer den spids den første tur der rører
# substratet; med varmning rammer den opstarten. Vagten her sikrer at
# varmningen ikke kan gøre opstarten dyrere end nødvendigt: den må aldrig
# kaste, og den skal faktisk have kørt en encode (ellers er ONNX-puljen
# ikke bygget — målt: init giver 4-6 tråde, encode giver 10-12).


def test_warm_embedder_kører_en_encode(monkeypatch):
    """Varmningen skal kalde encode — init alene bygger ikke den fulde pulje."""
    import core.services.experience_substrate as es

    kaldt = {"encode": 0}

    class _FakeEmbedder:
        def encode(self, text, normalize_embeddings=True):
            kaldt["encode"] += 1
            return [[0.0] * 384]

    monkeypatch.setattr(es, "_EMBEDDER", None)
    monkeypatch.setattr(es, "_get_embedder", lambda: _FakeEmbedder())

    assert es.warm_embedder() is True
    assert kaldt["encode"] == 1, "varmningen byggede embedderen men kørte ingen encode"


def test_warm_embedder_kaster_aldrig(monkeypatch):
    """En manglende embedder må ikke vælte opstarten — den kaldes fra en tråd."""
    import core.services.experience_substrate as es

    def _braek():
        raise RuntimeError("onnx utilgængelig")

    monkeypatch.setattr(es, "_get_embedder", _braek)
    assert es.warm_embedder() is False
