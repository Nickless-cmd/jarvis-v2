"""Smoke test for core.services.affective_state_renderer.

The public prompt helper should reuse a fresh cached affective state instead of
forcing a new render pass on every call.
"""

from core.runtime import db as runtime_db
from core.services import affective_state_renderer


def test_get_affective_state_returns_cached_value(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_db,
        "get_cached_affective_state",
        lambda max_age_seconds: "rolig og fokuseret",
    )
    saved: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        runtime_db,
        "save_cached_affective_state",
        lambda *args, **kwargs: saved.append(args),
    )

    assert (
        affective_state_renderer.get_affective_state_for_prompt()
        == "rolig og fokuseret"
    )
    assert saved == []
