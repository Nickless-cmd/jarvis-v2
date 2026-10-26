"""The extracted agent-contract handler family stays complete."""
from __future__ import annotations


def test_task_is_server_backed_and_legacy_dispatch_is_not_advertised():
    from core.tools.agent_contract_handlers import AGENT_CONTRACT_HANDLERS
    from core.tools.agent_contract_tools import AGENT_CONTRACT_TOOL_DEFINITIONS

    advertised = {d["function"]["name"] for d in AGENT_CONTRACT_TOOL_DEFINITIONS}
    assert "Task" in AGENT_CONTRACT_HANDLERS and "Task" in advertised
    assert "dispatch_agent" in AGENT_CONTRACT_HANDLERS
    assert "dispatch_agent" not in advertised
