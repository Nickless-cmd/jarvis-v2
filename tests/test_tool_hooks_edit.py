"""Redigering af hook-regler: validering, værn og den rå config-vej.

Testene rammer adfærden, ikke implementeringen. Det vigtigste værn er at en
UGYLDIG config ikke må kunne overskrive en gyldig — en halv config får
``_parse`` til at afvise alt, og så dør mekanismen tavst i stedet for at sige
fra. Derfor testes rækkefølgen: valider FØRST, skriv bagefter.
"""
from __future__ import annotations

import json

import pytest
from fastapi import HTTPException


def _body(**over):
    from apps.api.jarvis_api.routes.tool_hooks import HookRule, HooksConfigBody

    felter = {
        "name": "beskyt-roden",
        "match": "^bash$",
        "before": "exit 0",
        "after": "",
        "timeout_s": 5.0,
        "cwd": "",
    }
    felter.update(over)
    return HooksConfigBody(enabled=True, hooks=[HookRule(**felter)])


def test_ugyldig_config_overskriver_ikke_en_gyldig(tmp_path, monkeypatch) -> None:
    from core.services import tool_shell_hooks as hooks

    config = tmp_path / "tool_hooks.json"
    original = {"enabled": True, "hooks": [{"name": "orignal", "match": ".", "before": "x"}]}
    config.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(hooks, "CONFIG_STI", config)

    resultat = hooks.save_config({
        "enabled": True,
        "hooks": [{"name": "ny", "match": "([", "before": "x"}],
    })

    assert resultat["ok"] is False
    assert resultat["skrevet"] is False
    assert json.loads(config.read_text(encoding="utf-8")) == original


def test_gyldig_config_skrives_med_backup_og_snavr_mode(tmp_path, monkeypatch) -> None:
    from core.services import tool_shell_hooks as hooks

    config = tmp_path / "tool_hooks.json"
    config.write_text(json.dumps({"enabled": False, "hooks": []}), encoding="utf-8")
    monkeypatch.setattr(hooks, "CONFIG_STI", config)
    monkeypatch.setattr(hooks, "ensure_loaded", lambda *, tving=False: True)
    monkeypatch.setattr(hooks, "status", lambda: {"enabled": True, "hooks": []})

    resultat = hooks.save_config({
        "enabled": True,
        "hooks": [{"name": "ny", "match": "^bash$", "before": "exit 2", "timeout_s": 3}],
    })

    assert resultat["ok"] is True and resultat["skrevet"] is True
    assert config.stat().st_mode & 0o777 == 0o600
    skrevet = json.loads(config.read_text(encoding="utf-8"))
    assert skrevet["hooks"][0]["before"] == "exit 2"
    assert resultat["backup"], "den gamle config skal være gemt, ikke overskrevet uden spor"


def test_validering_samler_alle_fejl_ikke_kun_den_foerste() -> None:
    from core.services import tool_shell_hooks as hooks

    fejl = hooks.validate_config({"enabled": "ja", "hooks": [
        {"name": "", "match": ""},
        {"name": "a", "match": "([", "before": "x"},
        {"name": "a", "match": ".", "before": "", "after": "", "timeout_s": "abc"},
    ]})

    tekst = " | ".join(fejl)
    assert "enabled" in tekst
    assert "mangler navn" in tekst
    assert "ugyldigt regex" in tekst
    assert "brugt to gange" in tekst
    assert "hverken 'before' eller 'after'" in tekst
    assert "timeout_s" in tekst


def test_read_config_giver_kommandoerne_som_redigeringen_skal_bruge(tmp_path, monkeypatch) -> None:
    from core.services import tool_shell_hooks as hooks

    config = tmp_path / "tool_hooks.json"
    config.write_text(json.dumps({
        "enabled": True,
        "hooks": [{"name": "a", "match": "^bash$", "before": "exit 2", "after": "log"}],
    }), encoding="utf-8")
    monkeypatch.setattr(hooks, "CONFIG_STI", config)

    dokument = hooks.read_config()

    assert dokument["findes"] is True
    assert dokument["enabled"] is True
    # Kommandoerne SKAL med: uden dem ville et gem skrive tomme strenge
    # tilbage og tavst afvæbne hooken.
    assert dokument["hooks"][0]["before"] == "exit 2"
    assert dokument["hooks"][0]["after"] == "log"


def test_read_config_uden_fil_svarer_slukket(tmp_path, monkeypatch) -> None:
    from core.services import tool_shell_hooks as hooks

    monkeypatch.setattr(hooks, "CONFIG_STI", tmp_path / "findes-ikke.json")

    assert hooks.read_config() == {"enabled": False, "hooks": [], "findes": False}


def test_gem_uden_eksplicit_godkendelse_afvises(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import tool_hooks as routes

    monkeypatch.setattr(routes, "_kraev_ejer", lambda: "owner-1")
    gemt: list[dict] = []
    monkeypatch.setattr(routes.tool_shell_hooks, "save_config", lambda raw: gemt.append(raw) or {"ok": True})

    with pytest.raises(HTTPException) as denied:
        routes.put_tool_hooks(_body().__class__(enabled=True, hooks=_body().hooks, approved=False))

    assert denied.value.status_code == 409
    assert gemt == [], "et gem uden bekræftelse må ikke nå filen"


def test_gem_med_godkendelse_skriver(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import tool_hooks as routes

    monkeypatch.setattr(routes, "_kraev_ejer", lambda: "owner-1")
    gemt: list[dict] = []
    monkeypatch.setattr(routes.tool_shell_hooks, "save_config", lambda raw: gemt.append(raw) or {
        "ok": True, "skrevet": True, "backup": "/tmp/bak",
    })
    monkeypatch.setattr(routes, "_log_metadata", lambda: {"exists": False})

    body = _body()
    body.approved = True
    resultat = routes.put_tool_hooks(body)

    assert resultat["skrevet"] is True
    assert gemt[0]["hooks"][0]["name"] == "beskyt-roden"
    assert "approved" not in gemt[0], "flaget hører til ruten, ikke til filen"


def test_ugyldig_config_giver_422_med_alle_fejl(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import tool_hooks as routes

    monkeypatch.setattr(routes, "_kraev_ejer", lambda: "owner-1")
    monkeypatch.setattr(routes.tool_shell_hooks, "save_config", lambda raw: {
        "ok": False, "fejl": ["hook 'a' mangler 'match'", "hook 'b' har ugyldigt regex"],
    })

    body = _body()
    body.approved = True
    with pytest.raises(HTTPException) as afvist:
        routes.put_tool_hooks(body)

    assert afvist.value.status_code == 422
    assert afvist.value.detail["fejl"] == ["hook 'a' mangler 'match'", "hook 'b' har ugyldigt regex"]


def test_validate_skriver_intet(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import tool_hooks as routes

    monkeypatch.setattr(routes, "_kraev_ejer", lambda: "owner-1")
    kaldt: list[str] = []
    monkeypatch.setattr(routes.tool_shell_hooks, "save_config", lambda raw: kaldt.append("skrev") or {})
    monkeypatch.setattr(routes.tool_shell_hooks, "validate_config", lambda raw: ["en fejl"])

    svar = routes.validate_tool_hooks(_body())

    assert svar == {"ok": False, "fejl": ["en fejl"]}
    assert kaldt == [], "tør kørsel må ikke skrive"


def test_ikke_ejer_afvises_403(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import tool_hooks as routes

    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "member-1")
    monkeypatch.setattr("apps.api.jarvis_api.routes.account._current_role", lambda uid: "member")

    with pytest.raises(HTTPException) as denied:
        routes._kraev_ejer()

    assert denied.value.status_code == 403
