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


# ── Profil-sektionen (15/11-2026) ───────────────────────────────────────────
# `## Personal` og `## People` havde nul læsere: `_workspace_file_section`
# erstatter hele USER.md med `## Kerne`, og Lært-udvælgelsen kræver 34 %
# ord-dækning som korte spørgsmål aldrig opnår. Familien var derfor usynlig.

_PROFILE_MD = """# USER

## Kerne
- Dansk

## Personal
- **Fødselsdag:** 7. august
- **Bor:** Graaesvej, Svendborg

## People
- **Saselin** — datter, 9 år, bor i plejefamilie
- **Liva** — ældste datter, 19 år

## Lært
- noget lært om mellemregninger (2026-09-01, sagt eksplicit)
"""


def test_profile_section_reads_personal_and_people(tmp_path):
    (tmp_path / "USER.md").write_text(_PROFILE_MD, encoding="utf-8")
    text = LAU.build_profile_section(workspace_dir=tmp_path)
    assert text.startswith("Om Bjørn")
    assert "7. august" in text
    assert "Saselin" in text and "Liva" in text


def test_people_is_not_displaced_by_a_long_personal_section(tmp_path):
    """Eget budget pr. sektion: Personal må ikke spise People-pladsen."""
    long_personal = "\n".join(f"- **Felt {i}:** " + "x" * 200 for i in range(30))
    (tmp_path / "USER.md").write_text(
        f"# USER\n\n## Personal\n{long_personal}\n\n## People\n- **Saselin** — datter\n",
        encoding="utf-8",
    )
    text = LAU.build_profile_section(workspace_dir=tmp_path, max_chars=500)
    assert "Saselin" in text


def test_profile_section_is_empty_without_the_sections(tmp_path):
    (tmp_path / "USER.md").write_text("# USER\n\n## Kerne\n- Dansk\n", encoding="utf-8")
    assert LAU.build_profile_section(workspace_dir=tmp_path) == ""


# ── 15/11-2026: ejestedordene floodede udvalget ────────────────────────────
# Målt: `min` stod i 48 af 964 linjer og var IKKE et stopord (kun `mine`/`dine`
# var). Den opfyldte dækningskravet alene, så spørgsmål som «hvad hedder min
# mindste datter?» og «hvor mange watt er min el-cykel?» gav nul linjer, mens
# en tilfældig linje med «min» kunne vinde. Tærsklen blev IKKE rørt — målt var
# fire tærskel-/regelvarianter alle ringere end at fjerne ordene.

_POSSESSIVE_MD = """# USER

## Lært
- Noget ganske andet om min kop og min tallerken (2026-09-01, udledt)
- **El-cykel:** kører allerede med 2 batterier, ét per motor (2026-09-02, sagt eksplicit)
- Hardware: han justerer selv blæserne på værten (2026-09-03, sagt eksplicit)
"""


def test_possessives_are_not_content_words():
    terms = LAU._terms("hvad hedder min mindste datter?")
    assert "min" not in terms and "mit" not in terms
    assert "datter" in terms and "mindste" in terms


def test_topic_question_selects_the_topic_line(tmp_path, monkeypatch):
    """«hvor mange watt er min el-cykel?» skal ramme el-cykel-linjen.

    FØR: `min` og `mange` talte med, så dækningen blev 1/4 = 0,25 — under
    tærsklen — og spørgsmålet fik nul linjer.
    """
    (tmp_path / "USER.md").write_text(_POSSESSIVE_MD, encoding="utf-8")
    monkeypatch.setattr(LAU, "note_selected", lambda *_a, **_k: None)
    rows = LAU.select_learned_lines(
        "hvor mange watt er min el-cykel?", workspace_dir=tmp_path
    )
    texts = [r["text"] for r in rows]
    assert any("El-cykel" in t for t in texts), texts
    assert not any("min kop" in t for t in texts), texts
