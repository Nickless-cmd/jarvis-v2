"""Coverage-gate alias: real tests live in test_unfinished_intent_detector.py.

This file exists so the test-coverage pre-commit hook is satisfied for
edits to core/services/unfinished_intent.py. The bulk of the suite lives
in test_unfinished_intent_detector.py (collected on its own); this file
holds the question-ending regression directly so the two never depend on
a cross-test-module ``import *`` (which broke full-suite collection —
``tests`` is not a package).
"""


def test_question_ending_suppresses_continuation():
    """Bjørn 2026-06-23: Jarvis spurgte 'skal jeg genstarte?', fik intet svar, og
    genstartede SELV (continuation fabrikerede samtykke). Et afsluttende spørgsmål =
    han venter bevidst på brugeren → ALDRIG continuation."""
    from core.services.unfinished_intent import detect_unfinished_intent as d
    assert d("Jeg lovede en genstart. Jeg genstarter den nu — skal jeg gøre det?") is None
    assert d("Vil du have at jeg implementerer specen nu og deployer med det samme?") is None
    assert d("Skal jeg genstarte serveren?") is None
    # Løfte UDEN spørgsmål fanges stadig (ingen over-suppression)
    assert d("Jeg går i gang!").pattern == "future_action_promise"


def test_handoff_phrase_ending_suppresses_continuation():
    """Bjørn 2026-08-15: efter en fil-sletning sluttede Jarvis med den høflige afslutning
    'Hvis der er andet, jeg skal kigge på, så sig til.' — kontrollen givet tilbage til
    brugeren, men UDEN '?'. Detektoren misfyrede på 'jeg skal kigge' og spawnede en
    continuation der FABRIKEREDE en cache-check. En afsluttende handoff = venter bevidst
    på brugeren → ALDRIG continuation."""
    from core.services.unfinished_intent import detect_unfinished_intent as d
    # Det præcise real-world tilfælde (indeholder 'jeg skal kigge' + handoff-slut)
    assert d("Slettet og bekræftet — filen findes ikke længere på din maskine. Godt at "
             "have dig hjemme, Bjørn. Hvis der er andet, jeg skal kigge på, så sig til.") is None
    # Pause-pattern + handoff-slut i samme besked → handoff vinder
    assert d("Jeg skal lige kigge på det for en sikkerheds skyld. Men ellers, sig til.") is None
    assert d("Alt er ryddet op. Lad mig vide hvis du vil have mig til at tjekke mere.") is None
    assert d("Filen er væk. Giv besked hvis der dukker noget andet op.") is None
    # Ægte pause UDEN handoff-slut fanges stadig (ingen over-suppression)
    assert d("Jeg skal først undersøge databasen for at være sikker på tallene passer.").pattern == "jeg_skal"
    assert d("Hold — lad mig lige tjekke hvad der ligger, så vi ikke bygger parallelt.").pattern == "lad_mig"
