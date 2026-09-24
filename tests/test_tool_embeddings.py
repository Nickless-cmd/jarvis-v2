"""Værktøjs-embeddings skal ramme det samme sted som alle andre embeddings.

24/9-2026: dette modul havde sin egen adresse —
``os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")`` — og ramte derfor
det GPU Jarvis' arbejdsmodel kører på. Målt: `qwen3:4b` (4916 MiB) og
`nomic-embed-text` lå begge på GTX 1070 mens GTX 1050 Ti stod tom, og et
embed-kald gik fra 0,14 s i tomgang til 26 s under belastning.

Mekanismen til at pege embeddings et andet sted hen fandtes allerede
(`embed_ollama_base_url`). Den gjaldt bare kun ét modul.
"""
from __future__ import annotations

import importlib


def _frisk():
    import core.services.tool_embeddings as te
    return importlib.reload(te)


def test_adressen_foelger_den_faelles_resolver(monkeypatch) -> None:
    """Uden env-override skal modulet spørge `embed_base_url()`."""
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key",
        lambda navn, *a, **k: ("http://127.0.0.1:11435"
                               if navn == "embed_ollama_base_url" else None),
    )
    te = _frisk()
    assert te._embed_base() == "http://127.0.0.1:11435", (
        "tool_embeddings følger ikke med når embeddings flyttes til et andet GPU"
    )


def _fang_url(monkeypatch) -> list[str]:
    """Fang den URL `_compute_embedding` faktisk POSTer til."""
    urls: list[str] = []

    class _Svar:
        status_code = 200
        def raise_for_status(self): ...
        def json(self): return {"embedding": [0.0] * 768}

    class _Requests:
        @staticmethod
        def post(url, **kw):
            urls.append(url)
            return _Svar()

    import sys
    monkeypatch.setitem(sys.modules, "requests", _Requests)
    return urls


def test_en_bevidst_override_vinder(monkeypatch) -> None:
    """`OLLAMA_BASE_URL` fandtes før rettelsen og skal stadig virke.

    En rettelse må ikke fjerne en knap nogen kan have taget i brug. Testen
    måler den URL der FAKTISK kaldes — min første udgave sammenlignede
    positioner i kildeteksten og fandt funktionens definition i stedet for
    dens brug. Se `source_guards_need_ast`.
    """
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://et-andet-sted:9999")
    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key",
        lambda navn, *a, **k: ("http://127.0.0.1:11435"
                               if navn == "embed_ollama_base_url" else None),
    )
    urls = _fang_url(monkeypatch)
    te = _frisk()
    te._compute_embedding("hej")
    assert urls == ["http://et-andet-sted:9999/api/embeddings"], (
        f"env-overriden vandt ikke: {urls}"
    )


def test_uden_override_bruges_den_faelles_adresse(monkeypatch) -> None:
    """Og uden env-var skal kaldet lande på den dedikerede embed-instans."""
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key",
        lambda navn, *a, **k: ("http://127.0.0.1:11435"
                               if navn == "embed_ollama_base_url" else None),
    )
    urls = _fang_url(monkeypatch)
    te = _frisk()
    te._compute_embedding("hej")
    assert urls == ["http://127.0.0.1:11435/api/embeddings"], (
        f"kaldet ramte ikke den dedikerede instans: {urls}"
    )


def test_faldbagen_kaster_ikke(monkeypatch) -> None:
    """Kan resolveren ikke nås, skal modulet stadig have en brugbar adresse.

    Et embed-kald der kaster er værre end et der er langsomt — så forsvinder
    værktøjs-routingen helt i stedet for bare at vente.
    """
    def _braekker(*a, **k):
        raise RuntimeError("ingen runtime.json")

    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", _braekker)
    monkeypatch.setattr(
        "core.runtime.provider_router.load_provider_router_registry", _braekker)
    te = _frisk()
    assert te._embed_base().startswith("http")


def test_ingen_hardkodet_vaert_i_embed_kaldet() -> None:
    """AST, ikke grep — en streng-literal må ikke bære både vært og sti.

    Grep måler næsten ingenting: tidligere samme dag bestod en af mine tests
    fordi navnet den ledte efter stod i en import-linje.
    """
    import ast
    import inspect

    import core.services.tool_embeddings as te

    træ = ast.parse(inspect.getsource(te))
    syndere = [
        f"linje {n.lineno}: {n.value!r}"
        for n in ast.walk(træ)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and "/api/embed" in n.value
        and ("://" in n.value or "localhost" in n.value or "127.0.0.1" in n.value)
    ]
    assert not syndere, "værten er skrevet ind i kaldet:\n  " + "\n  ".join(syndere)
