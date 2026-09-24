"""Alle embedding-kald skal spørge ÉT sted hvor de skal hen.

24/9-2026: `qwen3:4b` (4916 MiB) og `nomic-embed-text` (610 MiB) lå begge på
GTX 1070, mens GTX 1050 Ti stod tom med 46 MiB. Når arbejdsmodellen genererer,
mætter den kortet — et embed-kald gik fra 0,14 s i tomgang til 26 s under
belastning, og 27 af 31 sekunder i en kold promptopbygning lå netop dér.

Løsningen er en dedikeret ollama på det tomme kort. Men den virker kun for de
kaldere der *spørger* hvor de skal hen. Mekanismen fandtes allerede —
runtime-nøglen `embed_ollama_base_url`, bygget mod præcis dette symptom — og
`semantic_memory` brugte den. Tre andre veje havde deres egen hardkodede
adresse:

    memory_search.py:23              _OLLAMA_BASE = "http://localhost:11434"
    tool_embeddings.py:61            os.getenv("OLLAMA_BASE_URL", "…11434")
    core/tools/session_search.py:152 hardkodet i selve kaldet

En delt spærre der kun gælder ét sted er ikke en spærre. Det samme gjaldt
`_HOT_RESOLVE_CAP_S` tidligere samme dag.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROD = Path(__file__).resolve().parents[1]

#: De moduler der FAKTISK laver embedding-kald.
EMBED_MODULER = (
    "core/services/semantic_memory.py",
    "core/services/memory_search.py",
    "core/services/tool_embeddings.py",
    "core/tools/session_search.py",
)


@pytest.mark.parametrize("sti", EMBED_MODULER)
def test_ingen_hardkodet_vaert_i_et_embed_kald(sti: str) -> None:
    """AST, ikke grep.

    En kilde-vagt der greper efter en streng måler næsten ingenting — det lærte
    jeg samme dag, da en test bestod fordi navnet stod i en import-linje. Her
    parses filen, og hver eneste streng-literal undersøges: indeholder den både
    en ollama-adresse OG `/api/embed`, er værten skrevet ind i kaldet.
    """
    træ = ast.parse((ROD / sti).read_text(encoding="utf-8"))
    syndere: list[str] = []
    for n in ast.walk(træ):
        if not isinstance(n, ast.Constant) or not isinstance(n.value, str):
            continue
        v = n.value
        if "/api/embed" in v and ("://" in v or "localhost" in v or "127.0.0.1" in v):
            syndere.append(f"linje {n.lineno}: {v!r}")
    assert not syndere, (
        f"{sti} skriver værten ind i embed-kaldet — så følger den ikke med når "
        f"embeddings flyttes til et andet GPU:\n  " + "\n  ".join(syndere)
    )


def test_alle_veje_giver_samme_adresse(monkeypatch) -> None:
    """Sætter man nøglen, skal ALLE fire veje pege samme sted.

    Det er hele pointen: én instans på det tomme kort hjælper kun de kaldere
    der spørger.
    """
    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key",
        lambda navn, *a, **k: "http://127.0.0.1:11435" if navn == "embed_ollama_base_url" else None,
    )
    from core.services.memory_search import _ollama_base
    from core.services.semantic_memory import embed_base_url
    from core.services.tool_embeddings import _embed_base

    forventet = "http://127.0.0.1:11435"
    assert embed_base_url() == forventet
    assert _ollama_base() == forventet, "memory_search fulgte ikke med"
    assert _embed_base() == forventet, "tool_embeddings fulgte ikke med"


def test_en_bevidst_override_vinder_stadig(monkeypatch) -> None:
    """`OLLAMA_BASE_URL` skal stadig kunne tvinge tool_embeddings et andet sted hen.

    Rettelsen må ikke tage en knap væk der fandtes.
    """
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://et-helt-andet-sted:9999")
    import importlib

    import core.services.tool_embeddings as te
    importlib.reload(te)
    import inspect
    kilde = inspect.getsource(te)
    assert 'os.getenv("OLLAMA_BASE_URL")' in kilde, (
        "env-overriden er væk — en knap der fandtes blev fjernet"
    )


def test_faldbagen_er_uskadelig(monkeypatch) -> None:
    """Kan nøglen ikke læses, må embeddings ikke holde op med at virke.

    Den gamle adresse er stadig en fungerende ollama. Et embed-kald der
    KASTER er værre end et der er langsomt.
    """
    def _braekker(*a, **k):
        raise RuntimeError("ingen runtime.json her")

    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", _braekker)
    monkeypatch.setattr(
        "core.runtime.provider_router.load_provider_router_registry", _braekker)
    from core.services.memory_search import _ollama_base
    from core.services.semantic_memory import embed_base_url

    assert embed_base_url().startswith("http")
    assert _ollama_base().startswith("http")
