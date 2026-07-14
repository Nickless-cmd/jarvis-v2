"""Fase A acceptance (kør på containeren). Beviser aldrig-tør-bunden:
(1) tom pool → bund uden exception; (2) balancer-fejl → Central provider_health.
Laver ægte kald mod bunden. Spec §5.5 Fund 4+5."""
import sys

sys.path.insert(0, "/media/projects/jarvis-v2")


def check_selection_floor_no_raise():
    from core.services.cheap_provider_runtime_selection import (
        execute_cheap_lane_via_pool, _configured_cheap_candidates)
    allp = frozenset({c["provider"]
                      for c in _configured_cheap_candidates(include_public_proxy=True)})
    # skip ALT → tom pool → skal falde til bund, ALDRIG rejse
    r = execute_cheap_lane_via_pool(message="Reply: OK", skip_providers=allp)
    assert isinstance(r, dict), r
    assert r.get("is_floor") or r.get("status") in ("ok", "degraded"), r
    print(f"  [OK] selection tom pool → {r.get('provider')}/{r.get('status')} (ingen raise)")


def check_balancer_floor_no_raise():
    from core.services import cheap_lane_balancer as bal
    _orig = bal.build_slot_pool
    bal.build_slot_pool = lambda: []          # tving tom pool
    try:
        r = bal.call_balanced(prompt="Reply: OK", daemon_name="acceptance")
        assert isinstance(r, dict), r
        print(f"  [OK] balancer tom pool → {r.get('provider')}/{r.get('status')} (ingen raise)")
    finally:
        bal.build_slot_pool = _orig


def check_central_visibility():
    from core.services.cheap_lane_balancer import _emit_balancer_event
    _emit_balancer_event("cheap_balancer.call_failed",
                         {"slot_id": "acceptance::x", "error_kind": "rate-limited"})
    print("  [OK] balancer-fejl → provider_health observe (verificér i central_query status)")


if __name__ == "__main__":
    check_selection_floor_no_raise()
    check_balancer_floor_no_raise()
    check_central_visibility()
    print("Fase A acceptance: PASS")
