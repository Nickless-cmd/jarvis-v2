from __future__ import annotations


def test_resultat_kan_kun_hentes_med_samme_tur_og_tool_id() -> None:
    from core.services.tool_result_binding_store import hent, registrer

    registrer("run-a", "call-1", {"status": "ok", "data": {"price": 6.91}})

    assert hent("run-a", "call-1") == {
        "status": "ok",
        "data": {"price": 6.91},
    }
    assert hent("run-b", "call-1") is None
    assert hent("run-a", "call-2") is None


def test_resultatkopien_kan_ikke_muteres_af_en_laeser() -> None:
    from core.services.tool_result_binding_store import hent, registrer

    original = {"data": {"values": [6.91]}}
    registrer("run-copy", "call-copy", original)
    laest = hent("run-copy", "call-copy")
    assert laest is not None
    laest["data"]["values"][0] = 0

    assert hent("run-copy", "call-copy") == {"data": {"values": [6.91]}}


def test_faelles_followup_konvertering_registrerer_det_strukturerede_resultat() -> None:
    from core.services.jarvis_ui_guard import normalisér
    from core.services.visible_followup_results import to_followup_results

    kald = [{"id": "call-followup", "function": {"name": "weather"}}]
    resultater = [{
        "tool_name": "weather",
        "arguments": {
            "_runtime_turn_id": "run-followup",
            "_runtime_tool_use_id": "call-followup",
        },
        "result": {"status": "ok", "current": {"temperature": 6.91}},
        "result_text": "6.91",
        "status": "ok",
    }]
    to_followup_results(kald, resultater, {0: "6.91"})
    tekst = (
        '```jarvis-ui\n'
        '{"type":"progress","items":[{"label":"Temperatur",'
        '"value":"{ref:call-followup.current.temperature}"}]}\n```'
    )

    ud = normalisér(tekst, run_id="run-followup")

    assert '"value": 6.91' in ud


def test_followup_konvertering_registrerer_og_guard_binder():
    import json

    from core.services.jarvis_ui_guard import normalisér
    from core.services.visible_followup_results import to_followup_results

    tc = [{"id": "toolu_e2e", "function": {"name": "maal"}}]
    sr = [{
        "tool_name": "maal", "status": "ok", "result_text": "ok",
        "result": {"temp": 6.91},
        "arguments": {"_runtime_turn_id": "run-e2e"},
    }]
    to_followup_results(tc, sr, {})
    blok = {"type": "progress", "items": [{"label": "T", "value": "{ref:toolu_e2e.temp}"}]}
    tekst = "```jarvis-ui\n" + json.dumps(blok) + "\n```"
    ud = normalisér(tekst, run_id="run-e2e")
    assert "6.91" in ud and "{ref:" not in ud
    # anden tur kan ikke læse den
    assert "6.91" not in normalisér(tekst, run_id="anden-tur")
