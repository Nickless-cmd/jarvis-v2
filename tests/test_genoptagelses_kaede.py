"""Genoptagelses-kaeden skal kunne taelles — og dermed stoppe.

Bjoern 30/9-2026: «den her bliver ved at fyre og starte alle runs». Beskeden var
«En tvungen slutrunde manglede bevis for at opgaven var faerdig. Jarvis
fortsaetter automatisk fra sit checkpoint.»

Der var TO lofter, og begge var ude af drift:

* `visible_terminal_policy` sammenligner `recovery_attempt` med
  `recovery_limit`. Tallet kom fra `auto_continuation.kaede_nr`, hvis register
  kun havde én skriver — `saet_kaede` — og den havde NUL kaldere. Opslaget gav
  derfor altid 0, og `0 >= 3` er aldrig sandt.
* `claim_due_recovery` taeller rigtigt op, men paa POSTEN. Hver genoptagelse
  fik et nyt run_id og dermed en ny post paa 0, fordi `start_visible_run` ikke
  tager recovery-parametre og journalfoerte forfra.

Maalt samme dag i én samtale: ti genoptagelser, ni med `recovery_attempt=1` —
hvert led var sit eget foerste forsoeg.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import auto_continuation as ac
from core.services import in_flight_runs as ifr
from core.services.visible_terminal_policy import (
    TerminalState,
    TerminalEvidence,
    classify_terminal,
)


@pytest.fixture(autouse=True)
def _isoleret_lager(monkeypatch):
    lager: dict = {}
    monkeypatch.setattr(ifr, "_load", lambda: lager)
    monkeypatch.setattr(ifr, "_save", lambda d: lager.update(d))
    return lager


def _start(rid, sid, **kw):
    ifr.mark_started(run_id=rid, session_id=sid, user_message="hej", **kw)


# ── Kaeden overlever journalfoeringen ────────────────────────────────────────

def test_stemplet_overlever_at_koerslen_journalfoerer_sig(_isoleret_lager):
    """Kernen. `detached_run` stempler forsoeg 2; `start_visible_run` kalder
    bagefter `mark_started` UDEN recovery-parametre. Uden arven skrev den 0 hen
    over stemplet, og kaeden begyndte forfra ved hvert eneste led."""
    ifr.stempl_genoptagelse(run_id="r2", session_id="s1", task_id="opgave",
                            recovery_attempt=2, recovery_generation=2)
    _start("r2", "s1")
    assert _isoleret_lager["r2"]["recovery_attempt"] == 2
    assert _isoleret_lager["r2"]["recovery_generation"] == 2


def test_en_aegte_brugertur_nulstiller_kaeden(_isoleret_lager):
    """Arven maa ikke blive en envejsdoer. En ny tur har intet stempel, og saa
    skal taelleren staa paa nul — ellers kunne et gammelt loft blokere en
    fortsaettelse timer senere af en grund ingen kan se."""
    _start("r1", "s1")
    assert _isoleret_lager["r1"]["recovery_attempt"] == 0


def test_stempel_paa_nul_skriver_ingenting(_isoleret_lager):
    """Kun en genoptagelse stempler. Et stempel paa 0 er ikke en genoptagelse,
    og maa ikke efterlade en halv post der ligner et levende run."""
    ifr.stempl_genoptagelse(run_id="r9", session_id="s1", recovery_attempt=0)
    assert "r9" not in _isoleret_lager


# ── Aflaesningen ────────────────────────────────────────────────────────────

def test_aktiv_kaede_nr_laeser_den_NYESTE_post(_isoleret_lager):
    """Nyeste, ikke stoerste. En gammel post der aldrig blev ryddet maa ikke
    kunne forgifte en frisk samtale."""
    gammel = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    _isoleret_lager["gammel"] = {
        "run_id": "gammel", "session_id": "s1", "kind": "visible",
        "status": "completed", "started_at": gammel, "recovery_attempt": 3,
    }
    _start("ny", "s1")
    assert ifr.aktiv_kaede_nr("s1") == 0


def test_aktiv_kaede_nr_ser_kun_sin_egen_samtale(_isoleret_lager):
    ifr.stempl_genoptagelse(run_id="a", session_id="s1", recovery_attempt=2)
    _start("a", "s1")
    _start("b", "s2")
    assert ifr.aktiv_kaede_nr("s1") == 2
    assert ifr.aktiv_kaede_nr("s2") == 0
    assert ifr.aktiv_kaede_nr("") == 0


def test_kaede_nr_spoerger_journalen(_isoleret_lager):
    """`auto_continuation.kaede_nr` returnerede FOER altid 0, fordi dens
    register aldrig blev skrevet. Nu er journalen kilden."""
    ifr.stempl_genoptagelse(run_id="r3", session_id="s1", recovery_attempt=3)
    _start("r3", "s1")
    assert ac.kaede_nr("s1") == 3


# ── Loftet fyrer faktisk ────────────────────────────────────────────────────

@pytest.mark.parametrize("forsoeg,forventet", [
    (0, TerminalState.RECOVERING),
    (2, TerminalState.RECOVERING),
    (3, TerminalState.FAILED_TERMINAL),
    (4, TerminalState.FAILED_TERMINAL),
])
def test_tvungen_slutrunde_stopper_ved_loftet(forsoeg, forventet):
    """Selve fejlen Bjoern saa: `forced_finalize` + manglende faerdighedsbevis.
    Med taelleren laast paa 0 var den foerste raekke det ENESTE udfald, uanset
    hvor mange gange kaeden havde koert."""
    dom = classify_terminal(TerminalEvidence(
        exit_reason="completed",
        forced_finalize=True,
        incompletion_evidence=True,
        recovery_attempt=forsoeg,
        recovery_limit=3,
    ))
    assert dom.state is forventet
    assert dom.reason == "forced-finalize-unverified"
    assert dom.should_continue is (forventet is TerminalState.RECOVERING)


# ── Rydningen ───────────────────────────────────────────────────────────────

def test_ny_tur_rydder_samtalens_afsluttede_poster(_isoleret_lager):
    """Docstringen har altid lovet det; koden gjorde det ikke. Maalt 30/9-2026:
    174 poster, 149 af dem paa én samtale, i en fil paa 287 kB som `_mutate`
    skriver HELT om under laasen ved hvert fremskridts-stempel."""
    # Ophobningen som den saa ud paa CT105: afsluttede poster der blev liggende.
    nu = datetime.now(UTC).isoformat()
    for i in range(5):
        _isoleret_lager[f"gl{i}"] = {
            "run_id": f"gl{i}", "session_id": "s1", "kind": "visible",
            "status": "completed", "started_at": nu, "settled_at": nu,
            "notice_pending": False,
        }
    assert len(_isoleret_lager) == 5
    _start("ny", "s1")
    assert set(_isoleret_lager) == {"ny"}


def test_rydningen_roerer_ikke_andre_samtaler(_isoleret_lager):
    _start("a", "s1")
    ifr.settle_terminal("a", status="completed", reason="completed")
    _start("b", "s2")
    assert "a" in _isoleret_lager


def test_et_ULAEST_varsel_overlever_rydningen(_isoleret_lager):
    """Den eneste besked om at en opgave blev OPGIVET. `recovery_snapshot`
    henter den netop paa `failed_terminal` + `notice_pending`, saa en rydning
    der tog den ville lade spoergsmaalet forsvinde i tavshed."""
    _start("opgivet", "s1")
    _isoleret_lager["opgivet"].update(status="failed_terminal", notice_pending=True)
    _start("ny", "s1")
    assert "opgivet" in _isoleret_lager

    # Og naar varslet ER hentet, maa posten gerne gaa.
    _isoleret_lager["opgivet"]["notice_pending"] = False
    _start("nyere", "s1")
    assert "opgivet" not in _isoleret_lager


def test_et_koerende_run_ryddes_ikke(_isoleret_lager):
    """Kun AFSLUTTEDE poster. En `recovering` post venter paa at blive taget
    op, og en `running` kan vaere et parallelt run."""
    _start("lever", "s1")
    _isoleret_lager["lever"]["status"] = "recovering"
    _start("ny", "s1")
    assert "lever" in _isoleret_lager
