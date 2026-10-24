from __future__ import annotations

import json
from pathlib import Path

from core.services.chat_response_policy import CHAT_CLOSURES, surface_for_reading_task


def test_presentation_eval_cases_cover_thresholds_and_closures() -> None:
    cases = json.loads(
        (Path(__file__).parent / "fixtures" / "chat_response_policy_cases.json").read_text()
    )
    assert len(cases) >= 12
    for case in cases:
        assert case["closure"] in CHAT_CLOSURES, case["name"]
        assert surface_for_reading_task(
            case["task"], item_count=case["items"],
            shared_dimensions=case["dimensions"],
            already_rendered=case.get("rendered", False),
        ) == case["surface"], case["name"]

