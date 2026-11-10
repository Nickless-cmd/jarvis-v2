"""Grænsen mellem continuation-vinduet og registreringen — målt og afgjort 10/11-2026.

To gates deler kernen ``_detect_intent_core`` i ``core/services/unfinished_intent.py``,
men de har vidt forskellig pris for et falsk træf:

* ``detect_unfinished_intent`` (continuation) starter et AUTONOMT run der svarer
  Bjørn i hans navn. Prisen er høj (23/6-incidenten: fabrikeret samtykke). Derfor
  scanner den kun de sidste ``_TAIL_WINDOW_CHARS`` tegn: et løfte midt i et svar
  der fortsætter og konkluderer er ikke en pause.
* ``detect_promise_intent`` (registrering) skriver ét ``matched_text`` til
  ``promise_ledger``. Målt 10/11-2026 er prisen IKKE nul: sektionen
  ``_pending_promises_section`` rejser løftet i næste turs prompt som en ordre
  («FØR du svarer noget andet: har du FAKTISK gjort det …»), og
  ``clear_promises`` kaldes ingen steder i produktionen — kun i tests. Et
  registreret løfte står derfor i op til 30 min (TTL), også når det blev indfriet
  i samme svar.

Derfor er vinduet BEVIDST beholdt for begge gates. Målt på 3000 nyeste
assistent-svar: registreringen fangede 21, mens 261 indeholdt et løfte-mønster
uden for vinduet — men 188 af dem blev indfriet i samme svar, og de resterende
75 var narrative overgange («Lad mig se hvad der står … Rollerne er …»). At
udvide vinduet ville registrere afsluttet arbejde som et åbent løfte.

Testene her fæstner den kontrakt, så grænsen er dokumenteret frem for tavs.
"""
from __future__ import annotations

import pytest

import core.services.unfinished_intent as ui


@pytest.fixture
def langt_svar_med_loefte() -> str:
    """Et svar hvor løftet ligger midt i teksten, langt fra slutningen."""
    status = (
        "Statusrapporten indeholder verificerede resultater "
        "fra dagens gennemgang. "
    )
    tekst = (
        status * 30
        + "Lad mig se hvad rollerne faktisk styrer i dag. "
        + status * 30
    )
    assert len(tekst) > 1000
    return tekst


def test_continuation_ignorerer_et_loefte_midt_i_svaret(
    langt_svar_med_loefte: str,
) -> None:
    """Et løfte midt i et svar der fortsætter må ikke starte et autonomt run."""
    assert ui.detect_unfinished_intent(langt_svar_med_loefte) is None


def test_continuation_bruger_stadig_tail_vinduet() -> None:
    """Vinduet er den mekanisme der bærer testen ovenfor — den må ikke forsvinde."""
    loefte = "Lad mig se hvad rollerne faktisk styrer i dag. "
    efter_loeftet = "x" * ui._TAIL_WINDOW_CHARS
    tekst = loefte + efter_loeftet

    # Løftet slutter præcis før det udsnit continuation må undersøge.
    assert tekst[-ui._TAIL_WINDOW_CHARS:] == efter_loeftet
    assert ui.detect_unfinished_intent(tekst) is None


def test_registreringen_ser_loeftet_naar_det_staar_i_slutningen() -> None:
    """Registreringen fanger løftet når det ER en pause — dvs. i vinduet."""
    tekst = (
        "Statusrapporten indeholder verificerede resultater. " * 10
        + "Lad mig se hvad rollerne faktisk styrer i dag."
    )
    intent = ui.detect_promise_intent(tekst)

    assert isinstance(intent, ui.UnfinishedIntent)
    assert intent.pattern == "lad_mig"


def test_registreringen_ser_ikke_et_indfriet_loefte_midt_i_svaret(
    langt_svar_med_loefte: str,
) -> None:
    """Den dokumenterede grænse: et løfte uden for vinduet registreres ikke.

    Det er et BEVIDST valg, ikke en glemt fejl. Prisen for at registrere det
    ville være et afsluttet arbejde der rejses som et åbent løfte i næste
    prompt — og ledgeren rydder det ikke selv (``clear_promises`` kaldes ikke
    i produktionen). Ændres beslutningen, skal denne test vendes eksplicit.
    """
    assert ui.detect_promise_intent(langt_svar_med_loefte) is None


def test_kort_tekst_under_graensen_registreres_ikke() -> None:
    """``_MIN_TEXT_LEN`` er målt uden praktisk betydning — og grænsen er tavs.

    Kun 23 af 4000 assistent-svar er under 50 tegn, og ingen af dem er løfter
    («Kører.», «Generation cancelled.»). Korttekst-grenen prøver bevidst kun
    ``_PROMISE_PHRASE_RE`` og ``_FUTURE_ACTION_PROMISE_RE`` — ikke
    ``_JEG_SKAL_RE``/``_LAD_MIG_RE``. Testen fæstner den nuværende adfærd, så
    en fremtidig ændring af grænsen bliver et bevidst valg.
    """
    tekst = "Jeg skal lige tjekke nøglerne"
    assert len(tekst) < ui._MIN_TEXT_LEN
    assert ui.detect_promise_intent(tekst) is None


def test_kort_future_action_registreres() -> None:
    """Den gren der FAKTISK virker under grænsen skal blive ved med at virke."""
    tekst = "Jeg tjekker lige nøglerne"
    assert len(tekst) < ui._MIN_TEXT_LEN
    intent = ui.detect_promise_intent(tekst)

    assert isinstance(intent, ui.UnfinishedIntent)
    assert intent.pattern == "future_action_promise"


@pytest.mark.parametrize(
    "tekst",
    [
        "Vil du have at jeg tjekker X?",
        # "nu" gør future-action-regexet relevant, så denne variant beviser
        # at registreringens sætnings-guard faktisk blokerer tilbuddet.
        "Vil du have at jeg tjekker X nu?",
    ],
)
def test_tilbud_til_brugeren_registreres_ikke(tekst: str) -> None:
    assert ui.detect_promise_intent(tekst) is None


def test_negation_registreres_ikke() -> None:
    assert ui.detect_promise_intent("Jeg skriver ikke noget nu") is None


def test_retorisk_spoergsmaalstegn_draeber_ikke_registreringen() -> None:
    """Rettelsen fra side-02afb491ea: et retorisk «?» er ikke et tilbud."""
    tekst = (
        "Jeg tjekker lige at nøglerne faktisk er væk fra pending, "
        "så det ikke bare er din overbevisning jeg citerer?"
    )
    intent = ui.detect_promise_intent(tekst)

    assert isinstance(intent, ui.UnfinishedIntent)
