"""Læsesiden for det Jarvis har lært om Bjørn (lærings-sløjfe 4/9, blok A).

Målt før: 146 præferencer i «## Durable Preferences» (linje 70 af 202) som
INGEN prompt-builder læste. Disse tests holder på at de nu kan nås.
"""
from __future__ import annotations

import pytest

from core.services.prompt_sections import learned_about_user as LAU

_USER_MD = """# USER.md — Bjørn

## Kerne
- **Sprog:** Dansk (altid)
- **Svar:** Korte, grounded

## Lært
- Bjørn vil have korte mellemregninger mellem tool-kald (2026-09-02, sagt eksplicit)
- Foretrækker ollama-lane fordi den svarer hurtigere end DeepSeek (2026-09-01, udledt)
- Kalendermøder lægges altid om formiddagen
- kort

## Personal
- Bor i Danmark

## Who He Is
- Bygger Jarvis som en vedvarende digital entitet paa sin egen maskine
- Arbejder oftest sent om aftenen og i weekender
- Foretrækker spec og plan før kodning, og vil se belæg frem for paastande
- Kører Proxmox derhjemme med flere containere og en pfSense-router
"""


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "USER.md").write_text(_USER_MD, encoding="utf-8")
    monkeypatch.setattr(LAU, "note_selected", lambda *_a, **_k: None)
    return tmp_path


def test_parses_lines_with_and_without_provenance(workspace):
    rows = LAU.learned_lines(workspace)
    texts = [r["text"] for r in rows]
    assert "Bjørn vil have korte mellemregninger mellem tool-kald" in texts
    assert "Kalendermøder lægges altid om formiddagen" in texts
    assert "kort" not in texts  # under 8 tegn → ikke en lærdom
    first = rows[0]
    assert first["date"] == "2026-09-02" and first["source"] == "sagt eksplicit"
    assert rows[2]["date"] == "" and rows[2]["source"] == ""


def test_kerne_and_laert_are_separate_sections(workspace):
    core = LAU.core_lines(workspace)
    assert any("Dansk" in line for line in core)
    assert not any("mellemregninger" in line for line in core)
    assert not any("Bor i Danmark" in r["text"] for r in LAU.learned_lines(workspace))


def test_selects_only_what_is_relevant(workspace):
    rows = LAU.select_learned_lines(
        "kan du skrive mellemregninger mellem tool-kaldene?", workspace_dir=workspace)
    assert len(rows) == 1
    assert "mellemregninger" in rows[0]["text"]
    assert LAU.select_learned_lines("hvad er vejret i morgen?", workspace_dir=workspace) == []
    assert LAU.select_learned_lines("hej", workspace_dir=workspace) == []


def test_section_text_carries_the_date(workspace):
    text = LAU.build_learned_section(
        "hvorfor er ollama hurtigere end deepseek?", workspace_dir=workspace)
    assert text.startswith("Lært om Bjørn")
    assert "ollama" in text and "(2026-09-01)" in text
    assert LAU.build_learned_section("hvad er klokken?", workspace_dir=workspace) == ""


def test_missing_laert_section_is_not_an_error(tmp_path):
    (tmp_path / "USER.md").write_text("# USER\n\n## Kerne\n- Dansk\n", encoding="utf-8")
    assert LAU.learned_lines(tmp_path) == []
    assert LAU.build_learned_section("noget om dansk sprog her", workspace_dir=tmp_path) == ""


def test_selection_is_counted_for_the_curator(tmp_path, monkeypatch):
    (tmp_path / "USER.md").write_text(_USER_MD, encoding="utf-8")
    seen: list[list[str]] = []
    monkeypatch.setattr(LAU, "note_selected", lambda texts: seen.append(list(texts)))
    LAU.select_learned_lines("noget om mellemregninger mellem tool-kald", workspace_dir=tmp_path)
    assert seen and "mellemregninger" in seen[0][0]
