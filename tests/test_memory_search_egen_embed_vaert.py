"""memory_search's tunge batch skal kunne pege paa sin EGEN embed-vaert.

Maalt 10/10-2026: memory_search laa paa den faelles embed-vaert (11435), som
routeren ogsaa bruger. Vaerten koerer med -np 1 (én slot), saa en fuld
gen-indeksering (~2.859 chunks) blokerede routerens kald — ét maalt til 7,65 s
mod routerens 4 s-deadline. Noeglen her flytter BATCHEN vaek fra den
latency-kritiske sti; de to tests laaser begge veje.
"""

from __future__ import annotations

import pytest


def test_egen_noegle_vinder(monkeypatch) -> None:
    """Er den dedikerede noegle sat, skal den bruges — ikke den faelles."""
    from core.services import memory_search as ms

    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key",
        lambda key, *a, **k: "http://127.0.0.1:11434" if key == "memory_search_embed_ollama_base_url" else "",
    )
    assert ms._ollama_base() == "http://127.0.0.1:11434"


def test_tom_noegle_falder_tilbage_til_faelles(monkeypatch) -> None:
    """Uden noeglen (eller naar den ikke kan laeses) er adfaerden som foer."""
    from core.services import memory_search as ms

    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", lambda key, *a, **k: "")
    monkeypatch.setattr(
        "core.services.semantic_memory.embed_base_url",
        lambda: "http://127.0.0.1:11435",
    )
    assert ms._ollama_base() == "http://127.0.0.1:11435"


def test_resolver_fejl_giver_en_adresse_der_virker(monkeypatch) -> None:
    """Kan hverken noeglen eller den faelles resolver naas, maa kaldet ikke kaste."""
    from core.services import memory_search as ms

    def _braek(*a, **k):
        raise RuntimeError("ingen adgang")

    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", _braek)
    monkeypatch.setattr("core.services.semantic_memory.embed_base_url", _braek)
    assert ms._ollama_base().startswith("http://")
