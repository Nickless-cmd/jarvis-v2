"""Cache-integritet i `memory_search` — atomisk skrivning og karantæne af brudt fil.

Rod (målt 3/11-2026): `_build_and_cache_index` skrev DIREKTE på den levende
cache med `open(cache, "wb")` + `pickle.dump`, og rebuild'en kører i en
daemon-tråd. En proces der stoppede midt i skrivningen efterlod en AFKORTET
pickle. Konsekvensen var ikke bare ét tabt indeks: hver efterfølgende søgning
fejlede med "Ran out of input", faldt til tfidf, og rebuild'en blev aldrig
færdig fordi filen stadig "fandtes" — den samme defekte fil blev forsøgt
indlæst igen og igen, indtil nogen slettede den i hånden. Målt: 12.953 chunks
og 29,5 minutters re-embed, med fejlen usynlig i svaret.

Disse tests værner de to ting der gjorde skaden mulig: at skrivningen er
atomisk, og at en brudt fil bliver lagt til side i stedet for at forgifte
hver efterfølgende søgning.
"""
from __future__ import annotations

import pickle

import numpy as np
import pytest

from core.services import memory_search as ms


def _workspace(tmp_path, text: str = "# Emne\n\nindhold her som er langt nok til at blive en chunk\n"):
    """Returnér (ws, filer) — filerne skal med, ellers chunkes der intet."""
    d = tmp_path / "ws"
    d.mkdir()
    f = d / "MEMORY.md"
    f.write_text(text, encoding="utf-8")
    return d, [f]


@pytest.fixture(autouse=True)
def _ingen_baggrundstraad(monkeypatch):
    """Rebuild-tråden er ikke det der testes her — og en ægte tråd ville gøre
    testen ikke-deterministisk."""
    monkeypatch.setattr(ms, "_schedule_background_rebuild", lambda *a, **k: None)


def _fast_embed(monkeypatch):
    monkeypatch.setattr(
        ms, "_embed_ollama",
        lambda texts: np.zeros((len(texts), 3), dtype="float32"),
    )


def test_skrivning_efterlader_ingen_tmp_fil(monkeypatch, tmp_path):
    """Efter en fuldført bygning skal der kun ligge ÉN cache — ingen rester."""
    ws, filer = _workspace(tmp_path)
    monkeypatch.setattr(ms, "_cache_path", lambda ws=None: tmp_path / "idx.pkl")
    _fast_embed(monkeypatch)

    ms._build_and_cache_index(filer, {"f": 1.0}, ws)

    cache = tmp_path / "idx.pkl"
    assert cache.exists()
    data = pickle.loads(cache.read_bytes())
    assert data["model"] == ms._EMBED_MODEL
    assert not list(tmp_path.glob("*.tmp-*")), "tmp-filen skal være væk efter replace"


def test_afbrudt_skrivning_bevarer_den_gamle_cache(monkeypatch, tmp_path):
    """Kernen i rettelsen: fejler skrivningen midtvejs, skal den GAMLE cache stå
    urørt. Før rettelsen blev den levende fil afkortet, og næste søgning fejlede."""
    ws, filer = _workspace(tmp_path)
    monkeypatch.setattr(ms, "_cache_path", lambda ws=None: tmp_path / "idx.pkl")
    _fast_embed(monkeypatch)

    ms._build_and_cache_index(filer, {"f": 1.0}, ws)
    cache = tmp_path / "idx.pkl"
    foer = pickle.loads(cache.read_bytes())

    def _braek(*_a, **_k):
        raise OSError("skrivning afbrudt midt i picklen")

    monkeypatch.setattr(ms.pickle, "dump", _braek)
    ms._build_and_cache_index(filer, {"f": 2.0}, ws)  # må ikke efterlade noget halvt

    efter = pickle.loads(cache.read_bytes())  # ville rejse EOFError før rettelsen
    assert efter["built_at"] == foer["built_at"], "den gamle cache skal stå urørt"
    assert efter["chunks"] == foer["chunks"]
    assert not list(tmp_path.glob("*.tmp-*")), "den halvskrevne tmp-fil skal ryddes op"


def test_brudt_cache_lægges_til_side_så_søgning_virker(monkeypatch, tmp_path):
    """En afkortet pickle må koste ÉN dårlig søgning — ikke alle fremtidige.

    Uden karantænen blev den samme fil forsøgt indlæst ved hvert kald, og
    rebuild'en startede aldrig fordi filen stadig fandtes."""
    ws, _filer = _workspace(tmp_path)
    cache = tmp_path / "idx.pkl"
    monkeypatch.setattr(ms, "_cache_path", lambda ws=None: cache)
    _fast_embed(monkeypatch)

    cache.write_bytes(pickle.dumps({"chunks": ["x"], "embeddings": None})[:8])

    chunks, embeddings, _ = ms._load_or_build_index(ws)

    assert chunks, "søgningen skal stadig have chunks (tfidf-fallback)"
    assert embeddings is None
    assert not cache.exists(), "den brudte fil skal være flyttet væk"
    korrupte = list(tmp_path.glob("idx.pkl.corrupt-*"))
    assert len(korrupte) == 1, "den brudte fil skal bevares til undersøgelse"

    # Andet kald: ingen ny karantæne-fil — filen er væk nu, så stien er ren.
    ms._load_or_build_index(ws)
    assert len(list(tmp_path.glob("idx.pkl.corrupt-*"))) == 1
