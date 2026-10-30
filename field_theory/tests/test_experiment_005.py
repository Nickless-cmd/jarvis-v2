from __future__ import annotations

from pathlib import Path

import pytest

from feltteori_research.experiment_005_audit import audit_investigation
from feltteori_research.experiment_005_learning import (
    EXPERTS,
    parse_silso_monthly,
    run_investigation,
)


def write_source(path: Path) -> None:
    rows = []
    for index in range(12 * 270):
        year = 1749 + index // 12
        month = index % 12 + 1
        value = 50.0 + 35.0 * ((index % 132) / 131) + (index % 7)
        definitive = 0 if index == 12 * 270 - 1 else 1
        rows.append(
            f"{year};{month};{year + (month - 0.5) / 12:.3f};"
            f"{value:.1f};3.0;20;{definitive}"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_parser_excludes_provisional_and_rejects_short_source(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    write_source(source)
    observations, excluded = parse_silso_monthly(source)
    assert observations[0].date == "1749-01"
    assert excluded == {"provisional": 1, "missing": 0}
    short = tmp_path / "short.csv"
    short.write_text(source.read_text(encoding="utf-8").splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="enough definitive"):
        parse_silso_monthly(short)


def test_investigation_preserves_source_and_distinguishes_retention(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv"
    write_source(source)
    output = tmp_path / "run"
    result = run_investigation(str(source), output)
    assert (output / "silso_monthly_total_v2.csv").read_bytes() == source.read_bytes()
    assert result["selected_fixed_expert_from_development_mae"] in EXPERTS
    summaries = {
        (row["mechanism"], row["period"]): row for row in result["mechanism_summaries"]
    }
    assert summaries[("fixed_uniform", "evaluation")]["mean_weight_change_l1"] == 0
    assert (
        summaries[("adaptive_short_continuity_continued", "evaluation")][
            "mean_weight_change_l1"
        ]
        > 0
    )
    comparisons = {
        row["retention_condition"]: row for row in result["continued_vs_reset"]
    }
    assert comparisons["one_encounter"]["different_prediction_rows"] == 1
    assert comparisons["cumulative_continuity"]["different_prediction_rows"] > 0
    assert (output / "exp005_learning_continuity.svg").exists()
    audit = audit_investigation(output)
    assert audit["evidence_status"].startswith("post-hoc")
    assert len(audit["lock_in"]) == 5
    assert (output / "exp005_posthoc_value_ranges.csv").exists()
    with pytest.raises(FileExistsError):
        audit_investigation(output)
    with pytest.raises(FileExistsError):
        run_investigation(str(source), output)
