"""Bider loftet gennem HELE kaeden — og overlever opgavens id?

`test_genoptagelses_kaeden.py` pinner at TALLET arves naar koerslen
journalfoerer sig. Den her fil gaar et skridt laengere og replikerer
produktionens raekkefoelge led for led:

    aegte brugertur -> segment loeb toer -> posten goeres genoptagelig
    -> dispatcheren tager kravet -> stempler kaeden -> fortsaettelsen
    journalfoerer sig -> det nye segment loeb toer -> ...

To ting maales, og de er ikke den samme:

1. **Loftet.** `recovery_attempt` skal stige for hvert led, saa
   `claim_due_recovery` til sidst naegter at tage kravet. Bjoern 14/10-2026:
   «Byg task_id-kaeden saa genoptagelses-loftet bider.»

2. **Identiteten.** Hvert led skal baere den SAMME opgave. Maalt i
   produktionen 14/10-2026: `mark_started` skriver `task_id = run_id`, saa
   hvert led fik sin egen identitet — `detached-run visible-9ae8aafd
   fortsaetter opgave visible-9f31b94c`, hvor `9f31b94c` selv var en
   fortsaettelse. Er identiteten ny ved hvert led, er der ikke én kaede men
   en raekke af enkelte opgaver, og saa kan ingen taeller i verden samle dem.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _isoleret_lager(monkeypatch):
    """Samme isolerede lager som `test_genoptagelses_kaeden.py` bruger."""
    lager: dict = {}
    monkeypatch.setattr(ifr, "_load", lambda: lager)
    monkeypatch.setattr(ifr, "_save", lambda d: lager.update(d))
    return lager


def _fortsaet(run_id: str, krav: dict) -> None:
    """Praecis den raekkefoelge dispatcheren og `detached_run` bruger.

    `detached_run` stempler kaeden FOER `start_visible_run` journalfoerer
    turen — og det er den raekkefoelge der goer at stemplet kan naa at blive
    skrevet hen over.
    """
    ifr.stempl_genoptagelse(
        run_id=run_id,
        session_id=str(krav.get("session_id") or ""),
        task_id=str(krav.get("task_id") or ""),
        recovery_attempt=int(krav.get("recovery_attempt") or 0),
        recovery_generation=int(krav.get("recovery_generation") or 0),
    )
    ifr.mark_started(run_id=run_id, session_id=str(krav.get("session_id") or ""),
                     user_message="opgave")


def _kraev_og_fortsaet(run_id: str) -> dict | None:
    """Ét led af kaeden: tag kravet, start fortsaettelsen, lad den loebe toer."""
    krav = ifr.claim_due_recovery(owner="api")
    if krav is None:
        return None
    _fortsaet(run_id, krav)
    ifr.settle_recovering(run_id, reason="budget-opbrugt")
    return krav


# ── 1. Loftet ───────────────────────────────────────────────────────────────

def test_loftet_bider_gennem_hele_kaeden(_isoleret_lager):
    """Kaeden skal stoppe af sig selv — ikke fortsaette i det uendelige.

    Maalt i produktionen 14/10-2026: seks led i traek (17:29 -> 17:34 -> 18:01
    -> 18:03 -> 18:26 -> 18:31), hvert af dem med «generation 1, forsoeg 1».
    """
    ifr.mark_started(run_id="r1", session_id="s1", user_message="opgave")
    ifr.settle_recovering("r1", reason="budget-opbrugt")

    tagne: list[int] = []
    for nr in range(2, 8):
        krav = _kraev_og_fortsaet(f"r{nr}")
        if krav is None:
            break
        tagne.append(int(krav.get("recovery_attempt") or 0))

    assert tagne, "dispatcheren tog aldrig et krav — repliken maaler ingenting"
    assert max(tagne) >= 3, (
        f"loftet naaede aldrig 3; krav taget med forsoeg={tagne}. "
        "Stiger tallet ikke, kan `claim_due_recovery` ikke naegte til sidst."
    )
    assert _kraev_og_fortsaet("r9") is None, (
        f"loftet bed ikke — kaeden fortsatte efter {len(tagne) + 1} led "
        f"(forsøg={tagne})"
    )


def test_en_aegte_brugertur_efter_kaeden_nulstiller_den(_isoleret_lager):
    """Loftet maa ikke kunne blokere en FRISK tur i samme samtale.

    En ny tur journalfoerer sig med 0 — det er hele grunden til at tallet bor
    paa posten og ikke i et register.
    """
    ifr.mark_started(run_id="r1", session_id="s1", user_message="opgave")
    ifr.settle_recovering("r1", reason="budget-opbrugt")
    for nr in range(2, 6):
        if _kraev_og_fortsaet(f"r{nr}") is None:
            break
    ifr.mark_started(run_id="frisk", session_id="s1", user_message="nyt spoergsmaal")
    assert ifr.aktiv_kaede_nr("s1") == 0


# ── 2. Identiteten ──────────────────────────────────────────────────────────

def test_opgavens_id_overlever_hele_kaeden(_isoleret_lager):
    """Hvert led skal baere den SAMME opgave.

    Maalt 14/10-2026 i produktionen: `detached-run visible-9ae8aafd fortsaetter
    opgave visible-9f31b94c` — hvor `9f31b94c` selv var en fortsaettelse af
    `visible-ea72d19e`. Identiteten blev altsaa skiftet ud for hvert led, og
    «opgaven» var i praksis kun det forrige run.
    """
    ifr.mark_started(run_id="r1", session_id="s1", user_message="opgave")
    oprindelig = _isoleret_lager["r1"]["task_id"]
    assert oprindelig == "r1"

    ifr.settle_recovering("r1", reason="budget-opbrugt")
    krav = ifr.claim_due_recovery(owner="api")
    assert krav is not None
    _fortsaet("r2", krav)

    assert _isoleret_lager["r2"]["task_id"] == oprindelig, (
        "fortsaettelsen fik sin EGEN identitet — kaeden er brudt i to opgaver, "
        "og ingen taeller kan samle dem"
    )


def test_den_nyeste_post_i_samtalen_er_det_nyeste_led(_isoleret_lager):
    """`aktiv_kaede_nr` laeser den NYESTE post — den skal vaere leddet vi staar i.

    Ellers laeser afregningen et tal fra et led der for laengst er lukket.
    """
    ifr.mark_started(run_id="r1", session_id="s1", user_message="opgave")
    ifr.settle_recovering("r1", reason="budget-opbrugt")
    krav = ifr.claim_due_recovery(owner="api")
    assert krav is not None
    _fortsaet("r2", krav)

    assert ifr.aktiv_kaede_nr("s1") == 1, (
        "afregningen laeser et andet led end det vi staar i"
    )
