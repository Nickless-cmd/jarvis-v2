import core.services.desktop_notifications as dn


def test_enqueue_then_drain_clears(monkeypatch):
    monkeypatch.setattr(dn, "_now", lambda: 1000.0)
    dn.reset()
    dn.enqueue("bjorn", {"notif_id": "n1", "kind": "answer_ready", "title": "Klar", "body": "svar", "session_id": "s1"})
    items = dn.drain("bjorn")
    assert len(items) == 1 and items[0]["notif_id"] == "n1"
    assert "_ts" not in items[0]
    assert dn.drain("bjorn") == []  # drain rydder


def test_prune_drops_old_undrained(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dn, "_now", lambda: box["t"])
    dn.reset()
    dn.enqueue("bjorn", {"notif_id": "n1", "kind": "reminder", "title": "x", "body": "y", "session_id": ""})
    box["t"] = 1000.0 + 400.0  # > _DESKTOP_NOTIF_TTL_S (300)
    dn.prune()
    assert dn.drain("bjorn") == []
