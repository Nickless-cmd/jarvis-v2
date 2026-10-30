"""A/B-armen modtager nu et udfald (28/10-2026).

BAGGRUND. `central_prompt_explore.record_trial()` har altid krævet et `outcome`, men den
ENESTE kalder (`prompt_contract.py:2302`) udelod parameteren — den har default `""`. Derfor
ramte hver tur `if not outcome: return`, og forsøget kunne ALDRIG samle ét datapunkt. Armens
tilstandsmaskine stod derfor urørt i månedsvis: et forsøg der så levende ud men var dødt.

Årsagen er arkitektonisk, ikke en glemt parameter: prompten bygges FØR turen kører, så
udfaldet eksisterer ikke på bygningstidspunktet. Rettelsen er to-faset — kompositionen gemmes
ved bygningen (`note_composition`), udfaldet sendes ved run-finalize (`record_turn_outcome`).

Disse tests værner tre ting:
  1. Kæden virker: et udfald tælles ind i den arm der faktisk kørte.
  2. En brudt kobling er SYNLIG (tælles), ikke tavs — det var netop fejlen før.
  3. Med live-flaget slukket tælles intet, og manglende kontekst er ikke en fejl.
"""
from __future__ import annotations

import pytest

from core.services import central_prompt_explore as cpe


@pytest.fixture()
def isoleret(monkeypatch):
    """Egen kv-state pr. test — rører ikke den levende runtime-state."""
    butik: dict[str, object] = {}

    monkeypatch.setattr(cpe, "_kv_get", lambda k, d=None: butik.get(k, d))
    monkeypatch.setattr(cpe, "_kv_set", lambda k, v: butik.__setitem__(k, v))
    # ContextVar er per-kontekst; nulstil så tests ikke lækker til hinanden.
    cpe._sidste_komposition.set(None)
    yield butik
    cpe._sidste_komposition.set(None)


def _start_forsoeg(butik: dict, arm: str = "absent", tt: str = "visible", sec: str = "attention"):
    st = cpe._new_state(tt, sec)
    st["arm"] = arm
    butik[cpe._STATE_KEY] = st
    return st


def test_udfald_taelles_i_absent_armen(isoleret):
    """Kernen: et udfald fra finalize lander i armen — det gjorde det ALDRIG før."""
    isoleret[cpe._EXPLORE_FLAG] = True
    st = _start_forsoeg(isoleret, arm="absent")
    foer = st["left"]

    # Prompt-bygningen: sektionen var IKKE med (absent-armen), udfaldet kendes ikke endnu.
    cpe.note_composition("visible", ["memory_recall", "affect"])
    # Run-finalize: nu kendes udfaldet.
    cpe.record_turn_outcome("completed")

    st = isoleret[cpe._STATE_KEY]
    assert st["absent_total"] == 1, "udfaldet blev ikke talt ind i absent-armen"
    assert st["absent_good"] == 1, "et 'completed' skal tælle som godt udfald"
    assert st["left"] == foer - 1, "forsøget skal skride frem — ellers står det stille"


def test_udfald_taelles_i_present_armen(isoleret):
    """Present-armen kræver at sektionen FAKTISK var med — forurening skal afvises."""
    isoleret[cpe._EXPLORE_FLAG] = True
    _start_forsoeg(isoleret, arm="present", sec="memory_recall")

    cpe.note_composition("visible", ["memory_recall", "affect"])
    cpe.record_turn_outcome("completed")

    st = isoleret[cpe._STATE_KEY]
    assert st["present_total"] == 1
    assert st["present_good"] == 1


def test_forurening_afvises(isoleret):
    """Sektionen var FRAVÆRENDE i present-armen → udfaldet må ikke tælles (det ville forurene)."""
    isoleret[cpe._EXPLORE_FLAG] = True
    _start_forsoeg(isoleret, arm="present", sec="memory_recall")

    cpe.note_composition("visible", ["affect"])          # memory_recall er IKKE med
    cpe.record_turn_outcome("completed")

    st = isoleret[cpe._STATE_KEY]
    assert st["present_total"] == 0, "inkonsistent tur blev talt — dataen er forurenet"


def test_daarligt_udfald_taelles_som_daarligt(isoleret):
    """'failed' må ikke tælles som godt — ellers kan armene ikke sammenlignes."""
    isoleret[cpe._EXPLORE_FLAG] = True
    _start_forsoeg(isoleret, arm="absent")

    cpe.note_composition("visible", ["affect"])
    cpe.record_turn_outcome("failed")

    st = isoleret[cpe._STATE_KEY]
    assert st["absent_total"] == 1
    assert st["absent_good"] == 0


def test_brudt_kobling_er_synlig_ikke_tavs(isoleret):
    """MODPRØVEN. Uden en komposition i konteksten skal det TÆLLES — ikke forsvinde.

    Det var præcis fejlen der holdt armen død: `if not outcome: return` gjorde et helt
    forsøg tavst. En fremtidig ændring der fjerner note_composition skal derfor ikke
    give grønne tests — den skal give en synlig tælling.
    """
    isoleret[cpe._EXPLORE_FLAG] = True
    _start_forsoeg(isoleret, arm="absent")

    cpe.record_turn_outcome("completed")                 # ingen note_composition først

    assert isoleret.get(cpe._MISSING_KEY) == 1, "brudt kobling forsvandt i tavshed"
    st = isoleret[cpe._STATE_KEY]
    assert st["absent_total"] == 0, "uden kontekst må intet tælles i armen"


def test_shadow_taeller_hverken_arm_eller_mangel(isoleret):
    """Flaget er OFF som default: intet forsøg kører, så manglende kontekst er ikke en fejl."""
    isoleret[cpe._EXPLORE_FLAG] = False
    _start_forsoeg(isoleret, arm="absent")

    cpe.record_turn_outcome("completed")

    assert cpe._MISSING_KEY not in isoleret, "shadow blev talt som fejl — det er støj"
    st = isoleret[cpe._STATE_KEY]
    assert st["absent_total"] == 0


def test_kalderen_i_composeren_sender_ikke_outcome_laengere_kraevet():
    """Dokumenterer rod-årsagen: composeren kan pr. konstruktion ikke kende udfaldet.

    Testen fejler hvis nogen en dag tror at `outcome`-parameteren i observe_composition
    løser problemet — den er tom på bygningstidspunktet, og det er derfor koblingen er
    to-faset. Læses som en vagt mod at 'forenkle' rettelsen væk.
    """
    import inspect

    from core.services.central_prompt_composer import observe_composition

    signatur = inspect.signature(observe_composition)
    assert signatur.parameters["outcome"].default == "", (
        "outcome har fået en anden default — så skal den to-fasede kobling revurderes"
    )
