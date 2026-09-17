"""En nedlukning må ikke tage turen med sig.

17/9-2026: nedluknings-sweepen stemplede en synlig tur `interrupted`. Det er
ikke forkert som beskrivelse — men en `interrupted` post er ikke forfalden for
genoptagelses-dispatcheren, så turen blev aldrig taget op igen efter
genstarten. Arbejdet, de færdige værktøjskald og checkpointet var tabt.
"""
from __future__ import annotations

import inspect

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(ifr, "_save", lambda v: (poster.clear(),
                                                 poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    return poster


def test_nedlukningen_gaar_gennem_settle_recovering_for_synlige_ture():
    """Kildelæsning, fordi sweepen kun kan køres i en rigtig nedlukning."""
    from apps.api.jarvis_api import app as app_mod
    kilde = inspect.getsource(app_mod)
    assert "settle_recovering(" in kilde
    # Ordet står også i en kommentar længere oppe; vi vil have SWEEPEN — den
    # der faktisk stempler, altså grenen omkring `reason="api-nedlukning"`.
    hvor = kilde.index('reason="api-nedlukning"')
    afsnit = kilde[hvor - 900:hvor + 200]
    assert "settle_recovering" in afsnit
    assert 'kind") or "visible") == "visible"' in afsnit


def test_en_genoptagelig_post_er_forfalden_men_en_afbrudt_er_ikke():
    """Dét er hele forskellen: kun den ene bliver taget op igen."""
    ifr.mark_started(run_id="r-recover", session_id="s1", user_message="x")
    ifr.settle_recovering("r-recover", reason="shutdown")
    ifr.mark_started(run_id="r-interrupt", session_id="s2", user_message="y")
    ifr.mark_interrupted("r-interrupt", reason="shutdown")

    taget = ifr.claim_due_recovery(owner="api:1")
    assert taget is not None and taget["run_id"] == "r-recover"
    assert ifr.claim_due_recovery(owner="api:1") is None
