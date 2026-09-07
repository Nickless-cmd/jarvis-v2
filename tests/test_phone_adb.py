"""ADB over Wi-Fi — ægte skal på telefonen, uden om app-sandkassen.

Testene handler om de tre ting der kan gøre en sådan vej farlig: at den
findes når den ikke burde, at den kører uden godkendelse, og at
parringskoden ender et sted den kan læses.
"""

from __future__ import annotations

import pytest

from core.tools import phone_adb as A


def test_navne_definitioner_og_handlere_daekker_hinanden():
    fra_def = {d["function"]["name"] for d in A.PHONE_ADB_TOOL_DEFINITIONS}
    assert fra_def == set(A.PHONE_ADB_TOOL_NAMES)
    assert set(A.PHONE_ADB_TOOL_EXECUTORS) == set(A.PHONE_ADB_TOOL_NAMES)


def test_vaerktoejerne_er_registreret_i_runtime():
    from core.tools.simple_tools import get_tool_definitions, _TOOL_HANDLERS

    annonceret = {(d.get("function") or d).get("name") for d in get_tool_definitions()}
    assert set(A.PHONE_ADB_TOOL_NAMES) <= annonceret
    assert set(A.PHONE_ADB_TOOL_NAMES) <= set(_TOOL_HANDLERS)


# ── godkendelse ─────────────────────────────────────────────────────────


def test_shell_kraever_godkendelse(monkeypatch):
    """Vilkaarlig eksekvering paa telefonen maa ikke have en lettere vej end paa computeren."""
    monkeypatch.setattr(A, "_adresse", lambda args=None: "10.0.0.50:5555")
    monkeypatch.setattr(A, "_koer_adb", lambda *a, **k: pytest.fail("maatte ikke koere"))

    r = A._exec_phone_adb_shell({"kommando": "rm -rf /sdcard/DCIM"})
    assert r["status"] == "approval_needed"
    # Kommandoen skal STAA der, ellers godkender Bjoern noget han ikke kan se.
    assert "rm -rf /sdcard/DCIM" in r["message"]


def test_shell_koerer_naar_den_er_godkendt(monkeypatch):
    set_argv: list[list[str]] = []
    monkeypatch.setattr(A, "_adresse", lambda args=None: "10.0.0.50:5555")
    monkeypatch.setattr(A, "_koer_adb",
                        lambda argv, **k: set_argv.append(argv) or {"status": "ok"})

    r = A._exec_phone_adb_shell({"kommando": "getprop ro.product.model",
                                 "_runtime_trust_all": True})
    assert r["status"] == "ok"
    assert set_argv[0] == ["-s", "10.0.0.50:5555", "shell", "getprop ro.product.model"]


def test_skaermbillede_kraever_ogsaa_godkendelse(monkeypatch):
    """Modsat computerens operator_screenshot.

    En telefonskaerm har bank, beskeder og totrins-koder paa sig, og den
    ligger ikke ved siden af Bjoern naar han arbejder.
    """
    monkeypatch.setattr(A, "_adresse", lambda args=None: "10.0.0.50:5555")
    r = A._exec_phone_adb_screenshot({})
    assert r["status"] == "approval_needed"


def test_status_kraever_ingen_godkendelse(monkeypatch):
    """Det aendrer intet — og skal kunne bruges til at finde ud af hvorfor noget fejler."""
    monkeypatch.setattr(A, "_adresse", lambda args=None: "10.0.0.50:5555")
    monkeypatch.setattr(A, "_koer_adb", lambda *a, **k: {"status": "ok", "stdout": "List of devices"})
    monkeypatch.setattr(A, "_forbundet", lambda adr: True)

    r = A._exec_phone_adb_status({})
    assert r["status"] == "ok" and r["forbundet"] is True


# ── parringskoden ───────────────────────────────────────────────────────


def test_parringskoden_ender_ikke_i_resultatet(monkeypatch):
    """Koden er selve sikkerhedskontrollen og maa ikke kunne laeses bagefter.

    ``_koer_adb`` returnerer normalt hele kommandolinjen, saa man kan
    efterproeve et fejlende kald i haanden — netop dét ville lække koden her.
    """
    monkeypatch.setattr(A, "_koer_adb",
                        lambda argv, **k: {"status": "ok", "stdout": "Successfully paired",
                                           "kommando": "adb " + " ".join(argv)})

    r = A._exec_phone_adb_pair({"par_adresse": "10.0.0.50:37123", "kode": "314159"})
    flad = repr(r)
    assert "314159" not in flad, "parringskoden lækkede i resultatet"
    assert "kode udeladt" in r["kommando"]


def test_parring_uden_kode_forklarer_hvor_den_findes():
    r = A._exec_phone_adb_pair({})
    assert r["status"] == "mangler_input"
    assert "parringskode" in r["hint"]


# ── porten ──────────────────────────────────────────────────────────────


def test_uden_adresse_findes_vaerktoejerne_slet_ikke(monkeypatch):
    """Ingen telefon opsat → ingen adb-vaerktoejer i kataloget.

    Samme princip som telefon- og desk-vaerktoejerne: overfladen udvides ikke
    naar der ikke er noget at pege den paa.
    """
    from core.tools import tool_scoping as TS

    monkeypatch.setattr(TS, "_adb_er_opsat", lambda: False)
    tilladt = TS.allowed_tool_names(
        role="owner", scope="chat", all_names=list(A.PHONE_ADB_TOOL_NAMES),
    )
    assert not (set(A.PHONE_ADB_TOOL_NAMES) & tilladt)


def test_med_adresse_er_de_der(monkeypatch):
    from core.tools import tool_scoping as TS

    monkeypatch.setattr(TS, "_adb_er_opsat", lambda: True)
    tilladt = TS.allowed_tool_names(
        role="owner", scope="chat", all_names=list(A.PHONE_ADB_TOOL_NAMES),
    )
    assert set(A.PHONE_ADB_TOOL_NAMES) <= tilladt


def test_porten_laeser_adressen_hver_gang(monkeypatch):
    """Ikke cachet: adressen kan saettes uden genstart.

    Var den cachet, ville en telefon der lige er sat op foerst virke efter
    naeste genstart — og det ville se ud som om opsaetningen ikke virkede.
    """
    from core.tools import tool_scoping as TS

    svar = iter(["", "10.0.0.50:5555"])
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key",
                        lambda k, *a, **kw: next(svar))
    assert TS._adb_er_opsat() is False
    assert TS._adb_er_opsat() is True


def test_manglende_adb_siger_hvad_der_skal_goeres(monkeypatch):
    monkeypatch.setattr(A, "_adb_sti", lambda: None)
    r = A._koer_adb(["devices"])
    assert r["error"] == "adb_ikke_installeret"
    assert "apt-get install" in r["hint"]
