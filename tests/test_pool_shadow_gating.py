"""Task 15 — shadow-safety regression guard.

Single regression file proving that with ALL FOUR pool/fallback flags forced
OFF, the new (Task 8/12/13/14 + non-visible fallback) behavior is completely
inert. If any of these FAIL, a flag-off code path has started to change
behavior — a real shadow-safety leak, not a test nit.

Flags covered (all default OFF):
  * cheap_pool_multiprofile_enabled      -> _flag_multiprofile()
  * non_visible_ollama_fallback_enabled  -> _fallback_enabled()
  * cheap_pool_adaptive_quota_enabled    -> _flag_adaptive_quota()
  * non_visible_rate_cap_enabled         -> _rate_cap_enabled()
"""

import pytest


def test_multiprofile_off_yields_single_profile(monkeypatch):
    """build_slot_pool with _flag_multiprofile()->False must NOT materialize an
    account2 slot even when auth_profile_scan would report two ready profiles."""
    from core.services import cheap_lane_balancer as bal

    monkeypatch.setattr(bal, "_router_enabled_models", lambda: [
        {"provider": "groq", "model": "llama-x", "enabled": True,
         "lane": "cheap", "auth_profile": "default"}])
    # Scan WOULD offer two profiles — the OFF flag must ignore it entirely.
    monkeypatch.setattr(
        "core.services.auth_profile_scan.ready_profiles_for",
        lambda provider: ["default", "account2"])
    monkeypatch.setattr(bal, "_credentials_ready", lambda p, a: True)
    monkeypatch.setattr(bal, "_flag_multiprofile", lambda: False)

    pool = bal.build_slot_pool()
    ids = {s.slot_id for s in pool}
    assert "groq::llama-x::default" in ids
    assert "groq::llama-x::account2" not in ids
    # No non-default profile leaked for the flagged provider (groq). Other
    # providers may carry a config-pinned profile via static injection — that is
    # not multiprofile expansion, so we scope the invariant to groq.
    groq_profiles = {s.auth_profile for s in pool if s.provider == "groq"}
    assert groq_profiles <= {"", "default"}


def test_fallback_off_reraises(monkeypatch):
    """run_non_visible_with_fallback with _fallback_enabled()->False must re-raise
    the primary error and never touch the cheap pool."""
    from core.services import non_visible_fallback as f

    monkeypatch.setattr(f, "_fallback_enabled", lambda: False)
    monkeypatch.setattr(
        f, "execute_cheap_lane_via_pool",
        lambda **k: pytest.fail("pool must NOT be called when fallback flag is OFF"))

    def boom():
        raise RuntimeError("primary-ollama-failed")

    with pytest.raises(RuntimeError, match="primary-ollama-failed"):
        f.run_non_visible_with_fallback(
            message="x", primary_call=boom, run_is_autonomous=True)


def test_adaptive_off_no_learning(monkeypatch):
    """_register_failure with _flag_adaptive_quota()->False must never set
    daily_observed nor stale_until_daily_reset, even on repeated genuine
    'quota exhausted daily' events."""
    from core.services import cheap_lane_balancer as bal

    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: False)
    st = bal.SlotState(slot_id="groq::x::default")
    for i in range(5):
        bal._register_failure(
            st, "quota exhausted daily", now=1000.0 + i,
            observed_used=1, config_daily=100)
    assert st.daily_observed is None
    assert st.stale_until_daily_reset is False
    assert st.quota_429_count == 0


def test_rate_cap_off_not_consulted(monkeypatch):
    """With _rate_cap_enabled()->False, run_non_visible_with_fallback must NOT
    consult non_visible_rate_cap.allow (it is behind the flag short-circuit)."""
    from core.services import non_visible_fallback as f
    from core.services import non_visible_rate_cap as rc

    monkeypatch.setattr(f, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(f, "_rate_cap_enabled", lambda: False)
    monkeypatch.setattr(
        rc, "allow",
        lambda *a, **k: pytest.fail("rate_cap.allow must NOT be called when flag OFF"))
    monkeypatch.setattr(
        f, "execute_cheap_lane_via_pool",
        lambda **k: {"lane": "cheap", "provider": "groq"})

    def boom():
        raise RuntimeError("q")

    r = f.run_non_visible_with_fallback(
        message="x", primary_call=boom, run_is_autonomous=True)
    assert r["lane"] == "cheap"


# ---------------------------------------------------------------------------
# Part B — light Central observability fires ONLY on the ON path (wiring proof).
# ---------------------------------------------------------------------------


def test_fallback_fired_observes_on_on_path(monkeypatch):
    """When the cheap-pool fallback arm fires (flag ON), a self-safe
    _observe_central call emits event=non_visible_fallback_fired."""
    from core.services import non_visible_fallback as f

    seen = []
    monkeypatch.setattr(f, "_observe_central", lambda payload: seen.append(payload))
    monkeypatch.setattr(f, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(f, "execute_cheap_lane_via_pool",
                        lambda **k: {"lane": "cheap", "provider": "groq"})

    def boom():
        raise RuntimeError("q")

    f.run_non_visible_with_fallback(
        message="x", primary_call=boom, run_is_autonomous=True)
    assert any(p.get("event") == "non_visible_fallback_fired" for p in seen)


def test_no_observe_on_off_path(monkeypatch):
    """With the fallback flag OFF the observability MUST stay silent — no
    observe call on the OFF path."""
    from core.services import non_visible_fallback as f

    seen = []
    monkeypatch.setattr(f, "_observe_central", lambda payload: seen.append(payload))
    monkeypatch.setattr(f, "_fallback_enabled", lambda: False)

    def boom():
        raise RuntimeError("q")

    with pytest.raises(RuntimeError):
        f.run_non_visible_with_fallback(
            message="x", primary_call=boom, run_is_autonomous=True)
    assert seen == []
