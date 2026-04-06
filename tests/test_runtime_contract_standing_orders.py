from __future__ import annotations


def test_runtime_contract_exposes_standing_orders_as_canonical(isolated_runtime) -> None:
    contract = __import__(
        "core.identity.runtime_contract",
        fromlist=["build_runtime_contract_state"],
    ).build_runtime_contract_state()

    canonical = {item["name"]: item for item in contract["files"]["canonical"]}
    assert "STANDING_ORDERS.md" in canonical
    assert canonical["STANDING_ORDERS.md"]["loaded_by_default"] is True

    visible_mode = contract["prompt_modes"]["visible_chat"]
    heartbeat_mode = contract["prompt_modes"]["heartbeat"]
    future_agent_mode = contract["prompt_modes"]["future_agent_task"]

    assert "STANDING_ORDERS.md" in visible_mode["always_loaded"]
    assert "STANDING_ORDERS.md" in heartbeat_mode["always_loaded"]
    assert "STANDING_ORDERS.md" in future_agent_mode["always_loaded"]
