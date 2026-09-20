"""Vagten skal AFVISE. En vagt uden en test der ser den afvise, måler intet.

DeepSeek-harness har 60 `verify-*`-scripts og en `.spec` til hvert eneste et.
Vores egne vagter har ikke alle haft det, og vi har betalt for det før: en
kilde-vagt der greper efter en streng målte næsten ingenting, og ingen
opdagede det, fordi ingen test havde set den sige nej.
"""
import json

import pytest

from scripts import verify_silent_except as vse


def _skriv(tmp_path, navn, kode):
    p = tmp_path / navn
    p.write_text(kode, encoding="utf-8")
    return p


def test_tavs_handler_uden_forklaring_fanges(tmp_path):
    p = _skriv(tmp_path, "a.py", "try:\n    x()\nexcept Exception:\n    pass\n")
    assert [linje for linje, _ in vse.fund_i_fil(p)] == [3]


def test_en_kommentar_er_forklaringen(tmp_path):
    """Reglen kræver at fejlen NAVNGIVES — ikke at den håndteres."""
    p = _skriv(tmp_path, "b.py",
               "try:\n    x()\nexcept Exception:  # tom liste er normalt her\n    pass\n")
    assert vse.fund_i_fil(p) == []


def test_kommentar_inde_i_kroppen_taeller_ogsaa(tmp_path):
    p = _skriv(tmp_path, "c.py",
               "try:\n    x()\nexcept Exception:\n    # telemetri må ikke vælte flowet\n    pass\n")
    assert vse.fund_i_fil(p) == []


def test_logning_og_reraise_er_ikke_tavse(tmp_path):
    p = _skriv(tmp_path, "d.py",
               "try:\n    x()\nexcept Exception as e:\n    logger.warning('nej: %s', e)\n"
               "try:\n    y()\nexcept Exception:\n    raise\n")
    assert vse.fund_i_fil(p) == []


def test_tavs_return_taeller_som_slugt(tmp_path):
    """`return ''` skjuler fejlen lige så effektivt som `pass`."""
    p = _skriv(tmp_path, "e.py",
               "def f():\n    try:\n        return x()\n    except Exception:\n        return ''\n")
    assert len(vse.fund_i_fil(p)) == 1


def test_langt_try_naevnes_saerskilt(tmp_path):
    """Den anden halvdel af reglen: et langt try fanger fejl du ikke mente."""
    p = _skriv(tmp_path, "f.py",
               "try:\n    a()\n    b()\n    c()\nexcept Exception:\n    pass\n")
    (_, aarsag), = vse.fund_i_fil(p)
    assert "3 sætninger" in aarsag


def test_syntaksfejl_faelder_ikke_vagten(tmp_path):
    p = _skriv(tmp_path, "g.py", "def (:\n")
    assert vse.fund_i_fil(p) == []


def test_grundlinjen_spaerrer_for_flere_men_ikke_for_faerre(tmp_path, monkeypatch):
    """Skraldespærren: over grundlinjen = fejl, under = i orden."""
    fil = _skriv(tmp_path, "h.py", "try:\n    x()\nexcept Exception:\n    pass\n")
    grund = tmp_path / "grundlinje.json"
    monkeypatch.setattr(vse, "GRUNDLINJE", grund)
    monkeypatch.setattr(vse, "ROD", tmp_path)

    grund.write_text(json.dumps({"pr_fil": {"h.py": 1}}), encoding="utf-8")
    assert vse.main([str(fil)]) == 0          # præcis på grundlinjen
    grund.write_text(json.dumps({"pr_fil": {"h.py": 5}}), encoding="utf-8")
    assert vse.main([str(fil)]) == 0          # under grundlinjen
    grund.write_text(json.dumps({"pr_fil": {}}), encoding="utf-8")
    assert vse.main([str(fil)]) == 1          # ny fil, ingen grundlinje → nej


def test_grundlinjen_i_repoet_holder():
    """Repoet selv skal være rent mod sin egen grundlinje."""
    assert vse.main([]) == 0


@pytest.mark.parametrize("omraade", vse.OMRAADER)
def test_vagten_daekker_de_omraader_den_lover(omraade):
    assert (vse.ROD / omraade).is_dir()
