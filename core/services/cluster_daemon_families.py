"""Cluster-daemon FAMILIES — the second file of consolidated nerve-families.

``core/services/cluster_daemon.py`` holds the primitive (:class:`ClusterDaemon`,
:class:`ClusterMember`) plus families #1–#5. That file has reached the 1500-line
code-rule limit, so new families live here and import the primitive:

    from core.services.cluster_daemon import ClusterDaemon, ClusterMember

Same contract as families #2–#5 (see the primitive's module docstring):

* **One event-gate for the whole family.** The gated (LLM) tier checks the
  family's aggregate signals ONCE per tick via
  ``should_generative_fire(family_name, …)`` — N daemons that each check → 1.
* **Two tiers.** GATED LLM members sit behind that one gate; NON-LLM maintenance
  members run UNCONDITIONALLY every tick and self-throttle on their OWN internal
  cadence, so their load-bearing outputs never stall.
* **Self-safe.** A member error is captured, never propagated — the family (and
  the heartbeat) never crashes. ``tick_cluster_*`` never raises.
* **Central has authority.** Every gated tick is reported to Central via the
  primitive's ``_report_to_central``.

---------------------------------------------------------------------------
Family #6 — memory / maintenance
---------------------------------------------------------------------------

The MEMORY-MAINTENANCE family. Eight daemons that keep Jarvis' memory stores
healthy: decay/forgetting, pruning, MEMORY.md dedup, missed-save safeguard,
selective consolidation, associative recall, the async write queue, plus the one
LLM member (council_memory). Runs LIVE (prove-then-retire END STATE), replacing
the 8 old daemons. TWO tiers (mirrors the cognition family #5):

  * GATED / LLM member — ``council_memory`` — sits behind the family's ONE
    ``should_generative_fire("cluster_memory", …)`` gate. It was a cooldown-timed
    cheap-LLM similarity call; the family gives it the event-driven salience gate
    it lacked. When the gate fires its ``live`` dispatches to the old tick (which
    still self-throttles on its 10-min cooldown), so council.memory_injected keeps
    filling the heartbeat's ``council_memory`` context section.

  * NON-LLM members — the other 7 — have NO generative gate; each is a
    rules/DB-driven maintenance tick with its OWN internal cadence, run
    UNCONDITIONALLY every family tick (independent of the gate) so nothing stalls:
      - memory_decay (24h self-throttle) → daily salience decay + re-discovery.
        Load-bearing: rediscovery fragment injected into the thought stream.
      - memory_pruning (6h self-throttle) → archives salience<0.05 brain/private
        records ("learning to forget"). Was ORPHANED (registered, NO tick site
        anywhere) → the family gives it its FIRST live tick.
      - memory_maintenance (12h self-throttle) → MEMORY.md Tier-A auto-merge +
        Tier-B overlap flag (section-level dedup).
      - memory_safeguard (every tick) → post-hoc missed-save check; fires
        memory_safeguard.missed_save + a next-prompt nudge. Its old bare tick site
        imported a NON-EXISTENT ``tick_memory_safeguard_daemon`` (ImportError,
        swallowed) so it was effectively DEAD; the family calls the real ``run()``
        and restores it.
      - selective_consolidation (24h self-throttle) → archives bottom-(100-K)% of
        the day's records so only top-K% reaches long-term storage.
      - associative_recall (2-min self-adaptive) → decays/evicts active recall
        memories + scans for new candidates. Persists via recall_active_memories.
      - memory_write_queue (120s self-throttle) → LOAD-BEARING + FREQUENT: drains
        the deferred sensory/brain/sidecar write queue (non-blocking memory
        writes). Must keep draining — every family tick calls it so it does.

Self-safe throughout: a member error is captured into ``member_errors`` and never
propagated; memory maintenance is critical, so one failing member never blocks
the other seven.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from core.services.cluster_daemon import ClusterDaemon, ClusterMember, _iv_surface_observe

MEMORY_FAMILY = "cluster_memory"


# ---------------------------------------------------------------------------
# Shared snapshot (only the gated council_memory member needs gate signals)
# ---------------------------------------------------------------------------


def _collect_memory_snapshot() -> dict[str, Any]:
    """Gather the memory family's shared snapshot once per tick.

    Only the gated member (council_memory) needs a gate signal — its salience is
    the volume of council-log conclusions available to inject — plus a best-effort
    ``recent_context`` (recent chat) for the relevance LLM. The 7 non-LLM members
    self-collect inside their own ticks and need nothing here. Self-safe: degrades
    to neutral defaults on any error; the family still ticks.
    """
    snap: dict[str, Any] = {"council_entry_count": 0, "recent_context": ""}
    try:
        from core.services.council_memory_service import read_all_entries
        entries = read_all_entries() or []
        snap["council_entry_count"] = len(entries)
    except Exception:
        pass
    try:
        from core.services.chat_sessions import recent_chat_session_messages
        msgs = recent_chat_session_messages(limit=3) or []
        snap["recent_context"] = " ".join(str(m.get("content") or "") for m in msgs)[:400]
    except Exception:
        pass
    return snap


# ---------------------------------------------------------------------------
# GATED LLM member — council_memory
# ---------------------------------------------------------------------------


def _mem_council_signals(snap: dict) -> dict[str, float]:
    """council_memory gate signal: how much council history there is to weigh."""
    n = float(snap.get("council_entry_count", 0) or 0)
    return {"entries": min(n / 3.0, 1.0)}


def _mem_council_live(snap: dict) -> dict[str, Any]:
    from core.services.council_memory_daemon import tick_council_memory_daemon
    return tick_council_memory_daemon(recent_context=str(snap.get("recent_context", "")))


def build_memory_family() -> ClusterDaemon:
    """Construct the memory/maintenance cluster-daemon (family #6), LIVE.

    ONE gated LLM member (council_memory) behind the family gate. The seven
    NON-LLM maintenance members are run UNCONDITIONALLY by
    ``tick_cluster_memory``, not gated here.
    """
    return ClusterDaemon(
        family_name=MEMORY_FAMILY,
        cluster="cognition",
        collect_snapshot=_collect_memory_snapshot,
        members=[
            ClusterMember(
                name="council_memory",
                signals=_mem_council_signals,
                observe=_iv_surface_observe(
                    ("core.services.council_memory_daemon", "build_council_memory_surface"),
                    ("last_llm_call_at", "injected_count"),
                ),
                live=_mem_council_live,
            ),
        ],
    )


# Process-level singleton (keeps the family's gate baselines + Central trace
# continuous across heartbeat ticks, mirroring the other families).
_MEMORY_FAMILY: ClusterDaemon | None = None


def memory_family() -> ClusterDaemon:
    global _MEMORY_FAMILY
    if _MEMORY_FAMILY is None:
        _MEMORY_FAMILY = build_memory_family()
    return _MEMORY_FAMILY


# ---------------------------------------------------------------------------
# UNCONDITIONAL (non-LLM) maintenance member live dispatchers
# ---------------------------------------------------------------------------


def _mem_decay_live(_snap: dict) -> dict[str, Any]:
    """Daily decay + re-discovery. Replicates the old heartbeat influence site:
    tick the decay cycle, then surface one near-forgotten record into the thought
    stream. Injection failure is contained inside this member."""
    from core.services.memory_decay_daemon import maybe_rediscover, tick_memory_decay_daemon
    out = tick_memory_decay_daemon()
    try:
        rediscovered = maybe_rediscover()
        if rediscovered and rediscovered.get("summary"):
            from core.services.thought_stream_daemon import inject_rediscovery_fragment
            inject_rediscovery_fragment(rediscovered["summary"])
            if isinstance(out, dict):
                out = {**out, "rediscovered": rediscovered.get("summary")}
    except Exception:
        pass
    return out


def _mem_pruning_live(_snap: dict) -> dict[str, Any]:
    from core.services.memory_pruning_daemon import tick_memory_pruning_daemon
    return tick_memory_pruning_daemon()


def _mem_maintenance_live(_snap: dict) -> dict[str, Any]:
    from core.services.memory_maintenance_daemon import tick_memory_maintenance_daemon
    return tick_memory_maintenance_daemon()


def _mem_safeguard_live(_snap: dict) -> dict[str, Any]:
    """The safeguard daemon exposes ``run()`` (its old heartbeat site imported a
    non-existent ``tick_memory_safeguard_daemon`` and silently died on ImportError
    — the family restores it by calling the real function)."""
    from core.services.daemon_memory_safeguard import run as run_memory_safeguard
    return run_memory_safeguard()


def _mem_selective_consolidation_live(_snap: dict) -> dict[str, Any]:
    from core.services.selective_consolidation_daemon import tick_selective_consolidation_daemon
    return tick_selective_consolidation_daemon()


def _mem_associative_recall_live(_snap: dict) -> dict[str, Any]:
    from core.services.associative_recall import tick_associative_recall
    return tick_associative_recall()


def _mem_write_queue_live(_snap: dict) -> dict[str, Any]:
    """LOAD-BEARING + FREQUENT — drains the deferred write queue every 120s."""
    from core.services.memory_write_queue import tick_memory_write_queue_daemon
    return tick_memory_write_queue_daemon()


# (member_name, live_fn) in a stable order. memory_write_queue is placed FIRST so
# the load-bearing drain runs even under tight scheduling.
_MEMORY_UNCONDITIONAL: tuple[tuple[str, Callable[[dict], Any]], ...] = (
    ("memory_write_queue", _mem_write_queue_live),
    ("memory_decay", _mem_decay_live),
    ("memory_pruning", _mem_pruning_live),
    ("memory_maintenance", _mem_maintenance_live),
    ("memory_safeguard", _mem_safeguard_live),
    ("selective_consolidation", _mem_selective_consolidation_live),
    ("associative_recall", _mem_associative_recall_live),
)


def _run_memory_nonllm_members(snap: dict, result: dict[str, Any]) -> None:
    """Run the NON-LLM maintenance members UNCONDITIONALLY (independent of the
    family generative gate), self-safe. Each self-throttles on its own internal
    cadence; a member error is isolated into ``member_errors`` and NEVER
    propagated (memory maintenance must be robust — one failure never blocks the
    others); a successful run is recorded into ``members_ran``/``outputs``.
    """
    for name, fn in _MEMORY_UNCONDITIONAL:
        try:
            out = fn(snap)
            result["outputs"][name] = out
            result["members_ran"].append(name)
        except Exception as exc:
            result["member_errors"][name] = f"{type(exc).__name__}: {exc}"


def tick_cluster_memory(snapshot: dict | None = None, *, shadow: bool | None = None) -> dict[str, Any]:
    """Heartbeat entry-point for the memory/maintenance cluster-daemon family (#6).

    Runs LIVE by default (``shadow=False``) — the prove-then-retire end state
    replacing the 8 old memory daemons. Two-tier: the gated LLM member
    (council_memory) runs behind the ONE family gate via ``memory_family().tick()``;
    the seven NON-LLM maintenance members run UNCONDITIONALLY every tick (each has
    its own internal cadence). Self-safe: NEVER raises into the heartbeat.
    """
    try:
        snap = _collect_memory_snapshot() if snapshot is None else snapshot
        run_live = False if shadow is None else bool(shadow)
        result = memory_family().tick(snap, shadow=run_live)
        # Unconditional non-LLM maintenance members (independent of the gate above).
        _run_memory_nonllm_members(snap, result)
        return result
    except Exception as exc:  # never crash the heartbeat
        return {
            "family": MEMORY_FAMILY,
            "fired": False,
            "gate_calls": 1,
            "members_ran": [],
            "member_errors": {"__entry__": f"{type(exc).__name__}: {exc}"},
        }


# ===========================================================================
# Family #7 — aesthetic / curiosity (aesthetic_taste + curiosity)
# ===========================================================================
#
# The AESTHETIC-INTERPRETATION family (spec §"event-drevet"). Two daemons that
# read what Jarvis has been doing and produce taste/curiosity:
#
#   * aesthetic_taste — LLM interpretation daemon. Accumulates motif observations
#     across daemon outputs (aesthetic_sense.accumulate_from_daemon) + records
#     each visible run's style/mode; once ≥3 unique motifs AND ≥30 min since the
#     last insight it asks the cheap LLM "what does my taste say about me?" and
#     stores a one-sentence insight. It ALREADY had an internal
#     should_generative_fire("aesthetic_taste", …) gate on top of those two
#     self-throttle guards — the family replaces that per-daemon gate with its ONE
#     family gate (the daemon's tick is called with skip_event_gate=True). Runs
#     behind the family gate. LOAD-BEARING: build_taste_surface()/latest_insight
#     feed central_inner_life_digest, signal_surface_router, Mission Control's
#     living-mind taste-state, the meta_reflection snapshot and the heartbeat
#     influence trace.
#
#   * curiosity — RULES-based (no LLM). Scans the thought-stream fragment buffer
#     for gap patterns (question marks, "ved ikke", "hvad hvis", "…") and emits a
#     structured curiosity-cue label (cause-seeking / counterfactual / … ) — NOT
#     an LLM-confabulated sentence (teater-pass 2026-05-13). Self-throttles on a
#     5-min cadence. Run UNCONDITIONALLY every family tick. LOAD-BEARING:
#     build_curiosity_surface()/get_latest_curiosity() feed inheritance_seed,
#     central_inner_life_digest, signal_surface_router, Mission Control's
#     living-mind curiosity-state and the innervoice/affect snapshots + the
#     curiosity.detected event + the persisted curiosity_open_questions state.
#
# TWO tiers (mirrors the affect family #3): the LLM member (aesthetic_taste) sits
# behind the ONE family gate; the non-LLM member (curiosity) runs unconditionally
# and self-throttles. Self-safe: a member error is captured into ``member_errors``
# and never propagated; ``tick_cluster_aesthetic`` never raises into the heartbeat.

AESTHETIC_FAMILY = "cluster_aesthetic"


# ---------------------------------------------------------------------------
# Shared snapshot
# ---------------------------------------------------------------------------


def _feed_aesthetic_choice() -> None:
    """Record the latest visible run's style/mode into the taste daemon.

    Replicates the OLD heartbeat aesthetic_taste block's ``record_choice`` feeding
    (which is retired along with that block). Runs every family tick so the taste
    daemon's ``_choice_log`` / ``_choices_since_insight`` keep accumulating exactly
    as before — otherwise the daemon's gate signal and ``build_taste_surface``
    dominant-modes/choice-count would go stale. Fully self-safe: any error is
    swallowed; the family still ticks.
    """
    try:
        from core.services.aesthetic_taste_daemon import record_choice
        from core.services.inner_voice_daemon import get_inner_voice_daemon_state
        from core.runtime.db import recent_visible_runs

        iv_state = get_inner_voice_daemon_state() or {}
        iv_mode = str((iv_state.get("last_result") or {}).get("mode") or "")
        style_signals: list[str] = []
        last_runs = recent_visible_runs(limit=1) or []
        if last_runs:
            preview = str(last_runs[0].get("text_preview") or "")
            style_signals.append("short" if len(preview.split()) < 100 else "long")
            style_signals.append("code_heavy" if "```" in preview else "prose_heavy")
            dk = sum(1 for w in ["jeg", "er", "og", "det", "at", "en"] if w in preview.lower())
            style_signals.append("danish" if dk >= 2 else "english")
        record_choice(mode=iv_mode, style_signals=style_signals)
    except Exception:
        pass


def _collect_aesthetic_snapshot() -> dict[str, Any]:
    """Gather the aesthetic family's shared snapshot once per tick.

    The gated member (aesthetic_taste) needs its accumulated motif/choice counts
    as gate signals; the non-LLM member (curiosity) needs the thought-stream
    fragment buffer to scan for gaps. Feeding ``record_choice`` happens here (as
    the old heartbeat block did every tick) BEFORE the counts are read, so the
    gate signal reflects the freshly-recorded choice. Self-safe: degrades to
    neutral defaults on any error; the family still ticks.
    """
    _feed_aesthetic_choice()
    snap: dict[str, Any] = {
        "unique_motif_count": 0.0,
        "choices_since_insight": 0.0,
        "fragment_buffer": [],
    }
    try:
        import core.services.aesthetic_taste_daemon as _atd
        snap["unique_motif_count"] = float(len(getattr(_atd, "_accumulated_motifs", set()) or set()))
        snap["choices_since_insight"] = float(getattr(_atd, "_choices_since_insight", 0) or 0)
    except Exception:
        pass
    try:
        from core.services.thought_stream_daemon import build_thought_stream_surface
        snap["fragment_buffer"] = list((build_thought_stream_surface() or {}).get("fragment_buffer") or [])
    except Exception:
        pass
    return snap


# ---------------------------------------------------------------------------
# GATED LLM member — aesthetic_taste
# ---------------------------------------------------------------------------


def _aesthetic_taste_signals(snap: dict) -> dict[str, float]:
    """aesthetic_taste gate signals: how much taste-evidence has accumulated.

    Mirrors the daemon's own (now family-gated) internal gate signal — unique
    motif volume and choices seen since the last insight — normalised to 0-1 for
    the family gate.
    """
    motifs = float(snap.get("unique_motif_count", 0.0) or 0.0)
    choices = float(snap.get("choices_since_insight", 0.0) or 0.0)
    return {
        "unique_motif_count": max(0.0, min(1.0, motifs / 3.0)),
        "choices_since_insight": max(0.0, min(1.0, choices / 5.0)),
    }


def _aesthetic_taste_live(_snap: dict) -> dict[str, Any]:
    """The family gate already fired → skip the daemon's per-daemon event-gate.

    The daemon's motif-threshold + 30-min time-gate self-throttle still apply, so
    the SAME insight cadence and ALL its outputs (build_taste_surface /
    latest_insight, the private-brain taste record, cognitive_taste.insight_noted
    and the heartbeat trigger) are preserved."""
    from core.services.aesthetic_taste_daemon import tick_taste_daemon
    return tick_taste_daemon(skip_event_gate=True)


def build_aesthetic_family() -> ClusterDaemon:
    """Construct the aesthetic/curiosity cluster-daemon (family #7), LIVE.

    ONE gated LLM member (aesthetic_taste) behind the family gate. The single
    NON-LLM member (curiosity) is run UNCONDITIONALLY by
    ``tick_cluster_aesthetic``, not gated here.
    """
    return ClusterDaemon(
        family_name=AESTHETIC_FAMILY,
        cluster="cognition",
        collect_snapshot=_collect_aesthetic_snapshot,
        members=[
            ClusterMember(
                name="aesthetic_taste",
                signals=_aesthetic_taste_signals,
                observe=_iv_surface_observe(
                    ("core.services.aesthetic_taste_daemon", "build_taste_surface"),
                    ("latest_insight", "unique_motif_count"),
                ),
                live=_aesthetic_taste_live,
            ),
        ],
    )


# Process-level singleton (keeps the family's gate baselines + Central trace
# continuous across heartbeat ticks, mirroring the other families).
_AESTHETIC_FAMILY: ClusterDaemon | None = None


def aesthetic_family() -> ClusterDaemon:
    global _AESTHETIC_FAMILY
    if _AESTHETIC_FAMILY is None:
        _AESTHETIC_FAMILY = build_aesthetic_family()
    return _AESTHETIC_FAMILY


# ---------------------------------------------------------------------------
# UNCONDITIONAL (non-LLM) member — curiosity
# ---------------------------------------------------------------------------


def _aesthetic_curiosity_live(snap: dict) -> dict[str, Any]:
    """Rules-based gap scan over the thought-stream fragment buffer. Self-throttles
    on its own 5-min cadence; no LLM, no family gate. Preserves all its outputs
    (build_curiosity_surface / get_latest_curiosity, the private-brain
    curiosity-signal record, the curiosity.detected event and the persisted
    curiosity_open_questions state)."""
    from core.services.curiosity_daemon import tick_curiosity_daemon
    return tick_curiosity_daemon(list(snap.get("fragment_buffer") or []))


# (member_name, live_fn) in a stable order.
_AESTHETIC_UNCONDITIONAL: tuple[tuple[str, Callable[[dict], Any]], ...] = (
    ("curiosity", _aesthetic_curiosity_live),
)


def _run_aesthetic_nonllm_members(snap: dict, result: dict[str, Any]) -> None:
    """Run the NON-LLM member(s) UNCONDITIONALLY (independent of the family
    generative gate), self-safe. Each self-throttles on its own internal cadence;
    a member error is isolated into ``member_errors`` and NEVER propagated; a
    successful run is recorded into ``members_ran``/``outputs``.
    """
    for name, fn in _AESTHETIC_UNCONDITIONAL:
        try:
            out = fn(snap)
            result["outputs"][name] = out
            result["members_ran"].append(name)
        except Exception as exc:
            result["member_errors"][name] = f"{type(exc).__name__}: {exc}"


def tick_cluster_aesthetic(snapshot: dict | None = None, *, shadow: bool | None = None) -> dict[str, Any]:
    """Heartbeat entry-point for the aesthetic/curiosity cluster-daemon family (#7).

    Runs LIVE by default (``shadow=False``) — the prove-then-retire end state
    replacing the aesthetic_taste + curiosity daemons. Two-tier: the gated LLM
    member (aesthetic_taste) runs behind the ONE family gate via
    ``aesthetic_family().tick()``; the NON-LLM member (curiosity) runs
    UNCONDITIONALLY every tick (its own 5-min cadence). Self-safe: NEVER raises
    into the heartbeat.
    """
    try:
        snap = _collect_aesthetic_snapshot() if snapshot is None else snapshot
        run_live = False if shadow is None else bool(shadow)
        result = aesthetic_family().tick(snap, shadow=run_live)
        # Unconditional non-LLM member(s) (independent of the gate above).
        _run_aesthetic_nonllm_members(snap, result)
        return result
    except Exception as exc:  # never crash the heartbeat
        return {
            "family": AESTHETIC_FAMILY,
            "fired": False,
            "gate_calls": 1,
            "members_ran": [],
            "member_errors": {"__entry__": f"{type(exc).__name__}: {exc}"},
        }


# ===========================================================================
# Family #8 — relation (user_model + communication_guard + relation_map_refresh)
# ===========================================================================
#
# The RELATION family (spec §"event-drevet" correction #3). Three daemons that
# keep Jarvis' model of, and conduct toward, the people he talks to:
#
#   * user_model — LLM interpretation daemon (Theory of Mind). Analyses recent
#     visible user messages (communication style, question-heaviness, avg length)
#     and asks the cheap LLM "what do I sense about the user?", storing a
#     one-to-two-sentence first-person inference. It ALREADY had an internal
#     should_generative_fire("user_model", …) gate on top of its 10-min cadence
#     guard — the family replaces THAT per-daemon gate with its ONE family gate
#     (the daemon's tick is called with skip_event_gate=True; its 10-min cadence
#     guard still applies). Spec correction #3: this LLM interpretation is a
#     DELIBERATE keep — stripping it would be a reduction of Jarvis' theory-of-mind
#     — so user_model stays an LLM member BEHIND the family gate, never demoted to
#     rules. Runs behind the family gate. LOAD-BEARING: build_user_model_surface()/
#     model_summary feeds central_soul_digest, central_inner_life_digest,
#     signal_surface_router and Mission Control's living-mind user-model state; it
#     also emits the user_model.updated event + a private-brain user-model-signal
#     record.
#
#   * communication_guard — RULES-based (no LLM). The godnat-split guard: every
#     tick it sweeps expired TTL communication-triggers (cleanup_expired) and logs
#     the active-trigger count. Self-throttles at the heartbeat cadence (it is a
#     cheap cleanup; no internal timer). Run UNCONDITIONALLY every family tick.
#     LOAD-BEARING: keeps the active trigger set from leaking stale phrases into
#     communication_guard.prompt_section() / guard_channel_text scrubbing.
#
#   * relation_map_refresh — RULES-based (no LLM). Refreshes the relation map:
#     bumps the primary user's last_seen and re-stamps stale (>12h) secondary-user
#     theory-of-mind snapshots. Self-throttles per-user via the 12h staleness
#     threshold (a re-run inside the window refreshes nothing). Run UNCONDITIONALLY
#     every family tick. LOAD-BEARING: persists relation-map state and emits the
#     relation_map.refresh_tick event; build_relation_map_surface() reads that
#     state for Mission Control.
#
# TWO tiers (mirrors families #6/#7): the ONE LLM member (user_model) sits behind
# the ONE family gate; the two non-LLM members (communication_guard,
# relation_map_refresh) run unconditionally and self-throttle. Self-safe: a member
# error is captured into ``member_errors`` and never propagated;
# ``tick_cluster_relation`` never raises into the heartbeat.

RELATION_FAMILY = "cluster_relation"

_VISIBLE_LANES = {"visible", "primary"}


# ---------------------------------------------------------------------------
# Shared snapshot
# ---------------------------------------------------------------------------


def _collect_relation_snapshot() -> dict[str, Any]:
    """Gather the relation family's shared snapshot once per tick.

    The gated member (user_model) needs recent visible user messages both as its
    gate signal (interaction volume/shape) AND as the input to its LLM analysis —
    collected here ONCE so the gate decision and the generation see the same
    messages (the old daemon self-fetched with an empty list; the family fetches
    identically and passes them in). The two non-LLM members self-collect inside
    their own ticks and need nothing here. Self-safe: degrades to neutral defaults
    on any error; the family still ticks.
    """
    snap: dict[str, Any] = {
        "user_messages": [],
        "message_count": 0.0,
        "avg_message_length": 0.0,
        "question_ratio": 0.0,
    }
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=10) or []
        messages = [
            str(r.get("text_preview") or "")
            for r in runs
            if str(r.get("lane") or "").lower() in _VISIBLE_LANES and r.get("text_preview")
        ]
        snap["user_messages"] = messages
        if messages:
            lengths = [len(m) for m in messages]
            snap["message_count"] = float(len(messages))
            snap["avg_message_length"] = float(sum(lengths) / len(lengths))
            q = sum(1 for m in messages if "?" in m)
            snap["question_ratio"] = float(q) / float(len(messages))
    except Exception:
        pass
    return snap


# ---------------------------------------------------------------------------
# GATED LLM member — user_model
# ---------------------------------------------------------------------------


def _relation_user_model_signals(snap: dict) -> dict[str, float]:
    """user_model gate signals: how much (and what shape of) user interaction has
    accumulated. Mirrors the daemon's own (now family-gated) internal gate signal —
    message volume, average message length and question-ratio — normalised to 0-1
    for the family gate."""
    count = float(snap.get("message_count", 0.0) or 0.0)
    avg_len = float(snap.get("avg_message_length", 0.0) or 0.0)
    q_ratio = float(snap.get("question_ratio", 0.0) or 0.0)
    return {
        "message_count": max(0.0, min(1.0, count / 10.0)),
        "avg_message_length": max(0.0, min(1.0, avg_len / 100.0)),
        "question_ratio": max(0.0, min(1.0, q_ratio)),
    }


def _relation_user_model_live(snap: dict) -> dict[str, Any]:
    """The family gate already fired → skip the daemon's per-daemon event-gate.

    The daemon's 10-min cadence guard still applies, and the LLM theory-of-mind
    interpretation (spec correction #3: a deliberate keep) is fully preserved, so
    ALL its outputs (build_user_model_surface / model_summary, the private-brain
    user-model-signal record and the user_model.updated event) are unchanged. The
    recent user messages collected in the shared snapshot are passed in so the
    generation sees exactly the messages the gate weighed."""
    from core.services.user_model_daemon import tick_user_model_daemon
    return tick_user_model_daemon(list(snap.get("user_messages") or []), skip_event_gate=True)


def build_relation_family() -> ClusterDaemon:
    """Construct the relation cluster-daemon (family #8), LIVE.

    ONE gated LLM member (user_model) behind the family gate. The two NON-LLM
    members (communication_guard, relation_map_refresh) are run UNCONDITIONALLY by
    ``tick_cluster_relation``, not gated here.
    """
    return ClusterDaemon(
        family_name=RELATION_FAMILY,
        cluster="cognition",
        collect_snapshot=_collect_relation_snapshot,
        members=[
            ClusterMember(
                name="user_model",
                signals=_relation_user_model_signals,
                observe=_iv_surface_observe(
                    ("core.services.user_model_daemon", "build_user_model_surface"),
                    ("model_summary", "last_generated_at"),
                ),
                live=_relation_user_model_live,
            ),
        ],
    )


# Process-level singleton (keeps the family's gate baselines + Central trace
# continuous across heartbeat ticks, mirroring the other families).
_RELATION_FAMILY: ClusterDaemon | None = None


def relation_family() -> ClusterDaemon:
    global _RELATION_FAMILY
    if _RELATION_FAMILY is None:
        _RELATION_FAMILY = build_relation_family()
    return _RELATION_FAMILY


# ---------------------------------------------------------------------------
# UNCONDITIONAL (non-LLM) member live dispatchers
# ---------------------------------------------------------------------------


def _relation_comm_guard_live(_snap: dict) -> dict[str, Any]:
    """Godnat-split guard: sweep expired TTL communication-triggers + log active
    count. Rules-based, no LLM, no family gate. Preserves its outputs (the pruned
    active trigger set that feeds prompt_section / guard_channel_text scrubbing)."""
    from core.services.communication_guard_daemon import tick_communication_guard_daemon
    return tick_communication_guard_daemon()


def _relation_map_refresh_live(_snap: dict) -> dict[str, Any]:
    """Refresh the relation map (primary last_seen + stale secondary ToM stamps).
    Rules-based, no LLM, no family gate. Self-throttles per-user via the 12h
    staleness threshold. Preserves its outputs (persisted relation-map state + the
    relation_map.refresh_tick event that build_relation_map_surface reads)."""
    from core.services.relation_map import tick_relation_map_refresh
    return tick_relation_map_refresh(trigger="heartbeat")


# (member_name, live_fn) in a stable order. communication_guard is placed FIRST so
# the cheap TTL cleanup runs even under tight scheduling.
_RELATION_UNCONDITIONAL: tuple[tuple[str, Callable[[dict], Any]], ...] = (
    ("communication_guard", _relation_comm_guard_live),
    ("relation_map_refresh", _relation_map_refresh_live),
)


def _run_relation_nonllm_members(snap: dict, result: dict[str, Any]) -> None:
    """Run the NON-LLM members UNCONDITIONALLY (independent of the family generative
    gate), self-safe. Each self-throttles on its own internal cadence; a member
    error is isolated into ``member_errors`` and NEVER propagated (one failing
    member never blocks the other); a successful run is recorded into
    ``members_ran``/``outputs``.
    """
    for name, fn in _RELATION_UNCONDITIONAL:
        try:
            out = fn(snap)
            result["outputs"][name] = out
            result["members_ran"].append(name)
        except Exception as exc:
            result["member_errors"][name] = f"{type(exc).__name__}: {exc}"


def tick_cluster_relation(snapshot: dict | None = None, *, shadow: bool | None = None) -> dict[str, Any]:
    """Heartbeat entry-point for the relation cluster-daemon family (#8).

    Runs LIVE by default (``shadow=False``) — the prove-then-retire end state
    replacing the user_model + communication_guard + relation_map_refresh daemons.
    Two-tier: the gated LLM member (user_model) runs behind the ONE family gate via
    ``relation_family().tick()``; the two NON-LLM members (communication_guard,
    relation_map_refresh) run UNCONDITIONALLY every tick (each self-throttles).
    Self-safe: NEVER raises into the heartbeat.
    """
    try:
        snap = _collect_relation_snapshot() if snapshot is None else snapshot
        run_live = False if shadow is None else bool(shadow)
        result = relation_family().tick(snap, shadow=run_live)
        # Unconditional non-LLM members (independent of the gate above).
        _run_relation_nonllm_members(snap, result)
        return result
    except Exception as exc:  # never crash the heartbeat
        return {
            "family": RELATION_FAMILY,
            "fired": False,
            "gate_calls": 1,
            "members_ran": [],
            "member_errors": {"__entry__": f"{type(exc).__name__}: {exc}"},
        }


# ===========================================================================
# Family #9 — projects (task_worker + my_projects_watchdog +
#             life_projects_reassessment + thought_action_proposal)
# ===========================================================================
#
# The PROJECTS / WORK-EXECUTION family. Four daemons that keep Jarvis' concrete
# work moving — the runtime task queue, his own background processes, his
# long-term life projects, and turning action-impulses into proposals. UNLIKE
# families #6/#7/#8 this family has NO LLM member: all four are rules/DB-driven,
# so there is NO gated (LLM) tier — every member runs in the UNCONDITIONAL tier
# and self-throttles on its own cadence. The ONE family gate is therefore
# fail-open (no gated member signals → it always fires); the load-reduction is
# purely structural: ONE family tick + ONE registry entry replacing four.
#
#   * task_worker — RULES, LOAD-BEARING INFRASTRUCTURE. Every tick it claims and
#     executes up to ``budget`` queued ``runtime_tasks`` (initiative/heartbeat/
#     open-loop followups + agency/observability/theater refactor briefs). It has
#     NO self-throttle by design — it MUST drain the queue every family tick, so
#     it is placed FIRST in the unconditional tier and runs with budget=3 exactly
#     as the old heartbeat site did. A sibling error must NEVER block it (per-member
#     isolation + a defensive entry-point that runs the unconditional tier even if
#     the gated tick blows up). Output: processed/succeeded/failed/blocked/
#     remaining_queued → consumed by the heartbeat's followup pipeline.
#
#   * my_projects_watchdog — RULES. Restarts Jarvis' own dead background processes
#     (grid-bot, dealwork-worker, superteam-scanner, toku-poller). Had NO internal
#     timer (relied on its 240-min registry cadence), so the family gives it a
#     240-min self-throttle to preserve that cadence and avoid a per-tick
#     list_processes hit. Output: running/restarted/errors.
#
#   * life_projects_reassessment — RULES. Scans active long_term_intentions and
#     publishes ``life_projects.reassessment_due`` for any older than the decay
#     threshold. Had NO internal timer (it relied on the internal_cadence
#     producer's 1440-min cooldown), and it re-publishes for every still-stale item
#     on each run → the family gives it a 1440-min (24h) self-throttle so it keeps
#     its daily cadence and never spams reassessment_due events. Kill-switch:
#     layer_life_projects_enabled (checked inside the tick). Output: reviewed/skipped.
#
#   * thought_action_proposal — RULES (regex classifier, NO LLM). Turns the latest
#     thought-stream fragment into an MC action-proposal when an action impulse is
#     detected. It self-throttles intrinsically via its ``_last_classified_fragment``
#     dedup (a repeated fragment → "duplicate_fragment"), so it runs every tick on
#     the freshly-collected fragment exactly as the old heartbeat site did (skip when
#     no fragment). Output: thought_action_proposal.created event + private-brain
#     record + build_proposal_surface/get_pending_proposals (read by cluster_affect's
#     conflict snapshot, central_inner_life_digest, signal_surface_router).
#
# Self-safe throughout: a member error is captured into ``member_errors`` and never
# propagated; task_worker's drain is paramount, so neither a failing sibling nor a
# broken family gate can block it; ``tick_cluster_projects`` never raises.

PROJECTS_FAMILY = "cluster_projects"


# ---------------------------------------------------------------------------
# Per-member self-throttle (for the members that had no internal cadence guard)
# ---------------------------------------------------------------------------

_PROJECTS_THROTTLE: dict[str, float] = {}


def _projects_throttle_ready(key: str, minutes: float) -> bool:
    """Return True (and stamp 'now') iff ``minutes`` have elapsed since the last
    ready for ``key``. First call is always ready (last defaults to 0). Gives the
    members that lacked an internal timer their own cadence self-throttle so
    folding them into the every-tick family does not change how often they fire."""
    now = time.time()
    last = _PROJECTS_THROTTLE.get(key, 0.0)
    if (now - last) >= float(minutes) * 60.0:
        _PROJECTS_THROTTLE[key] = now
        return True
    return False


# ---------------------------------------------------------------------------
# Shared snapshot
# ---------------------------------------------------------------------------


def _collect_projects_snapshot() -> dict[str, Any]:
    """Gather the projects family's shared snapshot once per tick.

    Only thought_action_proposal needs an input from here — the latest
    thought-stream fragment it classifies (collected once, as the old heartbeat
    site did via ``get_latest_thought_fragment``). task_worker, my_projects_watchdog
    and life_projects_reassessment self-collect inside their own ticks and need
    nothing here. This family has NO LLM member, so there are no gate signals to
    collect. Self-safe: degrades to a neutral default on any error; the family
    still ticks.
    """
    snap: dict[str, Any] = {"latest_fragment": ""}
    try:
        from core.services.thought_stream_daemon import get_latest_thought_fragment
        snap["latest_fragment"] = str(get_latest_thought_fragment() or "")
    except Exception:
        pass
    return snap


def build_projects_family() -> ClusterDaemon:
    """Construct the projects/work-execution cluster-daemon (family #9), LIVE.

    NO gated LLM member — all four members are rules/DB-driven and run in the
    UNCONDITIONAL tier via ``tick_cluster_projects``. The ClusterDaemon is built
    with an EMPTY ``members`` list (the gated tier): its one-gate call is therefore
    fail-open (no signals → always fires) and exists only to keep the family's
    ONE-gate invariant + Central trace continuous, mirroring the other families.
    """
    return ClusterDaemon(
        family_name=PROJECTS_FAMILY,
        cluster="cognition",
        collect_snapshot=_collect_projects_snapshot,
        members=[],  # no LLM member — every member is unconditional (see below)
    )


# Process-level singleton (keeps the family's Central trace continuous across
# heartbeat ticks, mirroring the other families).
_PROJECTS_FAMILY: ClusterDaemon | None = None


def projects_family() -> ClusterDaemon:
    global _PROJECTS_FAMILY
    if _PROJECTS_FAMILY is None:
        _PROJECTS_FAMILY = build_projects_family()
    return _PROJECTS_FAMILY


# ---------------------------------------------------------------------------
# UNCONDITIONAL (non-LLM) member live dispatchers
# ---------------------------------------------------------------------------


def _projects_task_worker_live(_snap: dict) -> dict[str, Any]:
    """LOAD-BEARING + EVERY TICK — drain up to 3 queued runtime_tasks. NO throttle:
    task_worker must drain the queue on every family tick exactly as the old
    heartbeat site (budget=3) did. Rules-based, no LLM, no family gate."""
    from core.services.task_worker import tick_task_worker
    return tick_task_worker(budget=3)


def _projects_my_projects_live(_snap: dict) -> dict[str, Any]:
    """Restart Jarvis' dead background processes. Rules-based, no LLM. Self-throttles
    on a 240-min cadence (the daemon has no internal timer) so folding it into the
    every-tick family preserves its cadence and avoids a per-tick list_processes."""
    if not _projects_throttle_ready("my_projects_watchdog", 240):
        return {"status": "throttled", "cadence_minutes": 240}
    from core.services.my_projects import tick_my_projects_watchdog
    return tick_my_projects_watchdog()


def _projects_life_reassessment_live(_snap: dict) -> dict[str, Any]:
    """Re-assess active life projects; publish reassessment_due for stale ones.
    Rules-based, no LLM. Self-throttles on a 1440-min (24h) cadence (the daemon has
    no internal timer and re-emits events for every still-stale item each run) so
    it keeps its daily cadence and never spams reassessment_due."""
    if not _projects_throttle_ready("life_projects_reassessment", 1440):
        return {"status": "throttled", "cadence_minutes": 1440}
    from core.services.life_projects import tick_life_projects_reassessment
    return tick_life_projects_reassessment(trigger="heartbeat")


def _projects_thought_action_live(snap: dict) -> dict[str, Any]:
    """Classify the latest thought-stream fragment into an action-proposal. Rules-
    based (regex classifier), no LLM, no family gate. Self-throttles intrinsically
    via the daemon's ``_last_classified_fragment`` dedup, so running it every tick on
    the freshly-collected fragment matches the old heartbeat behaviour. Skips
    harmlessly when there is no fragment this tick."""
    fragment = str(snap.get("latest_fragment") or "")
    if not fragment:
        return {"generated": False, "skip_reason": "no_fragment"}
    from core.services.thought_action_proposal_daemon import tick_thought_action_proposal_daemon
    return tick_thought_action_proposal_daemon(fragment)


# (member_name, live_fn) in a stable order. task_worker is placed FIRST so the
# LOAD-BEARING queue drain runs before any sibling — and its per-member try/except
# guarantees a failing sibling can never block it.
_PROJECTS_UNCONDITIONAL: tuple[tuple[str, Callable[[dict], Any]], ...] = (
    ("task_worker", _projects_task_worker_live),
    ("my_projects_watchdog", _projects_my_projects_live),
    ("life_projects_reassessment", _projects_life_reassessment_live),
    ("thought_action_proposal", _projects_thought_action_live),
)


def _run_projects_unconditional(snap: dict, result: dict[str, Any]) -> None:
    """Run every projects member UNCONDITIONALLY (this family has no LLM/gated tier),
    self-safe. task_worker runs FIRST; each member self-throttles on its own cadence;
    a member error is isolated into ``member_errors`` and NEVER propagated (task_worker
    robustness is paramount — one failing sibling never blocks the drain); a
    successful run is recorded into ``members_ran``/``outputs``.
    """
    for name, fn in _PROJECTS_UNCONDITIONAL:
        try:
            out = fn(snap)
            result["outputs"][name] = out
            result["members_ran"].append(name)
        except Exception as exc:
            result["member_errors"][name] = f"{type(exc).__name__}: {exc}"


def tick_cluster_projects(snapshot: dict | None = None, *, shadow: bool | None = None) -> dict[str, Any]:
    """Heartbeat entry-point for the projects/work-execution cluster-daemon family (#9).

    Runs LIVE by default (``shadow=False``) — the prove-then-retire end state
    replacing the task_worker + my_projects_watchdog + life_projects_reassessment +
    thought_action_proposal daemons. This family has NO LLM member: every member
    runs in the UNCONDITIONAL tier and self-throttles on its own cadence.

    task_worker robustness is paramount, so the unconditional tier is run
    DEFENSIVELY — the (empty, fail-open) family gate tick is wrapped so that even a
    catastrophic gate failure can never skip the queue drain, and task_worker is
    FIRST in the unconditional tier with per-member error isolation. Self-safe:
    NEVER raises into the heartbeat.
    """
    run_live = False if shadow is None else bool(shadow)
    try:
        snap = _collect_projects_snapshot() if snapshot is None else snapshot
    except Exception:
        snap = {"latest_fragment": ""}

    result: dict[str, Any] = {
        "family": PROJECTS_FAMILY,
        "shadow": run_live,
        "gate_calls": 1,
        "fired": False,
        "members_ran": [],
        "members_skipped": [],
        "member_errors": {},
        "outputs": {},
    }

    # The family's ONE gate tick (no gated members → fail-open) — kept only for the
    # one-gate invariant + Central trace. Wrapped so it can NEVER block task_worker.
    try:
        gres = projects_family().tick(snap, shadow=run_live)
        result["fired"] = bool(gres.get("fired"))
        result["gate_calls"] = int(gres.get("gate_calls") or 1)
        result["members_skipped"].extend(gres.get("members_skipped") or [])
        for _mn in (gres.get("members_ran") or []):
            if _mn not in result["members_ran"]:
                result["members_ran"].append(_mn)
        result["outputs"].update(gres.get("outputs") or {})
        result["member_errors"].update(gres.get("member_errors") or {})
    except Exception as exc:
        result["member_errors"]["__gated__"] = f"{type(exc).__name__}: {exc}"

    # Unconditional tier — task_worker FIRST — runs REGARDLESS of the gate above.
    _run_projects_unconditional(snap, result)
    return result
