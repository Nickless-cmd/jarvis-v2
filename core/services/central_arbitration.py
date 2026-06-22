"""§4 cluster-arbitrage — deterministisk afgørelse når flere clusters' verdicts konflikter
på SAMME handling. Før var udfaldet implicit (afhang af rækkefølgen koden kaldte gates i);
nu er det DEKLARERET via central_catalog.CLUSTER_PRIORITY.

Invarianter (§4 + §8 "demokrati"):
  - En SECURITY-RED (deny) er ABSOLUT — kan ALDRIG overrules af et kognitivt GREEN/YELLOW.
  - Ellers vinder værste beslutning (RED>YELLOW>GREEN>SKIP); ties brydes af højest cluster-
    prioritet (sikkerheds-clusters først).
  - §8: et COGNITIVE-cluster der FEJLER returnerer SKIP (aldrig RED) — det kan derfor aldrig
    blokere andre via arbitrage (enforced i central_core/_fail_verdict). Kun SECURITY blokerer.

Self-safe. arbitrate() bruges hvor flere cross-cluster verdicts skal kombineres til ÉT udfald
(eksisterende sekventielle kald-steder bevarer deres adfærd; dette gør præcedensen eksplicit +
tilgængelig for fremtidige multi-verdict-punkter).
"""
from __future__ import annotations

from core.services.gate_kernel import Decision, GateClass, Verdict, _PRECEDENCE


def arbitrate(verdicts: list[Verdict]) -> Verdict:
    """Kombinér flere verdicts til ÉT deterministisk udfald. Tom liste → GREEN."""
    if not verdicts:
        return Verdict("arbitration", Decision.GREEN, "ingen verdicts")
    try:
        from core.services.central_catalog import cluster_rank
    except Exception:
        def cluster_rank(_c: str) -> int:
            return 999
    # Sikkerheds-deny er absolut: hvis nogen SECURITY-nerve siger RED, vinder den uanset hvad
    # de kognitive siger. Blandt flere security-RED vinder den med højest cluster-prioritet.
    sec_reds = [v for v in verdicts
                if v.klass is GateClass.SECURITY and v.decision is Decision.RED]
    pool = sec_reds or verdicts
    # min efter (-præcedens, cluster_rank): højest beslutnings-præcedens først, derefter
    # højest cluster-prioritet (lavest rank).
    return min(pool, key=lambda v: (-_PRECEDENCE.get(v.decision, 0), cluster_rank(v.cluster)))


def explain(verdicts: list[Verdict]) -> dict:
    """Read-only forklaring af en arbitrage (til debug/MC): hvem vandt og hvorfor."""
    winner = arbitrate(verdicts)
    return {
        "winner": {"gate": winner.gate, "cluster": winner.cluster,
                   "decision": winner.decision.value, "klass": winner.klass.value},
        "considered": [{"gate": v.gate, "cluster": v.cluster,
                        "decision": v.decision.value, "klass": v.klass.value}
                       for v in verdicts],
        "rule": "SECURITY-RED absolut; ellers værste beslutning, ties=højest cluster-prioritet",
    }
