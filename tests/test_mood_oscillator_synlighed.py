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


def test_tikket_maaler_den_faktiske_tid_frem_for_at_paastaa_en_kadence() -> None:
    """`tick()` uden argument skal bruge den VIRKELIGE tid siden sidst.

    23/9-2026: hjerteslaget kaldte `tick(seconds=30)` hvert 15. MINUT. Humørets
    ur gik dermed 30 gange for langsomt — en halveringstid på fem minutter
    blev til 2½ time i vægurstid, og et nudge på -0,97 tog over et døgn at
    falde til ro.

    Det er den lumske af de to fejl: uret gik, det gik bare forkert. Selv
    efter at tikket blev genforbundet ville han have stået «distressed» i
    timevis.
    """
    import importlib
    from datetime import datetime, UTC

    m = importlib.reload(importlib.import_module("core.services.mood_oscillator"))
    m._loaded_from_disk = True          # ingen DB i denne test
    m._mood_nudge = -0.9
    m._tick_count = 0
    # Lad som om der er gået en halveringstid siden sidst.
    m._last_tick_ts = datetime.now(UTC).timestamp() - m._NUDGE_DECAY_HALF_LIFE_SECONDS

    m.tick()                             # uden argument

    # Én halveringstid → omtrent halvdelen tilbage.
    assert -0.50 < m._mood_nudge < -0.40, (
        f"nudget blev {m._mood_nudge:.3f} — tikket brugte ikke den faktiske "
        f"forløbne tid"
    )


def test_ingen_kalder_paastaar_en_fast_kadence() -> None:
    """Hverken hjerteslagets fase eller den gamle sti må sende et fast tal."""
    import inspect
    from core.services import heartbeat_phases, heartbeat_runtime

    for modul in (heartbeat_phases, heartbeat_runtime):
        kilde = inspect.getsource(modul)
        assert "mood_tick(seconds=" not in kilde, (
            f"{modul.__name__} påstår en kadence — brug tick() uden argument, "
            f"så uret måler sig selv"
        )


def test_workflow_kontrakten_beder_om_batching() -> None:
    """Kontrakten skal sige at uafhængige kald hører i SAMME runde.

    Målt 24/9-2026 over 740 runder: 75 % kaldte præcis ét værktøj, gennemsnit
    1,28 — mens `max_tool_calls_per_turn` sagde 36 og intet i runtime klippede.
    Det kostede ture på 30 runder, som ramte rundeloftet og blev afskåret
    midt i arbejdet.

    Årsagen var ikke en spærring, men en manglende opfordring: kontrakten
    rammesatte en runde som ét fortalt skridt, og så blev ét værktøj det
    naturlige valg. Narrationen skal blive — Bjørn skal kunne følge med — men
    den må ikke koste en runde pr. filopslag.
    """
    import inspect
    from core.services import prompt_contract as pc

    kilde = inspect.getsource(pc)
    i = kilde.index("WORKFLOW (every round)")
    kontrakt = kilde[i:i + 900]
    assert "same round" in kontrakt, (
        "workflow-kontrakten beder ikke om batching — så kalder han ét "
        "værktøj ad gangen og brænder runder"
    )
    # Narrationen skal stadig staa der; batching maa ikke have spist den.
    assert "one short synthesis" in kontrakt
    assert "Never run a round silently" in kontrakt
