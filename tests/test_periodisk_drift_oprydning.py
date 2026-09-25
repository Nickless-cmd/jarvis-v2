"""Periodisk oprydning af `recovering`-rækker — uden at vente på en genstart.

## Hullet

`_ryd_visible_drift` var korrekt, men dens ENESTE udløser var
`reconcile_on_boot`. En `recovering`-række blev derfor liggende indtil nogen
genstartede containeren.

Målt 25/9-2026: 16 rækker stod `recovering` med `finished_at` sat. Den nyeste
var 29 sekunder gammel. Ingen proces kendte dem — `claim_due_recovery`
filtrerer `kind=='visible'`, og genoptagelsen var sket under et nyt run_id. De
blev ryddet i hånden, fordi Bjørn ikke gad vente på en genstart.

## To ting blev rettet

1. **Udløseren.** Oprydningen kaldes nu af `cluster_infra`-familiens medlem
   `visible_drift_cleanup` — samme sted som husets øvrige vedligeholdelse.

2. **Beviset.** Alders-grænsen (6 t) hviler på et FRAVÆR i journalen, og fravær
   er svagere end ejerskab. Men en `recovering`-række MED `finished_at` har et
   stærkere bevis: `finished_at` sættes kun når udfaldet persisteres. Den række
   er beviseligt slut, uanset hvor ny den er. Alder var det forkerte bevis —
   samme fejlklasse som resten af 25/9.

Den anden ændring er den der fjerner ventetiden. Den første er den der gør at
nogen overhovedet kigger.
"""
from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture(autouse=True)
def _isolate_state_store(tmp_path, monkeypatch):
    """Hold disse tests væk fra produktionens ``in_flight_runs.json``.

    Se ``test_session_boot_reconciler.py`` for den fulde begrundelse: modulniveau-
    stien bindes ved import, så uden dette læser og SKRIVER testene den rigtige
    fil.
    """
    from core.runtime import state_store

    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path / "state")


def _fresh_modules():
    importlib.reload(importlib.import_module("core.services.in_flight_runs"))
    importlib.reload(importlib.import_module("core.services.session_persistence_flag"))
    return importlib.reload(
        importlib.import_module("core.services.session_boot_reconciler"))


def _vis_row(run_id, *, age_s=1000, status="running", finished_at=""):
    """Skriv én række direkte i `visible_runs` (den isolerede DB)."""
    from core.runtime.db import connect
    from core.runtime.db_visible import ensure_visible_tables

    started = (datetime.now(UTC) - timedelta(seconds=age_s)).isoformat()
    with connect() as conn:
        ensure_visible_tables(conn)
        conn.execute(
            "INSERT OR REPLACE INTO visible_runs "
            "(run_id, lane, provider, model, status, started_at, finished_at, "
            " text_preview, error, capability_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, "primary", "ollama", "glm-5.2:cloud", status, started,
             finished_at, "arbejde", None, None),
        )


def _vis_status(run_id):
    from core.runtime.db import connect

    with connect() as conn:
        row = conn.execute(
            "SELECT status FROM visible_runs WHERE run_id=?", (run_id,)
        ).fetchone()
    return row["status"] if row else None


def _nu() -> str:
    return datetime.now(UTC).isoformat()


# ── beviset: `finished_at`, ikke alder ──────────────────────────────────────

def test_recovering_MED_finished_at_ryddes_selv_om_den_er_NY(isolated_runtime):
    """Kernen i fixen. `finished_at` sættes kun når udfaldet persisteres — så
    rækken er beviseligt slut, og alderen er det forkerte bevis.

    Den gamle regel krævede seks timers alder for ALT, så en frisk afsluttet
    række lå der indtil nogen ryddede den i hånden.
    """
    rec = _fresh_modules()
    _vis_row("visible-frisk", status="recovering", finished_at=_nu(), age_s=30)

    assert rec._ryd_visible_drift(enforced=True) == 1
    assert _vis_status("visible-frisk") == "interrupted"


def test_running_UDEN_finished_at_kraever_stadig_ALDER(isolated_runtime):
    """Alders-reglen er ikke fjernet — den gælder dér hvor beviset mangler.

    En `running`-række uden `finished_at` kan stadig være i live (kapløb ved
    opstart), og fraværet i journalen er svagere end ejerskab. Den skal vente.
    """
    rec = _fresh_modules()
    _vis_row("visible-ung", status="running", finished_at="", age_s=30)

    assert rec._ryd_visible_drift(enforced=True) == 0
    assert _vis_status("visible-ung") == "running"


def test_recovering_UDEN_finished_at_kraever_stadig_ALDER(isolated_runtime):
    """Samme grænse for `recovering` naar beviset mangler."""
    rec = _fresh_modules()
    _vis_row("visible-ung-recover", status="recovering", finished_at="", age_s=30)

    assert rec._ryd_visible_drift(enforced=True) == 0
    assert _vis_status("visible-ung-recover") == "recovering"


def test_gammel_running_ryddes_stadig(isolated_runtime):
    """Den oprindelige vej virker uændret: alderen bærer den alene."""
    rec = _fresh_modules()
    _vis_row("visible-gammel", status="running", finished_at="", age_s=20 * 3600)

    assert rec._ryd_visible_drift(enforced=True) == 1
    assert _vis_status("visible-gammel") == "interrupted"


def test_recovering_med_finished_at_LUKKES_ikke_stemples_doed(isolated_runtime):
    """Den afløste kørsel er ikke død — den blev genoptaget under et nyt run_id,
    og `stamp_visible_run_interrupted` kræver med vilje `running`."""
    import core.services.visible_runs_outcomes as vro

    rec = _fresh_modules()
    _vis_row("visible-afloest", status="recovering", finished_at=_nu(), age_s=30)

    with __import__("unittest.mock").mock.patch.object(
            vro, "stamp_visible_run_superseded", wraps=vro.stamp_visible_run_superseded
    ) as afloest:
        assert rec._ryd_visible_drift(enforced=True) == 1
    assert afloest.call_count == 1


# ── udløseren: den periodiske indgang ───────────────────────────────────────

def test_periodisk_rydning_skriver_naar_flaget_er_ON(isolated_runtime, monkeypatch):
    rec = _fresh_modules()
    import core.services.session_persistence_flag as spf

    monkeypatch.setattr(spf, "session_persistence_enabled", lambda: True)
    _vis_row("visible-frisk", status="recovering", finished_at=_nu(), age_s=30)

    ud = rec.ryd_visible_drift_periodisk()

    assert ud["status"] == "ok"
    assert ud["ryddet"] == 1
    assert ud["enforced"] is True
    assert _vis_status("visible-frisk") == "interrupted"


def test_periodisk_rydning_taeller_men_skriver_IKKE_naar_flaget_er_OFF(
        isolated_runtime, monkeypatch):
    """Samme kill-switch som opstarts-vejen. Skygge er husets fremgangsmåde for
    en gate der skærer."""
    rec = _fresh_modules()
    import core.services.session_persistence_flag as spf

    monkeypatch.setattr(spf, "session_persistence_enabled", lambda: False)
    _vis_row("visible-frisk", status="recovering", finished_at=_nu(), age_s=30)

    ud = rec.ryd_visible_drift_periodisk()

    assert ud["ryddet"] == 1            # den SER den
    assert ud["enforced"] is False
    assert _vis_status("visible-frisk") == "recovering"   # men skriver intet


def test_periodisk_rydning_kaster_ALDRIG(isolated_runtime, monkeypatch):
    """Den kaldes fra en familie-tick. En fejl må ikke vælte tikket — men den
    skal meldes, ikke sluges."""
    rec = _fresh_modules()
    monkeypatch.setattr(
        rec, "_ryd_visible_drift",
        lambda enforced: (_ for _ in ()).throw(RuntimeError("db nede")))

    ud = rec.ryd_visible_drift_periodisk()

    assert ud["status"] == "error"
    assert "db nede" in ud["error"]


# ── medlemskabet: nogen skal faktisk kalde den ──────────────────────────────

def test_medlemmet_er_registreret_i_infra_familien():
    """En funktion ingen kalder er PRÆCIS den fejl fixen retter. Uden denne
    række er den periodiske oprydning død kode."""
    from core.services import cluster_daemon_families as cdf

    navne = [navn for navn, _ in cdf._INFRA_UNCONDITIONAL]
    assert "visible_drift_cleanup" in navne


def test_medlemmet_throttler_paa_30_minutter(monkeypatch):
    from core.services import cluster_daemon_families as cdf

    noegler: list[tuple[str, float]] = []
    monkeypatch.setattr(
        cdf, "_infra_throttle_ready",
        lambda key, minutes: (noegler.append((key, minutes)), False)[1])

    ud = cdf._infra_visible_drift_live({})

    assert ud["status"] == "throttled"
    assert noegler == [("visible_drift_cleanup", 30)]


def test_medlemmet_KALDER_den_periodiske_rydning(monkeypatch):
    from core.services import cluster_daemon_families as cdf

    monkeypatch.setattr(cdf, "_infra_throttle_ready", lambda key, minutes: True)

    import core.services.session_boot_reconciler as sbr

    kaldt: list[int] = []
    monkeypatch.setattr(
        sbr, "ryd_visible_drift_periodisk",
        lambda: (kaldt.append(1), {"status": "ok", "ryddet": 3})[1])

    ud = cdf._infra_visible_drift_live({})

    assert kaldt == [1], "medlemmet kaldte ikke oprydningen"
    assert ud["ryddet"] == 3


# ── kilde-vagten: fixturen i den anden fil svarer det samme uanset SQL ──────

def test_sql_kraever_IKKE_alder_for_recovering_med_finished_at():
    """`test_boot_reconciler_visible_drift.py` bruger en fixture der returnerer
    de samme rækker uanset hvilken SQL der stilles — så kun en vagt på kilden
    kan se at `finished_at`-grenen faktisk findes i forespørgslen."""
    import inspect

    from core.services import session_boot_reconciler as sbr

    kilde = inspect.getsource(sbr._ryd_visible_drift)
    assert "finished_at IS NOT NULL" in kilde, \
        "finished_at-grenen er væk — en frisk afsluttet række venter igen på en genstart"
