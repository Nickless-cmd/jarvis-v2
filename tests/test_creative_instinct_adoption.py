"""Regression test for the creative-instinct adoption transition."""
from __future__ import annotations

import json
from datetime import UTC, datetime

from core.services import autonomous_work_daemon as autonomous_work
from core.services import creative_instinct_daemon as creative_instinct


def test_completed_seed_proposal_adopts_seed_and_updates_surface(monkeypatch, tmp_path):
    creative_path = tmp_path / "creative_instinct.json"
    autonomous_path = tmp_path / "autonomous_work_log.json"
    incubator_path = tmp_path / "INCUBATOR.md"
    seed_id = "seed-adoption-test"
    proposal_id = "aw-adoption-test"
    now = datetime.now(UTC).isoformat()

    creative_path.write_text(
        json.dumps({
            "seeds": [{
                "seed_id": seed_id,
                "spark": "undersøg en konkret kreativ kobling",
                "confidence": 0.6,
                "why_now": "test",
                "depends_on": ["chat"],
                "status": "maturing",
                "created_at": now,
                "touched_at": now,
            }],
            "last_tick_at": now,
        }),
        encoding="utf-8",
    )
    autonomous_path.write_text(
        json.dumps([{
            "proposal_id": proposal_id,
            "at": now,
            "type": "research",
            "title": "Research seed",
            "details": {"seed_id": seed_id},
            "rationale": "Seedet blev valgt til synlig research.",
            "status": "pending",
        }]),
        encoding="utf-8",
    )
    monkeypatch.setattr(creative_instinct, "_storage_path", lambda: creative_path)
    monkeypatch.setattr(creative_instinct, "_incubator_path", lambda: incubator_path)
    monkeypatch.setattr(autonomous_work, "_storage_path", lambda: autonomous_path)

    assert autonomous_work.resolve_proposal(
        proposal_id,
        outcome="completed",
        note="visible run visible-123 completed research",
    ) is True

    adopted = creative_instinct.list_seeds(status="adopted")
    assert len(adopted) == 1
    assert adopted[0]["seed_id"] == seed_id
    assert adopted[0]["adopted_at"]
    assert adopted[0]["adoption_reference"] == {
        "kind": "autonomous_work_proposal",
        "proposal_id": proposal_id,
        "note": "visible run visible-123 completed research",
    }
    assert creative_instinct.build_creative_instinct_surface()["adopted_total"] == 1
