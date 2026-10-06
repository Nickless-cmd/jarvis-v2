"""Kan man se udefra om fejeren kørte? Indtil 6/10-2026: nej.

## Hvad der skete

`visible-bd1727a4` stod `running` med nul `costs`-opslag. Den var
fejeberettiget fra 19:06 og stod der stadig 19:24 — gennem omkring ni
familie-tick — mens genstarts-vagten blokerede hvert deploy.

Tre ting gjorde spørgsmålet ubesvarligt, og de rettes hver for sig her:

1. **Ledgeren klippede efter tre nøgler.** `record_daemon_tick` byggede
   resuméet af `list(result.items())[:3]`, og familiens nøgle-rækkefølge er
   `family, shadow, gate_calls, fired, members_ran, …`. `members_ran` — det
   eneste felt der siger hvilke medlemmer der kørte — lå efter snittet.
   Ledgeren stod derfor på «family: cluster_infra, shadow: False,
   gate_calls: 1», hvad der end var sket.

2. **Fejeren loggede intet ved succes.** Tavshed kan ikke skelne «kørte og
   fandt nul» fra «blev aldrig kaldt». Det er to forskellige fejl.

3. **Medlemmet self-throttlede 30 min** — oven i reglens egen 30-minutters
   aldersgrænse. To uafhængige ure gav et vindue på 30 til 60 minutter, og
   fasen var tilfældig, fordi `_INFRA_THROTTLE` er en in-process dict som hver
   genstart nulstiller.
"""
from __future__ import annotations

import logging

import pytest


# ── 1. ledger-resuméet ──────────────────────────────────────────────────────

def _familie_resultat() -> dict:
    """Nøjagtig den form og rækkefølge familierne bygger (cluster_daemon_families).

    Rækkefølgen ER defekten. Skrev testen sine egne nøgler i en anden orden,
    målte den sin egen opdigtede form i stedet for produktionens.
    """
    return {
        "family": "cluster_infra",
        "shadow": False,
        "gate_calls": 1,
        "fired": False,
        "members_ran": ["cache_maintenance", "visible_drift_cleanup"],
        "members_skipped": [],
        "member_errors": {},
        "outputs": {"visible_drift_cleanup": {"status": "ok", "ryddet": 1}},
    }


def test_members_ran_naar_frem_i_resumeet():
    """Kernen. Før ændringen stoppede resuméet ved `gate_calls`."""
    from core.services.daemon_manager import _tick_resume

    resume = _tick_resume(_familie_resultat())
    assert "members_ran" in resume
    assert "visible_drift_cleanup" in resume


def test_de_svarende_felter_staar_FOERST():
    """Et tegn-budget hjælper ikke hvis `family` og `shadow` spiser det først."""
    from core.services.daemon_manager import _tick_resume

    resume = _tick_resume(_familie_resultat())
    assert resume.index("members_ran") < resume.index("family"), resume


def test_en_afkortning_navngiver_sig_selv():
    """En grænse der klipper i tavshed er værre end ingen — det var hele fejlen."""
    from core.services.daemon_manager import _tick_resume

    stort = {f"felt_{i}": "x" * 60 for i in range(20)}
    resume = _tick_resume(stort)

    assert "felter" in resume, f"afkortningen var tavs: {resume!r}"
    assert len(resume) < 600


def test_et_resultat_med_egen_summary_vinder():
    from core.services.daemon_manager import _tick_resume

    assert _tick_resume({"summary": "lukkede 1 raekke", "family": "x"}) == "lukkede 1 raekke"


def test_et_tomt_resultat_vaelter_ikke():
    from core.services.daemon_manager import _tick_resume

    assert _tick_resume({}) == ""


# ── 2. fejeren siger at den kørte ───────────────────────────────────────────

@pytest.fixture
def _fejer(monkeypatch):
    """Bind reglen og kill-switchen, så testen måler LOGGEN og ikke SQL'en."""
    import core.services.session_boot_reconciler as R

    monkeypatch.setattr(
        "core.services.session_persistence_flag.session_persistence_enabled",
        lambda: True)
    return R


def test_loggen_siger_hvor_mange_der_blev_lukket(_fejer, monkeypatch, caplog):
    monkeypatch.setattr(_fejer, "_ryd_visible_drift", lambda enforced: 3)

    with caplog.at_level(logging.INFO, logger="core.services.session_boot_reconciler"):
        svar = _fejer.ryd_visible_drift_periodisk()

    assert svar == {"status": "ok", "ryddet": 3, "enforced": True}
    assert any("lukkede 3 raekke" in r.getMessage() for r in caplog.records), \
        [r.getMessage() for r in caplog.records]


def test_nul_raekker_logger_IKKE(_fejer, monkeypatch, caplog):
    """Første udgave loggede nul-tilfældet på DEBUG. Målt 6/10-2026 havde
    `jarvis-runtime` 0 DEBUG-linjer i journalen over 25 minutter mens
    `jarvis-api` havde 36 — og fejeren kører i RUNTIME. Linjen ville altså
    foregive et spor der ikke findes. Nul-tilfældet bæres af ledgeren i stedet
    (se `test_nul_tilfaeldet_kan_slaas_op_i_ledgeren`).
    """
    monkeypatch.setattr(_fejer, "_ryd_visible_drift", lambda enforced: 0)

    with caplog.at_level(logging.DEBUG, logger="core.services.session_boot_reconciler"):
        svar = _fejer.ryd_visible_drift_periodisk()

    assert svar["ryddet"] == 0
    assert caplog.records == [], [r.getMessage() for r in caplog.records]


def test_nul_tilfaeldet_kan_slaas_op_i_ledgeren():
    """DET er svaret på «kørte medlemmet?» — durabelt, uden en linje per tick."""
    from core.services.daemon_manager import _tick_resume

    resultat = _familie_resultat()
    resultat["outputs"]["visible_drift_cleanup"] = {"status": "ok", "ryddet": 0}

    resume = _tick_resume(resultat)
    assert "visible_drift_cleanup" in resume, resume


def test_en_fejl_i_reglen_vaelter_ikke_familie_tikket(_fejer, monkeypatch):
    def _sprael(enforced):
        raise RuntimeError("DB laast")

    monkeypatch.setattr(_fejer, "_ryd_visible_drift", _sprael)
    svar = _fejer.ryd_visible_drift_periodisk()
    assert svar["status"] == "error" and "DB laast" in svar["error"]


# ── 3. throttlen er væk ─────────────────────────────────────────────────────

def test_medlemmet_throttler_IKKE_laengere(monkeypatch):
    """To kald i træk skal BEGGE nå fejeren.

    Før: andet kald returnerede `{"status": "throttled", "cadence_minutes": 30}`,
    og med reglens egen 30-minutters aldersgrænse oveni blev vinduet 30-60 min.
    """
    import core.services.cluster_daemon_families as F

    kald: list[int] = []
    monkeypatch.setattr(
        "core.services.session_boot_reconciler.ryd_visible_drift_periodisk",
        lambda: (kald.append(1), {"status": "ok", "ryddet": 0, "enforced": True})[1])

    foerste = F._infra_visible_drift_live({})
    anden = F._infra_visible_drift_live({})

    assert len(kald) == 2, "andet kald naaede ikke fejeren — throttlen er tilbage"
    assert foerste["status"] == "ok" and anden["status"] == "ok"
    assert "throttled" not in (foerste.get("status"), anden.get("status"))


def test_de_OEVRIGE_medlemmer_throttler_stadig(monkeypatch):
    """Vagt mod en for bred rettelse. `mail_checker` kalder en LLM per mail —
    den må ikke komme til at køre hvert 2. minut."""
    import core.services.cluster_daemon_families as F

    monkeypatch.setattr(F, "_INFRA_THROTTLE", {}, raising=False)
    assert F._infra_throttle_ready("mail_checker", 15) is True
    assert F._infra_throttle_ready("mail_checker", 15) is False


def test_throttle_hjaelperen_har_stadig_sine_andre_brugere():
    """Kilde-vagt: fjernede nogen hjælperen som «ubrugt», ville seks medlemmer
    miste deres kadence i tavshed."""
    import inspect

    import core.services.cluster_daemon_families as F

    kilde = inspect.getsource(F)
    assert kilde.count("_infra_throttle_ready(") >= 6
    assert '_infra_throttle_ready("visible_drift_cleanup"' not in kilde
