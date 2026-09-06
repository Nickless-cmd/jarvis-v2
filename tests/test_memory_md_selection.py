"""Task 2 (memory repair 2026-09-04): MEMORY.md is selected by SECTION, not "last 4 lines"."""
from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pytest

from core.services import memory_search
from core.services.prompt_sections.memory_md_selection import select_memory_md_sections

MEMORY_MD = """# MEMORY

## Hardware
- ChiefOne er min fysiske vært, Gigabyte B650, Ubuntu 24.04.
- GPU 1070 i containeren, ollama embeddings.

## pfSense nøgle
- pfsense api-nøglen blev flyttet fra kode til .env via env_override.
- pfsense nøgle besluttet: python-dotenv i requirements.

## Wait-state ads
- Idlen bedste-case €100/md, Sponsoric overvej.
- Wait-state ads dækker ikke API-regningen.
"""


def _bow(text: str) -> np.ndarray:
    """Deterministic bag-of-words hashing embedder (768-dim) for tests."""
    v = np.zeros(768, dtype=np.float32)
    for w in text.lower().replace("-", " ").split():
        w = w.strip(".,:;()[]«»\"'")
        if len(w) < 3:
            continue
        v[hash(w) % 768] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


@pytest.fixture
def ws(tmp_path, monkeypatch) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "MEMORY.md").write_text(MEMORY_MD, encoding="utf-8")
    monkeypatch.setattr(memory_search, "_embed_ollama", lambda texts: np.stack([_bow(t) for t in texts]))
    monkeypatch.setattr(memory_search, "_embed_single", lambda text: _bow(text))
    memory_search._MEM_INDEX.clear()
    files = memory_search._memory_files(ws)
    mtimes = {str(f): memory_search._file_mtime(f) for f in files}
    memory_search._build_and_cache_index(files, mtimes, ws)  # synchronous, deterministic
    return ws


def test_selects_matching_section_with_heading(ws):
    lines = select_memory_md_sections(
        "hvor ligger pfsense api nøglen og hvad besluttede vi?", workspace_dir=ws,
    )
    assert lines, "expected at least one section"
    assert lines[0].startswith("§ pfSense nøgle:")
    assert "env_override" in lines[0]


def test_sections_are_deduped_by_heading_and_capped(ws):
    lines = select_memory_md_sections(
        "pfsense nøgle env_override python-dotenv", workspace_dir=ws, max_sections=3, max_chars=120,
    )
    headings = [ln.split(":")[0] for ln in lines]
    assert len(headings) == len(set(headings))
    assert sum(len(ln) for ln in lines) <= 120 or len(lines) == 1


def test_short_message_yields_nothing(ws):
    assert select_memory_md_sections("hej", workspace_dir=ws) == []


def test_search_memory_source_filter(ws):
    (ws / "USER.md").write_text("## Preferences\n- pfsense pfsense pfsense nøgle sprog dansk\n", encoding="utf-8")
    files = memory_search._memory_files(ws)
    mtimes = {str(f): memory_search._file_mtime(f) for f in files}
    memory_search._MEM_INDEX.clear()
    memory_search._build_and_cache_index(files, mtimes, ws)
    hits = memory_search.search_memory("pfsense nøgle", limit=5, sources=["MEMORY.md"], workspace_dir=ws)
    assert hits
    assert all(h["source"] == "MEMORY.md" for h in hits)


def test_selector_promotes_exact_match_over_semantic_noise(monkeypatch, tmp_path):
    def fake_search_memory(*args, **kwargs):
        return [
            {
                "section": "visible_output_text guard",
                "text": "Hukommelsen blev amputeret af tomme svar i agentiske runder.",
                "score": 0.95,
            },
            {
                "section": "Hardware",
                "text": "GPU-maskine LXC 107 kører Ollama med GTX 1070 passthrough.",
                "score": 0.40,
            },
        ]

    monkeypatch.setattr(memory_search, "search_memory", fake_search_memory)

    lines = select_memory_md_sections(
        "hvilken GPU har jeg og hvad bruges den til?",
        workspace_dir=tmp_path,
        max_sections=1,
    )

    assert lines == ["§ Hardware: GPU-maskine LXC 107 kører Ollama med GTX 1070 passthrough."]


def test_selector_falls_back_to_lexical_memory_scan(monkeypatch, tmp_path):
    (tmp_path / "MEMORY.md").write_text(
        "# MEMORY\n\n"
        "## Runtime støj\n"
        "- Tomme svar i agentiske runder.\n\n"
        "## Hardware\n"
        "- GPU-maskine LXC 107 kører Ollama med GTX 1070 passthrough.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        memory_search,
        "search_memory",
        lambda *args, **kwargs: [
            {
                "section": "Runtime støj",
                "text": "Tomme svar i agentiske runder.",
                "score": 0.90,
            }
        ],
    )

    lines = select_memory_md_sections(
        "hvilken GPU har jeg og hvad bruges den til?",
        workspace_dir=tmp_path,
        max_sections=1,
    )

    assert lines == ["§ Hardware: GPU-maskine LXC 107 kører Ollama med GTX 1070 passthrough."]


def test_curated_files_are_picked_by_mtime_not_name(tmp_path):
    ws = tmp_path / "ws2"
    (ws / "memory" / "curated").mkdir(parents=True)
    d = ws / "memory" / "curated"
    # 31 files named so that "curated-memory.md" sorts FIRST alphabetically …
    old = d / "curated-memory.md"
    old.write_text("# Curated\n- newest content\n", encoding="utf-8")
    now = time.time()
    for i in range(31):
        f = d / f"sansernes-arkiv-{i:02d}.md"
        f.write_text(f"# {i}\n- x\n", encoding="utf-8")
        os.utime(f, (now - 10_000 + i, now - 10_000 + i))  # all OLDER than curated-memory.md
    os.utime(old, (now, now))
    files = memory_search._memory_files(ws)
    names = {f.name for f in files}
    assert "curated-memory.md" in names, "newest file must survive the 30-file window"
    assert len([f for f in files if f.parent == d]) == 30
