"""Notifikations-afkøling i central_watch.

Baggrund (målt 2026-09-02): en tilstand som «disk 94% brugt» eller «host svarer
ikke» er sand ved HVERT watch-tick indtil nogen retter den. Incidenten dedupede
allerede, men notifikationen gjorde ikke — Bjørn fik samme to flag hver halve
time i døgndrift. Testen holder fast i, at et uændret flag kun ringer én gang
pr. afkølingsvindue, og at et flag der FORVÆRRES stadig kan trænge igennem.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.services import central_watch


@pytest.fixture
def kv(monkeypatch):
    store: dict = {}

    def _get(key, default=None):
        return store.get(key, default)

    def _set(key, value, **_kw):
        store[key] = value

    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value", _get, raising=False)
    monkeypatch.setattr("core.runtime.db_core.set_runtime_state_value", _set, raising=False)
    return store


def test_uaendret_flag_ringer_kun_en_gang_i_vinduet(kv):
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    key = "Central-flag: infra/pve_disk|Disk-pres på 'pve': 94% brugt"

    assert central_watch._notify_cooldown_active(key, now) is False
    central_watch._notify_cooldown_mark(key, now)

    # Et tick en halv time senere må IKKE ringe igen.
    assert central_watch._notify_cooldown_active(key, now + timedelta(minutes=30)) is True
    # Efter vinduet må den godt.
    later = now + timedelta(hours=central_watch._NOTIFY_COOLDOWN_H, minutes=1)
    assert central_watch._notify_cooldown_active(key, later) is False


def test_forvaerret_tilstand_traenger_igennem_afkolingen(kv):
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    central_watch._notify_cooldown_mark("Central-flag: infra/pve_disk|Disk-pres: 94% brugt", now)

    # Samme nerve, ny besked (94% → 97%) = nyt flag. Skal kunne ringe med det samme:
    # en tilstand der forværres må ikke tie bag sin egen afkøling.
    vaerre = "Central-flag: infra/pve_disk|Disk-pres: 97% brugt"
    assert central_watch._notify_cooldown_active(vaerre, now + timedelta(minutes=5)) is False


def test_fejlet_levering_markerer_ikke_afkoling(kv, monkeypatch):
    """Går notifikationen ikke igennem, må flaget ikke tie i seks timer."""
    monkeypatch.setattr(central_watch, "_owner_uid", lambda: "uid-1")

    import core.services.notification_router as nr
    monkeypatch.setattr(nr, "route_proactive_notification",
                        lambda *a, **k: {"delivered": False}, raising=False)

    assert central_watch._notify_owner("Central-flag: x/y", "noget", "high") is False
    assert kv.get(central_watch._NOTIFY_STATE_KEY) in (None, {})
