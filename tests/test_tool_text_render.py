"""Læsbar text-form for strukturerede tool-resultater.

Uden en `text`-nøgle dumpes resultatet som JSON og cappes ved 8000 tegn, mens
et tool der leverer `text` får 16000. Bjørn oplevede forskellen som at blive
«cuttet efter en tool-runde» — han fik en fil med et hul i midten.
"""
from __future__ import annotations

from core.tools.tool_text_render import render_daemons, render_events, render_rows


def test_daemons_udelader_beskrivelser_saa_67_stk_er_under_loftet():
    """Beskrivelserne er dét der sprænger loftet — og de ændrer sig aldrig.
    Man kigger på status for at vide hvad der KØRER."""
    daemons = [
        {"name": f"daemon_{i}", "enabled": i % 3 == 0,
         "description": "En meget lang beskrivelse " * 12,
         "effective_cadence_minutes": 5, "hours_since_last_run": 1.25,
         "last_result_summary": "alt vel"}
        for i in range(67)
    ]
    t = render_daemons(daemons)
    assert "En meget lang beskrivelse" not in t
    assert len(t) < 8000, "skal kunne være inden for JSON-cappen med god margen"
    assert "67 dæmoner" in t and "tændt" in t


def test_daemons_viser_de_taendte_hver_for_sig_og_samler_de_slukkede():
    daemons = [
        {"name": "koerer", "enabled": True, "effective_cadence_minutes": 3,
         "hours_since_last_run": 0.5, "last_result_summary": "ok"},
        {"name": "sover", "enabled": False, "effective_cadence_minutes": 9},
    ]
    t = render_daemons(daemons)
    assert "koerer" in t and "hver 3. min" in t and "sidst 0.5 t siden" in t
    assert "Slukket (1): sover" in t


def test_daemon_uden_koersel_siger_det_i_stedet_for_at_tie():
    t = render_daemons([{"name": "ny", "enabled": True}])
    assert "aldrig kørt" in t


def test_events_tager_ikke_payload_med_to_gange():
    """`payload` og `payload_json` er samme indhold. At sende begge fordoblede
    den dyreste del af resultatet."""
    ev = [{"created_at": "2026-09-04T08:05:51.850320+00:00",
           "kind": "heartbeat.phased_tick", "family": "heartbeat",
           "payload": "AAA-unikt", "payload_json": "BBB-unikt"}]
    t = render_events(ev)
    assert "AAA-unikt" in t
    assert "BBB-unikt" not in t
    assert "08:05:51" in t and "heartbeat.phased_tick" in t
    assert "2026-09-04" not in t, "datoen gentaget på hver linje er støj"


def test_lang_payload_klippes_pr_linje_ikke_pr_resultat():
    """En enkelt kæmpe payload må ikke æde de andre rækker."""
    ev = [{"created_at": "2026-09-04T08:00:00", "kind": "a", "payload": "x" * 5000},
          {"created_at": "2026-09-04T08:00:01", "kind": "vigtig-senere", "payload": "kort"}]
    t = render_events(ev)
    assert "vigtig-senere" in t, "den sidste række skal overleve den første"
    assert len(t) < 1000


def test_rows_bliver_en_justeret_tabel():
    t = render_rows(["id", "navn"], [{"id": 1, "navn": "en"}, {"id": 22, "navn": "to"}])
    linjer = t.split("\n")
    assert linjer[0] == "2 rækker"
    assert "id" in linjer[2] and "navn" in linjer[2]
    # kolonnebredden følger indholdet, ikke en fast bredde
    assert linjer[3].startswith("--")


def test_rows_siger_hoejt_naar_der_er_flere_end_de_200():
    t = render_rows(["a"], [{"a": i} for i in range(200)], capped=True)
    assert "AFKORTET ved 200" in t


def test_tomt_resultat_siger_hvilke_kolonner_der_var():
    t = render_rows(["id", "navn"], [])
    assert "0 rækker" in t and "id" in t and "navn" in t


def test_renderne_kaster_aldrig():
    """Et tool-resultat må ikke kunne vælte turen, uanset hvad der kom ind."""
    assert render_daemons(None) and render_events(None) and render_rows(None, None)
    assert render_daemons([{"navn-uden-name": 1}])
    assert render_events([{"intet": "match"}])
