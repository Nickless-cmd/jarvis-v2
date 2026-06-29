"""Unit tests for provider_circuit_breaker."""
from __future__ import annotations

import time
from unittest.mock import patch

import core.services.provider_circuit_breaker as cb


def setup_function(_fn):
    cb.reset_all()


def test_no_failures_does_not_skip():
    assert cb.should_skip("p", "m") is False


def test_under_threshold_does_not_open():
    cb.record_failure("p", "m")
    cb.record_failure("p", "m")
    assert cb.should_skip("p", "m") is False


def test_threshold_opens_breaker():
    for _ in range(3):
        cb.record_failure("p", "m")
    assert cb.should_skip("p", "m") is True


def test_success_clears_breaker():
    for _ in range(3):
        cb.record_failure("p", "m")
    assert cb.should_skip("p", "m") is True
    cb.record_success("p", "m")
    assert cb.should_skip("p", "m") is False


def test_breaker_isolated_per_provider_model():
    for _ in range(3):
        cb.record_failure("p1", "m1")
    assert cb.should_skip("p1", "m1") is True
    assert cb.should_skip("p2", "m2") is False
    assert cb.should_skip("p1", "m2") is False


def test_empty_provider_or_model_no_op():
    cb.record_failure("", "m")
    cb.record_failure("p", "")
    assert cb.should_skip("", "m") is False
    assert cb.should_skip("p", "") is False


def test_breaker_state_observability():
    cb.record_failure("p", "m")
    cb.record_failure("p", "m")
    state = cb.breaker_state()
    assert state["recent_failures"]
    assert state["recent_failures"][0]["failure_count"] == 2
    assert state["open_breakers"] == []


def test_open_state_in_observability():
    for _ in range(3):
        cb.record_failure("p", "m")
    state = cb.breaker_state()
    assert len(state["open_breakers"]) == 1
    assert state["open_breakers"][0]["provider"] == "p"
    assert state["open_breakers"][0]["retry_in_seconds"] > 0


def test_cooldown_expires_after_open_duration():
    for _ in range(3):
        cb.record_failure("p", "m")
    assert cb.should_skip("p", "m") is True
    # Fake time passing past the cooldown
    with patch.object(cb, "_OPEN_DURATION_SECONDS", 0.01):
        time.sleep(0.02)
        assert cb.should_skip("p", "m") is False


# ═════════════════════════════════════════════════════════════════════════════
# DELT per-PROVIDER breaker (spec §4 S6, §11.2) — keyed kun på provider_id.
# ═════════════════════════════════════════════════════════════════════════════


def setup_pp(_fn=None):
    cb.pp_reset_all()


def test_pp_opens_after_n_consecutive_failures():
    """Breakeren åbner FØRST efter threshold (default 4) fejl i træk."""
    cb.pp_reset_all()
    # Brug en deterministisk monotonic-tid så vinduet ikke spiller ind.
    now = 1000.0
    for i in range(3):
        opened = cb._PP.record_failure("prov", now=now + i)
        assert opened is False, f"fejl {i+1}/4 må IKKE åbne endnu"
    assert cb._PP.is_open("prov", now=now + 3.5) is False
    opened = cb._PP.record_failure("prov", now=now + 3)
    assert opened is True, "4. fejl i træk skal åbne breakeren (frisk kant)"
    assert cb._PP.is_open("prov", now=now + 3.5) is True


def test_pp_open_returns_true_only_once_as_edge():
    """record_failure returnerer True KUN på den friske open-kant, ikke igen."""
    cb.pp_reset_all()
    now = 0.0
    edges = [cb._PP.record_failure("p", now=now + i) for i in range(6)]
    # Præcis ÉN True (den friske kant ved 4. fejl).
    assert edges.count(True) == 1
    assert edges[3] is True


def test_pp_half_open_probe_then_close_on_success():
    """Efter cooldown → half-open: is_open slipper én probe (False); success lukker."""
    cb.pp_reset_all()
    cb.pp_configure("p", threshold=4, cooldown_s=60.0)
    t = 100.0
    for i in range(4):
        cb._PP.record_failure("p", now=t + i)
    assert cb._PP.is_open("p", now=t + 5) is True
    # Cooldown udløbet → half-open probe slipper igennem (False).
    assert cb._PP.is_open("p", now=t + 5 + 61) is False
    # Probe LYKKES → breakeren lukker (frisk close-kant).
    closed = cb._PP.record_success("p")
    assert closed is True
    assert cb._PP.is_open("p", now=t + 5 + 62) is False


def test_pp_half_open_probe_failure_reopens():
    """En half-open probe der FEJLER genåbner breakeren (ny cooldown)."""
    cb.pp_reset_all()
    cb.pp_configure("p", threshold=4, cooldown_s=30.0)
    t = 0.0
    for i in range(4):
        cb._PP.record_failure("p", now=t + i)
    # Udløs half-open.
    assert cb._PP.is_open("p", now=t + 40) is False
    # Probe FEJLER → genåbn.
    cb._PP.record_failure("p", now=t + 40)
    assert cb._PP.is_open("p", now=t + 41) is True


def test_pp_success_resets_consecutive():
    """Et success midt i en byge nulstiller consecutive-tælleren."""
    cb.pp_reset_all()
    cb.pp_configure("p", threshold=4, cooldown_s=60.0)
    cb._PP.record_failure("p", now=0)
    cb._PP.record_failure("p", now=1)
    cb._PP.record_success("p")
    # Efter reset kræves 4 NYE fejl i træk.
    for i in range(3):
        assert cb._PP.record_failure("p", now=10 + i) is False
    assert cb._PP.record_failure("p", now=13) is True


def test_pp_isolated_per_provider_id():
    """Breakeren er isoleret pr. provider_id."""
    cb.pp_reset_all()
    for i in range(4):
        cb._PP.record_failure("dead", now=i)
    assert cb._PP.is_open("dead", now=5) is True
    assert cb._PP.is_open("healthy", now=5) is False


def test_pp_window_resets_stale_consecutive():
    """Fejl ældre end vinduet nulstiller den consecutive-tæller (ingen falsk-åben)."""
    cb.pp_reset_all()
    cb.pp_configure("p", threshold=4, cooldown_s=60.0, window_s=10.0)
    cb._PP.record_failure("p", now=0)
    cb._PP.record_failure("p", now=1)
    cb._PP.record_failure("p", now=2)
    # Næste fejl er LANGT uden for vinduet → tælleren nulstilles → ikke åben.
    opened = cb._PP.record_failure("p", now=100)  # window=10 < 98 gap
    assert opened is False
    assert cb._PP.is_open("p", now=101) is False


def test_pp_is_open_fail_open_on_unknown():
    """is_open for en ukendt provider → False (fail-open; bloker aldrig en sund)."""
    cb.pp_reset_all()
    assert cb.pp_is_open("never-seen") is False


def test_pp_public_helpers_observe_edges(monkeypatch):
    """pp_record_failure/_success observerer open/close-kanter til Centralen."""
    cb.pp_reset_all()
    observed: list[dict] = []

    class _FakeCentral:
        def observe(self, payload):
            observed.append(payload)

    monkeypatch.setattr("core.services.central_core.central",
                        lambda: _FakeCentral())
    # Default threshold = 4.
    for _ in range(3):
        assert cb.pp_record_failure("obs") is False
    assert not [o for o in observed if o.get("nerve") == "provider_circuit_open"]
    assert cb.pp_record_failure("obs") is True  # 4. → åbner
    opens = [o for o in observed if o.get("nerve") == "provider_circuit_open"]
    assert len(opens) == 1
    assert opens[0]["cluster"] == "stream"
    assert opens[0]["provider_id"] == "obs"
    # Success → close-kant observeres.
    assert cb.pp_record_success("obs") is True
    closes = [o for o in observed if o.get("nerve") == "provider_circuit_close"]
    assert len(closes) == 1


def test_pp_reset_does_not_touch_provider_model_store():
    """pp_reset_all rører IKKE den gamle (provider, model)-store (isolation)."""
    cb.reset_all()
    for _ in range(3):
        cb.record_failure("legacy", "modelx")
    assert cb.should_skip("legacy", "modelx") is True
    cb.pp_reset_all()  # kun per-provider-store
    assert cb.should_skip("legacy", "modelx") is True


def test_reset_all_clears_both_stores():
    """Den gamle reset_all() rydder NU også per-provider-store'en (delt modul)."""
    cb.reset_all()
    for i in range(4):
        cb._PP.record_failure("x", now=i)
    assert cb._PP.is_open("x", now=5) is True
    cb.reset_all()
    assert cb._PP.is_open("x", now=6) is False
