"""Cross-cluster korrelation — saml ALT hvad der skete for ét run_id på tværs af ALLE clusters
til ÉN klar tidslinje: hvor, hvad, hvilke clusters, HVOR filmen knækker, og hvilke FILER der
relaterer. I stedet for at læse 10 steder får du én linje.

Fundamentet for orkestrering: TODO-aggregering, autonom-supervision og adaptiv læring bygger
alle på at kunne følge ét run på tværs af clusters. Bruger trace-sinkens records_for_run +
katalogets nerve_location (fil:linje). Self-safe; ring-buffer → virker for nylige runs.
"""
from __future__ import annotations

from typing import Any


def correlate(run_id: str) -> dict[str, Any]:
    """Saml ét run_id's fulde rejse på tværs af clusters. break_point = hvor filmen knækker
    (første RED-beslutning eller error). files = de katalog-filer der relaterer til runnet."""
    rid = str(run_id or "")
    out: dict[str, Any] = {"run_id": rid, "events": 0, "timeline": [],
                           "clusters_touched": [], "files": [], "break_point": None}
    if not rid:
        return out
    try:
        from core.services import central_trace
        from core.services.central_catalog import nerve_location
        recs = central_trace.sink().records_for_run(rid)
    except Exception:
        return out
    timeline: list[dict[str, Any]] = []
    for r in recs:
        nerve = str(getattr(r, "nerve", "") or "")
        timeline.append({
            "cluster": str(getattr(r, "cluster", "") or ""), "nerve": nerve,
            "kind": str(getattr(r, "kind", "") or ""),
            "decision": str(getattr(r, "decision", "") or ""),
            "reason": str(getattr(r, "reason", "") or "")[:200],
            "latency_ms": int(getattr(r, "latency_ms", 0) or 0),
            "file": nerve_location(nerve),
        })
    break_point = next((t for t in timeline
                        if t["decision"] == "red" or t["kind"] == "error"), None)
    out.update({
        "events": len(timeline), "timeline": timeline,
        "clusters_touched": sorted({t["cluster"] for t in timeline if t["cluster"]}),
        "files": sorted({t["file"] for t in timeline if t["file"]}),
        "break_point": break_point,
    })
    return out


def recent_broken_runs(*, window: int = 500) -> list[dict[str, Any]]:
    """Nylige run_ids hvor filmen knækkede (RED/error) → til TODO/debugging. Nyeste pr. run.
    Self-safe."""
    broken: dict[str, dict[str, Any]] = {}
    try:
        from core.services import central_trace
        from core.services.central_catalog import nerve_location
        for r in central_trace.sink().recent(limit=window):
            if str(getattr(r, "decision", "")) == "red" or str(getattr(r, "kind", "")) == "error":
                rid = str(getattr(r, "run_id", "") or "")
                if rid and rid not in broken:
                    nerve = str(getattr(r, "nerve", "") or "")
                    broken[rid] = {
                        "run_id": rid, "cluster": str(getattr(r, "cluster", "") or ""),
                        "nerve": nerve, "reason": str(getattr(r, "reason", "") or "")[:160],
                        "file": nerve_location(nerve),
                    }
    except Exception:
        pass
    return list(broken.values())
