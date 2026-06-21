"""Fit-pass-katalog (§13.2): det maskinlæsbare resultat af kortlægningen af hver nerve.
Bruges senere som kilde til registrering. Fit = 'merge' (homogen, kan smelte sammen),
'instrument' (kald Centralen på stedet), 'leave' (er ikke en request-path-gate)."""
from __future__ import annotations

from dataclasses import dataclass

from core.services.gate_kernel import GateClass

_MECHANISMS = {"verdict", "inline", "daemon", "filter", "tool", "persistence", "validation"}
_FITS = {"merge", "instrument", "leave"}


@dataclass(frozen=True)
class NerveSpec:
    name: str
    cluster: str
    klass: GateClass
    mechanism: str     # se _MECHANISMS
    fit: str           # se _FITS
    location: str      # fil:linje eller modul


# Foreløbig: kun Loop- + Truth-clustrene er kortlagt (fra eksisterende Explore-mapping).
# Øvrige clusters fyldes når deres egne fit-passes køres (cluster-planerne).
CATALOG: tuple[NerveSpec, ...] = (
    # ── Loop-cluster ──
    NerveSpec("run_closure", "loop", GateClass.COGNITIVE, "daemon", "leave",
              "core/services/run_closure_gate.py"),
    NerveSpec("tool_budget", "loop", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/visible_runs.py:1754-2351"),
    NerveSpec("capability_cap", "loop", GateClass.COGNITIVE, "filter", "leave",
              "core/tools/tool_scoping.py"),
    NerveSpec("good_enough", "loop", GateClass.COGNITIVE, "tool", "leave",
              "core/services/good_enough_gate.py"),
    NerveSpec("checkpoints", "loop", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/agentic_checkpoints.py"),
    NerveSpec("presentation_invariant", "loop", GateClass.COGNITIVE, "validation", "instrument",
              "core/services/visible_runs.py:5758-5806"),
    # ── Truth-cluster (allerede adaptere) ──
    NerveSpec("claim_scanner", "truth", GateClass.COGNITIVE, "verdict", "merge",
              "core/services/claim_scanner.py"),
    NerveSpec("fact_gate", "truth", GateClass.COGNITIVE, "verdict", "merge",
              "core/services/fact_gate.py"),
    NerveSpec("diagnosis", "truth", GateClass.COGNITIVE, "verdict", "merge",
              "core/services/diagnosis_gate.py"),
)


def clusters() -> list[str]:
    return sorted({n.cluster for n in CATALOG})


def by_cluster(cluster: str) -> list[NerveSpec]:
    return [n for n in CATALOG if n.cluster == cluster]


def validate() -> list[str]:
    """Returnér liste af problemer (tom = grøn)."""
    problems: list[str] = []
    seen: set[str] = set()
    for n in CATALOG:
        if n.name in seen:
            problems.append(f"duplikat-nerve: {n.name}")
        seen.add(n.name)
        if n.mechanism not in _MECHANISMS:
            problems.append(f"{n.name}: ukendt mekanisme {n.mechanism!r}")
        if n.fit not in _FITS:
            problems.append(f"{n.name}: ukendt fit {n.fit!r}")
    return problems
