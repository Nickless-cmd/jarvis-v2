from __future__ import annotations


def test_workspace_capabilities_reexports_approval_helpers() -> None:
    from core.tools import workspace_capabilities
    from core.tools import workspace_capabilities_approval

    assert (
        workspace_capabilities._persist_capability_approval_request
        is workspace_capabilities_approval._persist_capability_approval_request
    )
    assert (
        workspace_capabilities._workspace_write_proposal_content
        is workspace_capabilities_approval._workspace_write_proposal_content
    )
