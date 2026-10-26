"""Handler registry for the cohesive agent-contract tool family.

Extracted from simple_tools.py under the Boy Scout rule; the large dispatcher
now imports one mapping instead of owning this subsystem's individual wiring.
"""
from core.tools.agent_contract_tools import (
    _exec_close_agent,
    _exec_convene_agent_council,
    _exec_decide_agent_approval,
    _exec_dispatch_agent,
    _exec_followup_agent,
    _exec_integrate_agent_work,
    _exec_interrupt_agent,
    _exec_list_agents,
    _exec_review_agent_work,
    _exec_send_message_to_agent,
    _exec_task,
    _exec_wait_agents,
)


AGENT_CONTRACT_HANDLERS = {
    "Task": _exec_task,
    # Internal/legacy entry point; no longer advertised to the model.
    "dispatch_agent": _exec_dispatch_agent,
    "send_message_to_agent": _exec_send_message_to_agent,
    "list_agents": _exec_list_agents,
    "followup_agent": _exec_followup_agent,
    "wait_agents": _exec_wait_agents,
    "interrupt_agent": _exec_interrupt_agent,
    "integrate_agent_work": _exec_integrate_agent_work,
    "convene_agent_council": _exec_convene_agent_council,
    "review_agent_work": _exec_review_agent_work,
    "decide_agent_approval": _exec_decide_agent_approval,
    "close_agent": _exec_close_agent,
}
