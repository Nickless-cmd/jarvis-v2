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
