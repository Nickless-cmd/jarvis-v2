"""Svarstil pr. bruger — core.context.output_style."""
from __future__ import annotations

import json

import pytest

from core.context import output_style as os_


@pytest.fixture
def kv(monkeypatch, tmp_path):
    lager: dict = {}
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda k, d=None: lager.get(k, d))
    monkeypatch.setattr("core.runtime.db_core.set_runtime_state_value",
                        lambda k, v: lager.__setitem__(k, v))
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    return lager


def test_standard_uden_valg(kv):
    assert os_.hent_stil("u-a") == "balanced"
    assert os_.hint_for_bruger("u-a") == ""


def test_valget_er_pr_bruger(kv):
    os_.saet_stil("u-a", "concise")
    assert os_.hent_stil("u-a") == "concise"
    # En anden brugers valg må ikke styre dette svar.
    assert os_.hent_stil("u-b") == "balanced"


def test_hint_naevner_ingen_navn(kv):
    for stil in ("concise", "detailed", "technical"):
        os_.saet_stil("u-a", stil)
        h = os_.hint_for_bruger("u-a")
        assert h.startswith("Output style:")
        assert "Bjørn" not in h


def test_ukendt_stil_og_ingen_bruger_afvises(kv):
    with pytest.raises(ValueError):
        os_.saet_stil("u-a", "poetisk")
    with pytest.raises(ValueError):
        os_.saet_stil("", "concise")


def test_gammel_fil_er_faldback(kv, tmp_path):
    (tmp_path / "jarvisx_prefs.json").write_text(json.dumps({"output_style": "technical"}))
    assert os_.hent_stil("u-a") == "technical"
    os_.saet_stil("u-a", "concise")
    assert os_.hent_stil("u-a") == "concise"


def test_prompt_contract_bruger_modulet():
    """Kilde-vagt via AST: prompt_contract kalder hint_for_bruger og læser ikke filen selv."""
    import ast
    import inspect
    from core.services import prompt_contract
    kilde = inspect.getsource(prompt_contract)
    navne = {n.id for n in ast.walk(ast.parse(kilde)) if isinstance(n, ast.Name)}
    assert "hint_for_bruger" in navne
    assert "jarvisx_prefs.json" not in kilde


def test_tur_bruger_samtalens_ejers_arbejdsrum(kv, monkeypatch):
    """Valget gemmes under arbejdsrummet og findes igen, selv når turens
    kontekst er tom — ejerens stempel slås op til hans arbejdsrum."""
    monkeypatch.setattr("core.services.chat_sessions.get_session_owner", lambda sid: "id-123")
    monkeypatch.setattr("core.identity.session_access.arbejdsrum_for",
                        lambda u: {"id-123": "rum-a"}.get(u, u))
    os_.saet_stil("rum-a", "technical")
    assert os_.rum_for_tur("sess-1") == "rum-a"
    assert os_.hint_for_bruger(os_.rum_for_tur("sess-1")).startswith("Output style: TECHNICAL")


def test_tur_uden_ejer_falder_tilbage_til_anmodningens_rum(kv, monkeypatch):
    monkeypatch.setattr("core.services.chat_sessions.get_session_owner", lambda sid: "")
    from core.identity.workspace_context import current_workspace_name
    assert os_.rum_for_tur("sess-x") == current_workspace_name()
