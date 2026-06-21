"""GateKernel — central orchestrator for alle gates (spec 2026-06-21).

Erstatter ~26 spredte gates med ÉN kerne der kører dem isoleret + observerbart.
Værdien i Fase A er IKKE færre dele endnu — det er:
  1. Isoleret eksekvering: én gate der kaster/hænger kan ikke cascade hele runnet.
  2. Fail-mode pr. KLASSE: kognitive gates fail-OPEN, sikkerheds-gates fail-CLOSED.
  3. Ét struktureret `gate.evaluated`-event pr. fase → central debug/overvågning.
  4. Kill-switch pr. gate + bypass (der ALDRIG rører sikkerheds-gates → ingen bagdør).

Gate-funktioner får en `ctx`-dict og returnerer en `Verdict` (eller en (decision,
reason)-agtig værdi som kernen normaliserer). De ændrer INGEN egen logik i Fase A —
adaptere wrapper de eksisterende gates.
"""
from __future__ import annotations

import enum
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FTimeout
from dataclasses import dataclass, field
from typing import Any, Callable


class Decision(enum.Enum):
    GREEN = "green"    # ingen indvending
    YELLOW = "yellow"  # advar + log, men fortsæt
    RED = "red"        # blokér (pre_tool) / strip-flag (post_output)
    SKIP = "skip"      # gaten kørte ikke (disabled/fejl/timeout)


class GateClass(enum.Enum):
    COGNITIVE = "cognitive"  # fail-OPEN ved fejl
    SECURITY = "security"    # fail-CLOSED (deny) ved fejl


_PRECEDENCE = {Decision.RED: 3, Decision.YELLOW: 2, Decision.GREEN: 1, Decision.SKIP: 0}


@dataclass
class Verdict:
    gate: str
    decision: Decision = Decision.GREEN
    reason: str = ""
    action: str = "none"          # allow|strip|block|warn|none
    latency_ms: int = 0
    klass: GateClass = GateClass.COGNITIVE
    evidence: dict[str, Any] | None = None

    def is_blocking(self) -> bool:
        return self.decision is Decision.RED


def worst(verdicts: list[Verdict]) -> Decision:
    """Aggregeret beslutning efter præcedens RED>YELLOW>GREEN>SKIP."""
    if not verdicts:
        return Decision.GREEN
    return max((v.decision for v in verdicts), key=lambda d: _PRECEDENCE[d])


@dataclass
class _Gate:
    name: str
    phase: str
    fn: Callable[[dict[str, Any]], Any]
    klass: GateClass
    timeout_ms: int
    flag_key: str


class GateKernel:
    def __init__(self, *, flag_reader: Callable[[str], bool] | None = None,
                 emit: Callable[[str, dict], None] | None = None) -> None:
        self._gates: list[_Gate] = []
        self._pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="gate")
        self._flag_reader = flag_reader or _default_flag_reader
        self._emit = emit or _default_emit

    # ── registry ────────────────────────────────────────────────────────
    def register(self, name: str, phase: str, fn: Callable[[dict[str, Any]], Any],
                 *, klass: GateClass = GateClass.COGNITIVE, timeout_ms: int = 1500,
                 flag_key: str = "") -> None:
        self._gates.append(_Gate(name, phase, fn, klass, timeout_ms, flag_key or f"gate.{name}"))

    def gates_for(self, phase: str) -> list[_Gate]:
        return [g for g in self._gates if g.phase == phase]

    # ── eksekvering ─────────────────────────────────────────────────────
    def _fail_verdict(self, g: _Gate, reason: str) -> Verdict:
        # Fail-mode pr. klasse: kognitiv → SKIP (fortsæt); sikkerhed → RED-deny.
        if g.klass is GateClass.SECURITY:
            return Verdict(g.name, Decision.RED, reason, action="block", klass=g.klass)
        return Verdict(g.name, Decision.SKIP, reason, action="none", klass=g.klass)

    def _run_one(self, g: _Gate, ctx: dict[str, Any]) -> Verdict:
        t0 = time.monotonic()
        # kill-switch + bypass. flag_reader returnerer True/False/None (None=uset).
        # Default-semantik er PER NØGLE: bypass default OFF (kun hvis eksplicit True),
        # gate-enable default ON (kun disabled hvis eksplicit False).
        try:
            bypass = self._flag_reader("gate_kernel.bypass") is True
        except Exception:
            bypass = False
        if bypass and g.klass is GateClass.COGNITIVE:
            return Verdict(g.name, Decision.SKIP, "bypass", klass=g.klass)
        try:
            if self._flag_reader(g.flag_key) is False:
                return Verdict(g.name, Decision.SKIP, "disabled", klass=g.klass)
        except Exception:
            pass  # flag-læsning fejler → kør gaten (default-on)
        # isoleret kald m. timeout
        try:
            fut = self._pool.submit(g.fn, ctx)
            raw = fut.result(timeout=max(0.05, g.timeout_ms / 1000.0))
        except _FTimeout:
            return self._fail_verdict(g, "timeout")
        except Exception as e:
            return self._fail_verdict(g, f"error:{type(e).__name__}")
        v = _normalize(g, raw)
        v.latency_ms = int((time.monotonic() - t0) * 1000)
        return v

    def run_phase(self, phase: str, ctx: dict[str, Any]) -> list[Verdict]:
        """Kør alle gates i en fase isoleret; emit ÉT event; returnér verdicts.

        Kernel-niveau fail-open/closed: hvis selve run_phase kaster, fail-open'er
        kognitive (tom liste) men sikkerheds-gates deny'es eksplicit."""
        gates = self.gates_for(phase)
        verdicts: list[Verdict] = []
        for g in gates:
            try:
                verdicts.append(self._run_one(g, ctx))
            except Exception:
                verdicts.append(self._fail_verdict(g, "kernel-error"))
        try:
            self._emit("gate.evaluated", {
                "phase": phase,
                "verdicts": [
                    {"gate": v.gate, "decision": v.decision.value, "reason": v.reason,
                     "action": v.action, "latency_ms": v.latency_ms, "klass": v.klass.value}
                    for v in verdicts
                ],
                "aggregate": worst(verdicts).value,
            })
        except Exception:
            pass  # observabilitet må aldrig spærre turen
        return verdicts


def _normalize(g: _Gate, raw: Any) -> Verdict:
    """Tillad gates at returnere en færdig Verdict, et dict, eller None (=GREEN)."""
    if isinstance(raw, Verdict):
        return raw
    if raw is None:
        return Verdict(g.name, Decision.GREEN, klass=g.klass)
    if isinstance(raw, dict):
        dec = raw.get("decision")
        decision = dec if isinstance(dec, Decision) else {
            "green": Decision.GREEN, "yellow": Decision.YELLOW,
            "red": Decision.RED, "skip": Decision.SKIP,
        }.get(str(dec or "green").lower(), Decision.GREEN)
        return Verdict(g.name, decision, str(raw.get("reason") or ""),
                       action=str(raw.get("action") or "none"), klass=g.klass,
                       evidence=raw.get("evidence"))
    # ukendt returtype → behandl som GREEN men noter det
    return Verdict(g.name, Decision.GREEN, f"unparsed:{type(raw).__name__}", klass=g.klass)


def _default_flag_reader(flag_key: str) -> bool | None:
    """Returnér True/False hvis flag'et er EKSPLICIT sat i shared_cache, ellers None
    (uset). Kernen anvender per-nøgle-default (enable=on, bypass=off)."""
    try:
        from core.services import shared_cache
        val = shared_cache.get(f"flag:{flag_key}")
        if isinstance(val, dict) and "enabled" in val:
            return bool(val["enabled"])
        if isinstance(val, bool):
            return val
    except Exception:
        pass
    return None


def _default_emit(kind: str, payload: dict) -> None:
    try:
        from core.runtime import event_bus
        event_bus.publish(kind, payload)
    except Exception:
        pass


# Singleton — én kerne pr. proces.
_KERNEL: GateKernel | None = None


def kernel() -> GateKernel:
    global _KERNEL
    if _KERNEL is None:
        _KERNEL = GateKernel()
    return _KERNEL
