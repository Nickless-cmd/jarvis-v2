"""Investigation 7: the blend instrument must reproduce the preserved runs.

The experiment's whole value rests on two properties that are easy to lose
silently:

1. At blend 0 the mechanism must reproduce the preserved Investigation 5 and 6
   figures exactly. If it does not, the instrument has diverged from the
   mechanism it claims to reuse and no other row may be read.
2. The gap must be checked for monotonicity before condition 1 is allowed to
   carry a verdict. Measured 2026-11-25: the gap turns at blend 0.7 on both
   sources, so a fall in effective experts at high blend is the instrument's
   own shape.

The first version of the control compared against the three-decimal figure
1.886 with a 1e-6 tolerance and reported an instrument fault for a 0.0003
difference that was rounding in the report. These tests pin the full-precision
comparison so that cannot recur.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIELD_THEORY = PROJECT_ROOT / "field_theory"
sys.path.insert(0, str(FIELD_THEORY / "src"))

SILSO = (
    FIELD_THEORY
    / "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
)
NOAA = FIELD_THEORY / "artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv"
PRESERVED_006 = (
    FIELD_THEORY / "artifacts/exp_006_order/noaa_20261030_v2/exp006_results.json"
)


def _preserved_co2_long_continued() -> dict[str, float]:
    payload = json.loads(PRESERVED_006.read_text(encoding="utf-8"))
    for summary in payload["mechanism_summaries"]:
        if summary["mechanism"] == "long_continuity_continued":
            return {
                "effective_experts": float(summary["mean_effective_experts"]),
                "mae": float(summary["mae"]),
            }
    raise AssertionError("preserved run has no long_continuity_continued summary")


def test_kontrollen_bruger_fuld_praecision_fra_den_bevarede_koersel() -> None:
    """The control's expected values must match the preserved file, not a report."""
    from feltteori_research.experiment_007_gradient import CONTROL_EXPECTED

    preserved = _preserved_co2_long_continued()
    assert CONTROL_EXPECTED["co2"]["effective_experts"] == pytest.approx(
        preserved["effective_experts"], abs=1e-12
    )
    assert CONTROL_EXPECTED["co2"]["mae"] == pytest.approx(preserved["mae"], abs=1e-12)


def test_kontrollen_ville_have_fejlet_paa_det_afrundede_tal() -> None:
    """The rounded figure differs from the preserved one by more than 1e-6.

    This is the fault that fired first: 1.886 against 1.8856506370006225 is a
    0.0003 difference, which a 1e-6 tolerance reads as divergence.
    """
    preserved = _preserved_co2_long_continued()
    assert abs(1.886 - preserved["effective_experts"]) > 1e-6


def test_koerslen_reproducerer_de_bevarede_tal(tmp_path: Path) -> None:
    """End-to-end: blend 0 must reproduce both preserved runs."""
    from feltteori_research.experiment_007_gradient import run_investigation

    results = run_investigation(SILSO, NOAA, tmp_path / "run")
    assert results["control"]["passed"] is True
    for check in results["control"]["checks"]:
        assert check["effective_experts_ok"] is True, check
        assert check["mae_ok"] is True, check


def test_gappet_er_ikke_monotont_og_dommen_er_derfor_ingen_falsifikation(
    tmp_path: Path,
) -> None:
    """Condition 1 may not carry a verdict when the gap itself turns."""
    from feltteori_research.experiment_007_gradient import run_investigation

    results = run_investigation(SILSO, NOAA, tmp_path / "run")
    validity = results["condition_4_gap_validity"]
    assert validity["valid"] is False
    for source in ("sunspots", "co2"):
        assert validity["per_source"][source]["monotone"] is False
        assert validity["per_source"][source]["turns"], source
    assert results["conditions_fired"]["4_gap_not_monotone"] is True
    assert results["verdict"] == "inconclusive_instrument_cannot_reach_question"


def test_uopnaaelig_betingelse_2_baerer_ingen_dom(tmp_path: Path) -> None:
    """No matched-gap pair exists, so condition 2 must not count as a finding."""
    from feltteori_research.experiment_007_gradient import run_investigation

    results = run_investigation(SILSO, NOAA, tmp_path / "run")
    matched = results["condition_2_matched_gap"]
    assert matched["matched_pairs"] == []
    assert matched["reachable"] is False
    assert results["conditions_fired"]["2_sources_disagree_at_matched_gap"] is False
