from __future__ import annotations


def test_create_decision_dedupes_active_directive(monkeypatch) -> None:
    from core.services import behavioral_decisions as bd

    existing = {
        "decision_id": "dec-existing",
        "directive": "Stop after five tool calls.",
        "priority": 80,
        "status": "active",
    }
    created = []
    published = []
    monkeypatch.setattr(bd, "_db_list", lambda **kwargs: [existing])
    monkeypatch.setattr(bd, "_db_create", lambda **kwargs: created.append(kwargs) or {"decision_id": "new"})
    monkeypatch.setattr(bd.event_bus, "publish", lambda kind, payload: published.append((kind, payload)))

    result = bd.create_decision(
        directive="  stop   after five tool calls. ",
        priority=75,
        created_by="test",
    )

    assert result["decision_id"] == "dec-existing"
    assert result["deduped"] is True
    assert created == []
    assert published[0][0] == "decision.deduped"


def test_create_decision_creates_when_directive_is_new(monkeypatch) -> None:
    from core.services import behavioral_decisions as bd

    monkeypatch.setattr(bd, "_db_list", lambda **kwargs: [])
    monkeypatch.setattr(
        bd,
        "_db_create",
        lambda **kwargs: {"decision_id": "dec-new", "directive": kwargs["directive"], "priority": kwargs["priority"]},
    )
    monkeypatch.setattr(bd.event_bus, "publish", lambda *args, **kwargs: None)

    result = bd.create_decision(directive="Surface status before silence.", priority=70)

    assert result["decision_id"] == "dec-new"
    assert result.get("deduped") is None


def test_commit_observe_is_self_safe():
    """Commit-cluster instrument: _commit_observe må aldrig kaste (best-effort)."""
    from core.services.behavioral_decisions import _commit_observe
    _commit_observe("created", "decision-xyz")  # kaster ikke
    _commit_observe("deduped", None)


def test_dedup_henter_aktive_uden_loft(monkeypatch) -> None:
    """Et loft på 100 var aldrig en semantisk grænse.

    Den slap igennem som default, og da tabellen voksede forbi loftet så
    dedup'en ikke længere alle aktive — så samme direktiv blev oprettet i
    dublet. «undgå at slette filer uden backup» stod 27 gange (3/5 → 9/7-2026).
    """
    from core.services import behavioral_decisions as bd

    kald: list[dict] = []

    def fake_list(**kwargs):
        kald.append(kwargs)
        return []

    monkeypatch.setattr(bd, "_db_list", fake_list)
    monkeypatch.setattr(bd, "_db_create", lambda **kwargs: {"decision_id": "dec-new"})
    monkeypatch.setattr(bd.event_bus, "publish", lambda *a, **k: None)

    bd.create_decision(directive="Noget helt nyt.")

    aktive = [k for k in kald if k.get("status") == "active"]
    assert aktive, "dedup skal slå op blandt aktive"
    assert aktive[0].get("limit") is None, "dedup må ikke sætte et loft"


def test_genoprettelse_af_nyligt_revokeret_dedupes(monkeypatch) -> None:
    """Revoke frigiver direktivet — men ikke tilbage til en evig løkke.

    Uden cooldown kunne en auto-generator skrive opret → revoke → opret i det
    uendelige. Inden for vinduet skal kaldet dedupes mod den revokede række,
    ikke oprette en ny.
    """
    from datetime import UTC, datetime

    from core.services import behavioral_decisions as bd

    revokeret = {
        "decision_id": "dec-rev",
        "directive": "Undgå at slette filer uden backup",
        "status": "revoked",
        "updated_at": datetime.now(UTC).isoformat(),
    }

    def fake_list(*, status="active", limit=50):
        return [revokeret] if status == "revoked" else []

    oprettede: list[dict] = []
    monkeypatch.setattr(bd, "_db_list", fake_list)
    monkeypatch.setattr(
        bd, "_db_create", lambda **kw: oprettede.append(kw) or {"decision_id": "ny"}
    )
    monkeypatch.setattr(bd.event_bus, "publish", lambda *a, **k: None)

    ud = bd.create_decision(directive="undgå at slette filer uden backup")

    assert ud["decision_id"] == "dec-rev"
    assert ud["deduped"] is True
    assert ud["dedupe_reason"] == "directive-revoked-within-cooldown"
    assert oprettede == [], "der må ikke oprettes en ny række"


def test_gammel_revokeret_genoprettes(monkeypatch) -> None:
    """Cooldown må ikke låse for evigt.

    En bevidst revoke for en måned siden skal kunne genoprettes — ellers har
    jeg byttet et hul ud med et andet.
    """
    from datetime import UTC, datetime, timedelta

    from core.services import behavioral_decisions as bd

    revokeret = {
        "decision_id": "dec-gammel",
        "directive": "Undgå at slette filer uden backup",
        "status": "revoked",
        "updated_at": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
    }

    def fake_list(*, status="active", limit=50):
        return [revokeret] if status == "revoked" else []

    monkeypatch.setattr(bd, "_db_list", fake_list)
    monkeypatch.setattr(
        bd, "_db_create", lambda **kw: {"decision_id": "ny", "directive": kw["directive"]}
    )
    monkeypatch.setattr(bd.event_bus, "publish", lambda *a, **k: None)

    ud = bd.create_decision(directive="undgå at slette filer uden backup")

    assert ud["decision_id"] == "ny"
    assert ud.get("deduped") is None
