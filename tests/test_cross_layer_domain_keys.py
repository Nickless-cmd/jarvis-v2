"""Kontrakt: de tre kryds-lag-moduler skal læse domæne-nøgler ens.

Målt 4/11-2026 i den levende base: `runtime_development_focuses` har 4.026
rækker, hvoraf 3.093 bærer det nyere `focus:bearing:<sætning>` og kun 905 det
gamle `development-focus:runtime:<slug>`. `open_loop_signal_tracking` og
`temporal_recurrence_signal_tracking` havde hver deres private kopi af
`_focus_domain_key`, som krævede `development-focus:{kategori}:`-præfikset — de
så derfor 23 % af fokuslaget og returnerede tomt for resten. `internal_opposition`
så alle 4.026. Samme divergens i `_critic_domain_key`: producenten skriver
`reflective-critic:mismatch:{fokus-nøgle}` (reflective_critic_tracking.py:171),
men to af kopierne forventede et `development-focus:`-led indskudt som
producenten aldrig skriver — nul af 967 critics har nogensinde haft det præfiks.

Testen binder modulerne til de nøgle-formater PRODUCENTERNE faktisk skriver,
ikke til en kopi af implementeringen. Den fejler hvis en fjerde kopi opstår
med en anden form, eller hvis en af dem holder op med at kunne læse et format
der findes i data.
"""
from __future__ import annotations

import pytest

from core.services import internal_opposition_signal_tracking as opposition
from core.services import open_loop_signal_tracking as open_loop
from core.services import temporal_recurrence_signal_tracking as recurrence

# De formater der faktisk findes i `runtime_development_focuses` (målt 4/11-2026).
# Domænet er det TREDJE segment — begge formater har et to-segments præfiks, og
# det gamle format kan bære en undertype efter domænet. Den case blev fanget af
# `test_visible_runs_open_loop_materialization` da udtrækket blev forenet: en
# naiv forening på sidste segment gav ``reinforce-retain`` i stedet for
# ``visible-work`` og brød open-loop-kontrakten.
FOCUS_KEYS = [
    ("focus:bearing:Har afdækket at den åbne post", "Har afdækket at den åbne post"),
    ("development-focus:runtime:render-test", "render-test"),
    ("development-focus:runtime:visible-work:reinforce-retain", "visible-work"),
    ("development-focus:communication:dansk-kort", "dansk-kort"),
    ("development-focus:user-directed:morgenbrief", "morgenbrief"),
]

# Producenten skriver `reflective-critic:mismatch:{fokus-nøgle}`. Type-nøgler
# som `critic:user_correction` bærer intet domæne og skal give tomt.
CRITIC_KEYS = [
    ("reflective-critic:mismatch:focus:bearing:Måler frem for at antage", "Måler frem for at antage"),
    ("reflective-critic:mismatch:development-focus:runtime:render-test", "render-test"),
    ("critic:user_correction", ""),
    ("critic:outcome_failure", ""),
]

MODULES = [
    pytest.param(opposition, id="internal_opposition"),
    pytest.param(open_loop, id="open_loop"),
    pytest.param(recurrence, id="temporal_recurrence"),
]


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize("canonical_key,expected", FOCUS_KEYS)
def test_fokus_noegle_giver_domaene(module, canonical_key: str, expected: str) -> None:
    """Alle tre moduler skal kunne læse begge fokus-formater, ikke kun det gamle."""
    assert module._focus_domain_key(canonical_key) == expected


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize("canonical_key,expected", CRITIC_KEYS)
def test_critic_noegle_giver_domaene(module, canonical_key: str, expected: str) -> None:
    """Mismatch-critics bærer et domæne; type-critics gør ikke."""
    assert module._critic_domain_key(canonical_key) == expected


@pytest.mark.parametrize("canonical_key,_expected", FOCUS_KEYS + CRITIC_KEYS)
def test_modulerne_er_enige(canonical_key: str, _expected: str) -> None:
    """Ingen kopi må afvige fra de to andre for den samme nøgle.

    Det er den vagt der fanger en fjerde kopi: divergensen 4/11-2026 var netop
    at to moduler svarede tomt hvor det tredje svarede et domæne.
    """
    focus_answers = {module.__name__: module._focus_domain_key(canonical_key) for module in (opposition, open_loop, recurrence)}
    critic_answers = {module.__name__: module._critic_domain_key(canonical_key) for module in (opposition, open_loop, recurrence)}
    assert len(set(focus_answers.values())) == 1, focus_answers
    assert len(set(critic_answers.values())) == 1, critic_answers


def test_fokus_match_er_ikke_generisk() -> None:
    """Fokus-matchning må ikke blive løs for at «få liv i» de døde signaler.

    Fristelsen er nærliggende: de fire kryds-lag-producenter giver 0 kandidater,
    og en generisk ord-matchning ville se ud som en rettelse. Målt 4/11-2026 på
    400 historiske correction-critics gav den 41 «matches» — alle på funktionsord
    som «skal», «ikke», «hvordan». Et falsk domæne er værre end et tomt: det
    krydser to lag der ikke taler om det samme, og skriver et signal der ser
    virksomt ud.

    Derfor: en besked der deler funktionsord med en fokus-nøgle, men ikke emnet,
    skal IKKE matche. Den dag nogen bygger en rigtig domæne-dimension, skal
    denne test erstattes — ikke omgås ved at løsne matchningen.
    """
    from core.services.reflective_critic_tracking import _message_matches_focus_key

    fokus_noegle = "focus:bearing:Holder træet rent og commits verificeret"
    # Deler to indholdsord med nøglen («commits», «rent») men handler om noget
    # andet: om at køre commits, ikke om at holde træet rent. En løs matchning
    # ville krydse de to lag; den strenge gør ikke.
    assert not _message_matches_focus_key(fokus_noegle, "Kan du se om de commits der blev kørt er rent faktisk landet")
    # De to emner funktionen faktisk kender, matcher stadig.
    assert _message_matches_focus_key("focus:bearing:danish-concise-calibration", "svar kort på dansk")
    assert _message_matches_focus_key("focus:bearing:avoid-repetitive-openers", "du behøver ikke gentage det")
