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


def test_rank_foreground_desktop_beats_recently_used_background_mobile(monkeypatch):
    # BUG1: skift mobil→desktop. Desktop har kørt et stykke tid (gammel
    # interaction → recency 0), men er foreground NU. Mobil blev lige brugt
    # (frisk recency + away-bonus) men er nu baggrund. Foreground = hvor brugeren
    # ER, skal vinde — ikke mobilens lingering recency.
    box = {"t": 0.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    box["t"] = 700.0  # desktop-interaction nu > recency-horisont (600s) → recency 0
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=False)
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="away", interaction=True)
    box["t"] = 705.0  # bruger ved desktop: mobil baggrunder (foreground=False)
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=False)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="away", interaction=False)
    ranked = dp.rank("bjorn")
    assert ranked[0].device_key == "desk"


def test_rank_stale_foreground_loses_bonus(monkeypatch):
    # Hvis en enhed siger foreground=True men er holdt op med at pinge (baggrund,
    # transition-ping tabt), må den ikke beholde foreground-bonus i det uendelige.
    box = {"t": 0.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="away", interaction=True)
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    box["t"] = 50.0  # mobil pingede sidst ved t=0 (>35s) → stale foreground; desktop pinger videre
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=False)
    ranked = dp.rank("bjorn")
    assert ranked[0].device_key == "desk"


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


# ── Geolocation (opt-in) ────────────────────────────────────────────────────
def test_location_stored_and_in_summary(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="away",
                   interaction=True,
                   location={"lat": 55.86, "lon": 10.39, "label": "Toftegårdsvej, Svendborg",
                             "source": "gps", "precision": "precise"})
    st = dp._PRESENCE["bjorn"]["mob"]
    assert st.location and st.location["label"] == "Toftegårdsvej, Svendborg"
    assert "Toftegårdsvej, Svendborg" in dp.summary("bjorn")
    loc = dp.location_for("bjorn")
    assert loc["lat"] == 55.86 and loc["source"] == "gps"


def test_location_none_preserves_empty_clears(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="home",
                   interaction=False,
                   location={"lat": 55.0, "lon": 10.0, "label": "Et sted", "source": "ip",
                             "precision": "city"})
    # location=None (default) → bevar sidste kendte
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="home")
    assert dp._PRESENCE["bjorn"]["mob"].location is not None
    # location={} → brugeren slog det FRA → ryd
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="home",
                   location={})
    assert dp._PRESENCE["bjorn"]["mob"].location is None
    assert dp.location_for("bjorn") is None


def test_invalid_location_rejected(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="home",
                   location={"lat": 999.0, "lon": 10.0, "label": "Umulig"})
    # ugyldig lat → sanitize returnerer None → location ryddet (eksplicit {} semantik)
    assert dp._PRESENCE["bjorn"]["mob"].location is None


def test_rank_includes_registered_fcm_token_without_ping(monkeypatch):
    """Mikkel-scenariet: ingen aktivt ping, men en registreret FCM-token → rank()
    SKAL returnere den som nåbar fallback (ellers tom rank → invite-push fejler)."""
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    import core.services.device_tokens as dt
    monkeypatch.setattr(dt, "list_for_user", lambda uid: ["fcm-tok-1"] if uid == "mikkel" else [])
    ranked = dp.rank("mikkel")
    assert len(ranked) == 1
    assert ranked[0].device_key == "fcm-tok-1"
    assert ranked[0].reachable_via == "fcm"
    assert ranked[0].score > 0


def test_rank_does_not_duplicate_token_with_active_ping(monkeypatch):
    """En FCM-token der OGSÅ har et aktivt ping (device_key == token) må ikke
    tælles to gange; det aktive foreground-ping skal vinde."""
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    import core.services.device_tokens as dt
    monkeypatch.setattr(dt, "list_for_user", lambda uid: ["mob"])
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="home", interaction=True)
    ranked = dp.rank("bjorn")
    assert len(ranked) == 1
    assert ranked[0].score >= dp._FOREGROUND_BONUS
