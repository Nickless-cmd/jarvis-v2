"""Cluster-daemon primitive — one Central-governed daemon per FAMILY of nerves.

Spec: ``docs/superpowers/specs/2026-07-14-cluster-daemon-consolidation.md``.

Jarvis has ~40 ad-hoc timer-daemons — one per function, each on its own blind
timer, each competing for the heartbeat loop. This module is the primitive that
folds a FAMILY of related functions into ONE smart, Central-governed daemon:

* **One event-gate for the whole family.** The cluster checks the family's
  aggregate signals ONCE per tick via
  :func:`core.services.event_gate.should_generative_fire` (namespaced under the
  family name) — 10 daemons that each check → 1 cluster that checks. 10 ticks →
  1 tick. That IS the load reduction.
* **Multi-function dispatch.** When the family fires, the cluster dispatches only
  to the member functions that have a relevant signal.
* **Self-safe.** A member error is captured, never propagated — the family
  (and the heartbeat) never crashes. ``tick()`` never raises.
* **Central has authority (ground-invariant #1).** The cluster never decides
  independently; every tick is reported to the Central trace-sink via
  ``central().observe(...)``.

Migration is **prove-then-retire** (never both live). A family is first wired in
SHADOW: it runs ALONGSIDE the old member daemons and only *observes* what it
would produce (no DB writes, no event publishes) to Central under a
``cluster_shadow`` marker, so a later review can compare the cluster's one-gate
behaviour against the N old daemons before any old daemon is retired. The
``cluster_daemon_shadow`` runtime flag governs this and defaults to SHADOW.

Interface (call-sites and future families code against this exact surface)::

    fam = build_somatic_family()
    result = fam.tick()                      # zero-arg: family collects its own snapshot
    result = fam.tick(snapshot, shadow=True)  # explicit snapshot / mode

``result`` shape::

    {
        "family": "cluster_somatic",
        "shadow": True,
        "fired": True,               # did the ONE family gate fire this tick?
        "gate_calls": 1,             # ALWAYS 1 — the load-reduction invariant
        "members_ran": ["somatic", "experienced_time", "absence"],
        "members_skipped": [],       # members with no relevant signal this tick
        "member_errors": {},         # member_name -> error string (self-safe)
        "outputs": {"somatic": {...}, ...},  # per-member output shape (parity)
    }
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Runtime flags
# ---------------------------------------------------------------------------

# Kill-switch / governance flag. Default SHADOW (True) — the cluster observes
# only and never disables or replaces the old member daemons. Flip via
# runtime-state once parity is proven. Self-safe → SHADOW on any error (we must
# never accidentally run a family in live/replace mode because a flag lookup
# broke).
_SHADOW_FLAG = "cluster_daemon_shadow"


def shadow_mode_enabled() -> bool:
    """True when cluster-daemons run in SHADOW (observe-only) mode.

    Default True. Self-safe → True on any error. While True a family never
    writes/publishes and never disables the old member daemons — it only reports
    parity telemetry to Central.
    """
    try:
        from core.runtime.db_core import get_runtime_state_value

        v = get_runtime_state_value(_SHADOW_FLAG, True)
        return True if v is None else bool(v)
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Member declaration
# ---------------------------------------------------------------------------


@dataclass
class ClusterMember:
    """One function inside a cluster-daemon family.

    A new inner-life function joins a family by declaring three small things and
    inherits the family's contract, gate, learning, kill-switch and trace for
    free (spec §Builder-guide):

    * ``name`` — stable member id (matches the old daemon name for parity).
    * ``signals`` — extract this member's gate signals (float dict) from the
      shared snapshot. These are aggregated (namespaced ``member:signal``) into
      the family's ONE gate call. Return ``{}`` when the member has no numeric
      signal this tick.
    * ``observe`` — SHADOW output probe: given the snapshot, return a small,
      SIDE-EFFECT-FREE descriptor of what the member would produce (its output
      shape). Used for parity comparison against the old daemon. MUST NOT write
      to the DB or publish events.
    * ``relevant`` — optional cheap predicate: does the member have anything to
      do this tick? Defaults to "always relevant when the family fires".
    * ``live`` — optional future hook for the member's real (side-effecting)
      logic, used only after the family is flipped out of shadow. Unused today.
    """

    name: str
    signals: Callable[[dict], dict[str, float]]
    observe: Callable[[dict], Any]
    relevant: Callable[[dict], bool] | None = None
    live: Callable[[dict], Any] | None = None


# ---------------------------------------------------------------------------
# The primitive
# ---------------------------------------------------------------------------


@dataclass
class ClusterDaemon:
    """One Central-governed daemon for a FAMILY of member functions.

    ``family_name`` is also the namespace for the family's single event-gate
    (``should_generative_fire(family_name, aggregate_signals)``) and the Central
    nerve name.
    """

    family_name: str
    members: list[ClusterMember]
    cluster: str = "cognition"
    collect_snapshot: Callable[[], dict] | None = field(default=None, repr=False)

    # ── snapshot ────────────────────────────────────────────────────────
    def _snapshot(self, snapshot: dict | None) -> dict:
        if snapshot is not None:
            return snapshot
        if self.collect_snapshot is not None:
            try:
                snap = self.collect_snapshot()
                return snap if isinstance(snap, dict) else {}
            except Exception:
                return {}
        return {}

    # ── the ONE family gate ─────────────────────────────────────────────
    def _aggregate_signals(self, snapshot: dict) -> dict[str, float]:
        """Collect every member's signals into ONE namespaced dict for the gate.

        Each member's signal error is swallowed — a broken member signal must
        never silence the whole family.
        """
        agg: dict[str, float] = {}
        for m in self.members:
            try:
                sigs = m.signals(snapshot) or {}
                for k, v in sigs.items():
                    try:
                        agg[f"{m.name}:{k}"] = float(v)
                    except (TypeError, ValueError):
                        continue
            except Exception:
                continue
        return agg

    def _gate_fires(self, snapshot: dict) -> bool:
        """Run the family's SINGLE event-gate. Fail-OPEN → fire.

        The gate is consulted exactly once per tick regardless of member count —
        that is the load-reduction invariant. When event-driven mode is off we
        fire unconditionally (timer-parity), matching the individual daemons.
        """
        try:
            from core.services import event_gate

            if not event_gate.event_driven_enabled():
                return True
            agg = self._aggregate_signals(snapshot)
            if not agg:
                return True
            return bool(event_gate.should_generative_fire(self.family_name, agg))
        except Exception:
            # A broken gate must FIRE, never silence the family.
            return True

    # ── tick ────────────────────────────────────────────────────────────
    def tick(self, snapshot: dict | None = None, *, shadow: bool | None = None) -> dict[str, Any]:
        """Run the family for one heartbeat tick. NEVER raises.

        Checks the family's signals ONCE, then dispatches to the relevant
        members. In shadow mode each member's SIDE-EFFECT-FREE ``observe`` probe
        runs and the whole tick is reported to Central under ``cluster_shadow``.
        """
        is_shadow = shadow_mode_enabled() if shadow is None else bool(shadow)
        snap = self._snapshot(snapshot)

        result: dict[str, Any] = {
            "family": self.family_name,
            "shadow": is_shadow,
            "gate_calls": 1,  # invariant: ONE gate for the whole family
            "fired": False,
            "members_ran": [],
            "members_skipped": [],
            "member_errors": {},
            "outputs": {},
        }

        try:
            fired = self._gate_fires(snap)
            result["fired"] = fired
            if not fired:
                # Load reduction: the family gate said "no relevant change" —
                # skip every member this tick. Still report to Central.
                self._report_to_central(result, is_shadow)
                return result

            for m in self.members:
                try:
                    if m.relevant is not None and not m.relevant(snap):
                        result["members_skipped"].append(m.name)
                        continue
                    if is_shadow:
                        out = m.observe(snap)
                    else:
                        # Live path (post-parity, currently never reached under
                        # the default shadow flag). Fall back to observe if the
                        # member declared no live fn yet.
                        out = (m.live or m.observe)(snap)
                    result["outputs"][m.name] = out
                    result["members_ran"].append(m.name)
                except Exception as exc:  # member error MUST NOT crash the family
                    result["member_errors"][m.name] = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            # Absolute belt-and-suspenders — tick() never raises.
            result["member_errors"]["__family__"] = f"{type(exc).__name__}: {exc}"

        self._report_to_central(result, is_shadow)
        return result

    # ── Central authority / parity telemetry ────────────────────────────
    def _report_to_central(self, result: dict[str, Any], is_shadow: bool) -> None:
        """Best-effort parity telemetry to the Central trace-sink. Never raises.

        Emits enough for a later review to compare the cluster's ONE-gate,
        multi-dispatch behaviour against the N old member daemons: did the
        family fire, which members ran/were skipped, and each member's output
        shape. The ``cluster_shadow`` marker tags it as observe-only parity data.
        """
        try:
            from core.services.central_core import central

            central().observe(
                {
                    "cluster": self.cluster,
                    "nerve": self.family_name,
                    "kind": "cluster_tick",
                    "cluster_shadow": bool(is_shadow),
                    "fired": bool(result.get("fired")),
                    "gate_calls": int(result.get("gate_calls") or 1),
                    "member_count": len(self.members),
                    "members_ran": list(result.get("members_ran") or []),
                    "members_skipped": list(result.get("members_skipped") or []),
                    "member_errors": dict(result.get("member_errors") or {}),
                    "outputs": dict(result.get("outputs") or {}),
                }
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Family #1 — somatic / embodiment (somatic + experienced_time + absence)
# ---------------------------------------------------------------------------
#
# The mostly-raw-number family (spec §"De ~10 familier" #1). Per the
# LLM-continuity rule these are pure measurement/classification → no LLM in the
# cluster; the shadow probes read the members' own SIDE-EFFECT-FREE surface
# builders so the cluster observes exactly what the old daemons produced without
# any writes or publishes.

SOMATIC_FAMILY = "cluster_somatic"


def _somatic_signals(snapshot: dict) -> dict[str, float]:
    """Somatic member gate-signal: machine pressure (drain + energy band)."""
    body = snapshot.get("somatic") or {}
    energy = str(body.get("energy_level") or "").lower()
    energy_band = {"udmattet": 1.0, "lav": 0.75, "medium": 0.5, "høj": 0.25}.get(energy, 0.5)
    try:
        drain = float(body.get("drain_score") or 0.0)
    except (TypeError, ValueError):
        drain = 0.0
    return {"drain": max(0.0, min(1.0, drain)), "energy_band": energy_band}


def _somatic_observe(snapshot: dict) -> dict[str, Any]:
    body = snapshot.get("somatic") or {}
    return {
        "phrase": str(body.get("somatic_phrase") or ""),
        "energy_level": str(body.get("energy_level") or ""),
        "updated_at": str(body.get("somatic_updated_at") or ""),
    }


def _experienced_time_signals(snapshot: dict) -> dict[str, float]:
    et = snapshot.get("experienced_time") or {}
    try:
        base_minutes = float(et.get("base_minutes") or 0.0)
    except (TypeError, ValueError):
        base_minutes = 0.0
    try:
        events = float(et.get("session_event_count") or 0.0)
    except (TypeError, ValueError):
        events = 0.0
    # Normalise to 0-1: an hour of clock time, ~100 events of density.
    return {
        "clock_frac": max(0.0, min(1.0, base_minutes / 60.0)),
        "density_frac": max(0.0, min(1.0, events / 100.0)),
    }


def _experienced_time_observe(snapshot: dict) -> dict[str, Any]:
    et = snapshot.get("experienced_time") or {}
    return {
        "felt_label": str(et.get("felt_label") or ""),
        "session_event_count": int(et.get("session_event_count") or 0),
        "base_minutes": float(et.get("base_minutes") or 0.0),
    }


def _absence_signals(snapshot: dict) -> dict[str, float]:
    ab = snapshot.get("absence") or {}
    try:
        hours = float(ab.get("absence_duration_hours") or 0.0)
    except (TypeError, ValueError):
        hours = 0.0
    band = {"short": 0.0, "long": 0.5, "very_long": 1.0}
    b = band.get(str(ab.get("band") or "short"), 0.0)
    return {"hours_frac": max(0.0, min(1.0, hours / 24.0)), "band": b}


def _absence_observe(snapshot: dict) -> dict[str, Any]:
    ab = snapshot.get("absence") or {}
    return {
        "absence_label": str(ab.get("absence_label") or ""),
        "absence_duration_hours": float(ab.get("absence_duration_hours") or 0.0),
    }


def _collect_somatic_snapshot() -> dict:
    """Gather the somatic family's shared snapshot from the members' own
    SIDE-EFFECT-FREE surface builders. No LLM, no DB writes, no publishes.

    Self-safe: any missing member surface degrades to an empty dict for that
    member — the family still ticks.
    """
    snap: dict[str, Any] = {}
    try:
        from core.services.somatic_daemon import build_body_state_surface

        snap["somatic"] = build_body_state_surface() or {}
    except Exception:
        snap["somatic"] = {}
    try:
        from core.services.experienced_time_daemon import build_experienced_time_surface

        snap["experienced_time"] = build_experienced_time_surface() or {}
    except Exception:
        snap["experienced_time"] = {}
    try:
        from core.services.absence_daemon import build_absence_surface

        snap["absence"] = build_absence_surface() or {}
    except Exception:
        snap["absence"] = {}
    return snap


def build_somatic_family() -> ClusterDaemon:
    """Construct the somatic/embodiment cluster-daemon (family #1)."""
    return ClusterDaemon(
        family_name=SOMATIC_FAMILY,
        cluster="cognition",
        collect_snapshot=_collect_somatic_snapshot,
        members=[
            ClusterMember(
                name="somatic",
                signals=_somatic_signals,
                observe=_somatic_observe,
            ),
            ClusterMember(
                name="experienced_time",
                signals=_experienced_time_signals,
                observe=_experienced_time_observe,
            ),
            ClusterMember(
                name="absence",
                signals=_absence_signals,
                observe=_absence_observe,
            ),
        ],
    )


# Process-level singleton for the somatic family (mirrors the module-global
# pattern the individual daemons use; keeps the family's gate baselines and
# Central trace continuous across heartbeat ticks).
_SOMATIC_FAMILY: ClusterDaemon | None = None


def somatic_family() -> ClusterDaemon:
    global _SOMATIC_FAMILY
    if _SOMATIC_FAMILY is None:
        _SOMATIC_FAMILY = build_somatic_family()
    return _SOMATIC_FAMILY


def tick_cluster_somatic(snapshot: dict | None = None, *, shadow: bool | None = None) -> dict[str, Any]:
    """Heartbeat entry-point for the somatic cluster-daemon family.

    Self-safe wrapper: returns the tick result (or a minimal skipped result on
    catastrophic failure) and NEVER raises into the heartbeat.
    """
    try:
        return somatic_family().tick(snapshot, shadow=shadow)
    except Exception as exc:  # never crash the heartbeat
        return {
            "family": SOMATIC_FAMILY,
            "fired": False,
            "gate_calls": 1,
            "members_ran": [],
            "member_errors": {"__entry__": f"{type(exc).__name__}: {exc}"},
        }


# ---------------------------------------------------------------------------
# Family #2 — inner-voice (thought_stream + reflection_cycle + meta_reflection +
#             irony + existential_wonder + creative_drift)
# ---------------------------------------------------------------------------
#
# The heavy, LLM-with-context family (spec §"De ~10 familier" #3 + §LLM-
# kontinuitet). These are the thoughts that carry Jarvis' HISTORY to himself —
# a thought with an ORIGIN, not a context-less fragment — so the LLM is NEVER
# stripped here. Unlike the somatic family this one runs LIVE (not shadow):
# it is the prove-then-retire END STATE. Each member's ``live`` dispatches to
# the SAME generation function the old daemon used (``tick_<x>_daemon`` with
# ``skip_event_gate=True``), so every load-bearing output is preserved:
#
#   * thought_stream    → _cached_fragment / build_thought_stream_surface
#   * reflection_cycle  → _cached_reflection / build_reflection_surface
#   * meta_reflection   → _cached_meta_insight (+ Lag-1 credit assignment)
#   * irony             → _cached_observation / build_irony_surface
#   * existential_wonder→ _latest_wonder  (LOAD-BEARING: convene_judge,
#                         proactivity_bridge, visible_inner_life read this)
#   * creative_drift    → _drift_buffer / build_creative_drift_surface
#
# The OLD daemons update their own module-level caches, and every consumer reads
# those same caches via get_latest_*/build_*_surface — so folding generation
# into the cluster keeps the entire output pipeline flowing untouched. Each
# member keeps its intrinsic cadence/cap (thought 2min, reflection 10min, meta
# 30min, irony 1/day, drift 30min+3/day, wonder 24h floor); the ONE family gate
# replaces the 6 separate should_generative_fire() calls — that is the load cut.

INNERVOICE_FAMILY = "cluster_innervoice"


def _iv_text_signal(value: str) -> float:
    """Deterministic 0..1 proxy of a short text state (mirrors the daemons'
    own ``_text_signal`` — no hash randomisation, so the gate sees real moves)."""
    if not value:
        return 0.0
    return float(sum(ord(c) for c in value) % 100) / 100.0


def _collect_innervoice_snapshot() -> dict[str, Any]:
    """Gather the inner-voice family's shared snapshot once per tick.

    Reads the same live surfaces the heartbeat used to assemble inline for each
    of the 6 daemons. Self-safe: any missing source degrades to a neutral
    default; the family still ticks. NO LLM, no writes here — this is only the
    input gathering; the members' ``live`` functions do the generation.
    """
    snap: dict[str, Any] = {
        "energy_level": "",
        "inner_voice_mode": "",
        "latest_fragment": "",
        "fragment_count": 0,
        "fragment_buffer": [],
        "last_conflict": "",
        "last_surprise": "",
        "last_irony": "",
        "last_taste": "",
        "curiosity_signal": "",
        "absence_hours": 0.0,
        "user_inactive_min": 999.0,
        "cpu_pct": 0.0,
    }
    try:
        from core.runtime.circadian_state import get_circadian_context
        snap["energy_level"] = str(get_circadian_context().get("energy_level") or "")
    except Exception:
        pass
    try:
        from core.services.inner_voice_daemon import get_inner_voice_daemon_state
        _iv = get_inner_voice_daemon_state()
        snap["inner_voice_mode"] = str((_iv.get("last_result") or {}).get("mode") or "")
    except Exception:
        pass
    try:
        from core.services.thought_stream_daemon import build_thought_stream_surface
        _ts = build_thought_stream_surface() or {}
        snap["latest_fragment"] = str(_ts.get("latest_fragment") or "")
        snap["fragment_count"] = int(_ts.get("fragment_count") or 0)
        snap["fragment_buffer"] = list(_ts.get("fragment_buffer") or [])
    except Exception:
        pass
    try:
        from core.services.conflict_daemon import get_latest_conflict
        snap["last_conflict"] = str(get_latest_conflict() or "")
    except Exception:
        pass
    try:
        from core.services.surprise_daemon import build_surprise_surface
        snap["last_surprise"] = str((build_surprise_surface() or {}).get("last_surprise") or "")
    except Exception:
        pass
    try:
        from core.services.irony_daemon import build_irony_surface
        snap["last_irony"] = str((build_irony_surface() or {}).get("last_observation") or "")
    except Exception:
        pass
    try:
        from core.services.aesthetic_taste_daemon import build_taste_surface
        snap["last_taste"] = str((build_taste_surface() or {}).get("latest_insight") or "")
    except Exception:
        pass
    try:
        from core.services.curiosity_daemon import get_latest_curiosity
        snap["curiosity_signal"] = str(get_latest_curiosity() or "")
    except Exception:
        pass
    try:
        from core.services.absence_daemon import build_absence_surface
        snap["absence_hours"] = float((build_absence_surface() or {}).get("absence_duration_hours") or 0.0)
    except Exception:
        pass
    # user-inactivity + cpu for the irony gate signal (collected once here so the
    # irony member's cheap signal probe doesn't re-hit psutil/DB every tick).
    try:
        from core.services.irony_daemon import _collect_snapshot as _irony_collect
        _isnap = _irony_collect() or {}
        snap["user_inactive_min"] = float(_isnap.get("user_inactive_min", 999.0))
        snap["cpu_pct"] = float(_isnap.get("cpu_pct", 0.0))
    except Exception:
        pass
    return snap


# ── member signal extractors (aggregated into the ONE family gate) ──────────


def _iv_thought_stream_signals(snap: dict) -> dict[str, float]:
    return {
        "energy": _iv_text_signal(str(snap.get("energy_level", ""))),
        "mood": _iv_text_signal(str(snap.get("inner_voice_mode", ""))),
        "continuity": 1.0 if snap.get("latest_fragment") else 0.0,
    }


def _iv_reflection_signals(snap: dict) -> dict[str, float]:
    return {
        "conflict": 1.0 if snap.get("last_conflict") else 0.0,
        "surprise": 1.0 if snap.get("last_surprise") else 0.0,
        "valence": _iv_text_signal(str(snap.get("inner_voice_mode", ""))),
    }


def _iv_meta_signals(snap: dict) -> dict[str, float]:
    return {
        "latest_fragment": float(len(str(snap.get("latest_fragment") or ""))),
        "last_surprise": float(len(str(snap.get("last_surprise") or ""))),
        "last_conflict": float(len(str(snap.get("last_conflict") or ""))),
    }


def _iv_irony_signals(snap: dict) -> dict[str, float]:
    return {
        "user_inactive_min": float(snap.get("user_inactive_min", 0.0) or 0.0),
        "cpu_pct": float(snap.get("cpu_pct", 0.0) or 0.0),
    }


def _iv_wonder_signals(snap: dict) -> dict[str, float]:
    hours = float(snap.get("absence_hours", 0.0) or 0.0)
    frags = int(snap.get("fragment_count", 0) or 0)
    return {
        "existential_pressure": min(max(hours, 0.0) / 24.0, 1.0),
        "long_absence": min(max(hours, 0.0) / 24.0, 1.0),
        "thought_stream": min(max(frags, 0) / 20.0, 1.0),
    }


def _iv_drift_signals(snap: dict) -> dict[str, float]:
    return {
        "idle_seconds": float(snap.get("user_inactive_min", 0.0) or 0.0) * 60.0,
        "unused_fragments": float(len(snap.get("fragment_buffer") or [])),
    }


# ── member live dispatchers (reuse the old daemons' generation, one shared
#    family gate having already fired → skip_event_gate=True) ────────────────


def _iv_thought_stream_live(snap: dict) -> dict[str, Any]:
    from core.services.thought_stream_daemon import tick_thought_stream_daemon
    return tick_thought_stream_daemon(
        energy_level=str(snap.get("energy_level", "")),
        inner_voice_mode=str(snap.get("inner_voice_mode", "")),
        skip_event_gate=True,
    )


def _iv_reflection_live(snap: dict) -> dict[str, Any]:
    from core.services.reflection_cycle_daemon import tick_reflection_cycle_daemon
    return tick_reflection_cycle_daemon(
        {
            "energy_level": snap.get("energy_level", ""),
            "inner_voice_mode": snap.get("inner_voice_mode", ""),
            "latest_fragment": snap.get("latest_fragment", ""),
            "last_conflict": snap.get("last_conflict", ""),
            "last_surprise": snap.get("last_surprise", ""),
        },
        skip_event_gate=True,
    )


def _iv_meta_live(snap: dict) -> dict[str, Any]:
    from core.services.meta_reflection_daemon import tick_meta_reflection_daemon
    return tick_meta_reflection_daemon(
        {
            "energy_level": snap.get("energy_level", ""),
            "inner_voice_mode": snap.get("inner_voice_mode", ""),
            "latest_fragment": snap.get("latest_fragment", ""),
            "last_surprise": snap.get("last_surprise", ""),
            "last_conflict": snap.get("last_conflict", ""),
            "last_irony": snap.get("last_irony", ""),
            "last_taste": snap.get("last_taste", ""),
            "curiosity_signal": snap.get("curiosity_signal", ""),
        },
        skip_event_gate=True,
        skip_credit=True,  # credit-assignment already run unconditionally this tick
    )


def _iv_irony_live(snap: dict) -> dict[str, Any]:
    from core.services.irony_daemon import tick_irony_daemon
    return tick_irony_daemon(skip_event_gate=True)


def _iv_wonder_live(snap: dict) -> dict[str, Any]:
    from core.services.existential_wonder_daemon import tick_existential_wonder_daemon
    return tick_existential_wonder_daemon(
        absence_hours=float(snap.get("absence_hours", 0.0) or 0.0),
        fragment_count=int(snap.get("fragment_count", 0) or 0),
        skip_event_gate=True,
    )


def _iv_drift_live(snap: dict) -> dict[str, Any]:
    from core.services.creative_drift_daemon import tick_creative_drift_daemon
    return tick_creative_drift_daemon(list(snap.get("fragment_buffer") or []), skip_event_gate=True)


# ── member observe probes (side-effect-free; used only if ever run in shadow) ─


def _iv_surface_observe(builder_path: tuple[str, str], keys: tuple[str, ...]) -> Callable[[dict], Any]:
    def _obs(_snap: dict) -> dict[str, Any]:
        try:
            import importlib
            mod = importlib.import_module(builder_path[0])
            surf = getattr(mod, builder_path[1])() or {}
            return {k: surf.get(k) for k in keys}
        except Exception:
            return {}
    return _obs


def build_innervoice_family() -> ClusterDaemon:
    """Construct the inner-voice cluster-daemon (family #2), LIVE.

    Six members, ONE family gate. Each member dispatches to the proven
    generation function of the daemon it replaces (skip_event_gate=True), so all
    outputs — crucially ``existential_wonder``'s ``_latest_wonder`` — keep
    flowing to their existing consumers.
    """
    return ClusterDaemon(
        family_name=INNERVOICE_FAMILY,
        cluster="cognition",
        collect_snapshot=_collect_innervoice_snapshot,
        members=[
            ClusterMember(
                name="thought_stream",
                signals=_iv_thought_stream_signals,
                observe=_iv_surface_observe(
                    ("core.services.thought_stream_daemon", "build_thought_stream_surface"),
                    ("latest_fragment", "fragment_count"),
                ),
                live=_iv_thought_stream_live,
            ),
            ClusterMember(
                name="reflection_cycle",
                signals=_iv_reflection_signals,
                observe=_iv_surface_observe(
                    ("core.services.reflection_cycle_daemon", "build_reflection_surface"),
                    ("latest_reflection", "reflection_count"),
                ),
                live=_iv_reflection_live,
            ),
            ClusterMember(
                name="meta_reflection",
                signals=_iv_meta_signals,
                observe=_iv_surface_observe(
                    ("core.services.meta_reflection_daemon", "build_meta_reflection_surface"),
                    ("latest_insight", "insight_count"),
                ),
                live=_iv_meta_live,
            ),
            ClusterMember(
                name="irony",
                signals=_iv_irony_signals,
                observe=_iv_surface_observe(
                    ("core.services.irony_daemon", "build_irony_surface"),
                    ("last_observation", "observations_today"),
                ),
                live=_iv_irony_live,
            ),
            ClusterMember(
                name="existential_wonder",
                signals=_iv_wonder_signals,
                observe=_iv_surface_observe(
                    ("core.services.existential_wonder_daemon", "build_existential_wonder_surface"),
                    ("latest_wonder",),
                ),
                live=_iv_wonder_live,
            ),
            ClusterMember(
                name="creative_drift",
                signals=_iv_drift_signals,
                observe=_iv_surface_observe(
                    ("core.services.creative_drift_daemon", "build_creative_drift_surface"),
                    ("latest_drift", "drift_count_today"),
                ),
                live=_iv_drift_live,
            ),
        ],
    )


# Process-level singleton (keeps the family's gate baselines + Central trace
# continuous across heartbeat ticks, mirroring the somatic family).
_INNERVOICE_FAMILY: ClusterDaemon | None = None


def innervoice_family() -> ClusterDaemon:
    global _INNERVOICE_FAMILY
    if _INNERVOICE_FAMILY is None:
        _INNERVOICE_FAMILY = build_innervoice_family()
    return _INNERVOICE_FAMILY


def tick_cluster_innervoice(snapshot: dict | None = None, *, shadow: bool | None = None) -> dict[str, Any]:
    """Heartbeat entry-point for the inner-voice cluster-daemon family.

    Runs LIVE by default (``shadow=False``) — this family IS the prove-then-retire
    end state that replaces the 6 old inner-voice daemons, so it must actually
    produce their outputs, not merely observe. Before the single family gate it
    runs the NON-LLM Lag-1 credit-assignment pass UNCONDITIONALLY (as the old
    meta_reflection daemon did every heartbeat tick), independent of whether the
    generative family gate fires.

    Self-safe: returns a minimal skipped result on catastrophic failure and
    NEVER raises into the heartbeat.
    """
    try:
        snap = _collect_innervoice_snapshot() if snapshot is None else snapshot
        # Unconditional every-tick credit assignment (preserves old behaviour).
        try:
            from core.services.meta_reflection_daemon import run_credit_assignment
            run_credit_assignment(snap)
        except Exception:
            pass
        run_live = False if shadow is None else bool(shadow)
        return innervoice_family().tick(snap, shadow=run_live)
    except Exception as exc:  # never crash the heartbeat
        return {
            "family": INNERVOICE_FAMILY,
            "fired": False,
            "gate_calls": 1,
            "members_ran": [],
            "member_errors": {"__entry__": f"{type(exc).__name__}: {exc}"},
        }
