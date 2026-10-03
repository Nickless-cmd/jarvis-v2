"""Batch-indlejringen: arbejdet skal følge ÆNDRINGEN, ikke filens størrelse.

Bjørn 3/10-2026: «stortset alle mine beskeder kolder starter». Sporet endte her.

Målt samme dag: MEMORY.md har 5.095 linjer (763.000 tegn), og
`memory_recall._build` indlejrer dem ALLE når filens mtime ændrer sig.
Batch-kaldet med dem alle timer ud efter 30,1 s, hvorefter den faldt tilbage
til 5.095 serielle HTTP-kald á 43 ms = 219 sekunder. Hvert kald holder GIL'en
under sin SSL-opsætning, så den synlige streams tråd blev sultet: 228 sekunder
af en 463-sekunders tur gik hverken med at vente på nettet eller med at regne.

Journalen over to timer: 59.574 serielle kald mod 66 batch. Cache-hitraten var
0,9 % — fordi loftet var 256 mod et arbejdssæt på 5.095.
"""
from __future__ import annotations

import numpy as np
import pytest

from core.services import semantic_memory as sm


@pytest.fixture(autouse=True)
def ren_cache(monkeypatch):
    """Ren cache OG lukket net: testene maaler koden, ikke maskinen."""
    sm._EMBED_CACHE.clear()
    import httpx
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("testen naaede nettet — patch httpx eksplicit")))
    yield
    sm._EMBED_CACHE.clear()


def _vek(n: int) -> np.ndarray:
    return np.full(768, float(n), dtype=np.float32)


def test_kun_de_MANGLENDE_indlejres(monkeypatch):
    """Kernen. Ét nyt memory skal koste ét kald, ikke 5.095."""
    kaldt: list[list[str]] = []

    def _fake(tekster):
        kaldt.append(list(tekster))
        return [_vek(len(t)) for t in tekster]
    monkeypatch.setattr(sm, "_embed_fastembed", _fake)

    sm._embed_ollama_batch(["a", "bb", "ccc"])
    assert kaldt == [["a", "bb", "ccc"]]

    # Samme tekster igen plus én ny: kun den nye maa indlejres.
    kaldt.clear()
    ud = sm._embed_ollama_batch(["a", "bb", "ccc", "dddd"])
    assert kaldt == [["dddd"]], "hele listen blev indlejret igen"
    assert [float(v[0]) for v in ud] == [1.0, 2.0, 3.0, 4.0], "raekkefoelgen skred"


def test_alt_i_cachen_giver_NUL_kald(monkeypatch):
    monkeypatch.setattr(sm, "_embed_fastembed", lambda t: [_vek(len(x)) for x in t])
    sm._embed_ollama_batch(["a", "bb"])
    monkeypatch.setattr(sm, "_embed_fastembed",
                        lambda t: pytest.fail("der blev indlejret trods fuld cache"))
    ud = sm._embed_ollama_batch(["a", "bb"])
    assert [float(v[0]) for v in ud] == [1.0, 2.0]


def test_raekkefoelgen_bevares_ved_BLANDET_cache(monkeypatch):
    """Resultatet er parallelt med input — en forskydning ville knytte hver
    linje til den forkerte vektor, og det ville ingen test uden for denne
    opdage."""
    monkeypatch.setattr(sm, "_embed_fastembed", lambda t: [_vek(len(x)) for x in t])
    sm._embed_ollama_batch(["bb"])          # kun den midterste i cachen
    ud = sm._embed_ollama_batch(["a", "bb", "ccc"])
    assert [float(v[0]) for v in ud] == [1.0, 2.0, 3.0]


def test_en_fejlet_tekst_cachces_IKKE(monkeypatch):
    """Ellers ville ét mislykket kald fastholde `None` for evigt.

    Baade fastembed OG http lukkes: foerste udgave af testen lod httpx staa
    aaben, og den ramte en RIGTIG ollama paa 127.0.0.1 — saa den maalte
    maskinen i stedet for koden.
    """
    import httpx
    monkeypatch.setattr(sm, "_embed_fastembed", lambda t: None)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(
        TimeoutError("ReadTimeout")))
    monkeypatch.setattr(sm, "_embed_ollama", lambda t: None)
    ud = sm._embed_ollama_batch(["a"])
    assert len(ud) == 1 and ud[0] is None
    assert "a" not in sm._EMBED_CACHE, "en fejlet tekst blev cachet som None"

    monkeypatch.setattr(sm, "_embed_ollama", lambda t: _vek(7))
    assert float(sm._embed_ollama_batch(["a"])[0][0]) == 7.0


def test_loftet_daekker_arbejdssaettet():
    """256 var under MEMORY.md's 5.095 linjer, saa cachen smed ud hele tiden
    og naaede aldrig at hjaelpe — maalt hitrate 0,9 %."""
    assert sm._EMBED_CACHE_MAX >= 5095


def test_fallback_til_seriel_er_HOEJLYDT(monkeypatch, caplog):
    """Det var tavsheden der lod 59.574 serielle kald paa to timer passere.
    En fallback der er langsommere skal kunne ses i journalen."""
    import logging
    monkeypatch.setattr(sm, "_embed_fastembed", lambda t: None)

    def _timeout(*a, **k):
        raise TimeoutError("ReadTimeout")
    monkeypatch.setattr(sm, "_embed_ollama", lambda t: _vek(1))
    import httpx
    monkeypatch.setattr(httpx, "post", _timeout)
    with caplog.at_level(logging.WARNING, logger="core.services.semantic_memory"):
        ud = sm._embed_ollama_batch(["a", "b"])
    assert len(ud) == 2
    beskeder = " ".join(r.getMessage() for r in caplog.records)
    assert "falder til per-tekst" in beskeder
    assert "TimeoutError" in beskeder


def test_store_arbejdssaet_deles_i_BIDDER(monkeypatch):
    """Hele MEMORY.md (5.376 linjer) i ÉT kald timer ud efter 30 s (målt 22:39).
    Bidder holder hvert kald under timeouten — og gor at en fejl kun rammer
    sine egne tekster."""
    monkeypatch.setattr(sm, "_embed_fastembed", lambda t: None)
    kald: list[int] = []

    def _post(url, json=None, timeout=None):
        kald.append(len(json["input"]))
        ind = list(json["input"])

        class _R:
            status_code = 200

            def json(self):
                return {"embeddings": [[1.0] * 768 for _ in ind]}
        return _R()

    import httpx
    monkeypatch.setattr(httpx, "post", _post)
    tekster = [f"linje {i}" for i in range(sm._EMBED_BID * 2 + 5)]
    ud = sm._embed_ollama_batch(tekster)
    assert len(ud) == len(tekster)
    assert len(kald) == 3, f"ventede 3 bidder, fik {len(kald)}"
    assert max(kald) <= sm._EMBED_BID, "et bid var stoerre end loftet"
    assert sum(kald) == len(tekster), "tekster faldt ud mellem bidderne"


def test_en_fejlet_bid_vaelter_ikke_hele_arbejdssaettet(monkeypatch):
    """Den GLOBALE fallback var fejlen: ét timeout kostede 5.376 serielle kald.
    Nu skal kun den bid der fejlede gaa serielt."""
    monkeypatch.setattr(sm, "_embed_fastembed", lambda t: None)
    monkeypatch.setattr(sm, "_EMBED_BID", 2)
    import httpx
    kald = {"n": 0}

    def _post(url, json=None, timeout=None):
        kald["n"] += 1
        if kald["n"] == 2:
            raise TimeoutError("ReadTimeout")
        ind = list(json["input"])

        class _R:
            status_code = 200

            def json(self):
                return {"embeddings": [[1.0] * 768 for _ in ind]}
        return _R()

    monkeypatch.setattr(httpx, "post", _post)
    serielle: list[str] = []
    monkeypatch.setattr(sm, "_embed_ollama",
                        lambda t: (serielle.append(t), _vek(1))[1])
    ud = sm._embed_ollama_batch(["a", "b", "c", "d", "e"])
    assert len(ud) == 5
    assert kald["n"] == 3, f"ventede 3 bidder, fik {kald['n']}"
    assert serielle == ["c", "d"], f"kun den fejlede bid maa gaa serielt: {serielle}"


def test_tom_liste_er_stadig_tom():
    assert sm._embed_ollama_batch([]) == []


def test_cache_gem_afviser_None_direkte():
    """`_cache_gem` er en almen hjaelper, saa den maa ikke stole paa at
    kalderen har filtreret. Kaldestedet filtrerer ogsaa — derfor kan en test
    GENNEM batch-funktionen ikke se denne vagt, og den skal maales her."""
    sm._cache_gem([("x", None), ("y", _vek(5))])
    assert "x" not in sm._EMBED_CACHE, "None blev cachet som en vektor"
    assert float(sm._EMBED_CACHE["y"][0]) == 5.0


def test_cache_gem_toemmer_FIFO_ved_loftet(monkeypatch):
    """Uden halvtoemningen ville cachen vokse uden graense; med den skal de
    AELDSTE ryge foerst, saa det aktuelle arbejdssaet overlever."""
    monkeypatch.setattr(sm, "_EMBED_CACHE_MAX", 4)
    sm._cache_gem([(str(i), _vek(i)) for i in range(4)])
    assert len(sm._EMBED_CACHE) == 4
    sm._cache_gem([("ny", _vek(9))])
    assert "ny" in sm._EMBED_CACHE
    assert "0" not in sm._EMBED_CACHE, "den aeldste overlevede"
    assert "3" in sm._EMBED_CACHE, "den nyeste blev smidt ud"
