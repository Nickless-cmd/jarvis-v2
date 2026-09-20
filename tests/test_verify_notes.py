"""Note-vagten skal AFVISE — især når fravalgene mangler."""
import scripts.verify_notes as v

_GOD = """# Note: noget

Status: implementeret

## Problem
x
## Beslutning
y
## Overvejede alternativer
z
## Konsekvenser
q
"""


def _note(tmp_path, monkeypatch, navn, tekst, status="implementeret", slags="forenkling"):
    mappe = tmp_path / "docs/notes" / status / slags
    mappe.mkdir(parents=True, exist_ok=True)
    (mappe / navn).write_text(tekst, encoding="utf-8")
    monkeypatch.setattr(v, "NOTER", tmp_path / "docs/notes")
    monkeypatch.setattr(v, "ROD", tmp_path)
    return mappe / navn


def test_en_hel_note_gaar_igennem(tmp_path, monkeypatch, capsys):
    _note(tmp_path, monkeypatch, "2026-09-20-en-ting.md", _GOD)
    assert v.main([]) == 0
    assert "1 forenklinger" in capsys.readouterr().out


def test_manglende_fravalg_afvises(tmp_path, monkeypatch, capsys):
    """Den vigtigste overskrift. Uden den er noten en annoncering."""
    uden = _GOD.replace("## Overvejede alternativer\nz\n", "")
    _note(tmp_path, monkeypatch, "2026-09-20-en-ting.md", uden)
    assert v.main([]) == 1
    assert "Overvejede alternativer" in capsys.readouterr().out


def test_forkert_raekkefoelge_afvises(tmp_path, monkeypatch, capsys):
    byttet = """# N

Status: implementeret

## Beslutning
y
## Problem
x
## Overvejede alternativer
z
## Konsekvenser
q
"""
    _note(tmp_path, monkeypatch, "2026-09-20-en-ting.md", byttet)
    assert v.main([]) == 1
    assert "forkert rækkefølge" in capsys.readouterr().out


def test_status_der_modsiger_mappen_afvises(tmp_path, monkeypatch, capsys):
    """En note der siger «foreslaaet» i mappen «implementeret» lyver om koden."""
    _note(tmp_path, monkeypatch, "2026-09-20-en-ting.md",
          _GOD.replace("implementeret", "foreslaaet"))
    assert v.main([]) == 1
    assert "Status: implementeret" in capsys.readouterr().out


def test_filnavn_uden_dato_afvises(tmp_path, monkeypatch, capsys):
    _note(tmp_path, monkeypatch, "en-ting.md", _GOD)
    assert v.main([]) == 1
    assert "ÅÅÅÅ-MM-DD" in capsys.readouterr().out


def test_den_flade_bunke_roeres_ikke(tmp_path, monkeypatch):
    """De 21 gamle filer ligger i docs/notes/ selv — de må ikke tælles med."""
    (tmp_path / "docs/notes").mkdir(parents=True)
    (tmp_path / "docs/notes/gammel-uden-form.md").write_text("hej", encoding="utf-8")
    monkeypatch.setattr(v, "NOTER", tmp_path / "docs/notes")
    monkeypatch.setattr(v, "ROD", tmp_path)
    assert v.noter() == [] and v.main([]) == 0


def test_repoets_egne_noter_holder_formen():
    assert v.main([]) == 0
    assert any(p.parent.name == "forenkling" for p in v.noter())
