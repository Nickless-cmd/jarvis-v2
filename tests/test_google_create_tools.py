"""Opret-værktøjerne for Google Docs, Sheets og Slides.

Baggrund (Bjørn 27/10-2026): kataloget havde læsere og skrivere, men ingen
oprettere. `docs_create`, `sheets_create` og `slides_create` lukker det hul.

Det der kan gå stille galt, og som denne fil værner:

* Et værktøj der står i kataloget uden en handler — det ser ud som om det
  findes, og fejler først når nogen kalder det.
* En handler uden en force-handler — så svarer et GODKENDT kald
  `approval_needed` igen, i ring. Godkendelsen kom frem, handlingen skete
  aldrig. (Invarianten er også låst i `test_approval_har_force_handler.py`;
  her gentages den for de tre nye navne, så filen står alene.)
* En opretter der ikke kræver godkendelse — den skriver i brugerens Drive
  uden at nogen har set det.
* En tom titel der slipper igennem og laver et dokument uden navn.
"""

from __future__ import annotations

import pytest

NYE = ("docs_create", "sheets_create", "slides_create")


def test_alle_tre_er_i_kataloget(monkeypatch):
    """De skal annonceres naar godkendelses-broen er aktiv.

    Gaten `approval_rollout_gate` holder BEVIDST nye godkendelses-vaerktoejer
    tilbage saa laenge broen ikke er aktiv — det er dens hele formaal, og den
    skal ikke saenkes for at faa denne test groen. I produktion er broen aktiv
    (maalt 27/10-2026: `{'enabled': True}`); i en isoleret test-runtime er den
    det ikke, fordi HOME peger paa en tom mappe. Derfor maales der MED broen.
    """
    from core.tools import approval_rollout_gate as gate
    from core.tools.simple_tools import get_tool_definitions

    monkeypatch.setattr(gate, "bridge_active", lambda: True)
    navne = {(d.get("function") or {}).get("name") for d in (get_tool_definitions() or [])}
    mangler = [n for n in NYE if n not in navne]
    assert not mangler, f"mangler i kataloget: {mangler}"


def test_gaten_holder_dem_tilbage_naar_broen_er_i_skygge(monkeypatch):
    """Uden broen maa de IKKE annonceres — de er nye, ikke grandfathered.

    Dette er den anden halvdel af sandheden: testen ovenfor beviser at de kan
    rulles ud, denne beviser at de ikke smyger sig forbi gaten.
    """
    from core.tools import approval_rollout_gate as gate

    monkeypatch.setattr(gate, "bridge_active", lambda: False)
    for navn in NYE:
        ok, grund = gate.may_advertise(navn)
        assert ok is False, f"{navn} slap forbi gaten uden bro"
        assert "ikke aktiv" in grund
        assert navn not in gate.GRANDFATHERED, (
            f"{navn} er skrevet paa grandfathered-listen — den maa kun blive kortere"
        )


def test_alle_tre_har_en_handler():
    from core.tools.simple_tools import _TOOL_HANDLERS

    mangler = [n for n in NYE if n not in _TOOL_HANDLERS]
    assert not mangler, f"mangler handler: {mangler}"


def test_alle_tre_har_en_force_handler():
    """Uden force-handler gaar et godkendt kald i ring."""
    from core.tools.force_handlers import _FORCE_HANDLERS

    mangler = [n for n in NYE if n not in _FORCE_HANDLERS]
    assert not mangler, f"mangler force-handler: {mangler}"


def test_alle_tre_kraever_godkendelse():
    """Ingen af dem maa skrive i Drive uden at et menneske har set kaldet."""
    from core.tools.simple_tools_native import (
        _exec_docs_create,
        _exec_sheets_create,
        _exec_slides_create,
    )

    for handler in (_exec_docs_create, _exec_sheets_create, _exec_slides_create):
        svar = handler({"title": "test"})
        assert svar.get("status") == "approval_needed", (
            f"{handler.__name__} skrev uden godkendelse: {svar}"
        )


def test_tom_titel_afvises_foer_godkendelse():
    """En tom titel skal fejle som en fejl — ikke som et godkendelses-kort."""
    from core.tools.simple_tools_native import (
        _exec_docs_create,
        _exec_sheets_create,
        _exec_slides_create,
    )

    for handler in (_exec_docs_create, _exec_sheets_create, _exec_slides_create):
        svar = handler({"title": "   ", "_runtime_trust_all": True})
        assert svar.get("status") == "error"
        assert svar.get("error") == "title_required"


def test_connector_scope_laaser_de_tre_op():
    """Connector-kataloget skal naevne dem — ellers er de utilgaengelige."""
    from core.services.connectors import _CATALOG

    pr_connector = {c["id"]: c.get("tools") or [] for c in _CATALOG}
    assert "docs_create" in pr_connector["google-docs"]
    assert "sheets_create" in pr_connector["google-sheets"]
    assert "slides_create" in pr_connector["google-slides"]


def test_force_handler_springer_godkendelsen_over(monkeypatch):
    """Efter et ja skal kaldet gaa IGENNEM — ikke spoerge igen."""
    from core.tools import force_handlers

    kaldt = {}

    def falsk_create_doc(user_id, title, *, text=""):
        kaldt["user_id"] = user_id
        kaldt["title"] = title
        kaldt["text"] = text
        return {"status": "ok", "document_id": "abc"}

    monkeypatch.setattr(
        "core.services.google_connector.create_doc", falsk_create_doc
    )
    svar = force_handlers._force_docs_create({"title": "Mit dokument", "text": "hej"})
    assert svar.get("status") == "ok", svar
    assert kaldt["title"] == "Mit dokument"
    assert kaldt["text"] == "hej"


def test_create_doc_rapporterer_tekstfejl_uden_at_skjule_dokumentet(monkeypatch):
    """Dokumentet findes nu — en fejl i indsaettelsen maa ikke skjule id'et."""
    from core.services import google_connector as gc

    monkeypatch.setattr(
        gc, "_send", lambda *a, **k: {"status": "ok", "data": {"documentId": "doc-1"}}
    )
    monkeypatch.setattr(
        gc, "append_doc", lambda *a, **k: {"status": "error", "error": "docs_http_500"}
    )
    svar = gc.create_doc("u1", "Titel", text="noget")
    assert svar["status"] == "ok"
    assert svar["document_id"] == "doc-1"
    assert svar["text_status"] == "docs_http_500"


def test_create_sheet_rapporterer_raekkefejl_uden_at_skjule_arket(monkeypatch):
    from core.services import google_connector as gc

    monkeypatch.setattr(
        gc, "_send", lambda *a, **k: {"status": "ok", "data": {"spreadsheetId": "sh-1"}}
    )
    monkeypatch.setattr(
        gc, "write_sheet", lambda *a, **k: {"status": "error", "error": "sheets_http_400"}
    )
    svar = gc.create_sheet("u1", "Ark", values=[["a"]])
    assert svar["status"] == "ok"
    assert svar["spreadsheet_id"] == "sh-1"
    assert svar["values_status"] == "sheets_http_400"


@pytest.mark.parametrize("funktion", ["create_doc", "create_sheet", "create_slides"])
def test_tom_titel_i_connectoren_afvises(funktion):
    from core.services import google_connector as gc

    svar = getattr(gc, funktion)("u1", "  ")
    assert svar.get("status") == "error"
    assert svar.get("error") == "title_required"
