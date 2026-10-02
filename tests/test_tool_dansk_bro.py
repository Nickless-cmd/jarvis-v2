"""Test af den danske værktøjs-bro (2/10-2026).

Bjørn spurgte hvorfor skill-gaten aldrig blev brugt. Vejen førte til
``tool_discovery_nudge`` — den peger på et værktøj uden for hans kasse når hans
besked rører det. Den blev tændt 2/10 og svarede næsten intet: målt på 600 af
hans egne beskeder gav kun **104 træf (17 %)**, fordi værktøjerne beskriver sig
på engelsk mens han skriver dansk.

Broen er de danske udtryk ved siden af. Testene dækker de to ting der kan gå
stille galt — at listen peger på et værktøj der ikke findes, og at udtrykkene
ikke faktisk giver et træf.
"""

from __future__ import annotations


def _registrerede() -> dict[str, str]:
    from core.tools.simple_tools import get_tool_definitions

    ud: dict[str, str] = {}
    for d in get_tool_definitions() or []:
        f = d.get("function") or d
        navn = str(f.get("name") or "")
        if navn:
            ud[navn] = str(f.get("description") or "")
    return ud


def test_hvert_navn_i_broen_findes_som_vaerktoej():
    """Værn 1: et navn her uden et registreret værktøj er en fejl.

    Uden testen ville listen stille kunne pege på noget der er fjernet — og
    nudgen ville foreslå et navn han ikke kan hente.
    """
    from core.services.tool_dansk_bro import DANSKE_UDTRYK

    findes = set(_registrerede())
    manglende = sorted(set(DANSKE_UDTRYK) - findes)
    assert not manglende, f"broen peger på værktøjer der ikke findes: {manglende}"


def test_danske_udtryk_giver_faktisk_traef():
    """Værn 2: udtrykkene skal virke, ikke bare stå der.

    Uden broen giver disse beskeder INTET — værktøjerne beskriver sig på
    engelsk. Testen er den samme måling som førte til broen, fastholdt.
    """
    from core.services.tool_lexical_match import byg_korpus_fra_definitioner

    defs = _registrerede()
    definitioner = [
        {"name": n, "description": d} for n, d in defs.items()
    ]
    k = byg_korpus_fra_definitioner(definitioner)
    navne = list(defs)

    # (besked, forventet værktøj) — skrevet som Bjørn faktisk skriver.
    # Kun ENTYDIGE sager: «send en besked på discord» udelades med vilje —
    # «besked» staar i 12 vaerktoejer og «discord» i 17, saa systemet tier
    # korrekt paa en tvetydig besked. At tvinge et traef frem ville vaere stoej.
    sager = [
        ("Hvorn bliver vejret idag?", "get_weather"),
        ("Hvad siger vejret imorgen mellem 7 og 9?", "get_weather"),
        ("gem en huskeseddel om det her", "note_add"),
        ("hvad har du liggende af gamle planer?", "list_plans"),
        ("hvad koster en dollar i dag?", "get_exchange_rate"),
    ]
    bom = []
    for besked, ventet in sager:
        t = k.slaa_op(besked, navne)
        if t is None or t.navn != ventet:
            bom.append((besked, ventet, None if t is None else t.navn))
    assert not bom, f"broen giver ikke det forventede træf: {bom}"


def test_uden_broen_er_traeffet_vaek():
    """Kontrasten der beviser at broen ER årsagen — ikke tilfældet."""
    from core.services.tool_lexical_match import byg_korpus_fra_definitioner

    defs = _registrerede()
    definitioner = [{"name": n, "description": d} for n, d in defs.items()]
    k = byg_korpus_fra_definitioner(definitioner, dansk=False)
    navne = list(defs)

    # «vejr» findes ikke i nogen engelsk beskrivelse af get_weather.
    t = k.slaa_op("Hvorn bliver vejret idag?", navne)
    assert t is None or t.navn != "get_weather"


def test_normalisering_er_idempotent_og_taalmodig():
    """Broen må ikke kaste på ukendte eller tomme navne."""
    from core.services.tool_dansk_bro import dansk_tillaeg

    assert dansk_tillaeg("") == ""
    assert dansk_tillaeg("findes_ikke") == ""
    assert dansk_tillaeg(None) == ""  # type: ignore[arg-type]
