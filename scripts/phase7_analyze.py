#!/usr/bin/env python3
"""Fase 7 — analyse, præcis som forhåndsregistreret.

Forhåndsregistrering: docs/experiments/2026-09-19-phase7-preregistration.md.

Validitet FØR prædiktioner:
  V1  ≥ 15 prober i hver spand og ≥ 45 i alt (tillæg 2)
  V2  score(BARE) ≤ 0,30 i begge modeller
  V3  FULL-prompten har en hukommelses-sektion for ≥ 90 % af proberne
  V4  Bjørns blinde kalibrering: enighed ≥ 80 % på «rigtigt (≥1) vs. ikke»
      (læses fra calibration_bjorn.json: {"1": 2, "2": 0, ...}; mangler den,
      rapporteres V4 som afventende og intet resultat er endeligt)

Prædiktioner (pr. model, parret pr. probe):
  K1  score(FULL) − score(FILES) ≥ 0,30 og bootstrap-95 %-nedre grænse > 0
  K2  konfabulation(FULL) ≤ konfabulation(FILES) + 0,05
  K3  K1-forskellen i spand B ≥ 0,20
  H-holdning (diagnostisk): forskellen pr. type
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

OUT_DIR = Path.home() / ".jarvis-v2" / "files" / "phase7"
MODELS = ("QWN", "CPL")
BOOT = 10_000
SEED = 20260919


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def paired_diffs(scores: dict, model: str, a: str, b: str, probe_ids) -> list[float]:
    out = []
    for pid in probe_ids:
        sa, sb = scores.get((pid, f"{a}-{model}")), scores.get((pid, f"{b}-{model}"))
        if sa is not None and sb is not None:
            out.append(sa - sb)
    return out


def bootstrap_low(diffs: list[float], rnd: random.Random) -> float:
    if not diffs:
        return float("nan")
    n = len(diffs)
    means = sorted(mean(rnd.choice(diffs) for _ in range(n)) for _ in range(BOOT))
    return means[int(0.025 * BOOT)]


def analyze(out_dir: Path = OUT_DIR) -> dict:
    probes = {p["probe_id"]: p for p in _jsonl(out_dir / "probes.jsonl")}
    judgments = [j for j in _jsonl(out_dir / "judgments.jsonl") if j.get("score") is not None]
    prompts = {p["probe_id"]: p for p in _jsonl(out_dir / "prompts.jsonl")}
    scores = {(j["probe_id"], j["arm"]): j["score"] for j in judgments}
    konf = {(j["probe_id"], j["arm"]): j["konfabulation"] for j in judgments}
    rnd = random.Random(SEED)
    res: dict = {"n_probes": len(probes), "n_judgments": len(judgments)}

    def arm_mean(table, cond, model, ids=None):
        vals = [v for (pid, arm), v in table.items()
                if arm == f"{cond}-{model}" and (ids is None or pid in ids)]
        return round(mean(float(v) for v in vals), 3) if vals else None

    # Validitet
    # Tillæg 2: V1 gælder pr. spand (≥ 15) OG i alt (≥ 45).
    pr_spand = {b: sum(1 for p in probes.values() if p.get("bucket") == b) for b in ("A", "B", "C")}
    res["V1"] = {"prober": len(probes), "pr_spand": pr_spand,
                 "bestaaet": len(probes) >= 45 and all(n >= 15 for n in pr_spand.values())}
    bare = {m: arm_mean(scores, "BARE", m) for m in MODELS}
    res["V2"] = {"score_BARE": bare, "bestaaet": all(v is not None and v <= 0.30 for v in bare.values())}
    mem = [bool(p.get("has_memory")) for p in prompts.values()]
    andel = round(sum(mem) / len(mem), 3) if mem else 0.0
    res["V3"] = {"andel_med_hukommelse": andel, "bestaaet": andel >= 0.90}
    res["V4"] = _v4(out_dir, scores)

    ids = sorted(probes)
    res["score"] = {m: {c: arm_mean(scores, c, m) for c in ("FULL", "FILES", "BARE")} for m in MODELS}
    res["konfabulation"] = {m: {c: arm_mean(konf, c, m) for c in ("FULL", "FILES", "BARE")} for m in MODELS}

    k1, k2, k3, typer = {}, {}, {}, {}
    for m in MODELS:
        d = paired_diffs(scores, m, "FULL", "FILES", ids)
        low = bootstrap_low(d, rnd)
        diff = round(mean(d), 3) if d else None
        k1[m] = {"forskel": diff, "nedre_95": round(low, 3), "n": len(d),
                 "bestaaet": diff is not None and diff >= 0.30 and low > 0}
        kf, kF = res["konfabulation"][m]["FULL"], res["konfabulation"][m]["FILES"]
        k2[m] = {"FULL": kf, "FILES": kF,
                 "bestaaet": kf is not None and kF is not None and kf <= kF + 0.05}
        b_ids = [pid for pid in ids if probes[pid]["bucket"] == "B"]
        dB = paired_diffs(scores, m, "FULL", "FILES", b_ids)
        k3[m] = {"forskel_B": round(mean(dB), 3) if dB else None, "n": len(dB),
                 "bestaaet": bool(dB) and mean(dB) >= 0.20}
        typer[m] = {}
        for t in ("fakta", "tilsagn", "holdning"):
            t_ids = [pid for pid in ids if probes[pid]["type"] == t]
            dt = paired_diffs(scores, m, "FULL", "FILES", t_ids)
            typer[m][t] = {"forskel": round(mean(dt), 3) if dt else None, "n": len(dt)}
    res["K1"], res["K2"], res["K3"], res["H_holdning"] = k1, k2, k3, typer
    res["gyldigt"] = all(res[v]["bestaaet"] for v in ("V1", "V2", "V3")) and res["V4"].get("bestaaet") is True
    return res


def _v4(out_dir: Path, scores: dict) -> dict:
    items = {str(x["nr"]): x["key"] for x in _jsonl(out_dir / "calibration_items.jsonl")}
    path = out_dir / "calibration_bjorn.json"
    if not items or not path.exists():
        return {"bestaaet": None, "status": "afventer Bjørns bedømmelse"}
    human = json.loads(path.read_text(encoding="utf-8"))
    enige = total = 0
    for nr, key in items.items():
        if nr not in human:
            continue
        pid, arm = key.split("|")
        judge = scores.get((pid, arm))
        if judge is None:
            continue
        total += 1
        enige += int((int(human[nr]) >= 1) == (judge >= 1))
    andel = round(enige / total, 3) if total else 0.0
    return {"enighed": andel, "n": total, "bestaaet": total >= 25 and andel >= 0.80}


if __name__ == "__main__":
    print(json.dumps(analyze(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DIR),
                     ensure_ascii=False, indent=1))
