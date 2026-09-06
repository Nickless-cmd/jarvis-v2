"""Task 3 (memory repair 2026-09-04): retained-memory prompt signal hides empty topics."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

TEMPLATE_HMM = "I should keep carrying what helped around hmm. It still feels mere stabilt nu."
REAL = "I should keep carrying what helped around pfsense-nøglen flyttet til .env via env_override. It still feels mere stabilt nu."


def test_retained_prompt_signal_hidden_for_empty_topic():
    from core.services import prompt_support_signals as pss

    def _proj(focus):
        return {"active": True, "retained_focus": focus, "retained_kind": "reinforced pattern"}

    with patch.object(pss, "get_private_retained_memory_record", return_value=None), \
         patch.object(pss, "recent_private_retained_memory_records", return_value=[]), \
         patch.object(pss, "build_private_retained_memory_projection", return_value=_proj("hmm")):
        assert pss._retained_memory_support_signal_instruction() is None
    with patch.object(pss, "get_private_retained_memory_record", return_value=None), \
         patch.object(pss, "recent_private_retained_memory_records", return_value=[]), \
         patch.object(pss, "build_private_retained_memory_projection", return_value=_proj("pfsense nøgle i .env")):
        out = pss._retained_memory_support_signal_instruction()
    assert out and "pfsense" in out
