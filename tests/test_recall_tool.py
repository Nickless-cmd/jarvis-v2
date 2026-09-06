"""Task 4 (memory repair 2026-09-04): the `recall` tool wrapper."""
from __future__ import annotations

from unittest.mock import patch


def test_tool_exec_maps_args():
    from core.tools.recall_tool import _exec_recall

    with patch("core.services.recall.recall", return_value={"status": "ok", "count": 0, "results": []}) as rc:
        _exec_recall({"query": "pfsense", "limit": "3", "sources": "workspace,brain", "_runtime_session_id": "chat-1"})
    rc.assert_called_once_with("pfsense", limit=3, sources=["workspace", "brain"], session_id="chat-1")
