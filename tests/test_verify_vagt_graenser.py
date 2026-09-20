"""Grænse-vagten skal AFVISE en vagt der importerer et delsystem."""
import scripts.verify_vagt_graenser as v


def _vagt(tmp_path, monkeypatch, kode: str):
    (tmp_path / "core/services").mkdir(parents=True, exist_ok=True)
    (tmp_path / "core/services/min_vagt.py").write_text(kode, encoding="utf-8")
    monkeypatch.setattr(v, "ROD", tmp_path)
    monkeypatch.setattr(v, "VAGTER", ("core/services/min_vagt.py",))


def test_import_af_et_delsystem_afvises(tmp_path, monkeypatch, capsys):
    _vagt(tmp_path, monkeypatch, "from core.services.plan_proposals import propose_plan\n")
    assert v.main([]) == 1
    assert "plan_proposals" in capsys.readouterr().out


def test_ogsaa_et_import_INDE_i_en_funktion_fanges(tmp_path, monkeypatch):
    """Sen-import er den nemmeste vej udenom, og derfor den der tjekkes."""
    _vagt(tmp_path, monkeypatch,
          "def f():\n    from core.services import agent_todos\n    return agent_todos\n")
    assert v.main([]) == 1


def test_at_NAEVNE_vaerktoejsnavnet_er_i_orden(tmp_path, monkeypatch):
    """Hele pointen: en streng, så delsystemet kan ændre sig frit."""
    _vagt(tmp_path, monkeypatch, 'VAAGN = "schedule_self_wakeup"\n')
    assert v.main([]) == 0


def test_en_vagt_der_er_forsvundet_meldes(tmp_path, monkeypatch, capsys):
    """Ellers ville listen stille og roligt holde op med at måle noget."""
    monkeypatch.setattr(v, "ROD", tmp_path)
    monkeypatch.setattr(v, "VAGTER", ("core/services/findes-ikke.py",))
    assert v.main([]) == 1
    assert "findes ikke længere" in capsys.readouterr().out


def test_repoets_egen_vagt_holder_graensen():
    assert v.main([]) == 0
    assert v.VAGTER and len(v.DELSYSTEMER) >= 4
