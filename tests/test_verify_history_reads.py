"""Historik-vagten skal AFVISE et nyt kald — og kun et NYT."""
import json

import scripts.verify_history_reads as v

_KALD = "from core.services.chat_sessions import get_chat_session\n\n" \
        "def f(sid):\n    return get_chat_session(sid)\n"


def _opsaet(tmp_path, monkeypatch, grundlinje: dict):
    g = tmp_path / "grund.json"
    g.write_text(json.dumps({"pr_fil": grundlinje}), encoding="utf-8")
    monkeypatch.setattr(v, "GRUNDLINJE", g)
    monkeypatch.setattr(v, "ROD", tmp_path)
    f = tmp_path / "ny.py"
    f.write_text(_KALD, encoding="utf-8")
    return f


def test_et_nyt_kald_afvises(tmp_path, monkeypatch, capsys):
    f = _opsaet(tmp_path, monkeypatch, {})
    assert v.main([str(f)]) == 1
    ud = capsys.readouterr().out
    assert "HEL historik" in ud
    assert "recent_chat_session_messages" in ud     # alternativet skal nævnes


def test_et_kald_der_staar_i_grundlinjen_gaar_igennem(tmp_path, monkeypatch):
    f = _opsaet(tmp_path, monkeypatch, {"ny.py": 1})
    assert v.main([str(f)]) == 0


def test_et_EKSTRA_kald_i_en_kendt_fil_afvises(tmp_path, monkeypatch):
    """Grundlinjen er pr. fil, så en fil med ét lovligt kald ikke bliver fribillet."""
    f = _opsaet(tmp_path, monkeypatch, {"ny.py": 1})
    f.write_text(_KALD + "\ndef g(sid):\n    return get_chat_session(sid)\n",
                 encoding="utf-8")
    assert v.main([str(f)]) == 1


def test_definitionen_selv_er_ikke_et_kaldested(tmp_path, monkeypatch):
    f = _opsaet(tmp_path, monkeypatch, {})
    f.write_text("def get_chat_session(sid):\n    return None\n", encoding="utf-8")
    assert v.main([str(f)]) == 0


def test_de_bundne_laesere_er_ikke_ramt(tmp_path, monkeypatch):
    """Hele pointen: et VINDUE er lovligt, hele historikken er ikke."""
    f = _opsaet(tmp_path, monkeypatch, {})
    f.write_text("def f(sid):\n    return recent_chat_session_messages(sid, limit=12)\n",
                 encoding="utf-8")
    assert v.main([str(f)]) == 0


def test_syntaksfejl_faelder_ikke_vagten(tmp_path, monkeypatch):
    f = _opsaet(tmp_path, monkeypatch, {})
    f.write_text("def (:\n", encoding="utf-8")
    assert v.main([str(f)]) == 0


def test_repoet_holder_sin_egen_grundlinje():
    assert v.main([]) == 0
