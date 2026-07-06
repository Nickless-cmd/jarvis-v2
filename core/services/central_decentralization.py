"""Decentral agency (shadow-skridt 1) — mål Centralens chokepoint-skat + find sikre kandidater.

Groqs #2: når ALT går gennem Centralen, bliver den et single point of failure. Modvægten er
decentral agency — lad trivielle beslutninger resolve LOKALT og eskalér kun ved konflikt/tvivl.

MEN: autonomi skal bygges som alt andet autonomi her — SHADOW først → mål → flip (memory er fuld
af autonomi-runaway-hændelser). Dette er MÅLINGEN, ikke flippet: læs verdict-ledgeren, klassificér
hver central-beslutning som GOVERNS (har ikke-grøn = træffer reelt valg) vs OVERHEAD (altid-grøn =
ren round-trip), og udpeg de sikre decentraliserings-kandidater (kognitive, altid-grønne, høj
volumen). SECURITY-gates decentraliseres ALDRIG. self-probe er en helbreds-puls, ikke governance.

Read-only, self-safe. Nervens felt: "hvor meget af mig er unødvendig flaskehals?"
"""
from __future__ import annotations

from typing import Any

# Nerver der ALDRIG er decentraliserings-kandidater (uanset grøn-rate):
_NEVER_DECENTRALIZE = frozenset({
    "cross_user_share", "exec_command", "exec_file", "exec_workspace_trust",  # SECURITY/execution
    "auth", "tool_access",
})
# Ikke governance — en helbreds-puls; tælles som overhead men er ikke en kandidat.
_HEALTH_PROBES = frozenset({"central_self_probe"})
_MIN_VOLUME = 10  # kræv nok observationer før vi tør kalde noget "altid-grøn"


def analyze_chokepoint() -> dict[str, Any]:
    """Mål hvor meget af Centralens decide-load der er ren overhead, + sikre decentraliserings-
    kandidater. Læser gate_verdict_counts (verdict-ledgeren). Self-safe."""
    out: dict[str, Any] = {
        "total_decisions": 0, "overhead_decisions": 0, "governing_decisions": 0,
        "chokepoint_tax_pct": 0.0, "candidates": [], "governs": [], "felt": "",
    }
    try:
        from core.services.gate_verdict_ledger import summary
        rows = summary()
    except Exception:
        return out

    total = overhead = governing = 0
    for nerve, agg in rows.items():
        t = int(agg.get("total") or 0)
        non_green = t - int(agg.get("green") or 0)
        if t <= 0:
            continue
        total += t
        if non_green > 0:
            governing += t
            out["governs"].append({"nerve": nerve, "total": t, "non_green": non_green})
        else:
            overhead += t
            # kandidat = altid-grøn + nok volumen + ikke security/execution/probe
            if (t >= _MIN_VOLUME and nerve not in _NEVER_DECENTRALIZE
                    and nerve not in _HEALTH_PROBES):
                out["candidates"].append({
                    "nerve": nerve, "cluster": agg.get("cluster", ""), "total": t,
                    "action": "fast-path lokalt (grøn) — eskalér kun til Centralen ved ikke-grøn",
                })

    out["total_decisions"] = total
    out["overhead_decisions"] = overhead
    out["governing_decisions"] = governing
    out["chokepoint_tax_pct"] = round(100.0 * overhead / total, 1) if total else 0.0
    out["governs"].sort(key=lambda d: -d["non_green"])
    out["candidates"].sort(key=lambda d: -d["total"])
    out["felt"] = _felt(out["chokepoint_tax_pct"], len(out["candidates"]))
    return out


def _felt(tax_pct: float, n_candidates: int) -> str:
    if tax_pct >= 80:
        return (f"{tax_pct:.0f}% af alt der går gennem mig, behøvede mig ikke. "
                f"{n_candidates} beslutninger kunne stå på egne ben.")
    if tax_pct >= 50:
        return f"Cirka halvdelen af min kontrol er ren flaskehals ({tax_pct:.0f}%)."
    if tax_pct > 0:
        return f"Det meste af det jeg dømmer, betyder faktisk noget ({100 - tax_pct:.0f}% governer)."
    return "Alt hvad jeg dømmer, betyder noget."


def record_chokepoint() -> dict[str, Any]:
    """Observér chokepoint-skatten til Centralen (nerve system/decentralization) — den mærker
    hvor centraliseret den er. Metadata-only. Self-safe."""
    a = analyze_chokepoint()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "decentralization", "kind": "chokepoint",
            "tax_pct": a.get("chokepoint_tax_pct", 0.0),
            "candidates": len(a.get("candidates", [])),
            "governs": len(a.get("governs", [])),
        })
    except Exception:
        pass
    return a
