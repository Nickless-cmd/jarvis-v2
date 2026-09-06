"""Task 3 (memory repair 2026-09-04): private promotion is gated on substance."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

TEMPLATE_HMM = "I should keep carrying what helped around hmm. It still feels mere stabilt nu."
REAL = "I should keep carrying what helped around pfsense-nøglen flyttet til .env via env_override. It still feels mere stabilt nu."


def test_private_layer_pipeline_gate_rejects_template_and_accepts_real():
    from core.memory.private_layer_pipeline import _promotion_has_substance

    assert _promotion_has_substance({"promotion_target": TEMPLATE_HMM}, {"retained_value": TEMPLATE_HMM}) is False
    assert _promotion_has_substance({"promotion_target": REAL}, {"retained_value": REAL}) is True
