"""Tests for lukning af `acted`-poster der aldrig fik et outcome.

Anledningen er målt: 1.042 af 1.114 `acted`-poster havde tomt `outcome`, og
`_expire_stale` rører kun `pending` — der fandtes ingen vej ud af `acted`.
Puljen voksede fordi `acted` betyder «sendt til en kanal» og ikke «behandlet».

Testene dækker de fire ting der kan gå galt: at poster MED outcome bliver
lukket ved en fejl, at lukningen ikke er idempotent, at `action_summary`
tabes, og at `abandoned_at` ikke bliver sat (den er det signal resten af
koden læser som «ude af spil»).
"""
from __future__ import annotations

import core.services.initiative_queue as iq


def _post(iid: str, *, outcome: str = "", action: str = "", abandoned: str = "") -> dict:
    return {
        "initiative_id": iid,
        "status": "acted",
        "outcome": outcome,
        "outcome_note": "",
        "action_summary": action,
        "abandoned_at": abandoned,
    }


class _FakeDB:
    def __init__(self, poster: list[dict]) -> None:
        self.poster = poster
        self.opdateringer: dict[str, dict] = {}

    def list_runtime_initiatives(self, *, status: str = "", limit: int = 100, **kw):
        return [p for p in self.poster if not status or p["status"] == status][:limit]

    def update_runtime_initiative(self, iid: str, **felter):
        self.opdateringer.setdefault(iid, {}).update(felter)
        return {"initiative_id": iid, **felter}


def test_lukker_kun_acted_uden_outcome(monkeypatch):
    """De 72 med et reelt outcome må ikke røres — de er allerede afsluttede."""
    db = _FakeDB([
        _post("uden-1", action="surfaced via proactivity_bridge"),
        _post("med-1", outcome="approved"),
        _post("uden-2", action="Besvaret og maalt 8/11"),
    ])
    monkeypatch.setattr(iq, "runtime_db", db)

    r = iq.close_acted_without_outcome()

    assert r["lukket"] == 2
    assert "med-1" not in db.opdateringer
    assert "uden-1" in db.opdateringer and "uden-2" in db.opdateringer


def test_status_bliver_expired_og_abandoned_at_saettes(monkeypatch):
    """`abandoned_at` er det signal koden selv læser som «ude af spil»."""
    db = _FakeDB([_post("a", action="x")])
    monkeypatch.setattr(iq, "runtime_db", db)

    iq.close_acted_without_outcome()

    f = db.opdateringer["a"]
    assert f["status"] == "expired"
    assert f["abandoned_at"], "abandoned_at skal sættes — ellers ser dedup posten stadig"
    assert "acted uden outcome" in f["blocked_reason"]


def test_action_summary_bevares_i_grunden(monkeypatch):
    """Informationen må ikke tabes: hvad der faktisk skete skal kunne læses bagefter."""
    db = _FakeDB([_post("a", action="surfaced via proactivity_bridge")])
    monkeypatch.setattr(iq, "runtime_db", db)

    iq.close_acted_without_outcome()

    assert "surfaced via proactivity_bridge" in db.opdateringer["a"]["blocked_reason"]


def test_idempotent_allerede_lukkede_roeres_ikke(monkeypatch):
    """Anden kørsel må ikke skrive igen — ellers ændrer gentagne kald historikken."""
    db = _FakeDB([_post("a", action="x", abandoned="2026-11-08T00:00:00+00:00")])
    monkeypatch.setattr(iq, "runtime_db", db)

    r = iq.close_acted_without_outcome()

    assert r["lukket"] == 0
    assert db.opdateringer == {}


def test_tom_action_summary_giver_ren_grund(monkeypatch):
    db = _FakeDB([_post("a")])
    monkeypatch.setattr(iq, "runtime_db", db)

    iq.close_acted_without_outcome()

    assert db.opdateringer["a"]["blocked_reason"].rstrip().endswith("acted uden outcome")
