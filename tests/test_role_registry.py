"""role_registry — kørselstids-udvidelige agent-roller.

## Hvorfor DENNE fil findes

Modulet er fra marts og havde ingen test. `enforce-test-coverage` kigger på
staged filer, så hver fletning der rørte det faldt over gaten — og blev lukket
med `SKIP`. Samme mønster som `ambient_presence` (6/10-2026). Det der udløste
den her var ÉN linje: en værktøjs-beskrivelse der lovede at `convene_council`
ville acceptere nye roller. Værktøjet findes ikke mere.

## Hvad der faktisk kan gå i stykker her

`_CUSTOM_ROLES_PATH` er `Path.home()` på MODUL-niveau. Testene patcher den —
ellers ville `register_custom_role` skrive i Bjørns rigtige
`~/.jarvis-v2/config/custom_roles.json`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.services import role_registry as rr


@pytest.fixture(autouse=True)
def _egen_fil(tmp_path, monkeypatch):
    """Ingen test må røre den rigtige custom_roles.json."""
    sti = tmp_path / "config" / "custom_roles.json"
    monkeypatch.setattr(rr, "_CUSTOM_ROLES_PATH", sti)
    return sti


@pytest.fixture()
def indbyggede(monkeypatch):
    """Et lille, kendt sæt indbyggede roller — ikke det rigtige register.

    Ellers måler sammenligningerne nedenfor `AGENT_ROLE_TEMPLATES`' indhold,
    som ændrer sig af grunde der intet har med dette modul at gøre.
    """
    base = {
        "critic": {"title": "Kritiker", "default_tool_policy": "read-only"},
        "researcher": {"title": "Undersøger", "default_tool_policy": "read-only"},
    }
    monkeypatch.setattr(rr, "_builtin_roles", lambda: dict(base))
    return base


# ── fletningen: custom > builtin ────────────────────────────────────────────

def test_uden_egne_roller_er_resultatet_de_indbyggede(indbyggede):
    assert rr.list_all_roles() == indbyggede


def test_en_egen_rolle_laegges_oven_paa(_egen_fil, indbyggede):
    _egen_fil.parent.mkdir(parents=True)
    _egen_fil.write_text(json.dumps({"roles": [
        {"role": "revisor", "title": "Revisor", "system_prompt": "du reviderer"},
    ]}))
    roller = rr.list_all_roles()
    assert set(roller) == {"critic", "researcher", "revisor"}
    assert roller["revisor"]["title"] == "Revisor"


def test_extends_arver_basens_felter_og_overskriver_kun_sine_egne(_egen_fil, indbyggede):
    """`extends` er hele pointen i modulet: arv felterne, men lad egne vinde."""
    _egen_fil.parent.mkdir(parents=True)
    _egen_fil.write_text(json.dumps({"roles": [
        {"role": "sikkerhedsrevisor", "extends": "critic",
         "system_prompt": "du leder efter huller", "default_tool_policy": "write"},
    ]}))
    r = rr.get_role("sikkerhedsrevisor")
    assert r is not None
    assert r["title"] == "Kritiker", "arvede ikke basens titel"
    assert r["default_tool_policy"] == "write", "egen værdi skal slå basens"
    assert r["system_prompt"] == "du leder efter huller"
    assert "extends" not in r, "`extends` er en instruks, ikke et felt på rollen"


def test_en_egen_rolle_kan_skygge_en_indbygget(_egen_fil, indbyggede):
    _egen_fil.parent.mkdir(parents=True)
    _egen_fil.write_text(json.dumps({"roles": [
        {"role": "critic", "title": "Min egen kritiker", "system_prompt": "x"},
    ]}))
    assert rr.get_role("critic")["title"] == "Min egen kritiker"


def test_ukendt_rolle_giver_None(indbyggede):
    assert rr.get_role("findes-ikke") is None
    assert rr.get_role("") is None


# ── ødelagt fil må ikke vælte opslaget ─────────────────────────────────────

@pytest.mark.parametrize("indhold", [
    "{ ikke json",                      # syntaksfejl
    json.dumps({"roles": "en streng"}),  # roles er ikke en liste
    json.dumps({}),                      # ingen roles-nøgle
])
def test_oedelagt_fil_falder_tilbage_paa_de_indbyggede(_egen_fil, indbyggede, indhold):
    """Et opslag af en rolle sker midt i et agent-spawn. En ødelagt fil må
    koste de EGNE roller, aldrig de indbyggede."""
    _egen_fil.parent.mkdir(parents=True)
    _egen_fil.write_text(indhold)
    assert rr.list_all_roles() == indbyggede


def test_poster_uden_rolle_navn_springes_over(_egen_fil, indbyggede):
    _egen_fil.parent.mkdir(parents=True)
    _egen_fil.write_text(json.dumps({"roles": [
        {"title": "uden navn"},
        {"role": "", "title": "tomt navn"},
        "en streng midt i listen",
        {"role": "gyldig", "title": "Gyldig", "system_prompt": "x"},
    ]}))
    assert set(rr.list_all_roles()) == {"critic", "researcher", "gyldig"}


# ── skrivningen ────────────────────────────────────────────────────────────

def test_register_opretter_filen_og_mappen(_egen_fil, indbyggede):
    assert not _egen_fil.parent.exists()
    ud = rr.register_custom_role(role="revisor", title="Revisor", system_prompt="du reviderer")
    assert ud["status"] == "ok"
    assert ud["total_custom_roles"] == 1
    gemt = json.loads(_egen_fil.read_text())
    assert gemt["roles"][0]["role"] == "revisor"
    assert gemt["roles"][0]["default_tool_policy"] == "read-only", "standard skal skrives med"


def test_register_er_idempotent_paa_navnet(_egen_fil, indbyggede):
    rr.register_custom_role(role="revisor", title="Første", system_prompt="a")
    ud = rr.register_custom_role(role="revisor", title="Anden", system_prompt="b")
    assert ud["total_custom_roles"] == 1, "samme navn må ikke give to poster"
    assert rr.get_role("revisor")["title"] == "Anden", "den nye skal vinde"


def test_register_bevarer_de_andre_roller(_egen_fil, indbyggede):
    rr.register_custom_role(role="en", title="En", system_prompt="a")
    rr.register_custom_role(role="to", title="To", system_prompt="b")
    assert {r["role"] for r in json.loads(_egen_fil.read_text())["roles"]} == {"en", "to"}


@pytest.mark.parametrize("mangler", ["role", "title", "system_prompt"])
def test_register_afviser_et_manglende_paakraevet_felt(_egen_fil, indbyggede, mangler):
    felter = {"role": "r", "title": "T", "system_prompt": "p"}
    felter[mangler] = ""
    ud = rr.register_custom_role(**felter)
    assert ud["status"] == "error"
    assert "required" in ud["error"]
    assert not _egen_fil.exists(), "en afvist rolle må ikke efterlade en fil"


def test_register_overskriver_ikke_en_oedelagt_fils_andre_roller_i_tavshed(_egen_fil, indbyggede):
    """Er filen ødelagt, kan de gamle roller ikke læses. Så skal den NYE stå
    der alene — ikke blandes med halvt parset indhold."""
    _egen_fil.parent.mkdir(parents=True)
    _egen_fil.write_text("{ ikke json")
    ud = rr.register_custom_role(role="ny", title="Ny", system_prompt="x")
    assert ud["status"] == "ok"
    assert [r["role"] for r in json.loads(_egen_fil.read_text())["roles"]] == ["ny"]


# ── værktøjs-fladen ────────────────────────────────────────────────────────

def test_exec_list_roles_markerer_hvad_der_er_egne(_egen_fil, indbyggede):
    _egen_fil.parent.mkdir(parents=True)
    _egen_fil.write_text(json.dumps({"roles": [
        {"role": "revisor", "title": "Revisor", "system_prompt": "x", "tags": ["sik"]},
    ]}))
    ud = rr._exec_list_roles({})
    assert ud["status"] == "ok"
    assert ud["total"] == 3
    efter_navn = {r["role"]: r for r in ud["roles"]}
    assert efter_navn["revisor"]["is_custom"] is True
    assert efter_navn["revisor"]["tags"] == ["sik"]
    assert efter_navn["critic"]["is_custom"] is False
    assert [r["role"] for r in ud["roles"]] == sorted(efter_navn), "listen er sorteret"


def test_exec_register_sender_argumenterne_videre(_egen_fil, indbyggede):
    ud = rr._exec_register_custom_role({
        "role": "revisor", "title": "Revisor", "system_prompt": "x",
        "default_tool_policy": "write", "extends": "critic", "tags": ["a"],
    })
    assert ud["status"] == "ok"
    gemt = json.loads(_egen_fil.read_text())["roles"][0]
    assert gemt["extends"] == "critic"
    assert gemt["default_tool_policy"] == "write"
    assert gemt["tags"] == ["a"]


def test_vaerktoejs_definitionerne_lover_kun_vaerktoejer_der_FINDES():
    """Beskrivelsen lovede indtil 7/10-2026 at `convene_council` ville tage
    nye roller. Det værktøj er fjernet med den blinde rådsindkaldelse, og en
    beskrivelse der nævner et værktøj han ikke har, er en instruks til et
    kald der fejler."""
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    findes = {str(((d.get("function") or {}).get("name")) or "")
              for d in TOOL_DEFINITIONS}
    assert "spawn_agent_task" in findes, "forudsætning: kataloget blev læst"

    import re
    for d in rr.ROLE_REGISTRY_TOOL_DEFINITIONS:
        tekst = str((d.get("function") or {}).get("description") or "")
        for navn in re.findall(r"\b([a-z][a-z0-9_]{4,})\(|\b(spawn_agent_task|convene_council|quick_council_check)\b", tekst):
            kandidat = navn[0] or navn[1]
            if kandidat and kandidat in ("spawn_agent_task", "convene_council", "quick_council_check"):
                assert kandidat in findes, (
                    "%r naevner vaerktoejet %s, som ikke staar i kataloget"
                    % (str((d.get("function") or {}).get("name")), kandidat)
                )


def test_de_to_definitioner_har_det_skema_executoren_laeser():
    navne = {str((d.get("function") or {}).get("name")) for d in rr.ROLE_REGISTRY_TOOL_DEFINITIONS}
    assert navne == {"list_agent_roles", "register_custom_role"}
    for d in rr.ROLE_REGISTRY_TOOL_DEFINITIONS:
        f = d["function"]
        assert d["type"] == "function"
        assert f["description"].strip()
        assert f["parameters"]["type"] == "object"
    reg = next(d["function"] for d in rr.ROLE_REGISTRY_TOOL_DEFINITIONS
               if d["function"]["name"] == "register_custom_role")
    assert set(reg["parameters"]["required"]) == {"role", "title", "system_prompt"}
