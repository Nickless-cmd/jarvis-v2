"""Vagten over vagterne skal selv kunne ses sige nej.

Ellers gentager den præcis den fejl den findes for at forhindre.
"""
import scripts.verify_guard_tests as v


def _opsaet(monkeypatch, tmp_path, konfig: str, testfiler: dict[str, str]):
    k = tmp_path / ".pre-commit-config.yaml"
    k.write_text(konfig, encoding="utf-8")
    t = tmp_path / "tests"
    t.mkdir(exist_ok=True)
    for navn, indhold in testfiler.items():
        (t / navn).write_text(indhold, encoding="utf-8")
    monkeypatch.setattr(v, "KONFIG", k)
    monkeypatch.setattr(v, "TESTS", t)


_KONFIG = "      - id: x\n        entry: python scripts/min_vagt.py --staged\n"


def test_en_vagt_uden_nogen_test_afvises(monkeypatch, tmp_path, capsys):
    _opsaet(monkeypatch, tmp_path, _KONFIG, {})
    assert v.main([]) == 1
    assert "ingen test nævner den" in capsys.readouterr().out


def test_en_test_der_kun_importerer_er_ikke_nok(monkeypatch, tmp_path, capsys):
    """Det er afvisningen der skal være set — ikke at modulet kan indlæses."""
    _opsaet(monkeypatch, tmp_path, _KONFIG,
            {"test_min_vagt.py": "import scripts.min_vagt\n\ndef test_a():\n    assert True\n"})
    assert v.main([]) == 1
    assert "ser den aldrig sige nej" in capsys.readouterr().out


def test_en_test_der_ser_den_afvise_er_nok(monkeypatch, tmp_path):
    _opsaet(monkeypatch, tmp_path, _KONFIG,
            {"test_min_vagt.py": "import scripts.min_vagt as m\n\n"
                                 "def test_a():\n    assert m.main([]) == 1\n"})
    assert v.main([]) == 0


def test_hooks_der_ikke_koerer_vores_egne_scripts_kraeves_ikke(monkeypatch, tmp_path):
    _opsaet(monkeypatch, tmp_path,
            "      - id: y\n        entry: detect-secrets-hook --baseline x\n", {})
    assert v.vagter() == []
    assert v.main([]) == 0


def test_repoets_egne_vagter_har_alle_en_test():
    """Den der faktisk kører i hooken. Falder den, mangler der en test."""
    assert v.main([]) == 0
    assert len(v.vagter()) >= 8
