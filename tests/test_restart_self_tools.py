"""`restart_self` — Jarvis' egen genstart, nu med et blik først.

## Målingen

13/9-2026: **syv** nedlukninger på 75 minutter, **fem** dræbte kørsler. To af
dem havde preview'et «Forsæt» — altså den besked Bjørn skriver *når* en kørsel
er død.

Både denne vej og de manuelle ssh-genstarter spurgte ikke først. Jeg byggede et
script til min egen side; det her er den anden.

## Hvorfor den ikke bare nægter

En genstart der bare afviser ville blive omgået ad en anden vej, og så er vi
værre stillet. Værktøjet svarer i stedet med *hvad* der kører, så Jarvis selv
kan vælge at vente — og `force=true` er der, med prisen skrevet i beskrivelsen.
"""
from __future__ import annotations

import core.tools.restart_self_tools as rst


def test_afviser_naar_noget_koerer(monkeypatch):
    monkeypatch.setattr(rst, "_aktive_koersler",
                        lambda *a, **k: [{"run_id": "visible-1", "preview": "Forsæt"}])
    ud = rst._exec_restart_self({"services": ["jarvis-api"]})
    assert ud["status"] == "afvist"
    assert ud["aktive"][0]["preview"] == "Forsæt"
    assert "force=true" in ud["raad"]


def test_raadet_siger_hvad_det_KOSTER():
    """En noedudgang uden pris bliver brugt af vane. Det gjorde jeg selv, faa
    minutter efter at have bygget den tilsvarende vagt til mit eget script."""
    import json
    kilde = json.dumps(rst.RESTART_SELF_TOOL_DEFINITIONS, ensure_ascii=False)
    assert "api-nedlukning" in kilde
    assert "Forsæt" in kilde


def test_force_gaar_udenom(monkeypatch):
    """Vagten maa kunne omgaas MED VILJE — ellers goer den en noedvendig
    genstart umulig."""
    monkeypatch.setattr(rst, "_aktive_koersler",
                        lambda *a, **k: [{"run_id": "x", "preview": "y"}])
    kaldt: list = []
    monkeypatch.setattr(rst.subprocess, "Popen",
                        lambda *a, **k: kaldt.append(a) or type("P", (), {"pid": 1})())
    ud = rst._exec_restart_self({"services": ["jarvis-api"], "force": True})
    assert ud["status"] != "afvist"
    assert kaldt, "genstarten blev ikke sat i gang"


def test_ingen_aktive_lader_den_koere(monkeypatch):
    monkeypatch.setattr(rst, "_aktive_koersler", lambda *a, **k: [])
    monkeypatch.setattr(rst.subprocess, "Popen",
                        lambda *a, **k: type("P", (), {"pid": 1})())
    ud = rst._exec_restart_self({"services": ["jarvis-api"]})
    assert ud["status"] != "afvist"


def test_ukendte_services_afvises_stadig():
    """Den eksisterende vagt maa ikke forsvinde under den nye."""
    ud = rst._exec_restart_self({"services": ["nginx"]})
    assert ud["status"] == "error"


def test_opslaget_har_et_ALDERSLOFT():
    """En zombie-raekke ville ellers blokere enhver genstart for evigt — og en
    vagt der ikke kan tilfredsstilles bliver omgaaet.

    Maalt: 5 «aktive» koersler lokalt, hvoraf ingen levede. Paa runtime var
    tallet 1.
    """
    import inspect
    assert rst.LEVENDE_INDEN_FOR_SEKUNDER >= 3600
    assert "started_at >= ?" in inspect.getsource(rst._aktive_koersler)


def test_opslaget_kaster_aldrig(monkeypatch):
    """En vagt der blokerer paa sin EGEN fejl ville goere en noedvendig
    genstart umulig — vaerre end den fejl den beskytter mod."""
    import core.runtime.db as db
    monkeypatch.setattr(db, "connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    assert rst._aktive_koersler() == []
