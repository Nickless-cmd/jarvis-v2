import core.services.device_presence as dp


def test_record_ping_creates_and_updates_state(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()  # ryd global state mellem tests
    dp.record_ping("bjorn", "dev-A", "desktop", foreground=True, awake=True, network="home", interaction=True)
    st = dp._PRESENCE["bjorn"]["dev-A"]
    assert st.platform == "desktop"
    assert st.last_ping_at == 1000.0
    assert st.last_interaction_at == 1000.0
    assert st.foreground is True

    box["t"] = 1005.0
    dp.record_ping("bjorn", "dev-A", "desktop", foreground=False, awake=True, network="home", interaction=False)
    st = dp._PRESENCE["bjorn"]["dev-A"]
    assert st.last_ping_at == 1005.0
    assert st.last_interaction_at == 1000.0  # interaction=False bevarer gammel
    assert st.foreground is False


def test_rank_desktop_foreground_beats_background_mobile(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home", interaction=False)
    ranked = dp.rank("bjorn")
    assert [r.device_key for r in ranked][0] == "desk"
    assert ranked[0].reachable_via == "desktop_queue"


def test_rank_excludes_sleeping_desktop(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=False, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="away", interaction=True)
    ranked = dp.rank("bjorn")
    assert [r.device_key for r in ranked] == ["mob"]  # desktop sovende → ekskluderet


def test_rank_offline_desktop_dropped_mobile_stays_fcm(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="unknown", interaction=False)
    box["t"] = 1000.0 + 30.0  # desktop online-TTL=12s → desktop nu offline
    ranked = dp.rank("bjorn")
    keys = [r.device_key for r in ranked]
    assert "desk" not in keys          # desktop offline → ikke nåbar
    assert keys == ["mob"]             # mobil stadig FCM-nåbar
    assert ranked[0].reachable_via == "fcm"


def test_prune_drops_stale_records(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "old", "mobile", foreground=False, awake=True, network="home")
    box["t"] = 1000.0 + 200.0  # > _PRESENCE_TTL_S (120)
    dp.record_ping("bjorn", "fresh", "mobile", foreground=True, awake=True, network="home")
    dp.prune()
    keys = set((dp._PRESENCE.get("bjorn") or {}).keys())
    assert keys == {"fresh"}


def test_summary_active_desktop(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    s = dp.summary("bjorn")
    assert "desktop" in s.lower()


def test_summary_no_devices(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    assert "ingen" in dp.summary("bjorn").lower()
