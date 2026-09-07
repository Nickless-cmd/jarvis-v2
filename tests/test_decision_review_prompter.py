"""Anmelderen skal kunne se ALLE aktive direktiver — ikke de første 20.

Målt 7/9-2026: der var **45 aktive** behavioral_decisions, og
`list_active_decisions(limit=20)` gjorde de sidste 25 usynlige.

Sorteringen er `priority DESC, updated_at DESC`, så afskæringen **flytter
sig**: et opdateret direktiv rykker op og skubber et andet ud, uden at nogen
kan se hvilke der faldt ud af syne.

Hvad der lå i halen:

    #25  adherence 0,125  "Brug curiosity-værktøjerne aktivt"   ← 933 brud
    #32  adherence 0,025  "tjek mails ved ny session"           ← dårligst af alle
    #33  adherence None   "Spørg altid: har du lavet andre ændringer siden?"

Systemets to dårligst efterlevede direktiver kunne hverken genmåles,
eskaleres eller pensioneres. Og efter de første 20 var anmeldt, sprang
24-timers-porten dem over — så de følgende tik anmeldte ingenting.
"""

from __future__ import annotations


def test_anmelderen_henter_alle_aktive(monkeypatch):
    """Selve fejlen: grænsen skal dække mere end de 45 der fandtes."""
    from core.services import decision_review_prompter as P

    set_limit: list[int] = []
    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions",
        lambda *, limit: set_limit.append(limit) or [],
    )
    P.review_pending_decisions()
    assert set_limit and set_limit[0] >= 100, (
        "anmelderen henter kun %s aktive — halen bliver usynlig igen" % set_limit
    )


def test_loftet_pr_tik_er_uroert():
    """`_MAX_REVIEW_PER_TICK` er bremsen på LLM-belastning, ikke på synlighed.

    De to blev blandet sammen: fordi listen var afkortet til 20, så det ud som
    om loftet virkede. Loftet skal blive — det er 24-timers-porten der skal
    rotere gennem hele listen.
    """
    from core.services.decision_review_daemon import _MAX_REVIEW_PER_TICK

    assert 1 <= _MAX_REVIEW_PER_TICK <= 10


def test_graensen_er_et_TAL_ikke_uendelig():
    """_db_list kræver en grænse, og en uendelig ville bare flytte problemet
    til den dag nogen har 10.000 direktiver."""
    from core.services.decision_review_prompter import _ALL_ACTIVE

    assert isinstance(_ALL_ACTIVE, int) and _ALL_ACTIVE >= 100
