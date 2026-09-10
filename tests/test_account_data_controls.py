"""Eksporten forlader huset — hemmeligheder gør ikke. Fase 10.

MÅLT 10/9-2026 på Bjørns runtime: 50 af 40.000 chat-beskeder indeholder noget
`secret_redaction` fjerner. `export_all` sendte chat-beskeder, sanse-hukommelse,
privat hjerne og identitetsfiler ORDRET — uden ét redaktions-kald nogen steder.

En eksport forlader systemets beskyttelse: den lander i en fil, bliver sendt
videre, lagt op. Derfor er redaktionen obligatorisk, ikke et flag.
"""
from __future__ import annotations

import json


def _falsk_eksport(monkeypatch, indhold):
    from core.services import account_data_controls as a
    monkeypatch.setattr(a, "_export_raa", lambda user_id: indhold)
    return a


def test_hemmeligheder_fjernes_uanset_hvor_dybt_de_ligger(monkeypatch):
    """Eksporten er nøstet: sessioner rummer beskeder, hjernen rummer poster.
    En redaktion der kun ramte topniveauet ville SE UD til at virke."""
    hemmelig = "Bearer " + ("x" * 24)   # lav entropi: detect-secrets skal ikke
                                 # flage vores egen attrap
    a = _falsk_eksport(monkeypatch, {
        "sessions": [{"id": "s1", "messages": [{"content": hemmelig}]}],
        "brain": [{"note": {"dybt": [{"endnu_dybere": hemmelig}]}}],
        "identity": {"SOUL.md": f"noget tekst\n{hemmelig}\nmere tekst"},
        "tal": 42,
    })

    ud = a.export_all("u")
    raa = json.dumps(ud, ensure_ascii=False)
    assert ("x" * 24) not in raa, (
        "en hemmelighed slap ud af eksporten")
    assert ud["tal"] == 42, "ikke-strenge blev ødelagt"
    assert ud["redaction"]["values_redacted"] >= 3, (
        "alle tre niveauer skulle være ramt")


def test_redaktionen_er_synlig_i_eksporten(monkeypatch):
    """En redaktion man ikke kan se, kan man ikke kontrollere. Og modtageren
    skal vide at nøglerne stadig findes i systemet."""
    a = _falsk_eksport(monkeypatch, {"x": "Bearer " + ("y" * 24)})
    ud = a.export_all("u")
    assert ud["redaction"]["applied"] is True
    assert ud["redaction"]["values_redacted"] == 1
    assert "kopi" in ud["redaction"]["note"].lower()


def test_uskyldig_eksport_taeller_nul(monkeypatch):
    a = _falsk_eksport(monkeypatch, {"sessions": [{"messages": [{"content": "hej"}]}]})
    ud = a.export_all("u")
    assert ud["redaction"]["values_redacted"] == 0
    assert ud["sessions"][0]["messages"][0]["content"] == "hej"


def test_det_OFFENTLIGE_navn_er_det_sikre():
    """Da laget blev bygget, brugte den eneste eksisterende kalder `export_all`
    direkte. Havde det navn peget på den rå form, var laget født forbikoblet —
    præcis 'built but not connected', bare med sikkerhedskonsekvenser."""
    from core.services import account_data_controls as a

    assert hasattr(a, "_export_raa"), "den rå form skal være privat"
    assert not hasattr(a, "export_raa")
    import inspect
    assert "_export_raa" in inspect.getsource(a.export_all), (
        "export_all bygger ikke på den rå form — så redigerer den måske intet")


def test_export_json_gaar_gennem_redaktoeren(monkeypatch):
    a = _falsk_eksport(monkeypatch, {"x": "Bearer " + ("z" * 24)})
    tekst = a.export_json("u")
    assert ("z" * 24) not in tekst
    assert '"applied": true' in tekst.lower()
