"""En indflydelse der kun er halvt synlig, må ikke stå som fuldt synlig.

## Hvad der var galt (18/9-2026)

Agency Cartographer havde broen «Hidden Runtime → Mission Control» staaende
`partial` i tolv scans i traek, og opgaven `task-ec34be0fcce7` havde ventet paa
en implementerings-lane siden 6. juli. Den manglende markoer hed
`partial-surface` og lignede en streng der bare skulle skrives et sted.

Det var den ikke. Klassifikationen modsagde sit eget bevis: tre kanter stod som
`visible-surface` OG indroemmede hver et hul i samme post. En indflydelse der
aendrer adfaerd, og som kun er halvt synlig, stod paa fladen som fuldt synlig.

Broen ligger paa akserne witness, integrity og governance. En etiket der
overdriver synligheden er vaerre end ingen etiket, fordi den lukker
spoergsmaalet.
"""
from __future__ import annotations

from core.services.agency_map import (
    PARTIAL_SURFACE,
    _dark_edges,
    _udled_synlighed,
    build_agency_map_surface,
)


def test_en_kant_der_indroemmer_et_hul_kan_ikke_kalde_sig_fuldt_synlig():
    """Invarianten. Den er hele reparationen."""
    for kant in _dark_edges():
        if str(kant.get("remaining_gap") or "").strip():
            assert kant["visibility"] == PARTIAL_SURFACE, (
                f"{kant['source']} -> {kant['target']} indroemmer et hul "
                f"men staar som {kant['visibility']!r}")


def test_udledningen_kan_kun_NEDGRADERE():
    """Fravaeret af et indroemmet hul er ikke bevis for at der ikke er et.

    Derfor maa udledningen aldrig opfinde synlighed — en kant uden hul
    beholder den etiket den selv baerer.
    """
    uden_hul = {"visibility": "emerging-surface"}
    assert _udled_synlighed(uden_hul) == "emerging-surface"
    med_hul = {"visibility": "visible-surface", "remaining_gap": "mangler en tidslinje"}
    assert _udled_synlighed(med_hul) == PARTIAL_SURFACE
    # Tomt hul er intet hul.
    assert _udled_synlighed({"visibility": "visible-surface", "remaining_gap": "   "}) == "visible-surface"


def test_den_paastaaede_etiket_bevares_saa_forskellen_kan_SES():
    """Rettes etiketten i stilhed, forsvinder beviset for at den var forkert."""
    nedgraderede = [k for k in _dark_edges() if k.get("claimed_visibility")]
    assert nedgraderede, "ingen kant blev nedgraderet — er beviset forsvundet?"
    for kant in nedgraderede:
        assert kant["claimed_visibility"] != kant["visibility"]


def test_fladen_skelner_mellem_halvt_og_helt_synlig():
    """«4 dark edges» laeser som fire loeste sager. Det er ikke det samme som
    tre halvt synlige indflydelser."""
    opsummering = build_agency_map_surface()["summary"]
    assert "dark_edges_partial" in opsummering
    assert opsummering["dark_edges_partial"] >= 1
    assert (opsummering["dark_edges_partial"] + opsummering["dark_edges_visible"]
            <= opsummering["dark_edges"])


# ── en loest reparation skal LUKKES (18/9-2026) ───────────────────────────
#
# Kartografen fandt kun eksisterende opgaver for at undgaa dubletter — den
# lukkede dem aldrig. `task-ec34be0fcce7` stod `blocked` fra 6. juli og ville
# have staaet der ogsaa efter at broen var repareret, fordi ingen spurgte om
# den var det. Samme moenster som genoptagelses-journalen: arbejdet gjort,
# posten aldrig lukket. En koe man ikke kan stole paa, holder man op med at
# kigge i.

def test_en_forbundet_bro_lukker_sin_reparations_opgave(monkeypatch):
    import core.services.agency_cartographer as ac

    from core.services import runtime_tasks

    opdateringer: list[dict] = []
    monkeypatch.setattr(ac, "_find_existing_agency_task",
                        lambda kandidat: {"id": "task-1", "scope": kandidat["scope"]})
    monkeypatch.setattr(runtime_tasks, "update_task",
                        lambda tid, **kw: opdateringer.append({"id": tid, **kw}))
    ud = ac._luk_loeste_reparationer([
        {"status": "connected", "title": "Hidden Runtime -> Mission Control",
         "target": "Hidden Runtime -> Mission Control", "confidence": 1.0, "next_move": "x"},
    ])
    assert ud == ["task-1"]
    assert opdateringer[0]["status"] == "succeeded"
    assert opdateringer[0]["blocked_reason"] == ""


def test_en_bro_der_stadig_er_partial_lukker_INTET(monkeypatch):
    """«partial» er ikke loest. Lukkede vi den, ville koeen se ren ud, mens
    arbejdet stod uroert — praecis den loegn koeen er til for at undgaa."""
    import core.services.agency_cartographer as ac

    monkeypatch.setattr(ac, "_find_existing_agency_task",
                        lambda kandidat: {"id": "task-2", "scope": "x"})
    assert ac._luk_loeste_reparationer([
        {"status": "partial", "title": "t", "target": "t", "confidence": 0.67, "next_move": "x"},
    ]) == []
