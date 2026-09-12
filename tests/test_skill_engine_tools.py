"""Smoke tests for skill_engine_tools — tool wrappers around skill_engine.

Existing tests in tests/test_skill_engine.py cover the engine itself.
This file verifies the tool-layer imports and basic plumbing.
"""
from __future__ import annotations

from core.tools import skill_engine_tools as tools


def test_module_importable():
    """Verify module loads and key exec functions exist."""
    assert hasattr(tools, "_exec_skill_list")
    assert hasattr(tools, "_exec_skill_search")
    assert hasattr(tools, "_exec_skill_invoke")
    assert hasattr(tools, "_exec_skill_create")
    assert hasattr(tools, "_exec_skill_delete")
    assert hasattr(tools, "_exec_skill_import")
    assert hasattr(tools, "_exec_skill_reload")
    assert hasattr(tools, "_exec_skill_suggest")


def test_context_tags_in_exec_skill_list():
    """Verify _exec_skill_list reads context_tags from args (C2 gate)."""
    # Just verify the function accepts args dict with context_tags
    import inspect
    sig = inspect.signature(tools._exec_skill_list)
    assert "args" in sig.parameters


def test_context_tags_in_exec_skill_search():
    """Verify _exec_skill_search reads context_tags from args (C2 gate)."""
    import inspect
    sig = inspect.signature(tools._exec_skill_search)
    assert "args" in sig.parameters


# ── lokal embedder + leksikalsk anker (12/9-2026) ────────────────────────
#
# Matcheren hang paa HuggingFaces hostede API. Maalt paa runtime svarede den
# «HF HTTP 402: You have depleted your monthly included credits» — hvert kald
# fejlede, except fangede det, og funktionen returnerede [] i syv uger. Prompt-
# afsnittet «relevant skills» var derfor altid tomt.
#
# Den lokale embedder loeser tilgaengeligheden, men ikke hele problemet: den
# RANGERER godt og kan ikke sige «ingen passer». Maalt over de 66 installerede
# skills fik kontrollen «hvad er klokken» 0,640 paa en irrelevant skill —
# hoejere end en korrekt match paa 0,633. Derfor ankeret.

def _falsk_embedder(monkeypatch, vaegte):
    """Embedder hvor ligheden bestemmes af et opslag, saa proeven maaler
    ANKERET og ikke Ollamas humoer."""
    import core.services.tool_embeddings as TE

    def fake(noegle, tekst):
        for n, v in vaegte.items():
            if n in (tekst or "").lower():
                return v
        return [0.0, 1.0]
    monkeypatch.setattr(TE, "get_embedding", fake)


def test_uden_leksikalsk_anker_vises_ingen_skill(monkeypatch):
    """DEN afgoerende proeve. Embedderen peger altid paa NOGET; ankeret er det
    eneste der kan sige at intet passer."""
    from core.tools import skill_engine_tools as T
    monkeypatch.setattr(T.skill_engine, "list_skills", lambda: [
        {"name": "tdd", "description": "test driven development", "use_when": "naar du skriver tests"},
    ])
    _falsk_embedder(monkeypatch, {"tdd": [1.0, 0.0], "test": [1.0, 0.0]})
    # 'hvad er klokken' deler intet betydningsbaerende ord med skillen
    assert T._suggest_skills_for_query(query="hvad er klokken", threshold=0.0) == []


def test_med_anker_vises_den(monkeypatch):
    """Kontrolarm. Uden den ville en matcher der ALTID afviste bestaa ovenfor."""
    from core.tools import skill_engine_tools as T
    monkeypatch.setattr(T.skill_engine, "list_skills", lambda: [
        {"name": "youtube-downloader", "description": "hent videoer fra youtube",
         "use_when": "naar du skal hente en youtube-video"},
    ])
    _falsk_embedder(monkeypatch, {"youtube": [1.0, 0.0]})
    r = T._suggest_skills_for_query(query="hent en youtube-video ned", threshold=0.0)
    assert [x["name"] for x in r] == ["youtube-downloader"]
    assert "youtube" in r[0]["anker"]


def test_bindestreg_i_navnet_giver_to_ord():
    """«youtube-downloader» skal bidrage med baade «youtube» og «downloader»,
    ellers ville et navn-match kraeve hele navnet ordret."""
    from core.tools.skill_engine_tools import _skill_ord
    o = _skill_ord("youtube-downloader", "")
    assert "youtube" in o and "downloader" in o


def test_stopord_kan_ikke_baere_et_anker():
    """Ellers ville «kan du lige...» matche enhver skill der ogsaa siger «kan»."""
    from core.tools.skill_engine_tools import _betydende_ord
    o = _betydende_ord("kan du lige minde mig om noget")
    assert "kan" not in o and "lige" not in o
    assert "minde" in o


def test_HF_kaldes_ikke_laengere(monkeypatch):
    """Afhaengigheden der loeb toer for kredit maa ikke kunne snige sig ind igen."""
    import inspect
    from core.tools import skill_engine_tools as T
    kilde = inspect.getsource(T._suggest_skills_for_query)
    # Forbyd KALDET, ikke ordet. Foerste udgave af denne test forboed selve
    # ordet — og faldt over kommentaren der forklarer hvorfor afhaengigheden
    # blev fjernet. En test der rammer sin egen begrundelse maaler det forkerte.
    assert "hf_inference_tools import semantic_similarity" not in kilde
    assert "semantic_similarity(" not in kilde
    assert "tool_embeddings import get_embedding" in kilde
