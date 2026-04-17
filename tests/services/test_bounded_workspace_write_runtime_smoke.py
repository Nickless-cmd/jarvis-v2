"""Smoke test for core.services.bounded_workspace_write_runtime.

The workspace write surface should describe an approved, completed bounded file
write when the latest capability invocation says it executed successfully.
"""

from core.services import bounded_workspace_write_runtime


def test_workspace_write_surface_reflects_executed_invocation(monkeypatch) -> None:
    monkeypatch.setattr(
        bounded_workspace_write_runtime,
        "get_capability_invocation_truth",
        lambda: {
            "last_invocation": {
                "execution_mode": "workspace-file-write",
                "status": "executed",
                "detail": "Wrote workspace/default/MEMORY.md",
                "invoked_at": "2026-04-17T10:00:00+00:00",
                "finished_at": "2026-04-17T10:00:01+00:00",
                "result_preview": "updated memory note",
                "capability": {"target_path": "workspace/default/MEMORY.md"},
                "approval": {"granted": True},
                "proposal_content": {
                    "target": "workspace/default/MEMORY.md",
                    "content": "patched note",
                    "summary": "Update memory note",
                    "fingerprint": "abc123",
                    "source": "test",
                    "reason": "Refresh the note",
                },
            },
        },
    )
    monkeypatch.setattr(
        bounded_workspace_write_runtime,
        "latest_capability_approval_request",
        lambda **kwargs: None,
    )

    surface = (
        bounded_workspace_write_runtime.build_bounded_workspace_write_execution_surface()
    )

    assert surface["execution_state"] == "workspace-write-completed"
    assert surface["mutation_permitted"] is True
    assert surface["execution_target"] == "workspace/default/MEMORY.md"
    assert surface["write_proposal_content_summary"] == "Update memory note"
