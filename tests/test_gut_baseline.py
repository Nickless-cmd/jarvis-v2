"""Test: maven måles mod en KONSTANT baseline, ikke kun mod sin egen hit-rate.

Hvorfor (12/11-2026): fladen viste `Calibration: 0.99 (4489/4523 correct)` og blev læst
som «maven har ret i 99% af tilfældene». Målt mod de faktiske events var maven 92,77%
korrekt, mens en konstant «proceed» ville være 99,71% — altså 6,94 procentpoint
DÅRLIGHERE, fordi runs lykkes 99,7% af tiden og enhver advarsel derfor næsten altid er
forkert.

Reglen testene værner om: en hit-rate uden baseline kan ikke skelne «mekanismen er
dygtig» fra «systemet fejler næsten aldrig». Er mekanismen ikke bedre end konstanten,
skal fladen sige det — ikke skjule det bag et højt tal.
"""
from __future__ import annotations

import json

import pytest

from core.services import gut_engine as ge


@pytest.fixture(autouse=True)
def _nulstil_cache():
    """_BASELINE_CACHE er modul-global — uden nulstilling lækker state mellem tests."""
    ge._BASELINE_CACHE["at"] = 0.0
    ge._BASELINE_CACHE["value"] = None
    yield
    ge._BASELINE_CACHE["at"] = 0.0
    ge._BASELINE_CACHE["value"] = None


def _events(par: list[tuple[str, str]]):
    """Byg fake event-rækker som dem `_observed_baseline` læser (payload_json,)."""
    return [(json.dumps({"hunch": h, "actual": a}),) for h, a in par]


def _patch_db(monkeypatch, par: list[tuple[str, str]]):
    rows = _events(par)

    class _Conn:
        def execute(self, *_a, **_k):
            return self

        def fetchall(self):
            return rows

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr("core.runtime.db.connect", lambda: _Conn(), raising=False)


def test_altid_proceed_paa_altid_succes_giver_nul_udbytte(monkeypatch):
    """Maven siger «proceed» og alt lykkes: korrekt, men udbyttet over baseline er 0."""
    _patch_db(monkeypatch, [("proceed", "completed")] * 10)
    b = ge._observed_baseline()
    assert b is not None
    assert b["n_observed"] == 10
    assert b["maven_pct"] == 100.0
    assert b["baseline_pct"] == 100.0
    assert b["skill_pp"] == 0.0


def test_advarsel_om_succes_er_negativt_udbytte(monkeypatch):
    """DEN MÅLTE FEJLFORM: maven advarer, men runnet lykkes alligevel.

    Baseline (altid proceed) rammer alt; maven taber hver advarsel. Det er præcis
    situationen i produktion den 12/11-2026 (25 af 26 caution-runs lykkedes).
    """
    par = [("proceed", "completed")] * 8 + [("caution", "completed")] * 2
    _patch_db(monkeypatch, par)
    b = ge._observed_baseline()
    assert b is not None
    assert b["maven_pct"] == 80.0        # 8 korrekte af 10
    assert b["baseline_pct"] == 100.0    # alt lykkedes
    assert b["skill_pp"] == -20.0
    assert b["skill_pp"] < 0


def test_advarsel_om_fejl_er_positivt_udbytte(monkeypatch):
    """Bevis for at målingen KAN give overskud: en advarsel der rammer er en gevinst."""
    par = [("proceed", "completed")] * 5 + [("caution", "error")] * 5
    _patch_db(monkeypatch, par)
    b = ge._observed_baseline()
    assert b is not None
    assert b["maven_pct"] == 100.0
    assert b["baseline_pct"] == 50.0     # konstant proceed rammer kun halvdelen
    assert b["skill_pp"] == 50.0
    assert b["skill_pp"] > 0


def test_ukendt_hunch_tælles_ikke(monkeypatch):
    """Kun proceed/caution har en defineret forudsigelse — andre må ikke fortynde tallet."""
    _patch_db(monkeypatch, [("proceed", "completed"), ("tom", "completed")])
    b = ge._observed_baseline()
    assert b is not None
    assert b["n_observed"] == 1


def test_beskadiget_payload_springes_over(monkeypatch):
    """Én ødelagt række må ikke skjule de andre eller kaste."""
    class _Conn:
        def execute(self, *_a, **_k):
            return self

        def fetchall(self):
            return [("{ikke json",), (json.dumps({"hunch": "proceed", "actual": "completed"}),)]

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr("core.runtime.db.connect", lambda: _Conn(), raising=False)
    b = ge._observed_baseline()
    assert b is not None
    assert b["n_observed"] == 1


def test_uden_db_giver_none_ikke_crash(monkeypatch):
    """Uden DB skal fladen stadig kunne vises — men sige at baseline er utilgængelig."""
    def _boom():
        raise RuntimeError("db nede")

    monkeypatch.setattr("core.runtime.db.connect", _boom, raising=False)
    assert ge._observed_baseline() is None


def test_summary_viser_baseline_og_dommen(monkeypatch):
    """Summary'en skal bære dommen — et højt hit-tal alene må ikke kunne læses som dygtighed."""
    par = [("proceed", "completed")] * 8 + [("caution", "completed")] * 2
    _patch_db(monkeypatch, par)
    monkeypatch.setattr(
        ge, "get_cognitive_gut_state",
        lambda: {"total_predictions": 10, "calibrated_hits": 9,
                 "calibration_score": 0.9, "last_hunch": "proceed → completed (✓)"},
    )
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["baseline"] is not None
    assert s["baseline"]["skill_pp"] == -20.0
    assert "DAARLIGERE" in s["summary"]
    assert "baseline" in s["summary"]


def test_summary_siger_utilgaengelig_uden_baseline(monkeypatch):
    """Mangler baseline, skal fladen advare om at hit-raten ikke kan læses som dygtighed."""
    monkeypatch.setattr(ge, "_observed_baseline", lambda: None)
    monkeypatch.setattr(
        ge, "get_cognitive_gut_state",
        lambda: {"total_predictions": 10, "calibrated_hits": 9,
                 "calibration_score": 0.9, "last_hunch": "proceed → completed (✓)"},
    )
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["baseline"] is None
    assert "IKKE" in s["summary"]
