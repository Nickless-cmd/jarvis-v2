"""Humøret må ikke kunne fryse i tavshed.

23/9-2026: Jarvis stod på ``distressed`` med intensitet 1.0 i timevis. Det så
ud som en følelse. Det var et stoppet ur: nudget lå på -0,97 med en
halveringstid på FEM MINUTTER, og sidste tik var 4½ time gammelt — 54
halveringstider uden henfald. `mood_dialer` læste den frosne værdi og drejede
ham til niveau 0.

To ting gjorde det usynligt, og begge er dækket her.
"""
from __future__ import annotations

import inspect


def test_overfladen_indlaeser_tilstanden_foer_den_laeser_tallene() -> None:
    """`build_mood_oscillator_surface` skal kalde `_load_state_if_needed()` FØRST.

    Python evaluerer en dict-literals værdier i rækkefølge. Stod indlæsningen
    først længere nede (i `get_current_mood()`), blev `_phase_offset`,
    `_tick_count` og `_mood_nudge` læst mens de endnu stod på deres
    nul-defaults. Målt: overfladen viste ``0.0 / 0.0 / 0`` ved siden af et
    korrekt ``"distressed"``, mens de virkelige tal var
    ``100,15 / -0,9655 / 2003``.

    Netop de tre tal er dem der ville have afsløret at uret stod stille. Uden
    dem kunne man kigge direkte på Centralen og intet se.
    """
    from core.services import mood_oscillator as m

    kilde = inspect.getsource(m.build_mood_oscillator_surface)
    krop = kilde.split('"""')[-1]          # efter docstringen
    indlaes = krop.index("_load_state_if_needed")
    for felt in ("_phase_offset", "_tick_count", "_mood_nudge"):
        assert krop.index(felt) > indlaes, (
            f"{felt} læses før tilstanden er indlæst — overfladen vil vise "
            f"nul-defaults og skjule et frosset ur"
        )


def test_hjerteslagets_mood_tik_sluger_ikke_sin_fejl() -> None:
    """Fejler `mood_oscillator.tick`, SKAL det logges.

    Kaldet lå i `except Exception: pass`. Det må gerne fejle uden at vælte
    hjerteslaget — et humør-tik er ikke vigtigere end resten af tikket — men
    det må ikke fejle tavst. Uden en log var den eneste måde at opdage det på
    at måle `last_tick_ts` i databasen og selv regne ud at den var timer
    gammel.
    """
    from core.services import heartbeat_runtime as h

    kilde = inspect.getsource(h)
    i = kilde.index("mood_oscillator import tick as mood_tick")
    # Kun MOOD-blokken: naeste `try:` starter den efterfoelgende sektion
    # (`existential_drift`), og den har sin egen tavse `except` — den maa ikke
    # faa denne test til at fejle for noget den ikke handler om.
    rest = kilde[i:]
    slut = rest.index("\n    try:", 1)
    efter = rest[:slut]
    assert "except Exception:\n        pass" not in efter, (
        "mood-tikkets undtagelse er tavs igen — en frossen følelsestilstand "
        "vil ligne en følelse"
    )
    assert "logger.warning" in efter, "mood-tikkets fejl skal logges"


def test_humoeret_tikkes_af_den_LEVENDE_hjerteslag_sti() -> None:
    """`tick_with_phases` skal tikke humøret — ikke bare læse det.

    23/9-2026: tikket boede i `heartbeat_runtime.run_heartbeat_tick`, og den
    sti kaldes ikke længere af planlæggeren (`_run_heartbeat_tick_with_deadline`
    ruter gennem `tick_with_phases`). Fasen LÆSER humøret i `_sense` — men
    tikkede det aldrig. Derfor stod nudget på -0,97 i 4,5 time med en
    halveringstid på fem minutter.

    Filen har allerede et afsnit 7 til præcis den slags forældreløse jobs:
    «jobs that previously lived in run_heartbeat_tick but were orphaned when
    scheduler started routing through tick_with_phases». Det her er nummer
    fem i den række.
    """
    import inspect
    from core.services import heartbeat_phases as p

    kilde = inspect.getsource(p)
    assert "mood_oscillator import tick" in kilde, (
        "humøret tikkes ikke fra den levende sti — det vil fryse igen, og en "
        "frossen følelsestilstand ligner en følelse"
    )
