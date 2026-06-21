"""Gate-eval & paritets-harness (unified-gate Task 0.2).

To formål:
1. **Paritet** (B-H): bevis at en NY cluster-gate giver SAMME beslutning som de gamle
   gates på et fixtursæt, FØR de gamle fjernes. `parity(turns, old_fn, new_fn)`.
2. **Måling** (TruthGate): kør en gate over mærkede turns og mål ramt/forbi mod
   ground-truth. `score(turns, gate_fn, key="confab")`.

En "turn" er en dict med mindst `ctx` (det gates får) + valgfri forventninger
(`expect_decision`, ground-truth-labels). Holdes bevidst simpelt og afhængigheds-frit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from core.services.gate_kernel import Decision, Verdict, _normalize, _Gate, GateClass


def _as_verdict(name: str, raw: Any) -> Verdict:
    """Normalisér en gate-returværdi til Verdict (genbruger kernens parser)."""
    return _normalize(_Gate(name, "", lambda c: raw, GateClass.COGNITIVE, 1000, ""), raw)


def replay(turns: list[dict], gate_fn: Callable[[dict], Any], *, name: str = "gate") -> list[Verdict]:
    """Kør gate_fn over hver turns `ctx` og returnér normaliserede verdicts."""
    out: list[Verdict] = []
    for t in turns:
        ctx = t.get("ctx", t)
        try:
            out.append(_as_verdict(name, gate_fn(ctx)))
        except Exception as e:
            out.append(Verdict(name, Decision.SKIP, f"error:{type(e).__name__}"))
    return out


def parity(turns: list[dict], old_fn: Callable[[dict], Any],
           new_fn: Callable[[dict], Any]) -> dict[str, Any]:
    """Sammenlign to gate-implementeringer pr. turn. Grøn paritet = nul mismatches."""
    old = replay(turns, old_fn, name="old")
    new = replay(turns, new_fn, name="new")
    mismatches = []
    for i, (o, n) in enumerate(zip(old, new)):
        if o.decision is not n.decision:
            mismatches.append({"index": i, "old": o.decision.value, "new": n.decision.value,
                               "ctx": turns[i].get("ctx", turns[i])})
    return {"total": len(turns), "matches": len(turns) - len(mismatches),
            "mismatches": mismatches, "parity": not mismatches}


def score(turns: list[dict], gate_fn: Callable[[dict], Any], *,
          label_key: str = "expect_decision") -> dict[str, Any]:
    """Mål en gates beslutning mod ground-truth-labels pr. turn."""
    hit = miss = labeled = 0
    confusion: list[dict] = []
    for v, t in zip(replay(turns, gate_fn), turns):
        want = t.get(label_key)
        if want is None:
            continue
        labeled += 1
        if v.decision.value == str(want):
            hit += 1
        else:
            miss += 1
            confusion.append({"want": str(want), "got": v.decision.value,
                              "ctx": t.get("ctx", t)})
    rate = (hit / labeled) if labeled else 0.0
    return {"labeled": labeled, "hit": hit, "miss": miss,
            "accuracy": round(rate, 3), "confusion": confusion}


def load_fixtures(path: str | Path) -> list[dict]:
    """Læs et jsonl-fixturset (én turn pr. linje). Tomme/kommenterede linjer ignoreres."""
    rows: list[dict] = []
    p = Path(path)
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        try:
            rows.append(json.loads(s))
        except Exception:
            continue
    return rows
