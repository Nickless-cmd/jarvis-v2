"""Proaktivitet — en tanke der deles, ikke en notifikation der afbryder.

Kanalen fandtes uden begrænsning. En uhæmmet initiativ-kanal bliver til støj på
én dag, og så slår man den fra — og dermed mister han den helt. Testene dækker
de tre grænser og at TILBAGEHOLDTE tanker også journalføres.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import companion_initiative as ci


# ── 3. PROAKTIVITET ──────────────────────────────────────────────────────────

@pytest.fixture
def journal(monkeypatch):
    store: dict = {}
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda k, d=None: store.get(k, d), raising=False)
    monkeypatch.setattr("core.runtime.db_core.set_runtime_state_value",
                        lambda k, v, **kw: store.__setitem__(k, v), raising=False)
    return store


@pytest.fixture
def sender(monkeypatch):
    sent: list = []
    import core.services.push_dispatcher as pd
    monkeypatch.setattr(pd, "send_companion_push",
                        lambda uid, msg, title="Jarvis": (sent.append((uid, msg)), True)[1])
    return sent


def _midday(offset_min: int = 0) -> datetime:
    return datetime(2026, 9, 2, 12, 0, tzinfo=UTC) + timedelta(minutes=offset_min)


def test_foerste_tanke_gaar_igennem(journal, sender):
    out = ci.offer_thought("u1", "jeg tænkte på noget", now=_midday())
    assert out.delivered is True
    assert sender == [("u1", "jeg tænkte på noget")]


def test_to_tanker_taet_paa_hinanden_holdes_tilbage(journal, sender):
    """To beskeder med et minuts mellemrum føles som en app der pinger, ikke
    som nogen der tænker."""
    ci.offer_thought("u1", "første", now=_midday())
    out = ci.offer_thought("u1", "anden", now=_midday(5))
    assert out.delivered is False
    assert "tæt" in out.reason
    assert len(sender) == 1


def test_loft_pr_doegn(journal, sender):
    for i in range(ci._MAX_PER_DAY):
        assert ci.offer_thought("u1", f"tanke {i}", now=_midday(i * 100)).delivered
    out = ci.offer_thought("u1", "en for meget", now=_midday(ci._MAX_PER_DAY * 100))
    assert out.delivered is False
    assert "loftet" in out.reason


def test_stille_timer_udskyder_frem_for_at_kassere(journal, sender):
    natten = datetime(2026, 9, 2, 3, 0, tzinfo=UTC)
    out = ci.offer_thought("u1", "kl. tre om natten", now=natten)
    assert out.delivered is False
    assert out.reason == "stille timer"
    # En god tanke kl. 03 er stadig en god tanke kl. 07.
    assert out.deferred_until


def test_tilbageholdte_tanker_journalfoeres_ogsaa(journal, sender):
    """En tanke der blev holdt tilbage, er stadig en tanke han fik — og skal
    kunne ses, ellers kan man ikke vurdere om grænserne er sat rigtigt."""
    ci.offer_thought("u1", "første", now=_midday())
    ci.offer_thought("u1", "anden", now=_midday(5))
    items = ci.recent_thoughts("u1")
    assert len(items) == 2
    assert items[0]["delivered"] is False
    assert items[0]["reason"]


def test_tom_tanke_sendes_ikke(journal, sender):
    assert ci.offer_thought("u1", "   ", now=_midday()).delivered is False
    assert ci.offer_thought("", "noget", now=_midday()).delivered is False
    assert sender == []


def test_brugere_deler_ikke_journal(journal, sender):
    ci.offer_thought("u1", "til en", now=_midday())
    out = ci.offer_thought("u2", "til to", now=_midday(1))
    assert out.delivered is True
    assert len(ci.recent_thoughts("u1")) == 1
    assert len(ci.recent_thoughts("u2")) == 1


def test_stille_vindue_krydser_midnat():
    assert ci.is_quiet_hour(datetime(2026, 9, 2, 23, 0).astimezone(UTC)) is True
    assert ci.is_quiet_hour(datetime(2026, 9, 2, 4, 0).astimezone(UTC)) is True
    assert ci.is_quiet_hour(datetime(2026, 9, 2, 13, 0).astimezone(UTC)) is False
