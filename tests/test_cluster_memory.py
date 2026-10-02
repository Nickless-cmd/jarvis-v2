"""E2E tests for the memory/maintenance cluster-daemon family #6 (spec 2026-07-14).

Consolidation contract:
* the family runs its event-gate ONCE for the LLM tier — a single gated member
  (council_memory, a former cooldown-timer cheap-LLM call) now sits behind the
  family's one should_generative_fire("cluster_memory", …) call;
* when the gate fires, the gated member dispatches to the SAME tick the old daemon
  used (still self-throttling on its 10-min cooldown);
* the SEVEN non-LLM maintenance members (memory_write_queue, memory_decay,
  memory_pruning, memory_maintenance, memory_safeguard, selective_consolidation,
  associative_recall) run UNCONDITIONALLY every tick, independent of the gate, each
  self-throttling on its own internal cadence;
* memory_write_queue is LOAD-BEARING + frequent and MUST keep draining every tick;
* a member error never crashes the family (memory maintenance must be robust —
  one failing member never blocks the other seven); the tick never raises;
* the 8 old memory daemons are RETIRED and cluster_memory is registered LIVE.

Patches target the NEW module cluster_daemon_families (not cluster_daemon).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import core.services.cluster_daemon_families as cdmf

# The 7 NON-LLM members and the (module, fn) each runs unconditionally.
_NONLLM_TICKS = {
    "memory_write_queue": ("core.services.memory_write_queue", "tick_memory_write_queue_daemon"),
    "memory_decay": ("core.services.memory_decay_daemon", "tick_memory_decay_daemon"),
    "memory_pruning": ("core.services.memory_pruning_daemon", "tick_memory_pruning_daemon"),
    "memory_maintenance": ("core.services.memory_maintenance_daemon", "tick_memory_maintenance_daemon"),
    "memory_safeguard": ("core.services.daemon_memory_safeguard", "run"),
    "selective_consolidation": ("core.services.selective_consolidation_daemon", "tick_selective_consolidation_daemon"),
    "associative_recall": ("core.services.associative_recall", "tick_associative_recall"),
    "candidate_review_digest": ("core.services.candidate_review_digest", "tick_candidate_review_digest"),
}

_SNAP = {"council_entry_count": 5, "recent_context": "seneste samtale"}


# ---------------------------------------------------------------------------
# NUL gatede medlemmer siden 2/10-2026 (raadet pensioneret)
# ---------------------------------------------------------------------------


def test_familien_har_ingen_gatede_medlemmer_laengere():
    """Raadet var familiens ENESTE gatede LLM-medlem.

    Foer 2/10-2026 stod her `== {"council_memory"}`. Da raadet blev pensioneret
    (32 vaerktoejs-kald nogensinde, 15 af dem fejlede, intet siden 10/9) havde
    gaten ingenting at gate. De otte NON-LLM vedligeholdelses-medlemmer koeres
    ubetinget af `tick_cluster_memory` og er uberoerte — det daekkes nedenfor.
    """
    fam = cdmf.build_memory_family()
    assert fam.family_name == "cluster_memory"
    assert [m.name for m in fam.members] == []


def test_uden_medlemmer_spoerges_den_generative_gate_slet_ikke():
    """Maalt, ikke antaget: med nul medlemmer naas `should_generative_fire` ALDRIG.

    NB en uoverensstemmelse fundet samtidig: resultatet rapporterer
    `gate_calls == 1`, selv om gate-funktionen blev kaldt NUL gange. Familien
    siger altsaa at den gatede uden at have gjort det. Det pinnes IKKE her som
    forventet adfaerd — det er en rapporterings-fejl der hoerer i sit eget spor.
    """
    fam = cdmf.build_memory_family()
    kald = {"n": 0}

    def _fire(name, signals, **kw):
        kald["n"] += 1
        return True

    with ExitStack() as stack:
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", side_effect=_fire))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert kald["n"] == 0, "gaten blev spurgt, men der er ingen medlemmer at gate"
    assert result["members_ran"] == []


def _patch_nonllm_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _NONLLM_TICKS.items():
        m = MagicMock(return_value={"ran": True, "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    # memory_decay's live() also consults maybe_rediscover — stub it to no
    # rediscovery so the member doesn't reach into the thought stream.
    stack.enter_context(patch("core.services.memory_decay_daemon.maybe_rediscover", return_value={}))
    return mocks


# ---------------------------------------------------------------------------
# ONE gate for the whole family's LLM tier (the load-reduction invariant)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Dispatch — gated member runs iff the family gate fires
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Non-LLM members run UNCONDITIONALLY (via the entry-point), gate or no gate
# ---------------------------------------------------------------------------


def test_all_seven_nonllm_members_run_when_gate_fires():
    with ExitStack() as stack:
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_memory_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_memory()

    for member, m in nonllm.items():
        assert m.call_count == 1, f"{member} must run"
        assert member in result["members_ran"]


def test_nonllm_members_run_even_when_gate_does_not_fire():
    """The load-bearing maintenance — write-queue drain, decay, pruning, dedup,
    safeguard, consolidation, recall — must run every tick regardless of the
    generative family gate."""
    with ExitStack() as stack:
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_memory_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_memory()

    # 2/10-2026: her stod `assert result["fired"] is False`. Den kan ikke
    # arrangeres laengere, og grunden er vaerd at kende: familien har nul
    # medlemmer siden raadet blev pensioneret, saa `_aggregate_signals` giver
    # tomt, og `ClusterDaemon._gate_fires` har en fail-open — «if not agg:
    # return True» — der fyrer UDEN at spoerge `should_generative_fire`.
    # Resultatet melder derfor `fired: True` og `gate_calls: 1` selv om gaten
    # blev spurgt NUL gange. Virkningen er harmloes (medlems-loekken er tom),
    # men RAPPORTEN er forkert. `cluster_daemon.py` er faelles for alle
    # familier, saa den roeres ikke herfra — det er sit eget spor.
    #
    # Det testen faktisk daekker staar uaendret: vedligeholdelsen koerer hver
    # tik uanset den generative gate, fordi den gaar gennem
    # `tick_cluster_memory` og ikke gennem familiens gate.
    for member, m in nonllm.items():
        assert m.call_count == 1, f"{member} must run unconditionally"
        assert member in result["members_ran"]


def test_all_eight_members_run_in_one_tick():
    with ExitStack() as stack:
        _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_memory_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_memory()

    # 2/10-2026: ni -> otte. Raadet var det niende og er pensioneret.
    assert set(result["members_ran"]) == set(_NONLLM_TICKS)
    assert len(result["members_ran"]) == 8


# ---------------------------------------------------------------------------
# memory_write_queue is LOAD-BEARING + frequent → drains every tick
# ---------------------------------------------------------------------------


def test_memory_write_queue_drains_every_tick():
    with ExitStack() as stack:
        nonllm = _patch_nonllm_ticks(stack)
        # gate does NOT fire — the drain must still happen
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_memory_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_memory()

    assert nonllm["memory_write_queue"].call_count == 1, "write queue must drain every tick"
    assert "memory_write_queue" in result["members_ran"]
    assert result["outputs"]["memory_write_queue"] == {"ran": True, "member": "memory_write_queue"}


# ---------------------------------------------------------------------------
# Each member self-throttles on its OWN internal cadence
# ---------------------------------------------------------------------------


def test_members_self_throttle_when_cadence_not_elapsed():
    """write_queue (120s), selective_consolidation (24h) and maintenance (12h)
    return their throttled marker when their own cadence window hasn't elapsed —
    proving the family relies on each member's internal self-throttle."""
    from datetime import UTC, datetime

    import core.services.memory_maintenance_daemon as mmd
    import core.services.memory_write_queue as mwq
    import core.services.selective_consolidation_daemon as scd

    now = datetime.now(UTC)
    mwq._last_tick_at = now
    scd._last_tick_at = now
    mmd._last_tick_at = now

    assert cdmf._mem_write_queue_live({})["reason"] == "cadence"
    assert cdmf._mem_selective_consolidation_live({})["reason"] == "cadence_not_reached"
    assert cdmf._mem_maintenance_live({})["reason"] == "cadence"


# ---------------------------------------------------------------------------
# Load-bearing rediscovery injection preserved
# ---------------------------------------------------------------------------


def test_rediscovery_fragment_injected_when_decay_surfaces_one():
    """memory_decay member: when maybe_rediscover surfaces a near-forgotten record,
    it is injected into the thought stream and echoed in the member output."""
    with ExitStack() as stack:
        stack.enter_context(patch("core.services.memory_decay_daemon.tick_memory_decay_daemon", return_value={"decayed": True}))
        stack.enter_context(patch("core.services.memory_decay_daemon.maybe_rediscover", return_value={"summary": "en gammel tanke"}))
        inject = MagicMock()
        stack.enter_context(patch("core.services.thought_stream_daemon.inject_rediscovery_fragment", inject))
        out = cdmf._mem_decay_live({})

    inject.assert_called_once_with("en gammel tanke")
    assert out.get("rediscovered") == "en gammel tanke"


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_nonllm_member_error_isolated_and_siblings_still_run():
    with ExitStack() as stack:
        nonllm = _patch_nonllm_ticks(stack)
        nonllm["memory_pruning"].side_effect = RuntimeError("pruning boom")
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_memory_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_memory()

    assert "memory_pruning" in result["member_errors"]
    assert "boom" in result["member_errors"]["memory_pruning"]
    # every sibling still ran despite the one member's error
    assert nonllm["memory_write_queue"].call_count == 1
    assert nonllm["associative_recall"].call_count == 1
    assert "memory_write_queue" in result["members_ran"]
    assert "selective_consolidation" in result["members_ran"]


def test_entrypoint_never_raises_on_broken_family():
    with patch.object(cdmf, "memory_family", side_effect=RuntimeError("family down")), \
         patch.object(cdmf, "_collect_memory_snapshot", return_value=_SNAP):
        result = cdmf.tick_cluster_memory()
    assert result["family"] == "cluster_memory"
    assert result["gate_calls"] == 1
    assert "__entry__" in result["member_errors"]


def test_entrypoint_runs_live_by_default():
    """tick_cluster_memory defaults to LIVE (shadow=False) so it produces."""
    with ExitStack() as stack:
        _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_memory_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_memory()

    assert result["shadow"] is False


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_memory_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_memory" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_memory"]
    assert entry["enabled"] is True
    assert "memory" in entry["description"]


def test_seven_old_memory_daemons_retired():
    from core.services import daemon_manager as dm

    retired = [
        "memory_decay", "memory_pruning", "memory_maintenance", "memory_safeguard",
        "selective_consolidation", "associative_recall",
        "memory_write_queue",  # council_memory FJERNET 2/10 — posten findes ikke mere
    ]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert "cluster_memory" in dm._REGISTRY[name]["description"], f"{name} desc must point to cluster_memory"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
