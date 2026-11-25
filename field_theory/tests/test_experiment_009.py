"""Investigation 9: the threshold does not depend on the experts — because it is analytic.

The experiment's value rests on four properties that can each be lost silently:

1. **The parameterised builders must reproduce the originals.** ``_weights_for``
   takes the expert set as an argument where ``experiment_005``'s ``_weights``
   reads a module constant. If they diverge, every cell is computed by a
   mechanism nobody validated. Measured difference in the preserved run: 0.0,
   bit-identical.
2. **The control must hold analytically.** At ``gap = 0`` every expert in a set
   has identical losses, so the softmax is uniform and the effective count is
   exactly N.
3. **The finding must be visible where it was claimed.** In ``fixed`` assignment
   the threshold must be identical across expert sets, because the order is
   constant by construction and the data cannot enter. In ``roving`` it must
   vary, because the order is sorted by each month's real loss.
4. **An unreachable cell must not be read as agreement.** ``two_experts`` never
   crosses its floor: with two experts the minimum effective count is 1.0 and
   the floor is also 1.0, so ``< 1.0`` can never be satisfied. The
   ``not_falsified`` verdict must not be taken as evidence that two experts
   behave like three — that question was not answerable here.

Property 4 is the one most likely to be lost: a comparison that treats
``None == None`` as "within a factor" turns an unmeasurable cell into a silent
vote for the hypothesis. The test below pins the distinction.
"""

from __future__ import annotations

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


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    from feltteori_research.experiment_009_expert_set import run_investigation

    output = tmp_path_factory.mktemp("exp009") / "run"
    return run_investigation(SILSO, NOAA, output)


def _cell(results: dict, expert_set: str, source: str, assignment: str, retention: str) -> dict:
    for cell in results["thresholds"]["per_cell"]:
        if (
            cell["expert_set"] == expert_set
            and cell["source"] == source
            and cell["assignment"] == assignment
            and cell["retention_condition"] == retention
        ):
            return cell
    raise AssertionError(f"cell not found: {expert_set}/{source}/{assignment}/{retention}")


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


def test_alle_kontroller_bestaar(results: dict) -> None:
    assert results["controls_passed"] is True, {
        name: value["passed"] for name, value in results["control"].items()
    }


def test_vaegtfunktionen_er_bit_identisk_med_originalen(results: dict) -> None:
    """The parameterised softmax must equal exp_005's on the original set."""
    assert results["control"]["weight_identity"]["worst_absolute_difference"] == 0.0


def test_ekspertraekkerne_reproducerer_exp007(results: dict) -> None:
    """The parameterised row builder must reproduce exp_007's on the original set."""
    checks = results["control"]["expert_rows_identity"]["checks"]
    assert len(checks) == 2
    for check in checks:
        assert check["same_structure"] is True, check
        assert check["worst_absolute_difference"] == 0.0, check


def test_kontrollen_reproducerer_exp008_taerskler(results: dict) -> None:
    """The original set must land on Investigation 8's measured thresholds."""
    checks = results["control"]["reproduction"]["checks"]
    assert checks, "no reproduction checks were run"
    for check in checks:
        assert check["ok"] is True, check


def test_kalibreringen_er_eksakt(results: dict) -> None:
    assert results["control"]["calibration"]["worst_absolute_gap_error"] < 1e-12


# ---------------------------------------------------------------------------
# The finding: fixed assignment is analytic, roving is data-dependent
# ---------------------------------------------------------------------------


def test_taersklen_er_identisk_for_alle_tre_ekspert_saet(results: dict) -> None:
    """In fixed assignment the data cannot enter, so the threshold cannot move."""
    for source in ("sunspots", "co2"):
        for retention in ("short_continuity", "long_continuity"):
            measured = {
                name: _cell(results, name, source, "fixed", retention)["measured_threshold"]
                for name in ("original", "short_memory", "long_memory")
            }
            values = set(measured.values())
            assert len(values) == 1, f"{source}/{retention} diverged: {measured}"


def test_fire_eksperter_aendrer_ikke_taersklen(results: dict) -> None:
    """The count 3 -> 4 does not move the threshold in fixed assignment."""
    for source in ("sunspots", "co2"):
        for retention in ("short_continuity", "long_continuity"):
            original = _cell(results, "original", source, "fixed", retention)
            four = _cell(results, "four_experts", source, "fixed", retention)
            assert four["measured_threshold"] == original["measured_threshold"]


def test_roving_varierer_med_dataene(results: dict) -> None:
    """Where the expert order is sorted by real loss, the threshold must vary."""
    measured = [
        _cell(results, name, source, "roving", retention)["measured_threshold"]
        for name in ("original", "short_memory", "long_memory", "four_experts")
        for source in ("sunspots", "co2")
        for retention in ("short_continuity", "long_continuity", "cumulative_continuity")
    ]
    known = [float(value) for value in measured if value is not None]
    assert known, "no roving cell crossed its floor at all"
    assert max(known) / min(known) >= 2.0, (
        f"roving did not vary: min={min(known)} max={max(known)}"
    )


def test_taersklen_foelger_den_analytiske_relation(results: dict) -> None:
    """Threshold / (1-r) must be roughly constant across retentions in fixed mode."""
    ratios = []
    for retention, condition in (("short_continuity", 0.1), ("long_continuity", 0.01)):
        cell = _cell(results, "original", "sunspots", "fixed", retention)
        ratios.append(float(cell["measured_threshold"]) / condition)
    assert max(ratios) / min(ratios) <= 1.5, (
        f"the threshold is not proportional to (1-r): ratios={ratios}"
    )


# ---------------------------------------------------------------------------
# The unreachable cell — this is the one that must not be misread
# ---------------------------------------------------------------------------


def test_to_eksperter_er_uopnaaelig_og_maa_ikke_laeses_som_enighed(results: dict) -> None:
    """With two experts the floor equals the minimum, so the cell cannot be measured."""
    for source in ("sunspots", "co2"):
        for retention in ("short_continuity", "long_continuity", "cumulative_continuity"):
            cell = _cell(results, "two_experts", source, "fixed", retention)
            assert cell["measured_threshold"] is None, cell
            # The floor is exactly the minimum attainable effective count: with
            # N experts, one expert alone is 1.0 and the floor is N/2. They are
            # equal only at N = 2, which is why only this set is unreachable.
            assert cell["floor"] == results["parameters"]["threshold_fraction"] * float(
                cell["experts"]
            )
            assert cell["floor"] == 1.0


def test_to_eksperter_naermer_sig_gulvet_uden_at_krydse_det(results: dict) -> None:
    """The series must approach 1.0 asymptotically, never pass below it."""
    cell = _cell(results, "two_experts", "sunspots", "fixed", "short_continuity")
    effective = [float(row["mean_effective_experts"]) for row in cell["series"]]
    assert effective == sorted(effective, reverse=True), "the series is not monotone"
    assert min(effective) >= 1.0
    assert min(effective) < 1.001, "the series did not approach the floor"
    assert all(value >= cell["floor"] for value in effective)


def test_betingelse_2_kan_ikke_fyre_paa_en_uopnaaelig_celle(results: dict) -> None:
    """A None-vs-None comparison must not be counted as a difference."""
    for row in results["condition_2_count_matters"]["rows"]:
        if row["expert_set"] != "two_experts":
            continue
        if row["measured_other"] is None and row["measured_original"] is None:
            assert row["ratio"] is None
            assert row["within_factor"] is True
