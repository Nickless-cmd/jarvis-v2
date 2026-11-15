"""Kerne-kuratoren: løft det brugte op, foreslå det ubrugte ned (blok A)."""
from __future__ import annotations

import pytest

from core.services import kerne_curator as KC
from core.services.prompt_sections import learned_about_user as LAU

_USER_MD = """# USER.md

## Kerne
- Sprog: dansk altid
- Svar: korte og grounded

## Lært
- Bjørn vil have korte mellemregninger mellem tool-kald (2026-09-02, sagt eksplicit)
- Kalendermøder lægges altid om formiddagen (2026-08-30, udledt)

## Who He Is
- Bygger Jarvis som en vedvarende digital entitet paa sin egen maskine
- Arbejder oftest sent om aftenen og i weekender
- Foretrækker spec og plan før kodning, og vil se belæg frem for paastande
- Kører Proxmox derhjemme med flere containere og en pfSense-router
"""


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "USER.md").write_text(_USER_MD, encoding="utf-8")
    monkeypatch.setattr(KC, "_workspace_dir", lambda: tmp_path)
    return tmp_path


def test_promotes_only_what_has_been_used_enough(workspace, monkeypatch):
    monkeypatch.setattr(LAU, "selection_counts", lambda: {
        "bjørn vil have korte mellemregninger mellem tool-kald": 40,
        "kalendermøder lægges altid om formiddagen": 1,
    })
    cands = KC.promotion_candidates(workspace)
    assert len(cands) == 1 and cands[0]["used"] == 40
    text = KC.build_proposal_text(workspace)
    assert "mellemregninger" in text and "40 gange" in text


def test_long_lines_are_never_promoted(workspace, monkeypatch):
    """15/11-2026: antal valg korrelerede med linjens LÆNGDE (r = 0,648).

    En lang spec matcher bredt fordi den har mange ord — ikke fordi den er en
    regel. Målt i produktion: den mest valgte linje var 1.704 tegn og allerede
    leveret. Den hører i Lært, hvor den udvælges når den er relevant.
    """
    # Fast længde — IKKE udledt af loftet. En linje på `cap + 1` ville vokse med
    # loftet og aldrig kunne fælde vagten (målt 15/11-2026: testen var grøn selv
    # med loftet slået fra, fordi linjen så blev 100.000 tegn og stadig blev filtreret).
    lang = "x" * 400
    (workspace / "USER.md").write_text(
        f"# USER.md\n\n## Kerne\n- Sprog: dansk altid\n\n## Lært\n- {lang}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(LAU, "selection_counts", lambda: {lang.lower()[:120]: 1483})
    # Den ligger i Lært og har 1.483 valg — men den er for lang til Kerne.
    assert any(r["text"] == lang for r in LAU.learned_lines(workspace))
    assert KC.promotion_candidates(workspace) == []


def test_demotion_wins_when_kerne_is_over_the_cap(workspace, monkeypatch):
    """Den blinde vinkel: i produktion er der ALTID promotion-kandidater.

    Promote blev tjekket først, så demotion-grenen kørte aldrig og Kerne voksede
    til 46 linjer mod loftet på 25 — mens kuratoren foreslog at fylde MERE på.
    """
    linjer = "\n".join(f"- kerne-linje nummer {i} med lidt tekst" for i in range(30))
    (workspace / "USER.md").write_text(
        f"# USER\n\n## Kerne\n{linjer}\n\n## Lært\n"
        "- Bjørn vil have korte mellemregninger mellem tool-kald (2026-09-02)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(LAU, "selection_counts", lambda: {
        "bjørn vil have korte mellemregninger mellem tool-kald": 999,
    })
    # Der ER en promoverbar kandidat …
    assert KC.promotion_candidates(workspace)
    # … men der er ikke plads, så forslaget skal være at gøre plads.
    text = KC.build_proposal_text(workspace)
    assert "loft 25" in text
    assert "mellemregninger" not in text


def test_no_proposal_when_nothing_matured(workspace, monkeypatch):
    monkeypatch.setattr(LAU, "selection_counts", lambda: {})
    assert KC.promotion_candidates(workspace) == []
    assert KC.demotion_candidates(workspace) == []
    assert KC.build_proposal_text(workspace) == ""


def test_demotion_only_above_the_cap(tmp_path, monkeypatch):
    lines = "\n".join(f"- kerne-linje nummer {i} med lidt tekst" for i in range(30))
    (tmp_path / "USER.md").write_text(f"# USER\n\n## Kerne\n{lines}\n\n## Lært\n- noget lært her\n",
                                      encoding="utf-8")
    monkeypatch.setattr(KC, "_workspace_dir", lambda: tmp_path)
    monkeypatch.setattr(LAU, "selection_counts", lambda: {})
    assert len(KC.demotion_candidates(tmp_path)) == 5
    assert "loft 25" in KC.build_proposal_text(tmp_path)


def test_demotion_takes_the_expensive_lines_not_the_core_rules(tmp_path, monkeypatch):
    """15/11-2026: demotion tog de FØRSTE linjer — altså «Sprog: dansk», «Tone»
    og «Svar», de mest fundamentale regler i prompten. Den ærlige akse er
    længde: lange linjer koster mest pr. tur og er specs frem for regler.
    """
    kerne = (
        "- Sprog: dansk altid\n"
        "- Tone: afslappet og direkte\n"
        "- Svar: korte og grounded\n"
    ) + "\n".join(f"- {'x' * 200} lang linje {i}" for i in range(27))
    (tmp_path / "USER.md").write_text(
        f"# USER\n\n## Kerne\n{kerne}\n\n## Lært\n- noget lært her\n", encoding="utf-8"
    )
    monkeypatch.setattr(KC, "_workspace_dir", lambda: tmp_path)
    demote = KC.demotion_candidates(tmp_path)
    assert len(demote) == 5
    assert not any("Sprog:" in line or "Tone:" in line or "Svar:" in line
                   for line in demote)
    # Det der flyttes, er de dyre linjer — ikke de korte kerne-regler.
    assert all(len(" ".join(line.split())) > 100 for line in demote)


def test_promote_moves_the_line_between_sections(workspace):
    res = KC.promote_to_kerne("Kalendermøder lægges altid om formiddagen")
    assert res["moved"] is True
    text = (workspace / "USER.md").read_text(encoding="utf-8")
    assert text.count("Kalendermøder") == 1
    assert "Kalendermøder" in LAU.section_body(text, LAU.CORE_HEADINGS)
    assert "Kalendermøder" not in LAU.section_body(text, LAU.LEARNED_HEADINGS)


def test_demote_moves_it_back(workspace):
    KC.promote_to_kerne("Kalendermøder lægges altid om formiddagen")
    res = KC.demote_from_kerne("Kalendermøder lægges altid om formiddagen")
    assert res["moved"] is True
    text = (workspace / "USER.md").read_text(encoding="utf-8")
    assert "Kalendermøder" in LAU.section_body(text, LAU.LEARNED_HEADINGS)
    assert "Kalendermøder" not in LAU.section_body(text, LAU.CORE_HEADINGS)


def test_unknown_line_is_never_invented(workspace):
    res = KC.promote_to_kerne("noget der slet ikke står i filen")
    assert res["moved"] is False and res["reason"] == "not-found-in-source"


def test_cadence_blocks_a_second_run_within_the_week(workspace, monkeypatch):
    import datetime as dt
    state: dict[str, object] = {}
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value",
                        lambda k, d=None: state.get(k, d))
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value",
                        lambda k, v: state.__setitem__(k, v))
    monkeypatch.setattr(LAU, "selection_counts", lambda: {})
    now = dt.datetime(2026, 9, 4, tzinfo=dt.UTC)
    assert KC.run_kerne_curator(now=now)["ran"] is True
    assert KC.run_kerne_curator(now=now + dt.timedelta(days=2))["ran"] is False
    assert KC.run_kerne_curator(now=now + dt.timedelta(days=8))["ran"] is True
