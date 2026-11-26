"""Sammenlign C1 mod B3 og A1 på run_v5 — tester H5's tre forudsigelser.

Forudsigelserne, skrevet i protokollen FØR kørslen:
1. C1 skal nå 12 eller flere af 40 (ellers er H5 falsificeret).
2. C1's fordel skal vokse med vinduet.
3. Ved w=120 skal C1 og B3 give samme svar celle for celle.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

RESULTS = Path("artifacts/exp_020_representation/run_v5/results.json")
THRESHOLD = 0.9


def main() -> None:
    data = json.loads(RESULTS.read_text())
    cells = data["cells"]
    print(f"celler: {len(cells)}  reps: {sorted({c['representation'] for c in cells})}")

    # ---- per repræsentation: hvor mange celler-vinduer klarer C3? ----
    print("\n=== H5's første forudsigelse: C1 skal naa 12+ ===")
    per_rep: dict[str, list[float]] = {}
    for cell in cells:
        for window, values in cell["windows"].items():
            rate = values.get("control_identity_rate")
            if rate is None:
                continue
            per_rep.setdefault(cell["representation"], []).append(rate)

    rows = []
    for rep, rates in per_rep.items():
        passing = sum(1 for r in rates if r >= THRESHOLD)
        rows.append((rep, passing, len(rates), statistics.median(rates)))
    for rep, passing, total, median in sorted(rows, key=lambda r: -r[1]):
        print(f"  {rep:26s} {passing:2d}/{total}  median C3={median:.3f}")

    # ---- forudsigelse 2: vokser C1's fordel med vinduet? ----
    print("\n=== H5's anden forudsigelse: C1's fordel skal vokse med vinduet ===")
    by_window: dict[str, dict[str, list[float]]] = {}
    for cell in cells:
        rep = cell["representation"]
        for window, values in cell["windows"].items():
            rate = values.get("control_identity_rate")
            if rate is None:
                continue
            by_window.setdefault(window, {}).setdefault(rep, []).append(rate)

    for window in sorted(by_window, key=int):
        r0 = by_window[window].get("R0_baseline", [])
        b3 = by_window[window].get("B3_shared_removed", [])
        c1 = by_window[window].get("C1_shared_removed_pc1", [])
        a1 = by_window[window].get("A1_first_difference", [])
        if not (r0 and b3 and c1):
            print(f"  w={window:>4s}  mangler data")
            continue
        def pct(values: list[float]) -> int:
            return sum(1 for v in values if v >= THRESHOLD)
        print(
            f"  w={window:>4s}  n={len(c1):2d}  R0={pct(r0):2d}  A1={pct(a1):2d}  "
            f"B3={pct(b3):2d}  C1={pct(c1):2d}  (C1-R0 = {pct(c1) - pct(r0):+d})"
        )

    # ---- forudsigelse 3: enes C1 og B3 ved w=120? ----
    print("\n=== H5's tredje forudsigelse: C1 ~ B3 ved w=120 ===")
    keyed: dict[tuple[str, str, str], dict[str, dict[str, float]]] = {}
    for cell in cells:
        key = (cell["source"], cell["expert_set"], cell["representation"])
        keyed[key] = cell["windows"]

    agree = disagree = 0
    for (source, set_name, rep), windows in keyed.items():
        if rep != "C1_shared_removed_pc1":
            continue
        other = keyed.get((source, set_name, "B3_shared_removed"))
        if not other:
            continue
        w = windows.get("120", {}).get("control_identity_rate")
        o = other.get("120", {}).get("control_identity_rate")
        if w is None or o is None:
            continue
        same_side = (w >= THRESHOLD) == (o >= THRESHOLD)
        if same_side:
            agree += 1
        else:
            disagree += 1
            print(f"  UENIG {source}/{set_name}: C1={w:.3f} B3={o:.3f}")
    print(f"  w=120: C1 og B3 enige i {agree} celler, uenige i {disagree}")

    # ---- kontrol: reproducerer R0 stadig 11? ----
    print("\n=== kontrol ===")
    print(f"  C0 (R0 = 11/40): {sum(1 for r in per_rep.get('R0_baseline', []) if r >= THRESHOLD)}/40")
    print(f"  verdict: {data.get('verdict')}")
    print(f"  hypoteser: {data.get('hypotheses')}")


if __name__ == "__main__":
    main()
