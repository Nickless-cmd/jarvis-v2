"""Hygiejne-vagten skal AFVISE. Den har kørt uden en test siden den blev skrevet.

En vagt uden en test er værre end ingen vagt: ingen vagt ved man er ingen
vagt, men en tavs vagt ligner tryghed. Den her blokerede to af mine commits i
dag, så den VIRKER — men det vidste vi kun fordi jeg tilfældigvis ramte den.
"""
from pathlib import Path

import scripts.enforce_commit_hygiene as h


def _filer(monkeypatch, stier):
    monkeypatch.setattr(h, "_staged_files", lambda: [Path(s) for s in stier])
    monkeypatch.setattr(h, "_merge_in_progress", lambda: False)


def test_kode_og_stillads_i_samme_commit_afvises(monkeypatch, capsys):
    """Den altid-blokerende regel: kode sammen med værktøjs-stillads."""
    _filer(monkeypatch, ["core/services/x.py", ".claude/settings.json"])
    assert h.main() == 1
    assert "COMMIT HYGIENE GATE" in capsys.readouterr().out


def test_koekkenvask_over_tyve_filer_i_flere_domaener_afvises(monkeypatch, capsys):
    _filer(monkeypatch, [f"core/services/f{i}.py" for i in range(15)]
                        + [f"apps/api/g{i}.py" for i in range(8)])
    assert h.main() == 1
    assert "Kitchen-sink" in capsys.readouterr().out


def test_praecis_paa_graensen_gaar_igennem(monkeypatch):
    """20 filer er tilladt; 21 er ikke. Grænsen skal stå præcis hvor den siger."""
    _filer(monkeypatch, [f"core/f{i}.py" for i in range(10)]
                        + [f"apps/api/g{i}.py" for i in range(10)])
    assert h.main() == 0
    _filer(monkeypatch, [f"core/f{i}.py" for i in range(11)]
                        + [f"apps/api/g{i}.py" for i in range(10)])
    assert h.main() == 1


def test_mange_filer_i_ET_domaene_er_ikke_en_koekkenvask(monkeypatch):
    """En stor, fokuseret ændring er præcis det vagten IKKE skal ramme."""
    _filer(monkeypatch, [f"core/services/f{i}.py" for i in range(40)])
    assert h.main() == 0


def test_merge_springer_stoerrelsen_over(monkeypatch, capsys):
    """Begge sider er allerede gået gennem porten hver for sig."""
    monkeypatch.setattr(h, "_staged_files", lambda: [Path(f"core/f{i}.py") for i in range(50)]
                                                    + [Path("apps/api/g.py")])
    monkeypatch.setattr(h, "_merge_in_progress", lambda: True)
    assert h.main() == 0
    assert "merge commit" in capsys.readouterr().out


def test_ingen_staged_filer_er_ikke_en_fejl(monkeypatch):
    _filer(monkeypatch, [])
    assert h.main() == 0


def test_bloed_advarsel_blokerer_ikke(monkeypatch, capsys):
    """6-20 filer over tre domæner: en advarsel, ikke en spærring."""
    _filer(monkeypatch, ["core/a.py", "apps/api/b.py", "scripts/c.py",
                         "tests/d.py", "docs/e.md", "workspace/f.txt"])
    assert h.main() == 0
    assert "WARNING" in capsys.readouterr().out
