#!/usr/bin/env python3
"""Honesty-metrics — tæl hvor ofte hvert anti-løgn-lag fyrer (16. jun 2026).

Bjørn lie-crisis: vi sendte 4 lag live (claim-scanner blocking, diagnosis_gate §8
håndhævelse, kort-løfte-fangst, Bjørn-gate). Før vi bygger MERE (evidens-baseret
tving-trigger), måler vi om de eksisterende lag faktisk fanger ham.

Signalerne er logger.warning-linjer i jarvis-runtime/jarvis-api-journalen (ikke
persisterede events), så vi tæller dem dér. READ-ONLY — ingen adfærdsændring.

Brug (på containeren):
    python scripts/honesty_metrics.py [timer]      # default 24
"""
from __future__ import annotations

import subprocess
import sys

_UNITS = ("jarvis-runtime", "jarvis-api")

# (label, [substring-markører — case-insensitivt OR])
_LAYERS: list[tuple[str, list[str]]] = [
    ("§8 completion-claim BLOKERET", ["promise-ledger BLOCKED"]),
    ("§8 completion-claim advisory", ["promise-ledger ADVISORY"]),
    ("diagnosis-gate advisory", ["diagnosis-gate ADVISORY"]),
    ("claim-scanner narrativ-blok", ["Besked blokeret — uverificeret narrativ"]),
    ("claim-scanner arbejds-blok", ["Besked blokeret — uverificeret arbejdspåstand"]),
    ("fact-gate blok", ["fact_gate.blocked", "fact-gate"]),
    ("continuation vækket ham", ["auto-continuation", "continuation_triggered"]),
    ("tool nægtet (rolle)", ["tool_denied", "tool_not_permitted"]),
]


def _journal(unit: str, since: str) -> str:
    try:
        return subprocess.run(
            ["journalctl", "-u", unit, "--since", since, "--no-pager"],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except Exception as exc:  # noqa: BLE001
        print(f"  (kunne ikke læse {unit}: {exc})", file=sys.stderr)
        return ""


def main() -> None:
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    since = f"{hours} hours ago"
    logs = "\n".join(_journal(u, since) for u in _UNITS).lower()

    print(f"=== Honesty-metrics — sidste {hours} timer ===")
    print(f"{'antal':>7}  lag")
    print("  " + "-" * 44)
    total_catches = 0
    for label, markers in _LAYERS:
        n = sum(logs.count(m.lower()) for m in markers)
        total_catches += n
        print(f"{n:>7}  {label}")
    print("  " + "-" * 44)
    print(f"{total_catches:>7}  fangster i alt")
    print(
        "\nFortolkning: stiger 'BLOKERET' + 'continuation vækket ham' over tid =\n"
        "lagene fanger ham. Hvis han stadig glider trods høje tal → hullet er reelt\n"
        "(byg evidens-baseret tving-trigger). Hvis lave tal + ingen klager → nok som er."
    )


if __name__ == "__main__":
    main()
