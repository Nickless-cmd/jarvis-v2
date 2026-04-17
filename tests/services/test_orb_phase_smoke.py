"""Smoke test for core.services.orb_phase.

Setting the orb phase should persist the phase name in the watched JSON file.
"""

import json

from core.services import orb_phase


def test_set_phase_writes_phase_payload(tmp_path, monkeypatch) -> None:
    phase_file = tmp_path / "orb-phase.json"
    monkeypatch.setattr(orb_phase, "_PHASE_FILE", phase_file)

    orb_phase.set_phase("think")

    assert json.loads(phase_file.read_text(encoding="utf-8")) == {"phase": "think"}
