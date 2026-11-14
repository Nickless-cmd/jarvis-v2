import json
from pathlib import Path

from core.services.jarvis_ui_guard import _diagnosticér


CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "flade_maaling_over_tid_contract.json").read_text()
)


def test_maaling_over_tid_fixtures_match_guard_contract() -> None:
    for case in CASES:
        level, errors = _diagnosticér(case["input"])
        assert [level, errors] == [
            case["guard"]["level"],
            case["guard"]["errors"],
        ], case["name"]
