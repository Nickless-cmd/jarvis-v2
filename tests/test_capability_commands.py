from __future__ import annotations


def test_local_approval_fallback_explicitly_uses_owner_legacy_scope(monkeypatch) -> None:
    from core.cli import capability_commands

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        capability_commands,
        "request_json",
        lambda *_args, **_kwargs: (None, "offline"),
    )

    def fake_approve(request_id: str, **kwargs):
        captured.update(request_id=request_id, **kwargs)
        return {"request_id": request_id}

    monkeypatch.setattr(
        capability_commands,
        "approve_capability_approval_request",
        fake_approve,
    )

    request, source, error = capability_commands.approve_capability_request_truth(
        "legacy-request"
    )

    assert request == {"request_id": "legacy-request"}
    assert source == "local-fallback"
    assert error == "offline"
    assert captured["user_id"] is None
    assert captured["include_unassigned"] is True
