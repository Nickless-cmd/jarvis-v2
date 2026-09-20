"""Persistens-registret skal AFVISE et uregistreret format.

Hullet er målt på mig selv: jeg indførte `device_presence.json` — et nyt
varigt format med en håndskrevet «ignorér ukendte felter»-regel — uden at
registrere det nogen steder. Der var intet sted at registrere det.
"""
import json

import scripts.verify_persistens as v


def _opsaet(tmp_path, monkeypatch, kode: str, register: dict):
    (tmp_path / "core").mkdir(parents=True, exist_ok=True)
    (tmp_path / "core" / "m.py").write_text(kode, encoding="utf-8")
    reg = tmp_path / "register.json"
    reg.write_text(json.dumps({"formater": register}), encoding="utf-8")
    monkeypatch.setattr(v, "ROD", tmp_path)
    monkeypatch.setattr(v, "REGISTER", reg)
    monkeypatch.setattr(v, "OMRAADER", ("core",))


_SKRIV = 'save_json("min_nye_ting", {"a": 1})\n'


def test_et_uregistreret_format_afvises(tmp_path, monkeypatch, capsys):
    _opsaet(tmp_path, monkeypatch, _SKRIV, {})
    assert v.main([]) == 1
    assert "min_nye_ting" in capsys.readouterr().out


def test_et_registreret_format_gaar_igennem(tmp_path, monkeypatch):
    _opsaet(tmp_path, monkeypatch, _SKRIV,
            {"min_nye_ting": {"ejer": "core/m.py", "beskrivelse": "x",
                              "registreret": "2026-09-20"}})
    assert v.main([]) == 0


def test_et_format_ingen_roerer_laengere_meldes(tmp_path, monkeypatch, capsys):
    """Data kan stadig ligge på disken. Det skal nogen tage stilling til."""
    _opsaet(tmp_path, monkeypatch, "x = 1\n",
            {"glemt": {"ejer": "core/m.py", "beskrivelse": "x",
                       "registreret": "2026-01-01"}})
    assert v.main([]) == 1
    ud = capsys.readouterr().out
    assert "VÆK" in ud and "ryddes" in ud


def test_noeglen_findes_ogsaa_gennem_en_modul_konstant(tmp_path, monkeypatch):
    """`save_json(_NAVN, …)` er den form vores moduler faktisk bruger."""
    _opsaet(tmp_path, monkeypatch,
            '_NAVN = "via_konstant"\nsave_json(_NAVN, {})\n', {})
    assert "via_konstant" in v.noegler_i_traeet()


def test_ogsaa_en_LAESER_taeller_som_et_format(tmp_path, monkeypatch):
    """Et format der kun læses, er stadig et format vi har på disken."""
    _opsaet(tmp_path, monkeypatch, 'load_json("kun_laest", {})\n', {})
    assert "kun_laest" in v.noegler_i_traeet()


def test_beskrivelsen_hentes_fra_ejerens_docstring(tmp_path, monkeypatch):
    """En UDFYLD-plads bliver aldrig udfyldt. Modulets egen tekst er ægte."""
    _opsaet(tmp_path, monkeypatch, '"""Hvad den her gør.\n\nmere."""\n'
                                   'save_json("x", {})\n', {})
    assert v._modulbeskrivelse("core/m.py") == "Hvad den her gør."


def test_manglende_beskrivelser_er_efterslaeb_og_blokerer_ikke(tmp_path, monkeypatch, capsys):
    _opsaet(tmp_path, monkeypatch, _SKRIV,
            {"min_nye_ting": {"ejer": "core/m.py", "registreret": "2026-09-20",
                              "beskrivelse": "UDFYLD: core/m.py har ingen docstring"}})
    assert v.main([]) == 0
    assert "efterslæb" in capsys.readouterr().out


def test_repoets_eget_register_er_komplet():
    nye, forsvundne = v.afvigelser()
    assert nye == [] and forsvundne == []
