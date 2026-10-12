"""Tests for memory_maintenance_daemon — per-bruger-vedligeholdelse (12/10-2026).

Baggrund (målt 12/10-2026): daemonen pegede på `shared_dir()/MEMORY.md` — en
24 KB fil som ikke er nogen brugers hukommelse. Bjørn: «der er flere brugere».
Den tikker nu ALLE registrerede workspaces.

Samme måling afdækkede to fejl i selve merge-reglen, som disse tests låser:

* **Containment-reglen** stod for 81 af 94 kandidater på Bjørns fil, og de var
  alle forkerte — `Hardware` blev slået sammen med `VESC — hardware-status`.
* **Niveau-blindheden**: af 53 eksakte dubletter lå ALLE på niveau 3
  (`### Læren`, `### Fejlen`) under FORSKELLIGE forældre, så den ville lime to
  ubeslægtede hændelser sammen.

Plus en crash: `re.subn` fik indholdet uescaped som erstatning, så enhver
sektion med en backslash kastede `bad escape`.
"""
from __future__ import annotations

from pathlib import Path

from core.services import memory_maintenance_daemon as mm


def _sandkasse(monkeypatch, tmp_path: Path, filer: dict[str, str]) -> Path:
    """Peg daemonen på et temp-workspace-rod og skriv MEMORY.md-filerne."""
    ws_root = tmp_path / "workspaces"
    for navn, indhold in filer.items():
        d = ws_root / navn
        d.mkdir(parents=True, exist_ok=True)
        (d / "MEMORY.md").write_text(indhold, encoding="utf-8")
    monkeypatch.setattr(
        mm, "_memory_md", lambda workspace: ws_root / workspace / "MEMORY.md"
    )
    monkeypatch.setattr(mm, "_last_tick_at", None)
    return ws_root


def test_peger_paa_brugerens_workspace_ikke_shared(monkeypatch, tmp_path):
    """Den gamle sti var `shared_dir()/MEMORY.md` — ikke nogen brugers fil."""
    ws_root = _sandkasse(monkeypatch, tmp_path, {})
    sti = mm._memory_md("bjorn")
    assert sti == ws_root / "bjorn" / "MEMORY.md"
    assert "shared" not in str(sti)


def test_target_workspaces_daekker_alle_registrerede_brugere():
    """Unionen skal mindst rumme alle brugere fra users.json."""
    from core.identity.users import load_users

    forventet = {u.workspace for u in load_users() if u.workspace}
    assert forventet <= set(mm._target_workspaces())


def test_tik_vedligeholder_hver_bruger_ikke_kun_bjorn(monkeypatch, tmp_path):
    """Kernen i rettelsen: én brugers fil er ikke nok."""
    _sandkasse(monkeypatch, tmp_path, {
        "a": "## Same\n\nx\n\n## Same\n\ny\n",
        "b": "## One\n\nz\n\n## Two\n\nw\n",
    })
    monkeypatch.setattr(mm, "_target_workspaces", lambda: ["a", "b"])

    res = mm.tick_memory_maintenance_daemon()

    assert set(res["workspaces"]) == {"a", "b"}
    assert res["users"] == 2


def test_en_brugers_fejl_stopper_ikke_de_andre(monkeypatch, tmp_path):
    """Én utæsbar fil må ikke dræbe cyklussen for de øvrige brugere."""
    _sandkasse(monkeypatch, tmp_path, {
        "god": "## Same\n\nx\n\n## Same\n\ny\n",
    })
    monkeypatch.setattr(mm, "_target_workspaces", lambda: ["braendt", "god"])

    aegte = mm._maintain_workspace

    def _braendt(workspace: str) -> dict:
        if workspace == "braendt":
            raise OSError("simuleret ulaeselig fil")
        return aegte(workspace)

    monkeypatch.setattr(mm, "_maintain_workspace", _braendt)
    res = mm.tick_memory_maintenance_daemon()

    assert "error" in res["workspaces"]["braendt"]
    assert "god" in res["workspaces"]


def test_merger_kun_topniveau(monkeypatch, tmp_path):
    """`### Læren` under to FORSKELLIGE forældre må ikke smelte sammen."""
    ws_root = _sandkasse(monkeypatch, tmp_path, {
        "u": "## Event A\n\n### Læren\n\nalpha\n\n## Event B\n\n### Læren\n\nbeta\n",
    })

    res = mm._maintain_workspace("u")

    assert res["tier_a_merged"] == 0
    tekst = (ws_root / "u" / "MEMORY.md").read_text(encoding="utf-8")
    assert "alpha" in tekst and "beta" in tekst


def test_containment_reglen_er_væk(monkeypatch, tmp_path):
    """`Hardware` er indeholdt i `VESC — hardware-status`, men er ikke en dublet."""
    _sandkasse(monkeypatch, tmp_path, {
        "u": "## Hardware\n\nkort\n\n## VESC — hardware-status (2026-09-26)\n\nlang tekst\n",
    })

    res = mm._maintain_workspace("u")

    assert res["tier_a_merged"] == 0


def test_eksakt_dublet_paa_topniveau_merges_og_bevarer_indhold(monkeypatch, tmp_path):
    """Den ægte dublet skal stadig fanges — uden at tabe en linje."""
    ws_root = _sandkasse(monkeypatch, tmp_path, {
        "u": "## Dup\n\nalpha linje\n\n## Dup\n\nbeta linje\n",
    })

    res = mm._maintain_workspace("u")

    assert res["tier_a_merged"] == 1
    tekst = (ws_root / "u" / "MEMORY.md").read_text(encoding="utf-8")
    assert "alpha linje" in tekst
    assert "beta linje" in tekst


def test_indhold_med_backslash_crasher_ikke(monkeypatch, tmp_path):
    """Regressionsvaern: `re.subn` kastede `bad escape` paa en backslash."""
    ws_root = _sandkasse(monkeypatch, tmp_path, {
        "u": "## Dup\n\nsti C:\\x\\y og mere\n\n## Dup\n\nanden linje\n",
    })

    res = mm._maintain_workspace("u")

    assert res["tier_a_merged"] == 1
    tekst = (ws_root / "u" / "MEMORY.md").read_text(encoding="utf-8")
    assert "C:\\x\\y" in tekst
    assert "anden linje" in tekst


def test_tier_b_springes_over_paa_store_filer_og_rapporteres(monkeypatch, tmp_path):
    """Tier B er O(n²); på store filer skal den springes over — og SIGE det."""
    stor = "".join(
        f"## S{i}\n\nlinje {i} med nok indhold til at blive sammenlignet\n\n"
        for i in range(mm._MAX_TIER_B_SECTIONS + 5)
    )
    _sandkasse(monkeypatch, tmp_path, {"u": stor})

    res = mm._maintain_workspace("u")

    assert res["tier_b_skipped"].startswith("too_many_sections:")
    assert res["tier_b_flagged"] == 0
