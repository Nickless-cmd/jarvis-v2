"""Krydsproces-relæet: events fra den anden proces når de lokale lyttere.

Målt 19/9-2026: desk'ens chat kører i API-processen, lytterne i runtime-
processen, og subscribe() er en kø i processen — lytterne var døve for alt
API-processen publicerede.
"""
from __future__ import annotations

import queue

import pytest


@pytest.fixture
def bus(isolated_runtime):
    from core.eventbus.bus import EventBus
    b = EventBus()
    yield b
    b.stop()


def _fremmed_raekke(kind: str, payload_json: str = "{}") -> int:
    """En række skrevet af «den anden proces» — direkte i tabellen."""
    from core.runtime.db import connect
    with connect() as c:
        cur = c.execute("INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
                        (kind, payload_json, "2026-09-19T12:00:00+00:00"))
        return int(cur.lastrowid)


def _toem(q) -> list[dict]:
    ud = []
    while True:
        try:
            item = q.get_nowait()
        except queue.Empty:
            return ud
        if item is not None:
            ud.append(item)


def test_en_anden_proces_event_naar_den_lokale_lytter(bus):
    from core.eventbus.krydsproces import relae_en_gang
    q = bus.subscribe()
    eid = _fremmed_raekke("channel.chat_message_appended",
                          '{"session_id": "s1", "message": {"role": "assistant"}}')
    sidste, leveret = relae_en_gang(bus, eid - 1)
    assert (sidste, leveret) == (eid, 1)
    [ev] = _toem(q)
    assert ev["kind"] == "channel.chat_message_appended"
    assert ev["payload"]["session_id"] == "s1"


def test_egne_events_leveres_ikke_to_gange(bus):
    from core.eventbus.krydsproces import relae_en_gang
    q = bus.subscribe()
    bus.publish("runtime.noget", {"x": 1})
    bus.flush()
    foer = _toem(q)
    assert [e["kind"] for e in foer] == ["runtime.noget"]
    sidste, leveret = relae_en_gang(bus, foer[0]["id"] - 1)
    assert leveret == 0 and sidste == foer[0]["id"]
    assert _toem(q) == []


def test_pegepinden_flytter_sig_forbi_egne_og_fremmede(bus):
    from core.eventbus.krydsproces import relae_en_gang
    bus.publish("runtime.egen", {})
    bus.flush()
    a = _fremmed_raekke("runtime.fremmed")
    sidste, leveret = relae_en_gang(bus, 0)
    assert sidste == a and leveret == 1
    assert relae_en_gang(bus, sidste) == (sidste, 0)


def test_egne_ids_huskes_i_et_begraenset_vindue(bus, monkeypatch):
    import collections
    bus._egne_ids = collections.deque(maxlen=3)
    bus._egne_set = set()
    for i in range(1, 6):
        bus._noter_egen(i)
    assert not bus.er_egen(1) and not bus.er_egen(2)
    assert all(bus.er_egen(i) for i in (3, 4, 5))
