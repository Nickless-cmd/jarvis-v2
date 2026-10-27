"""Observationen af et faerdigt vaerktoejskald.

Udskilt fra `simple_tools.py` (2.141 linjer) efter Boy Scout-reglen, foer K2
lagde et skema-tjek ind i `execute_tool`.

Den ene egenskab der betyder noget: den maa aldrig kunne aendre eller vaelte
udfaldet. Alle tre observationer sidder paa veje der kan fejle — Centralen,
en DB-taeller, en klassificerings-skygge i en traad.
"""
from __future__ import annotations

import pytest

from core.tools.tool_call_observation import observe_tool_call


def test_den_kaster_ikke_paa_et_normalt_kald(isolated_runtime):
    observe_tool_call("write_file", {"path": "/a"}, {"status": "ok"})


def test_den_kaster_ikke_paa_et_fejlet_kald(isolated_runtime):
    observe_tool_call("write_file", {"path": "/a"},
                      {"status": "error", "error": "noget gik galt"})


@pytest.mark.parametrize("resultat", [None, "en streng", 42, [], {"uden": "status"}])
def test_den_kaster_ikke_paa_et_underligt_resultat(isolated_runtime, resultat):
    """Tidlige returns i dispatchen giver ikke altid en pæn dict."""
    observe_tool_call("noget", {}, resultat)


def test_en_kollapset_central_stopper_ikke_kaldet(isolated_runtime, monkeypatch):
    import core.services.central_core as CC
    monkeypatch.setattr(CC, "central",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    observe_tool_call("write_file", {"path": "/a"}, {"status": "ok"})


def test_den_returnerer_ingenting(isolated_runtime):
    """Den observerer. Den svarer ikke — kalderen har allerede sit resultat."""
    assert observe_tool_call("write_file", {}, {"status": "ok"}) is None


@pytest.mark.parametrize("status", ["ok", "accepted", "completed", "noop"])
def test_successtatusser_taelles_som_succes(isolated_runtime, monkeypatch, status):
    """Task returnerer accepted; det maa ikke blive til en falsk tool-fejl."""
    import core.services.tool_usage_store as usage

    set_ok = []
    monkeypatch.setattr(usage, "record_use",
                        lambda name, *, kind, ok: set_ok.append((name, ok)))
    observe_tool_call("Task", {}, {"status": status})
    assert set_ok == [("Task", True)]


def test_en_aegte_error_taelles_som_fejl(isolated_runtime, monkeypatch):
    import core.services.tool_usage_store as usage

    set_ok = []
    monkeypatch.setattr(usage, "record_use",
                        lambda name, *, kind, ok: set_ok.append((name, ok)))
    observe_tool_call("Task", {}, {"status": "error", "error": "nej"})
    assert set_ok == [("Task", False)]


def test_execute_tool_kalder_den(isolated_runtime, monkeypatch):
    """Boy Scout-udskilningen maa ikke have tabt koblingen: hvis ingen kalder
    den, er tre observationer stille forsvundet."""
    import core.tools.simple_tools as ST
    set_af = []
    monkeypatch.setattr(ST, "_execute_tool_impl", lambda n, a: {"status": "ok"})
    monkeypatch.setattr("core.tools.tool_call_observation.observe_tool_call",
                        lambda n, a, r: set_af.append((n, r)))
    ST.execute_tool("write_file", {"path": "/a", "content": "x"})
    assert set_af == [("write_file", {"status": "ok"})]


# ── Gaten maa ikke taelles som et ejer-nej (25/10-2026) ────────────────────
#
# `gate_blocked` og `blocked` er SYSTEMETS egne beslutninger: R2.5, inbox_gate,
# exec_command, autonomous_tool_policy, «Write blocked for safety». Ingen har
# set kortet, og ingen har klikket nej.
#
# Maalt 25/10-2026: begge blev mappet til `deny` — altsaa «ejeren afviste».
# Det laerte klassificeren at Bjoern afviser handlinger hun aldrig blev spurgt
# om: `operator_bash` stod med 154.670 forsoeg og 43.909 korrekte (28,4 %
# praecision mod et krav paa 95 %). Samme forveksling fodrede Agent Smith med
# «Bruger afviste tool-call til bash», som blev en BLOKERENDE indbakke-post
# (id 7985, 2 paamindelser) for et bash-kald Bjoern aldrig afviste.
#
# Et aegte nej maales KUN gennem gold-vejen: mennesket klikker Nej paa kortet,
# og `resolve_pending_approval` kalder `record_prediction_outcome` selv.


def _fang_klassificer_udfald(monkeypatch, resultat):
    """Kør observe_tool_call og returnér hvad klassificeren blev fortalt.

    Skyggen koerer i en daemon-traad, saa vi venter paa den i stedet for at
    sove et fast antal millisekunder — en sove-pause er en gaettekonkurrence.
    """
    import threading
    import core.services.permission_classifier as PC

    set_udfald = []
    faerdig = threading.Event()

    monkeypatch.setattr(PC, "permission_classifier_mode", lambda: "shadow")
    monkeypatch.setattr(PC, "is_mutating", lambda navn: True)
    monkeypatch.setattr(PC, "classify_action",
                        lambda *a, **k: PC.PermissionPrediction("approve", 0.9, "test"))

    def _fang(navn, *, predicted, actual, is_owner_gold):
        set_udfald.append({"tool": navn, "predicted": predicted,
                           "actual": actual, "gold": is_owner_gold})
        faerdig.set()

    monkeypatch.setattr(PC, "record_prediction_outcome", _fang)
    monkeypatch.setattr(PC, "stash_prediction", lambda *a, **k: None)

    observe_tool_call("bash", {"command": "ls"}, resultat)
    faerdig.wait(timeout=2.0)
    return set_udfald


@pytest.mark.parametrize("gate_status", ["gate_blocked", "blocked"])
def test_en_gate_blokering_er_ikke_et_ejer_nej(isolated_runtime, monkeypatch, gate_status):
    """Gatens egen blokering maa ALDRIG blive et `deny` — det er ikke et klik."""
    udfald = _fang_klassificer_udfald(
        monkeypatch, {"status": gate_status, "message": "blokeret af gaten"})

    assert all(u["actual"] != "deny" for u in udfald), (
        f"status={gate_status!r} blev talt som et ejer-nej. Gaten blokerede selv — "
        "ingen har set kortet. Et aegte nej kommer gennem gold-vejen."
    )


def test_et_gennemfoert_kald_taeller_stadig_som_ejer_godkendelse(isolated_runtime, monkeypatch):
    """Modproeven: fjerner vi ALT, bliver vagten groen af den forkerte grund."""
    udfald = _fang_klassificer_udfald(monkeypatch, {"status": "ok"})

    assert udfald, "et gennemfoert kald skal stadig give klassificeren et udfald"
    assert udfald[0]["actual"] == "approve"
    assert udfald[0]["gold"] is False
